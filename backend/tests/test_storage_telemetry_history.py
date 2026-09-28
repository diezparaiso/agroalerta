from datetime import datetime, timezone

from app.core.storage import Storage
from app.schemas import Device, TelemetryCreate


def test_latest_telemetry_history_is_ordered_and_owner_scoped(tmp_path):
    storage = Storage()
    storage.path = tmp_path / "telemetry.db"
    storage._initialize()

    owner = "owner-1"
    parcel = "parcel-1"
    storage.create_device(Device(
        parcel_id=parcel,
        device_id="sensor-1",
        name="Estación",
        device_type="weather_station",
        registered_at=datetime.now(timezone.utc),
        owner_id=owner,
    ))
    storage.create_device(Device(
        parcel_id=parcel,
        device_id="sensor-2",
        name="Otro",
        device_type="soil_sensor",
        registered_at=datetime.now(timezone.utc),
        owner_id="other-owner",
    ))

    for device_id, measured_at, temperature in [
        ("sensor-1", "2026-09-28T10:00:00+00:00", 20.0),
        ("sensor-1", "2026-09-28T11:00:00+00:00", 21.0),
        ("sensor-2", "2026-09-28T12:00:00+00:00", 99.0),
    ]:
        payload = TelemetryCreate(
            parcel_id=parcel,
            device_id=device_id,
            temperature_c=temperature,
            relative_humidity=60,
            leaf_wetness_hours=1,
            soil_moisture=30,
            battery_percent=90,
            measured_at=datetime.fromisoformat(measured_at),
            owner_id=owner if device_id == "sensor-1" else "other-owner",
        )
        storage.create_telemetry(payload)

    history = storage.list_latest_telemetry(parcel, owner, 10)
    assert [row["temperature_c"] for row in history] == [21.0, 20.0]
    assert all(row["device_id"] == "sensor-1" for row in history)

    filtered = storage.list_latest_telemetry(parcel, owner, 10, device_id="sensor-1")
    assert [row["device_id"] for row in filtered] == ["sensor-1", "sensor-1"]

    assert storage.list_latest_telemetry(parcel, owner, 10, device_id="sensor-2") == []
