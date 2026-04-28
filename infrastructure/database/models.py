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


def initialize_schema(conn: sqlite3.Connection) -> None:
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute(WORKS_TABLE_SQL)
    conn.execute(CHAPTERS_TABLE_SQL)
    conn.execute(EDIT_SESSIONS_TABLE_SQL)
    for statement in INDEX_STATEMENTS:
        conn.execute(statement)
