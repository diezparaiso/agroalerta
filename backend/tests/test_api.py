import pytest
from datetime import datetime, timezone
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


def test_alert_user_state_tracks_read_and_acknowledgement_by_owner():
    parcel = client.post('/api/v1/parcels', headers={'Authorization': 'Bearer user-a'}, json={'label': 'Estado alerta', 'latitude': 37.39, 'longitude': -5.99, 'crop_type': 'olivar', 'comarca': 'Sevilla'}).json()
    alert = storage.save_alert(parcel['id'], 'user-a', 'repilo', 'risk_transition', 'medio', 0.6, 'Riesgo medio', datetime.now(timezone.utc), dedup_key='test-alert-state-1')
    assert alert is not None
    initial = client.get('/api/v1/alerts/%s/state' % alert.id, headers={'Authorization': 'Bearer user-a'})
    assert initial.status_code == 200
    assert initial.json()['read'] is False
    assert initial.json()['acknowledged'] is False
    updated = client.patch('/api/v1/alerts/%s/state' % alert.id, headers={'Authorization': 'Bearer user-a'}, json={'read': True, 'acknowledged': True})
    assert updated.status_code == 200
    assert updated.json()['read'] is True
    assert updated.json()['acknowledged'] is True
    assert updated.json()['read_at'] is not None
    assert updated.json()['acknowledged_at'] is not None
    other = client.get('/api/v1/alerts/%s/state' % alert.id, headers={'Authorization': 'Bearer user-b'})
    assert other.status_code == 404

def test_telemetry_quality_summary_is_owner_scoped_and_reports_window():
    parcel = client.post("/api/v1/parcels", headers={"Authorization": "Bearer user-a"}, json={
        "label": "Calidad", "latitude": 37.39, "longitude": -5.99,
        "crop_type": "olivar", "comarca": "Sevilla",
    }).json()
    client.post("/api/v1/devices", headers={"Authorization": "Bearer user-a"}, json={
        "parcel_id": parcel["id"], "device_id": "quality-sensor",
        "name": "Quality", "device_type": "weather_station",
    })
    response = client.get(
        f"/api/v1/telemetry/{parcel['id']}/quality?since_hours=24",
        headers={"Authorization": "Bearer user-a"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["window_hours"] == 24
    assert body["device_count"] == 1
    assert body["active_device_count"] == 1
    assert body["devices"][0]["device_id"] == "quality-sensor"
    assert body["devices"][0]["sample_count"] == 0

    other = client.get(
        f"/api/v1/telemetry/{parcel['id']}/quality",
        headers={"Authorization": "Bearer user-b"},
    )
    assert other.status_code == 404


def test_parcel_activity_timeline_is_owner_scoped_and_ordered() -> None:
    parcel = client.post("/api/v1/parcels", headers={"Authorization": "Bearer user-a"}, json={
        "label": "Actividad", "latitude": 37.39, "longitude": -5.99,
        "crop_type": "olivar", "comarca": "Sevilla",
    }).json()
    parcel_id = parcel["id"]
    client.post(
        "/api/v1/devices",
        headers={"Authorization": "Bearer user-a"},
        json={"parcel_id": parcel_id, "device_id": "activity-sensor", "name": "Actividad", "device_type": "weather_station"},
    )
    client.post(
        "/api/v1/telemetry",
        headers={"Authorization": "Bearer user-a"},
        json={
            "telemetry_id": "activity-telemetry-1", "parcel_id": parcel_id, "device_id": "activity-sensor",
            "temperature_c": 21, "relative_humidity": 60, "leaf_wetness_hours": 2,
            "soil_moisture": 35, "battery_percent": 90, "measured_at": "2026-09-28T10:00:00+00:00",
        },
    )
    client.post(
        "/api/v1/field-reports",
        headers={"Authorization": "Bearer user-a"},
        json={
            "report_id": "activity-report-1", "parcel_id": parcel_id, "type": "trampa",
            "count": 2, "latitude": 37.39, "longitude": -5.99,
            "reported_at": "2026-09-28T11:00:00+00:00",
        },
    )
    response = client.get(f"/api/v1/parcels/{parcel_id}/activity?limit=10", headers={"Authorization": "Bearer user-a"})
    assert response.status_code == 200
    body = response.json()
    assert [item["event_type"] for item in body[:2]] == ["field_report", "telemetry"]
    assert body[0]["event_id"] == "activity-report-1"
    assert body[1]["event_id"] == "activity-telemetry-1"

    other = client.get(f"/api/v1/parcels/{parcel_id}/activity", headers={"Authorization": "Bearer user-b"})
    assert other.status_code == 404


def test_crop_campaign_lifecycle_is_owner_scoped() -> None:
    parcel = client.post("/api/v1/parcels", headers={"Authorization": "Bearer user-a"}, json={
        "label": "Campaña", "latitude": 37.39, "longitude": -5.99,
        "crop_type": "olivar", "comarca": "Sevilla",
    }).json()
    parcel_id = parcel["id"]

    created = client.post(
        f"/api/v1/parcels/{parcel_id}/campaigns",
        headers={"Authorization": "Bearer user-a"},
        json={"name": "Campaña 2026", "crop_type": "olivar", "started_at": "2026-09-01T00:00:00+00:00"},
    )
    assert created.status_code == 201
    campaign = created.json()
    assert campaign["status"] == "activa"
    assert campaign["crop_type"] == "olivar"

    listed = client.get(f"/api/v1/parcels/{parcel_id}/campaigns", headers={"Authorization": "Bearer user-a"})
    assert listed.status_code == 200
    assert len(listed.json()) == 1

    closed = client.patch(
        f"/api/v1/campaigns/{campaign['id']}/status",
        headers={"Authorization": "Bearer user-a"},
        json={"status": "cerrada"},
    )
    assert closed.status_code == 200
    assert closed.json()["status"] == "cerrada"
    assert closed.json()["ended_at"] is not None

    other = client.get(f"/api/v1/parcels/{parcel_id}/campaigns", headers={"Authorization": "Bearer user-b"})
    assert other.status_code == 404


def test_irrigation_event_is_recorded_and_owner_scoped() -> None:
    parcel = client.post("/api/v1/parcels", headers={"Authorization": "Bearer user-a"}, json={
        "label": "Riego", "latitude": 37.39, "longitude": -5.99,
        "crop_type": "olivar", "comarca": "Sevilla",
    }).json()
    parcel_id = parcel["id"]

    created = client.post(
        f"/api/v1/parcels/{parcel_id}/irrigation",
        headers={"Authorization": "Bearer user-a"},
        json={
            "started_at": "2026-09-28T07:30:00+00:00",
            "duration_minutes": 45,
            "water_liters": 1800,
            "method": "goteo",
            "notes": "Riego de mantenimiento",
        },
    )
    assert created.status_code == 201
    body = created.json()
    assert body["parcel_id"] == parcel_id
    assert body["method"] == "goteo"
    assert body["duration_minutes"] == 45
    assert body["water_liters"] == 1800

    listed = client.get(f"/api/v1/parcels/{parcel_id}/irrigation", headers={"Authorization": "Bearer user-a"})
    assert listed.status_code == 200
    assert len(listed.json()) == 1

    other = client.get(f"/api/v1/parcels/{parcel_id}/irrigation", headers={"Authorization": "Bearer user-b"})
    assert other.status_code == 404


def test_treatment_record_is_recorded_and_owner_scoped() -> None:
    parcel = client.post("/api/v1/parcels", headers={"Authorization": "Bearer user-a"}, json={
        "label": "Tratamiento", "latitude": 37.39, "longitude": -5.99,
        "crop_type": "olivar", "comarca": "Sevilla",
    }).json()
    parcel_id = parcel["id"]

    created = client.post(
        f"/api/v1/parcels/{parcel_id}/treatments",
        headers={"Authorization": "Bearer user-a"},
        json={
            "applied_at": "2026-09-28T08:00:00+00:00",
            "product_name": "Producto registrado por el usuario",
            "active_substance": "Sustancia activa",
            "dose": "2 L/ha",
            "treated_area_ha": 4.5,
            "notes": "Aplicación registrada",
        },
    )
    assert created.status_code == 201
    body = created.json()
    assert body["parcel_id"] == parcel_id
    assert body["product_name"] == "Producto registrado por el usuario"
    assert body["treated_area_ha"] == 4.5

    listed = client.get(f"/api/v1/parcels/{parcel_id}/treatments", headers={"Authorization": "Bearer user-a"})
    assert listed.status_code == 200
    assert len(listed.json()) == 1

    other = client.get(f"/api/v1/parcels/{parcel_id}/treatments", headers={"Authorization": "Bearer user-b"})
    assert other.status_code == 404


def test_alert_preferences_are_owner_scoped_and_persisted() -> None:
    default = client.get("/api/v1/alert-preferences", headers={"Authorization": "Bearer user-a"})
    assert default.status_code == 200
    assert default.json()["minimum_risk_level"] == "medio"
    assert default.json()["push_enabled"] is True

    updated = client.put(
        "/api/v1/alert-preferences",
        headers={"Authorization": "Bearer user-a"},
        json={"minimum_risk_level": "alto", "push_enabled": False},
    )
    assert updated.status_code == 200
    assert updated.json()["minimum_risk_level"] == "alto"
    assert updated.json()["push_enabled"] is False

    reread = client.get("/api/v1/alert-preferences", headers={"Authorization": "Bearer user-a"})
    assert reread.json()["minimum_risk_level"] == "alto"
    assert reread.json()["push_enabled"] is False

    other = client.get("/api/v1/alert-preferences", headers={"Authorization": "Bearer user-b"})
    assert other.status_code == 200
    assert other.json()["minimum_risk_level"] == "medio"
    assert other.json()["push_enabled"] is True


def test_irrigation_summary_aggregates_recorded_events_and_scopes_owner() -> None:
    parcel = client.post("/api/v1/parcels", headers={"Authorization": "Bearer user-a"}, json={
        "label": "Riego resumen", "latitude": 37.39, "longitude": -5.99,
        "crop_type": "olivar", "comarca": "Sevilla",
    }).json()
    parcel_id = parcel["id"]
    headers = {"Authorization": "Bearer user-a"}

    for started_at, minutes, liters in [
        ("2026-09-27T07:00:00+00:00", 30, 1000),
        ("2026-09-28T07:00:00+00:00", 45, 1500),
    ]:
        response = client.post(
            f"/api/v1/parcels/{parcel_id}/irrigation",
            headers=headers,
            json={"started_at": started_at, "duration_minutes": minutes, "water_liters": liters, "method": "goteo"},
        )
        assert response.status_code == 201

    summary = client.get(f"/api/v1/parcels/{parcel_id}/irrigation/summary", headers=headers)
    assert summary.status_code == 200
    assert summary.json()["event_count"] == 2
    assert summary.json()["total_duration_minutes"] == 75
    assert summary.json()["total_water_liters"] == 2500

    other = client.get(
        f"/api/v1/parcels/{parcel_id}/irrigation/summary",
        headers={"Authorization": "Bearer user-b"},
    )
    assert other.status_code == 404


def test_agronomic_report_is_consolidated_and_owner_scoped() -> None:
    headers = {"Authorization": "Bearer report-owner"}
    parcel = client.post("/api/v1/parcels", headers=headers, json={
        "label": "Informe agronómico", "latitude": 37.39, "longitude": -5.99,
        "crop_type": "olivar", "comarca": "Sevilla",
    }).json()
    parcel_id = parcel["id"]

    irrigation = client.post(
        f"/api/v1/parcels/{parcel_id}/irrigation",
        headers=headers,
        json={"started_at": "2026-09-28T07:00:00+00:00", "duration_minutes": 30,
              "water_liters": 800, "method": "goteo"},
    )
    assert irrigation.status_code == 201

    report = client.get(
        f"/api/v1/parcels/{parcel_id}/agronomic-report",
        headers=headers,
    )
    assert report.status_code == 200
    data = report.json()
    assert data["parcel"]["id"] == parcel_id
    assert data["irrigation"]["event_count"] == 1
    assert data["irrigation"]["total_water_liters"] == 800
    assert data["campaign_count"] == 0
    assert data["treatment_count"] == 0

    other = client.get(
        f"/api/v1/parcels/{parcel_id}/agronomic-report",
        headers={"Authorization": "Bearer another-owner"},
    )
    assert other.status_code == 404
