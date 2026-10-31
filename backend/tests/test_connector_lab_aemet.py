from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.api import connector_lab
from app.main import app

client = TestClient(app)


def test_aemet_without_key_is_reported_as_not_configured(monkeypatch):
    monkeypatch.setattr(
        connector_lab,
        "settings",
        SimpleNamespace(aemet_api_key="", aemet_base_url="https://opendata.aemet.es/opendata/api"),
    )

    response = client.get("/api/v1/connector-lab/aemet")

    assert response.status_code == 200
    body = response.json()
    assert body["connector"] == "AEMET"
    assert body["status"] == "not_configured"
    assert body["configured"] is False
    assert body["raw_data"] is None
    assert "AEMET_API_KEY" in body["message"]


def test_aemet_with_key_returns_live_client_payload(monkeypatch):
    class FakeAemetClient:
        async def get_daily_forecast(self, municipality_code):
            assert municipality_code == "41091"
            return [{"fecha": "2026-10-31", "estado_cielo": "Despejado"}]

        async def aclose(self):
            pass

    monkeypatch.setattr(
        connector_lab,
        "settings",
        SimpleNamespace(
            aemet_api_key="test-key-not-a-real-secret",
            aemet_base_url="https://opendata.aemet.es/opendata/api",
        ),
    )
    monkeypatch.setattr(connector_lab, "AemetClient", FakeAemetClient)

    response = client.get("/api/v1/connector-lab/aemet?municipality_code=41091")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "connected"
    assert body["record_count"] == 1
    assert body["raw_data"][0]["fecha"] == "2026-10-31"
    assert "test-key-not-a-real-secret" not in response.text
