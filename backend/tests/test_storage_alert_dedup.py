from datetime import datetime, timezone

from app.core.storage import Storage


def test_save_alert_deduplicates_by_transition_key(tmp_path, monkeypatch):
    database = tmp_path / "agroalerta.db"
    monkeypatch.setenv("AGROALERTA_DB_PATH", str(database))
    storage = Storage()
    created_at = datetime.now(timezone.utc)
    key = "parcel-1:repilo:risk_increase:medio:previous-123"

    first = storage.save_alert(
        parcel_id="parcel-1",
        owner_id="owner-1",
        disease_code="repilo",
        alert_type="riesgo_incrementado",
        risk_level="medio",
        risk_score=0.72,
        message="Riesgo medio de repilo.",
        created_at=created_at,
        dedup_key=key,
    )
    duplicate = storage.save_alert(
        parcel_id="parcel-1",
        owner_id="owner-1",
        disease_code="repilo",
        alert_type="riesgo_incrementado",
        risk_level="medio",
        risk_score=0.75,
        message="Riesgo medio de repilo.",
        created_at=created_at,
        dedup_key=key,
    )

    assert first is not None
    assert duplicate is None
    assert len(storage.list_alerts(owner_id="owner-1")) == 1


def test_new_transition_key_creates_new_alert(tmp_path, monkeypatch):
    database = tmp_path / "agroalerta.db"
    monkeypatch.setenv("AGROALERTA_DB_PATH", str(database))
    storage = Storage()
    created_at = datetime.now(timezone.utc)

    common = dict(
        parcel_id="parcel-1",
        owner_id="owner-1",
        disease_code="repilo",
        alert_type="riesgo_incrementado",
        risk_level="medio",
        risk_score=0.72,
        message="Riesgo medio de repilo.",
        created_at=created_at,
    )
    assert storage.save_alert(**common, dedup_key="transition-1") is not None
    assert storage.save_alert(**common, dedup_key="transition-2") is not None

    assert len(storage.list_alerts(owner_id="owner-1")) == 2
