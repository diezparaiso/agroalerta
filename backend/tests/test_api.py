import pytest
from fastapi.testclient import TestClient

from app.main import app, storage

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


def test_telemetry_requires_registered_active_device() -> None:
    parcel = client.post(
        "/api/v1/parcels",
        headers={"Authorization": "Bearer user-a"},
        json={"label": "IoT", "latitude": 37.39, "longitude": -5.99, "crop_type": "olivar", "comarca": "Sevilla"},
    ).json()
    parcel_id = parcel["id"]
    payload = {
        "parcel_id": parcel_id,
        "device_id": "sensor-1",
        "temperature_c": 20,
        "relative_humidity": 70,
        "leaf_wetness_hours": 2,
        "soil_moisture": 30,
        "battery_percent": 90,
        "measured_at": "2026-09-28T10:00:00Z",
    }

    unknown = client.post("/api/v1/telemetry", headers={"Authorization": "Bearer user-a"}, json=payload)
    assert unknown.status_code == 404

    device = client.post(
        "/api/v1/devices",
        headers={"Authorization": "Bearer user-a"},
        json={"parcel_id": parcel_id, "device_id": "sensor-1", "name": "Sensor 1", "device_type": "weather_station"},
    )
    assert device.status_code == 201

    accepted = client.post("/api/v1/telemetry", headers={"Authorization": "Bearer user-a"}, json=payload)
    assert accepted.status_code == 202


def test_telemetry_rejects_inactive_device() -> None:
    parcel = client.post(
        "/api/v1/parcels",
        headers={"Authorization": "Bearer user-a"},
        json={"label": "IoT inactivo", "latitude": 37.39, "longitude": -5.99, "crop_type": "olivar", "comarca": "Sevilla"},
    ).json()
    parcel_id = parcel["id"]
    client.post(
        "/api/v1/devices",
        headers={"Authorization": "Bearer user-a"},
        json={"parcel_id": parcel_id, "device_id": "sensor-off", "name": "Sensor apagado", "device_type": "weather_station"},
    )
    with storage._connect() as connection:
        connection.execute("UPDATE devices SET active = 0 WHERE device_id = ?", ("sensor-off",))

    response = client.post(
        "/api/v1/telemetry",
        headers={"Authorization": "Bearer user-a"},
        json={
            "parcel_id": parcel_id,
            "device_id": "sensor-off",
            "temperature_c": 20,
            "relative_humidity": 70,
            "leaf_wetness_hours": 2,
            "soil_moisture": 30,
            "battery_percent": 90,
            "measured_at": "2026-09-28T10:00:00Z",
        },
    )
    assert response.status_code == 409
