from app.core.storage import Storage
from app.schemas import FieldReportCreate


def _report() -> FieldReportCreate:
    return FieldReportCreate(
        report_id="report-123",
        parcel_id="parcel-1",
        type="sintoma",
        notes="Manchas",
        count=2,
        latitude=37.3,
        longitude=-5.9,
        reported_at="2026-09-28T10:00:00+00:00",
    )


def test_field_report_idempotency_does_not_duplicate(tmp_path, monkeypatch):
    monkeypatch.setenv("AGROALERTA_DB_PATH", str(tmp_path / "agroalerta.db"))
    storage = Storage()
    first = storage.create_report("report-123", _report())
    second = storage.create_report("report-123", _report())

    assert first is True
    assert second is False

    with storage._connect() as connection:
        row = connection.execute(
            "SELECT COUNT(*) AS count FROM field_reports WHERE id = ?",
            ("report-123",),
        ).fetchone()
    assert row["count"] == 1
