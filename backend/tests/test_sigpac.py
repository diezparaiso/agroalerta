import json

import httpx
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.main import app
from app.api.sigpac import search_recintos


client = TestClient(app)


def test_sigpac_health_reports_disabled_without_configuration(monkeypatch):
    monkeypatch.delenv("SIGPAC_WFS_URL", raising=False)
    monkeypatch.delenv("SIGPAC_WFS_TYPENAME", raising=False)
    response = client.get("/api/v1/sigpac/health")
    assert response.status_code == 200
    assert response.json()["configured"] is False


def test_sigpac_recintos_requires_configuration(monkeypatch):
    monkeypatch.delenv("SIGPAC_WFS_URL", raising=False)
    monkeypatch.delenv("SIGPAC_WFS_TYPENAME", raising=False)
    response = client.get("/api/v1/sigpac/recintos", params={"bbox": "-6.1,37.2,-5.8,37.5"})
    assert response.status_code == 503


@pytest.mark.parametrize("bbox", ["bad", "1,2,3", "5,2,3,4", "-6,95,-5,96"])
def test_sigpac_recintos_rejects_invalid_bbox(monkeypatch, bbox):
    monkeypatch.setenv("SIGPAC_WFS_URL", "https://example.invalid/geoserver/wfs")
    monkeypatch.setenv("SIGPAC_WFS_TYPENAME", "sigpac:recintos")
    response = client.get("/api/v1/sigpac/recintos", params={"bbox": bbox})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_sigpac_recintos_returns_geojson_from_upstream(monkeypatch):
    monkeypatch.setenv("SIGPAC_WFS_URL", "https://sigpac.example.test/wfs")
    monkeypatch.setenv("SIGPAC_WFS_TYPENAME", "sigpac:recintos")
    feature_collection = {
        "type": "FeatureCollection",
        "features": [{
            "type": "Feature",
            "id": "recinto.1",
            "geometry": {"type": "Polygon", "coordinates": [[[-6, 37], [-5.9, 37], [-5.9, 37.1], [-6, 37]]]},
            "properties": {"provincia": "Sevilla", "municipio": "Demo", "recinto": 1},
        }],
    }

    def handler(request):
        assert request.url.params["request"] == "GetFeature"
        assert request.url.params["typeNames"] == "sigpac:recintos"
        assert request.url.params["bbox"] == "-6.1,37.0,-5.8,37.5,EPSG:4326"
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
    result = await search_recintos(bbox="-6.1,37,-5.8,37.5", limit=100)
    assert result["type"] == "FeatureCollection"
    assert result["numberReturned"] == 1
    assert result["features"][0]["geometry"]["type"] == "Polygon"



def test_sigpac_import_persists_and_deduplicates_features(monkeypatch, tmp_path):
    from app.api import sigpac

    monkeypatch.setenv("AGROALERTA_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("SIGPAC_WFS_URL", "https://sigpac.example.test/wfs")
    monkeypatch.setenv("SIGPAC_WFS_TYPENAME", "sigpac:recintos")
    feature_collection = {
        "type": "FeatureCollection",
        "features": [{
            "type": "Feature",
            "id": "recinto.123",
            "geometry": {"type": "Polygon", "coordinates": []},
            "properties": {"provincia": "Sevilla", "recinto": 123},
        }],
    }

    async def fake_search_recintos(bbox, limit):
        return {**feature_collection, "numberReturned": 1, "bbox": [-6.1, 37.0, -5.8, 37.5]}

    monkeypatch.setattr(sigpac, "search_recintos", fake_search_recintos)
    first = client.post(
        "/api/v1/sigpac/importar",
        json={"bbox": "-6.1,37.0,-5.8,37.5", "limit": 100},
        headers={"Authorization": "Bearer test-owner"},
    )
    assert first.status_code == 200
    assert first.json()["imported"] == 1
    assert first.json()["updated"] == 0

    second = client.post(
        "/api/v1/sigpac/importar",
        json={"bbox": "-6.1,37.0,-5.8,37.5", "limit": 100},
        headers={"Authorization": "Bearer test-owner"},
    )
    assert second.status_code == 200
    assert second.json()["imported"] == 0
    assert second.json()["updated"] == 1

    listed = client.get("/api/v1/sigpac/importados", headers={"Authorization": "Bearer test-owner"})
    assert listed.status_code == 200
    body = listed.json()
    assert body["total"] == 1
    assert body["features"][0]["geometry"]["type"] == "Polygon"
    assert body["features"][0]["properties"]["provincia"] == "Sevilla"
