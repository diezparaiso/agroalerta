from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.api import connector_lab
from app.main import app

client = TestClient(app)


class FakeRiaClient:
    async def list_stations(self):
        return [{"codigoEstacion": "12", "nombre": "Estacion de prueba"}]

    async def aclose(self):
        pass


def test_ria_lab_returns_original_station_fields(monkeypatch):
    monkeypatch.setattr(connector_lab, "RiaIfapaClient", FakeRiaClient)
    response = client.get("/api/v1/connector-lab/ria")
    assert response.status_code == 200
    body = response.json()
    assert body["connector"] == "RIA-IFAPA"
    assert body["status"] == "connected"
    assert body["raw_data"][0]["codigoEstacion"] == "12"


def test_aemet_without_key_is_not_configured(monkeypatch):
    monkeypatch.setattr(connector_lab, "settings", SimpleNamespace(
        aemet_api_key="", aemet_base_url="https://opendata.aemet.es/opendata/api",
        ria_base_url="https://example.test"))
    response = client.get("/api/v1/connector-lab/aemet")
    assert response.status_code == 200
    assert response.json()["status"] == "not_configured"
    assert response.json()["configured"] is False


def test_aemet_key_is_never_returned(monkeypatch):
    secret = "unit-test-only-secret"

    class FakeAemetClient:
        async def get_daily_forecast(self, municipality_code):
            assert municipality_code == "41091"
            return [{"fecha": "2026-10-31"}]

        async def aclose(self):
            pass

    monkeypatch.setattr(connector_lab, "settings", SimpleNamespace(
        aemet_api_key=secret, aemet_base_url="https://opendata.aemet.es/opendata/api",
        ria_base_url="https://example.test"))
    monkeypatch.setattr(connector_lab, "AemetClient", FakeAemetClient)
    response = client.get("/api/v1/connector-lab/aemet?municipality_code=41091")
    assert response.status_code == 200
    assert response.json()["status"] == "connected"
    assert secret not in response.text


def test_mapa_and_sigpac_are_explicitly_pending():
    for connector in ("mapa", "sigpac"):
        response = client.get(f"/api/v1/connector-lab/{connector}")
        assert response.status_code == 200
        assert response.json()["status"] == "not_implemented"
