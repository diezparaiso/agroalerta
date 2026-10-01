import asyncio
import httpx
from fastapi.testclient import TestClient

from app.main import app
from app.api.sigpac import search_recintos

client = TestClient(app)


def test_sigpac_health_checks_configured_collection(monkeypatch):
    monkeypatch.setenv("SIGPAC_OGC_API_URL", "https://sigpac-hubcloud.es/ogcapi")
    monkeypatch.setenv("SIGPAC_OGC_COLLECTION", "recintos")
    response = client.get("/api/v1/sigpac/health")
    assert response.status_code == 200
    assert response.json()["configured"] is True
    assert response.json()["provider"] == "SIGPAC HubCloud"


def test_sigpac_recintos_rejects_invalid_bbox(monkeypatch):
    monkeypatch.setenv("SIGPAC_OGC_API_URL", "https://sigpac-hubcloud.es/ogcapi")
    for bbox in ("bad", "1,2,3", "5,2,3,4", "-6,95,-5,96"):
        response = client.get("/api/v1/sigpac/recintos", params={"bbox": bbox})
        assert response.status_code == 422


def test_sigpac_recintos_queries_ogc_api_and_returns_geojson(monkeypatch):
    monkeypatch.setenv("SIGPAC_OGC_API_URL", "https://sigpac-hubcloud.es/ogcapi")
    monkeypatch.setenv("SIGPAC_OGC_COLLECTION", "recintos")
    feature_collection = {
        "type": "FeatureCollection",
        "features": [{
            "type": "Feature",
            "id": "recinto.1",
            "geometry": {"type": "Polygon", "coordinates": [[[-6, 37], [-5.9, 37], [-5.9, 37.1], [-6, 37]]]},
            "properties": {"provincia": "Sevilla", "municipio": "Demo", "recinto": 1},
        }],
        "links": [],
    }

    def handler(request):
        assert request.url.path == "/ogcapi/collections/recintos/items"
        assert request.url.params["f"] == "json"
        assert request.url.params["bbox"] == "-6.1,37.0,-5.8,37.5"
        assert request.url.params["limit"] == "100"
        return httpx.Response(200, json=feature_collection)

    original_client = httpx.AsyncClient

    class MockAsyncClient:
        def __init__(self, *args, **kwargs):
            self.client = original_client(transport=httpx.MockTransport(handler), *args, **kwargs)

        async def __aenter__(self):
            await self.client.__aenter__()
            return self

        async def __aexit__(self, *args):
            return await self.client.__aexit__(*args)

        async def get(self, *args, **kwargs):
            return await self.client.get(*args, **kwargs)

    monkeypatch.setattr("app.api.sigpac.httpx.AsyncClient", MockAsyncClient)
    result = asyncio.run(search_recintos(bbox="-6.1,37,-5.8,37.5", limit=100))
    assert result["type"] == "FeatureCollection"
    assert result["numberReturned"] == 1
    assert result["source"] == "sigpac-hubcloud-ogcapi"
    assert result["features"][0]["geometry"]["type"] == "Polygon"


def test_sigpac_import_persists_geometry_and_deduplicates(monkeypatch, tmp_path):
    from app.api import sigpac

    monkeypatch.setenv("AGROALERTA_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("SIGPAC_OGC_API_URL", "https://sigpac-hubcloud.es/ogcapi")
    monkeypatch.setenv("SIGPAC_OGC_COLLECTION", "recintos")
    feature_collection = {
        "type": "FeatureCollection",
        "features": [{
            "type": "Feature",
            "id": "recinto.123",
            "geometry": {"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 0]]]},
            "properties": {"provincia": "Sevilla", "recinto": 123},
        }],
    }

    async def fake_search_recintos(bbox, limit):
        return {**feature_collection, "numberReturned": 1, "bbox": [-6.1, 37.0, -5.8, 37.5], "source": "sigpac-hubcloud-ogcapi"}

    monkeypatch.setattr(sigpac, "search_recintos", fake_search_recintos)
    request = {"bbox": "-6.1,37.0,-5.8,37.5", "limit": 100}
    first = client.post("/api/v1/sigpac/importar", json=request)
    assert first.status_code == 200
    assert first.json()["imported"] == 1
    assert first.json()["updated"] == 0

    second = client.post("/api/v1/sigpac/importar", json=request)
    assert second.status_code == 200
    assert second.json()["imported"] == 0
    assert second.json()["updated"] == 1

    listed = client.get("/api/v1/sigpac/importados")
    assert listed.status_code == 200
    body = listed.json()
    assert body["total"] == 1
    assert body["features"][0]["geometry"]["type"] == "Polygon"
    assert body["features"][0]["properties"]["provincia"] == "Sevilla"


def test_sigpac_import_rejects_selected_ids_outside_bbox(monkeypatch, tmp_path):
    from app.api import sigpac

    monkeypatch.setenv("AGROALERTA_DB_PATH", str(tmp_path / "selected.db"))
    feature_collection = {
        "type": "FeatureCollection",
        "features": [{
            "type": "Feature",
            "id": "recinto.123",
            "geometry": {"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 0]]]},
            "properties": {"recinto": 123},
        }],
    }

    async def fake_search_recintos(bbox, limit):
        return {**feature_collection, "numberReturned": 1, "bbox": [-6.1, 37.0, -5.8, 37.5], "source": "sigpac-hubcloud-ogcapi"}

    monkeypatch.setattr(sigpac, "search_recintos", fake_search_recintos)
    response = client.post(
        "/api/v1/sigpac/importar",
        json={"bbox": "-6.1,37.0,-5.8,37.5", "limit": 100, "feature_ids": ["recinto.no-existe"]},
    )
    assert response.status_code == 422
