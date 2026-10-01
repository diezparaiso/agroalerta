import pytest
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient

from app.main import app, storage
from app.domain.disease_rules import evaluate_risk
from app.schemas import TelemetryCreate

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_database() -> None:
    with storage._connect() as connection:
        connection.execute('DELETE FROM risk_snapshots')
        connection.execute('DELETE FROM telemetry')
        connection.execute('DELETE FROM devices')
        connection.execute('DELETE FROM field_reports')
        connection.execute('DELETE FROM parcels')


def test_health() -> None:
    assert client.get("/health").json()["status"] == "ok"


def test_integrations_health_hides_credentials() -> None:
    response = client.get('/health/integrations')
    assert response.status_code == 200
    body = response.json()
    assert body['aemet']['mode'] in {'live', 'fallback'}
    assert 'api_key' not in str(body).lower()


def test_parcel_risk_flow() -> None:
    response = client.post(
        "/api/v1/parcels",
        json={
            "label": "Olivar de prueba",
            "latitude": 37.39,
            "longitude": -5.99,
            "crop_type": "olivar",
            "comarca": "Campina de Sevilla",
        },
    )
    assert response.status_code == 201
    parcel_id = response.json()["id"]
    risk = client.get(f"/api/v1/disease-risk/{parcel_id}")
    assert risk.status_code == 200
    assert risk.json()[0]["disease_code"] == "repilo"


def test_parcels_are_isolated_by_bearer_token() -> None:
    first = client.post(
        "/api/v1/parcels",
        headers={"Authorization": "Bearer user-a"},
        json={"label": "Parcela A", "latitude": 37.39, "longitude": -5.99, "crop_type": "olivar", "comarca": "Sevilla"},
    )
    second = client.post(
        "/api/v1/parcels",
        headers={"Authorization": "Bearer user-b"},
        json={"label": "Parcela B", "latitude": 37.4, "longitude": -5.9, "crop_type": "vinedo", "comarca": "Cordoba"},
    )
    assert first.status_code == 201
    assert second.status_code == 201
    labels_a = [parcel["label"] for parcel in client.get("/api/v1/parcels", headers={"Authorization": "Bearer user-a"}).json()]
    labels_b = [parcel["label"] for parcel in client.get("/api/v1/parcels", headers={"Authorization": "Bearer user-b"}).json()]
    assert labels_a == ["Parcela A"]
    assert labels_b == ["Parcela B"]


def test_risk_history_deduplicates_repeated_calculations() -> None:
    response = client.post(
        "/api/v1/parcels",
        json={"label": "Historial", "latitude": 37.39, "longitude": -5.99, "crop_type": "olivar", "comarca": "Sevilla"},
    )
    parcel_id = response.json()["id"]
    client.get(f"/api/v1/disease-risk/{parcel_id}")
    client.get(f"/api/v1/disease-risk/{parcel_id}")
    history = client.get(f"/api/v1/risk-history/{parcel_id}").json()
    assert len(history) == 1


def test_risk_history_accepts_pagination_parameters() -> None:
    response = client.post(
        "/api/v1/parcels",
        json={"label": "Paginada", "latitude": 37.39, "longitude": -5.99, "crop_type": "olivar", "comarca": "Sevilla"},
    )
    parcel_id = response.json()["id"]
    history = client.get(f"/api/v1/risk-history/{parcel_id}?limit=1&offset=0")
    assert history.status_code == 200
    assert len(history.json()) <= 1


def test_risk_response_marks_missing_weather_data_as_insufficient():
    response = client.post('/api/v1/parcels', json={'label': 'Sin datos', 'latitude': 37.39, 'longitude': -5.99, 'crop_type': 'olivar', 'comarca': 'Sevilla'})
    parcel_id = response.json()['id']
    risk = client.get(f'/api/v1/disease-risk/{parcel_id}').json()[0]
    assert risk['data_status'] == 'insuficiente'
    assert risk['risk_score'] == 0
    assert risk['variables_used'] == []


def test_risk_rule_marks_old_telemetry_insufficient():
    old_reading = TelemetryCreate(
        parcel_id="p1", device_id="s1", temperature_c=18,
        relative_humidity=90, leaf_wetness_hours=12, soil_moisture=30,
        battery_percent=90,
        measured_at=datetime.now(timezone.utc) - timedelta(hours=30),
    )
    result = evaluate_risk("p1", "mildiu", "vinedo", old_reading)
    assert result.data_status == "insuficiente"
    assert result.variables_used == []


def test_risk_rule_marks_sensor_signal_as_preliminary():
    reading = TelemetryCreate(
        parcel_id="p1", device_id="s1", temperature_c=20,
        relative_humidity=90, leaf_wetness_hours=8, soil_moisture=30,
        battery_percent=90, measured_at=datetime.now(timezone.utc),
    )
    result = evaluate_risk("p1", "mildiu", "vinedo", reading)
    assert result.data_status == "preliminar"
    assert result.risk_level == "medio"
    assert result.confidence_level == "estimada"


def test_parcel_detail_does_not_trust_owner_id_query_parameter() -> None:
    created = client.post(
        "/api/v1/parcels",
        headers={"Authorization": "Bearer user-a"},
        json={"label": "Privada", "latitude": 37.39, "longitude": -5.99, "crop_type": "olivar", "comarca": "Sevilla"},
    )
    parcel_id = created.json()["id"]
    response = client.get(f"/api/v1/parcels/{parcel_id}?owner_id=user-a")
    assert response.status_code == 404


def test_telemetry_read_is_scoped_to_authenticated_owner() -> None:
    created = client.post(
        "/api/v1/parcels",
        headers={"Authorization": "Bearer user-a"},
        json={"label": "Telemetría privada", "latitude": 37.39, "longitude": -5.99, "crop_type": "olivar", "comarca": "Sevilla"},
    )
    parcel_id = created.json()["id"]
    response = client.get(f"/api/v1/telemetry/{parcel_id}")
    assert response.status_code == 404



def test_production_auth_fails_closed_without_firebase(monkeypatch):
    from fastapi import HTTPException
    from app.core.security import optional_bearer_token

    monkeypatch.setenv('ENVIRONMENT', 'production')
    monkeypatch.delenv('FIREBASE_SERVICE_ACCOUNT_JSON', raising=False)
    with pytest.raises(HTTPException) as error:
        optional_bearer_token(None)
    assert error.value.status_code == 503


def test_production_auth_requires_bearer_token(monkeypatch):
    from fastapi import HTTPException
    from app.core.security import optional_bearer_token

    monkeypatch.setenv('ENVIRONMENT', 'production')
    monkeypatch.setenv('FIREBASE_SERVICE_ACCOUNT_JSON', '{"project_id":"configured"}')
    with pytest.raises(HTTPException) as error:
        optional_bearer_token(None)
    assert error.value.status_code == 401

def test_sigpac_stable_feature_id_prefers_properties_id() -> None:
    from app.api.sigpac import _stable_feature_id

    assert _stable_feature_id({"properties": {"id": "recinto-123"}, "geometry": None}) == "recinto-123"
    assert _stable_feature_id({"id": "geojson-456", "properties": {"id": "other"}}) == "geojson-456"

def test_metrics_endpoint_requires_authentication_in_production(monkeypatch):
    monkeypatch.setenv('ENVIRONMENT', 'production')
    monkeypatch.setenv('FIREBASE_SERVICE_ACCOUNT_JSON', '{"project_id":"configured"}')
    response = client.get('/health/metrics')
    assert response.status_code == 401


def test_risk_rule_rejects_unsupported_disease_code():
    with pytest.raises(ValueError, match='Enfermedad no soportada'):
        evaluate_risk('p1', 'roya' , 'olivar', None)


def test_ria_ifapa_daily_endpoint_returns_provider_payload(monkeypatch):
    import app.api.ria_ifapa as ria_api

    class FakeRiaClient:
        async def get_daily_data(self, province, station, year, month_start, month_end):
            return {"datos": [{"fecha": "2026-09-01", "temperatura_media": 22.1}]}

        async def aclose(self):
            pass

    monkeypatch.setattr(ria_api, "RiaIfapaClient", FakeRiaClient)
    response = client.get(
        "/api/v1/ria-ifapa/daily?province=Sevilla&station=A1&year=2026&month_start=9&month_end=9"
    )
    assert response.status_code == 200
    assert response.json()["datos"][0]["temperatura_media"] == 22.1


def test_ria_ifapa_daily_endpoint_rejects_reversed_month_range():
    response = client.get(
        "/api/v1/ria-ifapa/daily?province=Sevilla&station=A1&year=2026&month_start=10&month_end=2"
    )
    assert response.status_code == 422


def test_ria_ifapa_monthly_endpoint_returns_provider_payload(monkeypatch):
    import app.api.ria_ifapa as ria_api

    class FakeRiaClient:
        async def get_monthly_data(self, province, station, year, month_start, month_end):
            return {"datos": [{"mes": "2026-09", "precipitacion": 12.4}]}

        async def aclose(self):
            pass

    monkeypatch.setattr(ria_api, "RiaIfapaClient", FakeRiaClient)
    response = client.get(
        "/api/v1/ria-ifapa/monthly?province=Sevilla&station=A1&year=2026&month_start=9&month_end=9"
    )
    assert response.status_code == 200
    assert response.json()["datos"][0]["precipitacion"] == 12.4


def test_ria_ifapa_daily_endpoint_maps_provider_http_error(monkeypatch):
    import asyncio
    import httpx
    import app.api.ria_ifapa as ria_api

    class FakeRiaClient:
        async def get_daily_data(self, *args):
            request = httpx.Request("GET", "https://ria.example.test")
            response = httpx.Response(503, request=request)
            raise httpx.HTTPStatusError("unavailable", request=request, response=response)

        async def aclose(self):
            pass

    monkeypatch.setattr(ria_api, "RiaIfapaClient", FakeRiaClient)
    response = client.get(
        "/api/v1/ria-ifapa/daily?province=Sevilla&station=HTTPERR&year=2026&month_start=9&month_end=9"
    )
    assert response.status_code == 502
    assert response.json()["detail"] == "RIA/IFAPA devolvió un error HTTP"


def test_ria_integration_health_does_not_claim_live_verification():
    response = client.get("/health/integrations")
    assert response.status_code == 200
    ria = response.json()["ria_ifapa"]
    assert ria["mode"] in {"configured_not_verified", "disabled"}
    assert ria["live_connection_verified"] is False


def test_ria_ifapa_daily_endpoint_maps_provider_timeout(monkeypatch):
    import httpx
    import app.api.ria_ifapa as ria_api

    class FakeRiaClient:
        async def get_daily_data(self, *args):
            request = httpx.Request("GET", "https://ria.example.test")
            raise httpx.ReadTimeout("provider timed out", request=request)

        async def aclose(self):
            pass

    monkeypatch.setattr(ria_api, "RiaIfapaClient", FakeRiaClient)
    response = client.get(
        "/api/v1/ria-ifapa/daily?province=Sevilla&station=TIMEOUT-UNIQUE&year=2026&month_start=9&month_end=9"
    )
    assert response.status_code == 504
    assert response.json()["detail"] == "Tiempo de espera agotado al consultar RIA/IFAPA"


@pytest.mark.parametrize("endpoint", ["daily", "monthly"])
@pytest.mark.parametrize("parameter", ["province", "station"])
def test_ria_ifapa_endpoints_reject_whitespace_only_parameters(endpoint, parameter):
    params = {"province": "Sevilla", "station": "A1", "year": 2026, "month_start": 9, "month_end": 9}
    params[parameter] = "   "
    response = client.get(f"/api/v1/ria-ifapa/{endpoint}", params=params)
    assert response.status_code == 422
    assert response.json()["detail"] == "province y station no pueden estar vacíos"
