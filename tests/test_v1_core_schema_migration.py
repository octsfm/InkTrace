from infrastructure.database.v1 import connect, migrate_core_schema, verify_core_schema


def test_v1_core_schema_creates_required_tables_and_columns(tmp_path):
    conn = connect(tmp_path / "v1.db")

    migrate_core_schema(conn)
    migrate_core_schema(conn)

    schema = verify_core_schema(conn)
    assert {"works", "chapters", "edit_sessions"} == set(schema)
    assert {"id", "title", "author", "word_count", "created_at", "updated_at"}.issubset(schema["works"])
    assert {
        "id",
        "work_id",
        "title",
        "content",
        "word_count",
        "order_index",
        "version",
        "created_at",
        "updated_at",
    }.issubset(schema["chapters"])
    assert {
        "work_id",
        "last_open_chapter_id",
        "cursor_position",
        "scroll_top",
        "updated_at",
    }.issubset(schema["edit_sessions"])

    version_column = next(
        row for row in conn.execute("PRAGMA table_info(chapters)").fetchall()
        if row[1] == "version"
    )
    assert version_column[2].upper() == "INTEGER"
    assert str(version_column[4]) == "1"
    assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1
    conn.close()


def test_v1_core_schema_repeated_migration_preserves_existing_rows(tmp_path):
    conn = connect(tmp_path / "preserve.db")
    migrate_core_schema(conn)
    conn.execute(
        """
        INSERT INTO works (id, title, author, word_count, created_at, updated_at)
        VALUES ('work-1', 'Work', '', 0, '2026-04-30T00:00:00+08:00', '2026-04-30T00:00:00+08:00')
        """
    )
    conn.execute(
        """
        INSERT INTO chapters (
            id, work_id, title, content, word_count, order_index, version, created_at, updated_at
        )
        VALUES (
            'chapter-1', 'work-1', '', '', 0, 1, 1,
            '2026-04-30T00:00:00+08:00', '2026-04-30T00:00:00+08:00'
        )
        """
    )
    conn.commit()

    migrate_core_schema(conn)

    assert conn.execute("SELECT COUNT(*) FROM works").fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM chapters").fetchone()[0] == 1
    assert conn.execute("SELECT version FROM chapters WHERE id = 'chapter-1'").fetchone()[0] == 1
    conn.close()


def test_v1_core_schema_migrates_legacy_chapter_columns(tmp_path):
    conn = connect(tmp_path / "legacy.db")
    conn.execute(
        """
        CREATE TABLE works (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL DEFAULT '',
            author TEXT NOT NULL DEFAULT '',
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
            content TEXT
        )
        """
    )
    conn.execute(
        """
        INSERT INTO chapters (id, novel_id, number, title, content)
        VALUES ('chapter-1', 'work-1', 3, NULL, NULL)
        """
    )
    conn.commit()

    migrate_core_schema(conn)

    row = conn.execute(
        """
        SELECT work_id, title, content, word_count, order_index, version
        FROM chapters
        WHERE id = 'chapter-1'
        """
    ).fetchone()
    assert tuple(row) == ("work-1", "", "", 0, 3, 1)
    conn.close()
