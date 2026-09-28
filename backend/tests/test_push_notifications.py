from app.domain.push_notifications import PushDeliveryResult, send_alert_push
from app.schemas import Alert
from datetime import datetime, timezone


def _alert() -> Alert:
    now = datetime.now(timezone.utc)
    return Alert(
        id=1,
        parcel_id="p1",
        owner_id="u1",
        disease_code="repilo",
        alert_type="riesgo_incrementado",
        risk_level="alto",
        risk_score=0.9,
        message="Riesgo alto de repilo detectado en la parcela.",
        created_at=now,
    )


def test_push_without_tokens_is_noop(monkeypatch):
    monkeypatch.delenv("FIREBASE_SERVICE_ACCOUNT_JSON", raising=False)
    result = send_alert_push(_alert(), [])
    assert result == PushDeliveryResult("no_tokens", 0, 0, 0)


def test_push_is_disabled_without_firebase_credentials(monkeypatch):
    monkeypatch.delenv("FIREBASE_SERVICE_ACCOUNT_JSON", raising=False)
    result = send_alert_push(_alert(), ["token-12345678901234567890"])
    assert result == PushDeliveryResult("disabled", 1, 0, 0)
