from app.core.storage import Storage


def test_fresh_storage_records_schema_version(tmp_path, monkeypatch):
    monkeypatch.setenv("AGROALERTA_DB_PATH", str(tmp_path / "agroalerta.db"))

    storage = Storage()

    assert storage.schema_version() == 2


def test_schema_version_is_idempotent(tmp_path, monkeypatch):
    database = tmp_path / "agroalerta.db"
    monkeypatch.setenv("AGROALERTA_DB_PATH", str(database))

    assert Storage().schema_version() == 2
    assert Storage().schema_version() == 1
