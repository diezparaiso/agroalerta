from fastapi.testclient import TestClient

from app.api import connector_lab
from app.main import app

client = TestClient(app)


class _FakeRiaClient:
    async def list_stations(self):
        return [
            {"codigoEstacion": "12", "nombre": "Estacion de prueba",
             "activa": True, "provincia": {"id": 41}},
        ]

    async def aclose(self):
        pass


def test_ria_lab_returns_original_service_fields(monkeypatch):
    monkeypatch.setattr(connector_lab, "RiaIfapaClient", _FakeRiaClient)

    response = client.get("/api/v1/connector-lab/ria")

    assert response.status_code == 200
    body = response.json()
    assert body["connector"] == "RIA-IFAPA"
    assert body["status"] == "connected"
    assert body["record_count"] == 1
    assert body["raw_data"][0]["codigoEstacion"] == "12"
    assert body["raw_data"][0]["provincia"]["id"] == 41


def test_mapa_lab_does_not_claim_direct_connection():
    response = client.get("/api/v1/connector-lab/mapa")

    assert response.status_code == 200
    assert response.json()["status"] == "not_implemented"
    assert response.json()["configured"] is False


def test_sigpac_lab_does_not_claim_direct_connection():
    response = client.get("/api/v1/connector-lab/sigpac")

    assert response.status_code == 200
    assert response.json()["status"] == "not_implemented"
    assert response.json()["configured"] is False


def test_unknown_connector_returns_404():
    response = client.get("/api/v1/connector-lab/not-a-connector")

    assert response.status_code == 404
