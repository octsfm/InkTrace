"""V1.1 Workbench core schema migration."""

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

WORK_OUTLINES_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS work_outlines (
    id TEXT PRIMARY KEY,
    work_id TEXT NOT NULL UNIQUE,
    content_text TEXT NOT NULL DEFAULT '',
    content_tree_json TEXT NOT NULL DEFAULT '[]',
    version INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY(work_id) REFERENCES works(id) ON DELETE CASCADE
)
"""


CHAPTER_OUTLINES_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS chapter_outlines (
    id TEXT PRIMARY KEY,
    chapter_id TEXT NOT NULL UNIQUE,
    content_text TEXT NOT NULL DEFAULT '',
    content_tree_json TEXT NOT NULL DEFAULT '[]',
    version INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY(chapter_id) REFERENCES chapters(id) ON DELETE CASCADE
)
"""


TIMELINE_EVENTS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS timeline_events (
    id TEXT PRIMARY KEY,
    work_id TEXT NOT NULL,
    order_index INTEGER NOT NULL,
    title TEXT NOT NULL DEFAULT '',
    description TEXT NOT NULL DEFAULT '',
    chapter_id TEXT,
    version INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY(work_id) REFERENCES works(id) ON DELETE CASCADE,
    FOREIGN KEY(chapter_id) REFERENCES chapters(id) ON DELETE SET NULL
)
"""


FORESHADOWS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS foreshadows (
    id TEXT PRIMARY KEY,
    work_id TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'open',
    title TEXT NOT NULL DEFAULT '',
    description TEXT NOT NULL DEFAULT '',
    introduced_chapter_id TEXT,
    resolved_chapter_id TEXT,
    version INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY(work_id) REFERENCES works(id) ON DELETE CASCADE,
    FOREIGN KEY(introduced_chapter_id) REFERENCES chapters(id) ON DELETE SET NULL,
    FOREIGN KEY(resolved_chapter_id) REFERENCES chapters(id) ON DELETE SET NULL
)
"""


CHARACTERS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS characters (
    id TEXT PRIMARY KEY,
    work_id TEXT NOT NULL,
    name TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    aliases_json TEXT NOT NULL DEFAULT '[]',
    version INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY(work_id) REFERENCES works(id) ON DELETE CASCADE
)
"""


INDEX_STATEMENTS = (
    "CREATE INDEX IF NOT EXISTS idx_v1_chapters_work_order ON chapters(work_id, order_index)",
    "CREATE INDEX IF NOT EXISTS idx_v1_timeline_events_work_order ON timeline_events(work_id, order_index)",
    "CREATE INDEX IF NOT EXISTS idx_v1_foreshadows_work_status ON foreshadows(work_id, status)",
    "CREATE INDEX IF NOT EXISTS idx_v1_characters_work_name ON characters(work_id, name)",
)


CORE_TABLES = (
    "works",
    "chapters",
    "edit_sessions",
    "work_outlines",
    "chapter_outlines",
    "timeline_events",
    "foreshadows",
    "characters",
)


def _table_columns(conn: sqlite3.Connection, table_name: str) -> set[str]:
    rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    return {str(row[1]) for row in rows}


def _table_has_columns(conn: sqlite3.Connection, table_name: str, columns: set[str]) -> bool:
    return columns.issubset(_table_columns(conn, table_name))


def _add_column_if_missing(conn: sqlite3.Connection, table_name: str, column_name: str, definition: str) -> None:
    if column_name not in _table_columns(conn, table_name):
        conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {definition}")


def _ensure_works_columns(conn: sqlite3.Connection) -> None:
    existing_columns = _table_columns(conn, "works")
    _add_column_if_missing(conn, "works", "title", "TEXT NOT NULL DEFAULT ''")
    _add_column_if_missing(conn, "works", "author", "TEXT NOT NULL DEFAULT ''")
    _add_column_if_missing(conn, "works", "word_count", "INTEGER NOT NULL DEFAULT 0")
    _add_column_if_missing(conn, "works", "created_at", "TEXT NOT NULL DEFAULT ''")
    _add_column_if_missing(conn, "works", "updated_at", "TEXT NOT NULL DEFAULT ''")
    if "current_word_count" in existing_columns:
        conn.execute(
            "UPDATE works SET word_count = current_word_count WHERE word_count = 0 AND current_word_count IS NOT NULL"
        )
    conn.execute("UPDATE works SET title = '' WHERE title IS NULL")
    conn.execute("UPDATE works SET author = '' WHERE author IS NULL")
    conn.execute("UPDATE works SET word_count = 0 WHERE word_count IS NULL")
    conn.execute("UPDATE works SET created_at = '' WHERE created_at IS NULL")
    conn.execute("UPDATE works SET updated_at = '' WHERE updated_at IS NULL")


def _ensure_chapters_columns(conn: sqlite3.Connection) -> None:
    existing_columns = _table_columns(conn, "chapters")
    _add_column_if_missing(conn, "chapters", "work_id", "TEXT")
    _add_column_if_missing(conn, "chapters", "title", "TEXT NOT NULL DEFAULT ''")
    _add_column_if_missing(conn, "chapters", "content", "TEXT NOT NULL DEFAULT ''")
    _add_column_if_missing(conn, "chapters", "word_count", "INTEGER NOT NULL DEFAULT 0")
    _add_column_if_missing(conn, "chapters", "order_index", "INTEGER")
    _add_column_if_missing(conn, "chapters", "version", "INTEGER NOT NULL DEFAULT 1")
    _add_column_if_missing(conn, "chapters", "created_at", "TEXT NOT NULL DEFAULT ''")
    _add_column_if_missing(conn, "chapters", "updated_at", "TEXT NOT NULL DEFAULT ''")

    if "novel_id" in existing_columns:
        conn.execute("UPDATE chapters SET work_id = novel_id WHERE work_id IS NULL OR work_id = ''")
    if "chapter_number" in existing_columns:
        conn.execute("UPDATE chapters SET order_index = chapter_number WHERE order_index IS NULL")
    if "number" in existing_columns:
        conn.execute("UPDATE chapters SET order_index = number WHERE order_index IS NULL")
    conn.execute("UPDATE chapters SET title = '' WHERE title IS NULL")
    conn.execute("UPDATE chapters SET content = '' WHERE content IS NULL")
    conn.execute("UPDATE chapters SET word_count = 0 WHERE word_count IS NULL")
    conn.execute("UPDATE chapters SET order_index = 1 WHERE order_index IS NULL")
    conn.execute("UPDATE chapters SET version = 1 WHERE version IS NULL")
    conn.execute("UPDATE chapters SET created_at = '' WHERE created_at IS NULL")
    conn.execute("UPDATE chapters SET updated_at = '' WHERE updated_at IS NULL")


def _ensure_edit_sessions_columns(conn: sqlite3.Connection) -> None:
    _add_column_if_missing(conn, "edit_sessions", "last_open_chapter_id", "TEXT")
    _add_column_if_missing(conn, "edit_sessions", "cursor_position", "INTEGER NOT NULL DEFAULT 0")
    _add_column_if_missing(conn, "edit_sessions", "scroll_top", "INTEGER NOT NULL DEFAULT 0")
    _add_column_if_missing(conn, "edit_sessions", "updated_at", "TEXT NOT NULL DEFAULT ''")
    conn.execute("UPDATE edit_sessions SET cursor_position = 0 WHERE cursor_position IS NULL")
    conn.execute("UPDATE edit_sessions SET scroll_top = 0 WHERE scroll_top IS NULL")
    conn.execute("UPDATE edit_sessions SET updated_at = '' WHERE updated_at IS NULL")


def _ensure_core_columns(conn: sqlite3.Connection) -> None:
    _ensure_works_columns(conn)
    _ensure_chapters_columns(conn)
    _ensure_edit_sessions_columns(conn)
    _ensure_structured_asset_columns(conn)


def _ensure_structured_asset_columns(conn: sqlite3.Connection) -> None:
    for table_name, columns in {
        "work_outlines": {
            "content_text": "TEXT NOT NULL DEFAULT ''",
            "content_tree_json": "TEXT NOT NULL DEFAULT '[]'",
            "version": "INTEGER NOT NULL DEFAULT 1",
            "created_at": "TEXT NOT NULL DEFAULT ''",
            "updated_at": "TEXT NOT NULL DEFAULT ''",
        },
        "chapter_outlines": {
            "content_text": "TEXT NOT NULL DEFAULT ''",
            "content_tree_json": "TEXT NOT NULL DEFAULT '[]'",
            "version": "INTEGER NOT NULL DEFAULT 1",
            "created_at": "TEXT NOT NULL DEFAULT ''",
            "updated_at": "TEXT NOT NULL DEFAULT ''",
        },
        "timeline_events": {
            "title": "TEXT NOT NULL DEFAULT ''",
            "description": "TEXT NOT NULL DEFAULT ''",
            "chapter_id": "TEXT",
            "version": "INTEGER NOT NULL DEFAULT 1",
            "created_at": "TEXT NOT NULL DEFAULT ''",
            "updated_at": "TEXT NOT NULL DEFAULT ''",
        },
        "foreshadows": {
            "status": "TEXT NOT NULL DEFAULT 'open'",
            "title": "TEXT NOT NULL DEFAULT ''",
            "description": "TEXT NOT NULL DEFAULT ''",
            "introduced_chapter_id": "TEXT",
            "resolved_chapter_id": "TEXT",
            "version": "INTEGER NOT NULL DEFAULT 1",
            "created_at": "TEXT NOT NULL DEFAULT ''",
            "updated_at": "TEXT NOT NULL DEFAULT ''",
        },
        "characters": {
            "name": "TEXT NOT NULL DEFAULT ''",
            "description": "TEXT NOT NULL DEFAULT ''",
            "aliases_json": "TEXT NOT NULL DEFAULT '[]'",
            "version": "INTEGER NOT NULL DEFAULT 1",
            "created_at": "TEXT NOT NULL DEFAULT ''",
            "updated_at": "TEXT NOT NULL DEFAULT ''",
        },
    }.items():
        for column_name, definition in columns.items():
            _add_column_if_missing(conn, table_name, column_name, definition)
        if "version" in columns:
            conn.execute(f"UPDATE {table_name} SET version = 1 WHERE version IS NULL")


def migrate_core_schema(conn: sqlite3.Connection) -> None:
    """Create the V1.1 core tables if they do not exist."""
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute(WORKS_TABLE_SQL)
    conn.execute(CHAPTERS_TABLE_SQL)
    conn.execute(EDIT_SESSIONS_TABLE_SQL)
    conn.execute(WORK_OUTLINES_TABLE_SQL)
    conn.execute(CHAPTER_OUTLINES_TABLE_SQL)
    conn.execute(TIMELINE_EVENTS_TABLE_SQL)
    conn.execute(FORESHADOWS_TABLE_SQL)
    conn.execute(CHARACTERS_TABLE_SQL)
    _ensure_core_columns(conn)
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
