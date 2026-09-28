from datetime import datetime, timezone

from app.domain.disease_rules import evaluate_risk
from app.schemas import TelemetryCreate


def telemetry(**overrides) -> TelemetryCreate:
    values = {
        "parcel_id": "parcel-1",
        "device_id": "sensor-1",
        "temperature_c": 20,
        "relative_humidity": 92,
        "leaf_wetness_hours": 14,
        "soil_moisture": 70,
        "rainfall_mm_24h": 18,
        "battery_percent": 90,
        "measured_at": datetime.now(timezone.utc),
    }
    values.update(overrides)
    return TelemetryCreate(**values)


def test_repilo_risk_increases_with_wet_conditions() -> None:
    dry = evaluate_risk("parcel-1", "repilo", "olivar", telemetry(
        relative_humidity=55,
        leaf_wetness_hours=1,
        rainfall_mm_24h=0,
        temperature_c=8,
    ))
    wet = evaluate_risk("parcel-1", "repilo", "olivar", telemetry())
    assert wet.risk_score > dry.risk_score
    assert {item.name for item in wet.variables_used} >= {
        "lluvia_24h_mm",
        "horas_mojado_foliar",
        "temperatura_media_c",
        "humedad_relativa",
    }


def test_mildiu_uses_soil_moisture_and_rainfall() -> None:
    low = evaluate_risk("parcel-1", "mildiu", "vinedo", telemetry(
        relative_humidity=60,
        leaf_wetness_hours=1,
        rainfall_mm_24h=0,
        soil_moisture=30,
    ))
    high = evaluate_risk("parcel-1", "mildiu", "vinedo", telemetry(
        relative_humidity=95,
        leaf_wetness_hours=10,
        rainfall_mm_24h=12,
        soil_moisture=85,
        temperature_c=20,
    ))
    assert high.risk_score > low.risk_score


def test_rules_reject_wrong_crop() -> None:
    try:
        evaluate_risk("parcel-1", "repilo", "vinedo", telemetry())
    except ValueError as error:
        assert "olivar" in str(error)
    else:
        raise AssertionError("Expected crop validation error")
