import sqlite3

from app.core.storage import Storage


def test_sqlite_connections_enable_concurrency_pragmas(tmp_path, monkeypatch):
    database = tmp_path / "agroalerta.db"
    monkeypatch.setenv("AGROALERTA_DB_PATH", str(database))

    storage = Storage()
    connection = storage._connect()
    try:
        assert connection.execute("PRAGMA busy_timeout").fetchone()[0] == 30000
        assert connection.execute("PRAGMA foreign_keys").fetchone()[0] == 1
        assert connection.execute("PRAGMA journal_mode").fetchone()[0].lower() == "wal"
    finally:
        connection.close()
