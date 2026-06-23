"""Runtime database schema delegates to the V1.1 Workbench schema source."""

from __future__ import annotations

import sqlite3

from infrastructure.database.v1.models import (
    CORE_TABLES,
    INDEX_STATEMENTS,
    migrate_core_schema,
    verify_core_schema,
)

LLM_CALL_LOGS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS llm_call_logs (
    request_id TEXT PRIMARY KEY,
    work_id TEXT NOT NULL DEFAULT '',
    trace_id TEXT NOT NULL DEFAULT '',
    session_id TEXT NOT NULL DEFAULT '',
    step_id TEXT NOT NULL DEFAULT '',
    prompt_key TEXT NOT NULL DEFAULT '',
    prompt_version TEXT NOT NULL DEFAULT '',
    model_role TEXT NOT NULL DEFAULT '',
    provider_name TEXT NOT NULL DEFAULT '',
    model_name TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'succeeded',
    error_code TEXT NOT NULL DEFAULT '',
    error_message TEXT NOT NULL DEFAULT '',
    attempt_no INTEGER NOT NULL DEFAULT 1,
    input_tokens INTEGER,
    output_tokens INTEGER,
    total_tokens INTEGER,
    estimated_cost REAL NOT NULL DEFAULT 0.0,
    price_snapshot_json TEXT NOT NULL DEFAULT '{}',
    context_pack_snapshot_id TEXT NOT NULL DEFAULT '',
    output_schema_key TEXT NOT NULL DEFAULT '',
    started_at TEXT NOT NULL DEFAULT '',
    finished_at TEXT NOT NULL DEFAULT ''
)
"""

CANDIDATE_DRAFTS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS candidate_drafts (
    candidate_draft_id TEXT PRIMARY KEY,
    work_id TEXT NOT NULL,
    chapter_id TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'generated',
    applied_at TEXT DEFAULT NULL,
    revision_count INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT '',
    updated_at TEXT NOT NULL DEFAULT ''
)
"""

MULTI_CHAPTER_SESSIONS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS multi_chapter_sessions (
    session_id TEXT PRIMARY KEY,
    work_id TEXT NOT NULL,
    start_chapter_id TEXT NOT NULL,
    target_chapters INTEGER NOT NULL DEFAULT 1,
    current_index INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'pending',
    per_chapter_status_json TEXT NOT NULL DEFAULT '[]',
    agent_session_ids_json TEXT NOT NULL DEFAULT '[]',
    candidate_draft_ids_json TEXT NOT NULL DEFAULT '[]',
    candidate_story_state_json TEXT NOT NULL DEFAULT '{}',
    queue_state_snapshots_json TEXT NOT NULL DEFAULT '[]',
    warning_codes_json TEXT NOT NULL DEFAULT '[]',
    error_code TEXT NOT NULL DEFAULT '',
    error_message TEXT NOT NULL DEFAULT '',
    paused_reason TEXT NOT NULL DEFAULT '',
    blocked_source TEXT NOT NULL DEFAULT '',
    blocked_reason_code TEXT NOT NULL DEFAULT '',
    request_id TEXT NOT NULL DEFAULT '',
    trace_id TEXT NOT NULL DEFAULT '',
    created_by TEXT NOT NULL DEFAULT 'user_action',
    created_at TEXT NOT NULL DEFAULT '',
    updated_at TEXT NOT NULL DEFAULT '',
    started_at TEXT NOT NULL DEFAULT '',
    finished_at TEXT NOT NULL DEFAULT '',
    auto_mode TEXT NOT NULL DEFAULT 'safe',
    pending_pause INTEGER NOT NULL DEFAULT 0,
    metadata_json TEXT NOT NULL DEFAULT '{}'
)
"""

CITATION_LINKS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS citation_links (
    citation_id TEXT PRIMARY KEY,
    candidate_version_id TEXT NOT NULL,
    candidate_draft_id TEXT NOT NULL,
    work_id TEXT NOT NULL DEFAULT '',
    source_type TEXT NOT NULL,
    source_id TEXT NOT NULL DEFAULT '',
    source_hash TEXT NOT NULL DEFAULT '',
    source_name_snapshot TEXT DEFAULT '',
    source_span TEXT DEFAULT '',
    source_excerpt TEXT DEFAULT '',
    context_in_draft TEXT DEFAULT '',
    verification_status TEXT NOT NULL DEFAULT 'unknown_source',
    verification_detail TEXT DEFAULT '',
    confidence REAL DEFAULT 0.0,
    verified_at TEXT DEFAULT '',
    created_at TEXT NOT NULL
)
"""

CHAPTER_CHUNKS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS chapter_chunks (
    chunk_id TEXT PRIMARY KEY,
    work_id TEXT NOT NULL,
    chapter_id TEXT NOT NULL,
    chapter_order INTEGER NOT NULL DEFAULT 0,
    chunk_index INTEGER NOT NULL DEFAULT 0,
    text_excerpt TEXT NOT NULL DEFAULT '',
    content_hash TEXT NOT NULL DEFAULT '',
    token_count INTEGER NOT NULL DEFAULT 0,
    start_offset INTEGER NOT NULL DEFAULT 0,
    end_offset INTEGER NOT NULL DEFAULT 0,
    source TEXT NOT NULL DEFAULT 'confirmed_chapter',
    index_status TEXT NOT NULL DEFAULT 'active',
    stale_status TEXT NOT NULL DEFAULT 'fresh',
    created_at TEXT NOT NULL DEFAULT '',
    updated_at TEXT NOT NULL DEFAULT ''
)
"""

CHUNK_EMBEDDINGS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS chunk_embeddings (
    embedding_id TEXT PRIMARY KEY,
    chunk_id TEXT NOT NULL,
    work_id TEXT NOT NULL,
    chapter_id TEXT NOT NULL,
    embedding_model TEXT NOT NULL DEFAULT '',
    embedding_provider TEXT NOT NULL DEFAULT '',
    embedding_version TEXT NOT NULL DEFAULT '',
    vector_id TEXT NOT NULL DEFAULT '',
    content_hash TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'active',
    created_at TEXT NOT NULL DEFAULT '',
    updated_at TEXT NOT NULL DEFAULT ''
)
"""

VECTOR_INDEX_STATUS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS vector_index_status (
    work_id TEXT PRIMARY KEY,
    index_status TEXT NOT NULL DEFAULT 'missing',
    stale_status TEXT NOT NULL DEFAULT 'fresh',
    chunk_count INTEGER NOT NULL DEFAULT 0,
    active_embedding_count INTEGER NOT NULL DEFAULT 0,
    updated_at TEXT NOT NULL DEFAULT ''
)
"""


def _table_columns(conn: sqlite3.Connection, table_name: str) -> set[str]:
    rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    return {str(row[1]) for row in rows}


def _add_column_if_missing(conn: sqlite3.Connection, table_name: str, column_name: str, definition: str) -> None:
    if column_name not in _table_columns(conn, table_name):
        conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {definition}")


def migrate_ai_schema(conn: sqlite3.Connection) -> None:
    conn.execute(LLM_CALL_LOGS_TABLE_SQL)
    conn.execute(CANDIDATE_DRAFTS_TABLE_SQL)
    conn.execute(MULTI_CHAPTER_SESSIONS_TABLE_SQL)
    conn.execute(CITATION_LINKS_TABLE_SQL)
    conn.execute(CHAPTER_CHUNKS_TABLE_SQL)
    conn.execute(CHUNK_EMBEDDINGS_TABLE_SQL)
    conn.execute(VECTOR_INDEX_STATUS_TABLE_SQL)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_multi_chapter_work_id ON multi_chapter_sessions(work_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_multi_chapter_status ON multi_chapter_sessions(status)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_citations_candidate_version ON citation_links(candidate_version_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_citations_candidate_draft ON citation_links(candidate_draft_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_citations_source ON citation_links(source_type, source_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_chapter_chunks_work_id ON chapter_chunks(work_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_chapter_chunks_chapter_id ON chapter_chunks(work_id, chapter_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_chapter_chunks_stale_status ON chapter_chunks(work_id, stale_status)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_chunk_embeddings_chunk_id ON chunk_embeddings(chunk_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_chunk_embeddings_work_id ON chunk_embeddings(work_id)")

    _add_column_if_missing(conn, "llm_call_logs", "work_id", "TEXT NOT NULL DEFAULT ''")
    _add_column_if_missing(conn, "llm_call_logs", "trace_id", "TEXT NOT NULL DEFAULT ''")
    _add_column_if_missing(conn, "llm_call_logs", "session_id", "TEXT NOT NULL DEFAULT ''")
    _add_column_if_missing(conn, "llm_call_logs", "step_id", "TEXT NOT NULL DEFAULT ''")
    _add_column_if_missing(conn, "llm_call_logs", "estimated_cost", "REAL NOT NULL DEFAULT 0.0")
    _add_column_if_missing(conn, "llm_call_logs", "price_snapshot_json", "TEXT NOT NULL DEFAULT '{}'")
    _add_column_if_missing(conn, "candidate_drafts", "applied_at", "TEXT DEFAULT NULL")
    _add_column_if_missing(conn, "candidate_drafts", "revision_count", "INTEGER NOT NULL DEFAULT 0")
    _add_column_if_missing(conn, "citation_links", "work_id", "TEXT NOT NULL DEFAULT ''")
    _add_column_if_missing(conn, "citation_links", "source_hash", "TEXT NOT NULL DEFAULT ''")

    conn.execute("UPDATE candidate_drafts SET revision_count = 0 WHERE revision_count IS NULL")
    conn.execute("UPDATE llm_call_logs SET estimated_cost = 0.0 WHERE estimated_cost IS NULL")
    conn.execute("UPDATE llm_call_logs SET price_snapshot_json = '{}' WHERE price_snapshot_json IS NULL")
    conn.execute("UPDATE citation_links SET work_id = '' WHERE work_id IS NULL")
    conn.execute("UPDATE citation_links SET source_hash = '' WHERE source_hash IS NULL")


def initialize_schema(conn: sqlite3.Connection) -> None:
    migrate_core_schema(conn)
    migrate_ai_schema(conn)


__all__ = [
    "CORE_TABLES",
    "INDEX_STATEMENTS",
    "initialize_schema",
    "migrate_core_schema",
    "verify_core_schema",
]
