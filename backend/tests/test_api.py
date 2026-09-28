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


def test_device_state_can_be_changed_by_owner() -> None:
    parcel = client.post(
        "/api/v1/parcels",
        headers={"Authorization": "Bearer user-a"},
        json={"label": "IoT estado", "latitude": 37.39, "longitude": -5.99, "crop_type": "olivar", "comarca": "Sevilla"},
    ).json()
    parcel_id = parcel["id"]
    client.post(
        "/api/v1/devices",
        headers={"Authorization": "Bearer user-a"},
        json={"parcel_id": parcel_id, "device_id": "sensor-state", "name": "Sensor estado", "device_type": "weather_station"},
    )

    disabled = client.patch(
        "/api/v1/devices/sensor-state",
        headers={"Authorization": "Bearer user-a"},
        json={"active": False},
    )
    assert disabled.status_code == 200
    assert disabled.json()["active"] is False

    enabled = client.patch(
        "/api/v1/devices/sensor-state",
        headers={"Authorization": "Bearer user-a"},
        json={"active": True},
    )
    assert enabled.status_code == 200
    assert enabled.json()["active"] is True


def test_device_state_cannot_be_changed_by_other_owner() -> None:
    parcel = client.post(
        "/api/v1/parcels",
        headers={"Authorization": "Bearer user-a"},
        json={"label": "IoT privado", "latitude": 37.39, "longitude": -5.99, "crop_type": "olivar", "comarca": "Sevilla"},
    ).json()
    client.post(
        "/api/v1/devices",
        headers={"Authorization": "Bearer user-a"},
        json={"parcel_id": parcel["id"], "device_id": "sensor-private", "name": "Sensor privado", "device_type": "weather_station"},
    )
    response = client.patch(
        "/api/v1/devices/sensor-private",
        headers={"Authorization": "Bearer user-b"},
        json={"active": False},
    )
    assert response.status_code == 404


def test_telemetry_rejects_future_timestamp() -> None:
    parcel = client.post(
        "/api/v1/parcels",
        headers={"Authorization": "Bearer user-a"},
        json={"label": "IoT temporal", "latitude": 37.39, "longitude": -5.99, "crop_type": "olivar", "comarca": "Sevilla"},
    ).json()
    client.post(
        "/api/v1/devices",
        headers={"Authorization": "Bearer user-a"},
        json={"parcel_id": parcel["id"], "device_id": "sensor-clock", "name": "Reloj", "device_type": "weather_station"},
    )
    response = client.post(
        "/api/v1/telemetry",
        headers={"Authorization": "Bearer user-a"},
        json={
            "parcel_id": parcel["id"],
            "device_id": "sensor-clock",
            "temperature_c": 20,
            "relative_humidity": 60,
            "leaf_wetness_hours": 1,
            "soil_moisture": 30,
            "battery_percent": 90,
            "measured_at": "2099-01-01T00:00:00+00:00",
        },
    )
    assert response.status_code == 422


def test_telemetry_retry_is_idempotent() -> None:
    parcel = client.post("/api/v1/parcels", headers={"Authorization": "Bearer user-a"}, json={"label": "IoT retry", "latitude": 37.39, "longitude": -5.99, "crop_type": "olivar", "comarca": "Sevilla"}).json()
    client.post("/api/v1/devices", headers={"Authorization": "Bearer user-a"}, json={"parcel_id": parcel["id"], "device_id": "sensor-retry", "name": "Retry", "device_type": "weather_station"})
    payload = {"telemetry_id": "event-001", "parcel_id": parcel["id"], "device_id": "sensor-retry", "temperature_c": 20, "relative_humidity": 60, "leaf_wetness_hours": 1, "soil_moisture": 30, "battery_percent": 90, "measured_at": "2026-09-28T10:00:00+00:00"}
    first = client.post("/api/v1/telemetry", headers={"Authorization": "Bearer user-a"}, json=payload)
    second = client.post("/api/v1/telemetry", headers={"Authorization": "Bearer user-a"}, json=payload)
    assert first.json()["status"] == "accepted"
    assert second.json()["status"] == "already_received"


def test_device_health_reports_latest_telemetry() -> None:
    parcel = client.post("/api/v1/parcels", headers={"Authorization": "Bearer user-a"}, json={"label": "IoT health", "latitude": 37.39, "longitude": -5.99, "crop_type": "olivar", "comarca": "Sevilla"}).json()
    client.post("/api/v1/devices", headers={"Authorization": "Bearer user-a"}, json={"parcel_id": parcel["id"], "device_id": "sensor-health", "name": "Health", "device_type": "weather_station"})
    client.post("/api/v1/telemetry", headers={"Authorization": "Bearer user-a"}, json={"telemetry_id": "health-001", "parcel_id": parcel["id"], "device_id": "sensor-health", "temperature_c": 21, "relative_humidity": 55, "leaf_wetness_hours": 2, "soil_moisture": 40, "battery_percent": 73, "measured_at": "2026-09-28T10:00:00+00:00"})
    response = client.get(f"/api/v1/devices/{parcel['id']}/health", headers={"Authorization": "Bearer user-a"})
    assert response.status_code == 200
    item = response.json()[0]
    assert item["device_id"] == "sensor-health"
    assert item["battery_percent"] == 73
    assert item["telemetry_count"] == 1
    assert item["last_seen_at"] == "2026-09-28T10:00:00+00:00"


def test_parcel_agronomic_summary_aggregates_operational_data() -> None:
    parcel = client.post("/api/v1/parcels", headers={"Authorization": "Bearer user-a"}, json={"label": "Resumen", "latitude": 37.39, "longitude": -5.99, "crop_type": "olivar", "comarca": "Sevilla"}).json()
    client.post("/api/v1/devices", headers={"Authorization": "Bearer user-a"}, json={"parcel_id": parcel["id"], "device_id": "summary-sensor", "name": "Summary", "device_type": "weather_station"})
    client.post("/api/v1/telemetry", headers={"Authorization": "Bearer user-a"}, json={"telemetry_id": "summary-001", "parcel_id": parcel["id"], "device_id": "summary-sensor", "temperature_c": 21, "relative_humidity": 55, "leaf_wetness_hours": 2, "soil_moisture": 40, "battery_percent": 81, "measured_at": "2026-09-28T10:00:00+00:00"})
    response = client.get(f"/api/v1/parcels/{parcel['id']}/agronomic-summary", headers={"Authorization": "Bearer user-a"})
    assert response.status_code == 200
    body = response.json()
    assert body["crop_type"] == "olivar"
    assert body["device_count"] == 1
    assert body["active_device_count"] == 1
    assert body["latest_battery_percent"] == 81
    assert body["recent_alert_count"] == 0


def test_field_report_summary_aggregates_recent_reports() -> None:
    parcel = client.post("/api/v1/parcels", headers={"Authorization": "Bearer user-a"}, json={
        "label": "Partes", "latitude": 37.39, "longitude": -5.99,
        "crop_type": "olivar", "comarca": "Sevilla",
    }).json()
    parcel_id = parcel["id"]
    for report_id, report_type, reported_at in (
        ("report-1", "trampa", "2026-09-27T10:00:00+00:00"),
        ("report-2", "sintoma", "2026-09-28T10:00:00+00:00"),
    ):
        response = client.post("/api/v1/field-reports", headers={"Authorization": "Bearer user-a"}, json={
            "report_id": report_id, "parcel_id": parcel_id, "type": report_type,
            "count": 2, "latitude": 37.39, "longitude": -5.99, "reported_at": reported_at,
        })
        assert response.status_code == 201

    response = client.get(f"/api/v1/parcels/{parcel_id}/field-reports/summary", headers={"Authorization": "Bearer user-a"})
    assert response.status_code == 200
    assert response.json()["total_reports"] == 2
    assert response.json()["reports_by_type"] == {"trampa": 1, "sintoma": 1}
    assert response.json()["recent_reports_30d"] == 2
    assert response.json()["latest_report_type"] == "sintoma"


def test_field_report_summary_is_owner_scoped() -> None:
    parcel = client.post("/api/v1/parcels", headers={"Authorization": "Bearer user-a"}, json={
        "label": "Privado", "latitude": 37.39, "longitude": -5.99,
        "crop_type": "olivar", "comarca": "Sevilla",
    }).json()
    response = client.get(f"/api/v1/parcels/{parcel['id']}/field-reports/summary", headers={"Authorization": "Bearer user-b"})
    assert response.status_code == 404


def test_weather_evidence_summary_reports_no_evidence_without_observations() -> None:
    parcel = client.post("/api/v1/parcels", headers={"Authorization": "Bearer user-a"}, json={
        "label": "Evidencia meteorológica", "latitude": 37.39, "longitude": -5.99,
        "crop_type": "olivar", "comarca": "Sevilla",
    }).json()
    response = client.get(
        f"/api/v1/parcels/{parcel['id']}/weather-evidence",
        headers={"Authorization": "Bearer user-a"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["available"] is False
    assert body["station_count"] == 0
    assert body["source"] == "none"
    assert body["fresh_window_hours"] == 72


def test_weather_evidence_summary_is_owner_scoped() -> None:
    parcel = client.post("/api/v1/parcels", headers={"Authorization": "Bearer user-a"}, json={
        "label": "Evidencia privada", "latitude": 37.39, "longitude": -5.99,
        "crop_type": "olivar", "comarca": "Sevilla",
    }).json()
    response = client.get(
        f"/api/v1/parcels/{parcel['id']}/weather-evidence",
        headers={"Authorization": "Bearer user-b"},
    )
    assert response.status_code == 404


def test_notification_delivery_history_is_owner_scoped_and_filterable() -> None:
    parcel = client.post("/api/v1/parcels", headers={"Authorization": "Bearer user-a"}, json={
        "label": "Notificaciones", "latitude": 37.39, "longitude": -5.99,
        "crop_type": "olivar", "comarca": "Sevilla",
    }).json()
    alert_id = 9001
    storage.save_notification_delivery("user-a", alert_id, "sent", 2, 2, 0)
    storage.save_notification_delivery("user-a", 9002, "error", 2, 0, 2)
    response = client.get(
        "/api/v1/notifications/deliveries?alert_id=9001",
        headers={"Authorization": "Bearer user-a"},
    )
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["status"] == "sent"

    other = client.get(
        "/api/v1/notifications/deliveries",
        headers={"Authorization": "Bearer user-b"},
    )
    assert other.status_code == 200
    assert other.json() == []
