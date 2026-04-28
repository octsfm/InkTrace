from __future__ import annotations

import sqlite3


WORKS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS works (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    author TEXT NOT NULL DEFAULT '',
    current_word_count INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
)
"""


CHAPTERS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS chapters (
    id TEXT PRIMARY KEY,
    work_id TEXT NOT NULL,
    title TEXT NOT NULL,
    content TEXT NOT NULL DEFAULT '',
    chapter_number INTEGER NOT NULL,
    order_index INTEGER NOT NULL,
    version INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY(work_id) REFERENCES works(id) ON DELETE CASCADE
)
"""


EDIT_SESSIONS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS edit_sessions (
    work_id TEXT PRIMARY KEY,
    last_open_chapter_id TEXT NOT NULL DEFAULT '',
    cursor_position INTEGER NOT NULL DEFAULT 0,
    scroll_top INTEGER NOT NULL DEFAULT 0,
    updated_at TEXT NOT NULL,
    FOREIGN KEY(work_id) REFERENCES works(id) ON DELETE CASCADE
)
"""


INDEX_STATEMENTS = (
    "CREATE INDEX IF NOT EXISTS idx_chapters_work_order ON chapters(work_id, order_index)",
    "CREATE INDEX IF NOT EXISTS idx_chapters_work_number ON chapters(work_id, chapter_number)",
)


def _table_columns(conn: sqlite3.Connection, table_name: str) -> set[str]:
    rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    return {str(row[1]) for row in rows}


def _column_exists(conn: sqlite3.Connection, table_name: str, column_name: str) -> bool:
    return str(column_name) in _table_columns(conn, table_name)


def _ensure_legacy_chapters_compat(conn: sqlite3.Connection) -> None:
    columns = _table_columns(conn, "chapters")
    if not columns:
        return

    if "work_id" not in columns and "novel_id" in columns:
        conn.execute("ALTER TABLE chapters ADD COLUMN work_id TEXT")
        conn.execute("UPDATE chapters SET work_id = novel_id WHERE work_id IS NULL OR work_id = ''")

    if "chapter_number" not in columns and "number" in columns:
        conn.execute("ALTER TABLE chapters ADD COLUMN chapter_number INTEGER")
        conn.execute("UPDATE chapters SET chapter_number = number WHERE chapter_number IS NULL")

    if "order_index" not in columns:
        conn.execute("ALTER TABLE chapters ADD COLUMN order_index INTEGER")
        if _column_exists(conn, "chapters", "number"):
            conn.execute("UPDATE chapters SET order_index = number WHERE order_index IS NULL")
        conn.execute("UPDATE chapters SET order_index = 1 WHERE order_index IS NULL")

    if "version" not in columns:
        conn.execute("ALTER TABLE chapters ADD COLUMN version INTEGER")
        conn.execute("UPDATE chapters SET version = 1 WHERE version IS NULL")


def initialize_schema(conn: sqlite3.Connection) -> None:
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute(WORKS_TABLE_SQL)
    conn.execute(CHAPTERS_TABLE_SQL)
    conn.execute(EDIT_SESSIONS_TABLE_SQL)
    _ensure_legacy_chapters_compat(conn)
    for statement in INDEX_STATEMENTS:
        conn.execute(statement)
