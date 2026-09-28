from datetime import datetime, timedelta, timezone

from app.domain.irrigation_intelligence import build_irrigation_intelligence


def test_irrigation_intelligence_detects_dry_soil() -> None:
    now = datetime.now(timezone.utc)
    result = build_irrigation_intelligence(
        "parcel-1",
        [{"started_at": (now - timedelta(days=1)).isoformat(), "water_liters": 1200}],
        {"soil_moisture": 20},
        7,
    )
    assert result["soil_status"] == "seco"
    assert result["action"] == "revisar"
    assert result["total_water_liters"] == 1200


def test_irrigation_intelligence_flags_high_water_with_wet_soil() -> None:
    now = datetime.now(timezone.utc)
    result = build_irrigation_intelligence(
        "parcel-1",
        [
            {"started_at": (now - timedelta(days=1)).isoformat(), "water_liters": 5000},
            {"started_at": (now - timedelta(days=2)).isoformat(), "water_liters": 5000},
        ],
        {"soil_moisture": 82},
        7,
    )
    assert result["water_use_level"] == "alto"
    assert result["soil_status"] == "humedo"
    assert result["action"] == "revisar"


def test_irrigation_intelligence_without_history_requests_registration() -> None:
    result = build_irrigation_intelligence("parcel-1", [], None, 7)
    assert result["action"] == "registrar"
    assert result["water_use_level"] == "sin_datos"
