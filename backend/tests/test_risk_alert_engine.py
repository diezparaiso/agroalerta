from datetime import datetime, timezone

from app.domain.risk_alert_engine import decide_risk_alert
from app.schemas import DiseaseRisk, RiskSnapshot


def _risk(level: str, score: float = 0.5) -> DiseaseRisk:
    now = datetime.now(timezone.utc)
    return DiseaseRisk(
        parcel_id="p1",
        disease_code="repilo",
        risk_score=score,
        risk_level=level,
        confidence_level="estimada",
        recommendation_text="test",
        variables_used=[],
        calculated_at=now,
        valid_until=now,
    )


def _snapshot(level: str, score: float = 0.5) -> RiskSnapshot:
    return RiskSnapshot(
        parcel_id="p1",
        owner_id="u1",
        disease_code="repilo",
        risk_score=score,
        risk_level=level,
        calculated_at=datetime.now(timezone.utc),
    )


def test_first_medium_risk_creates_and_notifies():
    decision = decide_risk_alert(_risk("medio"), None)
    assert decision.should_create is True
    assert decision.should_notify is True
    assert decision.reason_code == "first_risk"


def test_first_low_risk_does_not_create_alert():
    decision = decide_risk_alert(_risk("bajo"), None)
    assert decision.should_create is False
    assert decision.should_notify is False


def test_low_to_medium_creates_alert():
    decision = decide_risk_alert(_risk("medio"), _snapshot("bajo"))
    assert decision.should_create is True
    assert decision.reason_code == "risk_increase"


def test_medium_to_high_creates_alert():
    decision = decide_risk_alert(_risk("alto"), _snapshot("medio"))
    assert decision.should_create is True
    assert decision.reason_code == "risk_increase"


def test_same_level_does_not_duplicate_alert():
    decision = decide_risk_alert(_risk("alto", 0.91), _snapshot("alto", 0.82))
    assert decision.should_create is False
    assert decision.should_notify is False
    assert decision.reason_code == "unchanged"


def test_risk_decrease_is_not_push_alert():
    decision = decide_risk_alert(_risk("medio"), _snapshot("alto"))
    assert decision.should_create is False
    assert decision.should_notify is False
    assert decision.reason_code == "risk_decrease"
