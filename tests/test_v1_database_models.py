from infrastructure.database.session import create_connection, get_database_path, initialize_database


def test_v1_database_models_create_core_tables(monkeypatch, tmp_path):
    db_path = tmp_path / "runtime" / "models.db"
    monkeypatch.setenv("INKTRACE_DB_PATH", str(db_path))
    get_database_path.cache_clear()

    initialize_database()

    with create_connection() as conn:
        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name IN ('works', 'chapters', 'edit_sessions')"
            ).fetchall()
        }
        indexes = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='index' AND name IN ('idx_chapters_work_order')"
            ).fetchall()
        }

    assert tables == {"works", "chapters", "edit_sessions"}
    assert indexes == {"idx_chapters_work_order"}

    get_database_path.cache_clear()
