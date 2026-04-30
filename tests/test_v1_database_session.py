import sqlite3

from infrastructure.database.session import (
    create_connection,
    get_database_path,
    initialize_database,
)
from application.services.v1.work_service import WorkService


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


def test_v1_database_session_migrates_legacy_chapters_schema(monkeypatch, tmp_path):
    db_path = tmp_path / "runtime" / "legacy.db"
    monkeypatch.setenv("INKTRACE_DB_PATH", str(db_path))
    get_database_path.cache_clear()

    db_path.parent.mkdir(parents=True, exist_ok=True)
    with create_connection(row_factory=None) as conn:
        conn.execute(
            """
            CREATE TABLE chapters (
                id TEXT PRIMARY KEY,
                novel_id TEXT NOT NULL,
                number INTEGER NOT NULL,
                title TEXT,
                content TEXT,
                word_count INTEGER,
                summary TEXT,
                status TEXT DEFAULT 'draft',
                created_at TEXT,
                updated_at TEXT
            )
            """
        )
        conn.execute(
            """
            INSERT INTO chapters (id, novel_id, number, title, content, created_at, updated_at)
            VALUES ('chapter-1', 'work-1', 3, '第一章', '正文', '2026-04-28T12:00:00', '2026-04-28T12:00:00')
            """
        )

    initialize_database()

    with create_connection(row_factory=None) as conn:
        columns = [row[1] for row in conn.execute("PRAGMA table_info(chapters)").fetchall()]
        row = conn.execute(
            "SELECT work_id, number, order_index, version FROM chapters WHERE id = 'chapter-1'"
        ).fetchone()

    assert "work_id" in columns
    assert "order_index" in columns
    assert "version" in columns
    assert row == ("work-1", 3, 3, 1)

    get_database_path.cache_clear()


def test_v1_database_session_allows_create_work_on_legacy_chapters_schema(monkeypatch, tmp_path):
    db_path = tmp_path / "runtime" / "legacy-create.db"
    monkeypatch.setenv("INKTRACE_DB_PATH", str(db_path))
    get_database_path.cache_clear()

    db_path.parent.mkdir(parents=True, exist_ok=True)
    with create_connection(row_factory=None) as conn:
        conn.execute(
            """
            CREATE TABLE works (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                author TEXT NOT NULL DEFAULT '',
                current_word_count INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE chapters (
                id TEXT PRIMARY KEY,
                novel_id TEXT NOT NULL,
                number INTEGER NOT NULL,
                title TEXT,
                content TEXT,
                word_count INTEGER,
                summary TEXT,
                status TEXT DEFAULT 'draft',
                created_at TEXT,
                updated_at TEXT
            )
            """
        )

    work = WorkService().create_work("遗留库创建作品", "")

    with create_connection(row_factory=None) as conn:
        row = conn.execute(
            """
            SELECT novel_id, work_id, number, order_index, version
            FROM chapters
            WHERE work_id = ?
            """,
            (work.id,),
        ).fetchone()

    assert row[0] == work.id
    assert row[1] == work.id
    assert row[2] == 1
    assert row[3] == 1
    assert row[4] == 1

    get_database_path.cache_clear()


def test_v1_database_session_uses_v11_runtime_schema_for_new_databases(monkeypatch, tmp_path):
    db_path = tmp_path / "runtime" / "v11-runtime-schema.db"
    monkeypatch.setenv("INKTRACE_DB_PATH", str(db_path))
    get_database_path.cache_clear()

    initialize_database()

    conn = sqlite3.connect(db_path)
    work_columns = {row[1] for row in conn.execute("PRAGMA table_info(works)").fetchall()}
    chapter_columns = {row[1] for row in conn.execute("PRAGMA table_info(chapters)").fetchall()}

    assert "word_count" in work_columns
    assert "current_word_count" not in work_columns
    assert {"work_id", "word_count", "order_index", "version"}.issubset(chapter_columns)
    assert "chapter_number" not in chapter_columns
    assert "number" not in chapter_columns
    assert "novel_id" not in chapter_columns

    conn.close()
    get_database_path.cache_clear()
