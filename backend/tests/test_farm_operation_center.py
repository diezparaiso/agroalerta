from datetime import datetime, timezone
from types import SimpleNamespace

from app.domain.farm_operation_center import build_farm_center


def test_center_builds_operational_parcel_cards() -> None:
    now = datetime.now(timezone.utc)
    parcel = SimpleNamespace(id="p1", label="Olivar Norte", crop_type="olivar", comarca="Sierra")
    risk = SimpleNamespace(disease_code="repilo", risk_level="alto", risk_score=0.82, confidence_level="alta", calculated_at=now)
    telemetry = SimpleNamespace(measured_at=now, soil_moisture=31.5, relative_humidity=91.0)
    device = SimpleNamespace(name="Sensor 1", device_type="leaf_sensor", registered_at=now, active=True)

    result = build_farm_center([parcel], [{"parcel": parcel, "telemetry": telemetry, "devices": [device], "risks": [risk]}])

    assert result["parcel_count"] == 1
    assert result["parcel_attention_count"] == 1
    assert result["sensor_count"] == 1
    assert result["parcels"][0]["priority"] == "revisar"
    assert result["recent_events"][0]["parcel_id"] == "p1"
