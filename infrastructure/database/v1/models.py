"""V1.1 Workbench core schema baseline.

The migration entry here is intentionally limited to Stage 0 infrastructure:
it creates empty core tables only and performs no business writes.
"""

from __future__ import annotations

import sqlite3


WORKS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS works (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL DEFAULT '',
    author TEXT NOT NULL DEFAULT '',
    word_count INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
)
"""


CHAPTERS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS chapters (
    id TEXT PRIMARY KEY,
    work_id TEXT NOT NULL,
    title TEXT NOT NULL DEFAULT '',
    content TEXT NOT NULL DEFAULT '',
    word_count INTEGER NOT NULL DEFAULT 0,
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
    last_open_chapter_id TEXT,
    cursor_position INTEGER NOT NULL DEFAULT 0,
    scroll_top INTEGER NOT NULL DEFAULT 0,
    updated_at TEXT NOT NULL,
    FOREIGN KEY(work_id) REFERENCES works(id) ON DELETE CASCADE,
    FOREIGN KEY(last_open_chapter_id) REFERENCES chapters(id) ON DELETE SET NULL
)
"""


INDEX_STATEMENTS = (
    "CREATE INDEX IF NOT EXISTS idx_v1_chapters_work_order ON chapters(work_id, order_index)",
)


CORE_TABLES = ("works", "chapters", "edit_sessions")


def _table_has_columns(conn: sqlite3.Connection, table_name: str, columns: set[str]) -> bool:
    rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    existing_columns = {str(row[1]) for row in rows}
    return columns.issubset(existing_columns)


def migrate_core_schema(conn: sqlite3.Connection) -> None:
    """Create the V1.1 core tables if they do not exist."""
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute(WORKS_TABLE_SQL)
    conn.execute(CHAPTERS_TABLE_SQL)
    conn.execute(EDIT_SESSIONS_TABLE_SQL)
    if _table_has_columns(conn, "chapters", {"work_id", "order_index"}):
        for statement in INDEX_STATEMENTS:
            conn.execute(statement)
    conn.commit()


def verify_core_schema(conn: sqlite3.Connection) -> dict[str, set[str]]:
    """Return existing columns for the Stage 0 core tables."""
    schema: dict[str, set[str]] = {}
    for table_name in CORE_TABLES:
        rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
        schema[table_name] = {str(row[1]) for row in rows}
    return schema
