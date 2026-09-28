from datetime import datetime, timedelta, timezone

from app.domain.raif_evidence import score_raif_evidence


def test_recent_nearby_raif_evidence_has_signal() -> None:
    now = datetime(2026, 9, 28, tzinfo=timezone.utc)
    records = [{
        "external_id": "raif-1",
        "observed_at": (now - timedelta(days=1)).isoformat(),
        "latitude": 37.39,
        "longitude": -5.99,
        "payload": {"fields": {"PLAGA": "Repilo"}},
    }]
    result = score_raif_evidence(37.39, -5.99, records, "repilo", now)
    assert result["evidence_count"] == 1
    assert float(result["signal"]) > 0


def test_old_raif_evidence_expires() -> None:
    now = datetime(2026, 9, 28, tzinfo=timezone.utc)
    records = [{
        "external_id": "raif-old",
        "observed_at": (now - timedelta(days=120)).isoformat(),
        "latitude": 37.39,
        "longitude": -5.99,
        "payload": {"fields": {"PLAGA": "Repilo"}},
    }]
    result = score_raif_evidence(37.39, -5.99, records, "repilo", now)
    assert result["evidence_count"] == 0
