from app.domain.agronomic_decision import make_agronomic_decision


def test_decision_escalates_when_independent_signals_agree() -> None:
    result = make_agronomic_decision(
        "p1",
        "repilo",
        {"risk_score": 0.62, "confidence_level": "alta"},
        telemetry={"relative_humidity": 92, "leaf_wetness_hours": 12},
        weather={"rainfall_mm_24h": 9, "relative_humidity": 90},
        field_reports=[{"type": "sintoma"}],
        raif_signal=0.7,
    )
    assert result["priority"] == "revisar"
    assert result["confidence"] == "alta"
    assert len(result["evidence"]) >= 5


def test_decision_stays_informative_with_low_signal() -> None:
    result = make_agronomic_decision(
        "p1",
        "mildiu",
        {"risk_score": 0.15, "confidence_level": "estimada"},
    )
    assert result["priority"] == "informativa"
    assert result["confidence"] == "baja"
