from infrastructure.database.session import (
    create_connection,
    get_database_path,
    initialize_database,
)


def test_v1_database_session_enables_wal_and_busy_timeout(monkeypatch, tmp_path):
    db_path = tmp_path / "runtime" / "v1.db"
    monkeypatch.setenv("INKTRACE_DB_PATH", str(db_path))
    get_database_path.cache_clear()

    resolved = initialize_database()

    assert resolved == db_path.resolve()
    assert resolved.parent.exists()

    with create_connection() as conn:
        journal_mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
        busy_timeout = conn.execute("PRAGMA busy_timeout").fetchone()[0]

    assert str(journal_mode).lower() == "wal"
    assert int(busy_timeout) == 10000

    get_database_path.cache_clear()
