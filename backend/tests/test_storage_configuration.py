import pytest

from app.core.storage import Storage


def test_storage_accepts_sqlite_database_url(tmp_path, monkeypatch):
    database = tmp_path / "agroalerta.db"
    monkeypatch.setenv("AGROALERTA_DB_URL", f"sqlite:///{database}")

    storage = Storage()

    assert storage.health() is True


def test_storage_rejects_unsupported_database_driver(monkeypatch):
    monkeypatch.setenv("AGROALERTA_DB_URL", "postgresql://example.invalid/agroalerta")

    with pytest.raises(ValueError, match="PostgreSQL adapter"):
        Storage()
