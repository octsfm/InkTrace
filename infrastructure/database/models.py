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
    job_id TEXT NOT NULL DEFAULT '',
    run_id TEXT NOT NULL DEFAULT '',
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
    ,canonical_digest TEXT NOT NULL DEFAULT ''
    ,usage_status TEXT NOT NULL DEFAULT 'unknown'
    ,cost_status TEXT NOT NULL DEFAULT 'unknown'
    ,cost_currency TEXT NOT NULL DEFAULT ''
    ,estimated_cost_text TEXT
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

STYLE_PROFILES_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS style_profiles (
    profile_id TEXT PRIMARY KEY,
    work_id TEXT NOT NULL,
    source_type TEXT NOT NULL,
    source_ref TEXT DEFAULT '',
    source_text_hash TEXT DEFAULT '',
    source_text_length INTEGER DEFAULT 0,
    confidence REAL DEFAULT 0.0,
    low_confidence_reason TEXT DEFAULT '',
    avg_sentence_length REAL DEFAULT 0.0,
    sentence_length_variance REAL DEFAULT 0.0,
    short_sentence_ratio REAL DEFAULT 0.0,
    long_sentence_ratio REAL DEFAULT 0.0,
    compound_sentence_ratio REAL DEFAULT 0.0,
    avg_paragraph_length REAL DEFAULT 0.0,
    paragraph_length_variance REAL DEFAULT 0.0,
    dialogue_ratio REAL DEFAULT 0.0,
    psychological_ratio REAL DEFAULT 0.0,
    action_ratio REAL DEFAULT 0.0,
    description_ratio REAL DEFAULT 0.0,
    narrative_perspective TEXT DEFAULT '',
    tense_preference TEXT DEFAULT '',
    style_summary TEXT DEFAULT '',
    style_tags_json TEXT DEFAULT '[]',
    version INTEGER DEFAULT 1,
    status TEXT NOT NULL DEFAULT 'pending_confirm',
    created_at TEXT NOT NULL DEFAULT '',
    updated_at TEXT NOT NULL DEFAULT '',
    confirmed_at TEXT DEFAULT ''
)
"""

CHAPTER_MENTIONS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS chapter_mentions (
    mention_id TEXT PRIMARY KEY,
    chapter_id TEXT NOT NULL,
    work_id TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL DEFAULT '',
    entity_name_snapshot TEXT NOT NULL DEFAULT '',
    start_pos INTEGER NOT NULL DEFAULT 0,
    end_pos INTEGER NOT NULL DEFAULT 0,
    source TEXT NOT NULL DEFAULT 'user_input',
    ai_suggestion_id TEXT DEFAULT '',
    status TEXT NOT NULL DEFAULT 'active',
    is_active INTEGER NOT NULL DEFAULT 1,
    validation_detail TEXT DEFAULT '',
    created_at TEXT NOT NULL DEFAULT '',
    updated_at TEXT NOT NULL DEFAULT ''
)
"""

SELECTION_REWRITE_CANDIDATES_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS selection_rewrite_candidates (
    rewrite_id TEXT PRIMARY KEY,
    chapter_id TEXT NOT NULL,
    work_id TEXT NOT NULL,
    rewrite_mode TEXT NOT NULL,
    source_text TEXT NOT NULL,
    source_hash TEXT NOT NULL DEFAULT '',
    source_start_pos INTEGER NOT NULL DEFAULT 0,
    source_end_pos INTEGER NOT NULL DEFAULT 0,
    rewritten_text TEXT NOT NULL DEFAULT '',
    applied_text TEXT NOT NULL DEFAULT '',
    word_count_before INTEGER NOT NULL DEFAULT 0,
    word_count_after INTEGER NOT NULL DEFAULT 0,
    diff_summary TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'generating',
    model_role TEXT NOT NULL DEFAULT '',
    chapter_revision INTEGER NOT NULL DEFAULT 0,
    draft_revision INTEGER NOT NULL DEFAULT 0,
    draft_text_hash TEXT NOT NULL DEFAULT '',
    draft_length INTEGER NOT NULL DEFAULT 0,
    edited_before_apply INTEGER NOT NULL DEFAULT 0,
    context_before TEXT DEFAULT '',
    context_after TEXT DEFAULT '',
    error_code TEXT DEFAULT '',
    error_message TEXT DEFAULT '',
    request_id TEXT DEFAULT '',
    trace_id TEXT DEFAULT '',
    created_at TEXT NOT NULL DEFAULT '',
    applied_at TEXT DEFAULT ''
)
"""

AUTO_QUEUE_CONFIGS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS auto_queue_configs (
    config_id TEXT PRIMARY KEY,
    work_id TEXT NOT NULL UNIQUE,
    target_chapters INTEGER DEFAULT 0,
    target_word_count INTEGER DEFAULT 0,
    stop_at_sequence_end INTEGER DEFAULT 1,
    stop_on_blocking_review INTEGER DEFAULT 1,
    max_consecutive_blocking INTEGER DEFAULT 2,
    stop_on_budget_exceeded INTEGER DEFAULT 1,
    stop_on_foreshadow_premature INTEGER DEFAULT 1,
    max_consecutive_revision_failures INTEGER DEFAULT 3,
    budget_limit_tokens INTEGER DEFAULT 0,
    enabled INTEGER DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT '',
    updated_at TEXT NOT NULL DEFAULT ''
)
"""

AUTO_QUEUE_RUNS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS auto_queue_runs (
    run_id TEXT PRIMARY KEY,
    job_id TEXT DEFAULT '',
    config_id TEXT NOT NULL,
    work_id TEXT NOT NULL,
    multi_chapter_session_id TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    generated_count INTEGER DEFAULT 0,
    total_word_count INTEGER DEFAULT 0,
    consumed_tokens INTEGER DEFAULT 0,
    current_stop_evaluation_json TEXT DEFAULT '{}',
    stop_record_json TEXT DEFAULT '{}',
    stop_record_history_json TEXT DEFAULT '[]',
    resume_allowed INTEGER NOT NULL DEFAULT 1,
    current_candidate_story_state_json TEXT DEFAULT '{}',
    queue_state_snapshots_json TEXT DEFAULT '[]',
    consecutive_blocking_count INTEGER DEFAULT 0,
    consecutive_revision_failure_count INTEGER DEFAULT 0,
    error_code TEXT DEFAULT '',
    error_message TEXT DEFAULT '',
    request_id TEXT DEFAULT '',
    trace_id TEXT DEFAULT '',
    created_at TEXT NOT NULL DEFAULT '',
    updated_at TEXT NOT NULL DEFAULT '',
    started_at TEXT DEFAULT '',
    stopped_at TEXT DEFAULT '',
    finished_at TEXT DEFAULT ''
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

COST_BUDGETS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS cost_budgets (
    budget_id TEXT PRIMARY KEY,
    work_id TEXT NOT NULL DEFAULT '',
    budget_type TEXT NOT NULL,
    enabled INTEGER NOT NULL DEFAULT 1,
    inherit_global INTEGER NOT NULL DEFAULT 0,
    limit_value TEXT NOT NULL,
    currency TEXT NOT NULL DEFAULT '',
    alert_threshold TEXT NOT NULL DEFAULT '0.800000',
    revision INTEGER NOT NULL DEFAULT 1,
    updated_at TEXT NOT NULL,
    UNIQUE(work_id, budget_type)
)
"""

MODEL_PRICE_POLICIES_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS model_price_policies (
    policy_id TEXT PRIMARY KEY,
    work_id TEXT NOT NULL DEFAULT '',
    provider_name TEXT NOT NULL,
    model_name TEXT NOT NULL,
    enabled INTEGER NOT NULL DEFAULT 1,
    inherit_global INTEGER NOT NULL DEFAULT 0,
    input_price_per_1m TEXT NOT NULL,
    output_price_per_1m TEXT NOT NULL,
    currency TEXT NOT NULL,
    revision INTEGER NOT NULL DEFAULT 1,
    updated_at TEXT NOT NULL,
    UNIQUE(work_id, provider_name, model_name)
)
"""

COST_CONTROL_RECEIPTS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS cost_control_receipts (
    receipt_id TEXT PRIMARY KEY,
    key_hash TEXT NOT NULL UNIQUE,
    request_hash TEXT NOT NULL,
    response_json TEXT NOT NULL,
    audit_status TEXT NOT NULL DEFAULT 'completion_pending',
    post_event_ref TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
)
"""

COST_CONTROL_AUDITS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS cost_control_audits (
    event_ref TEXT PRIMARY KEY,
    event_key TEXT NOT NULL UNIQUE,
    event_stage TEXT NOT NULL,
    user_id_hash TEXT NOT NULL,
    resource_hash TEXT NOT NULL,
    old_value_hash TEXT NOT NULL DEFAULT '',
    new_value_hash TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL
)
"""

ANALYSIS_METRICS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS analysis_metrics (
    work_id TEXT NOT NULL,
    metric_type TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    source_fingerprint TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'ready',
    error_code TEXT NOT NULL DEFAULT '',
    stale INTEGER NOT NULL DEFAULT 0,
    computed_at TEXT NOT NULL,
    PRIMARY KEY(work_id, metric_type)
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
    conn.execute(STYLE_PROFILES_TABLE_SQL)
    conn.execute(CHAPTER_MENTIONS_TABLE_SQL)
    conn.execute(SELECTION_REWRITE_CANDIDATES_TABLE_SQL)
    conn.execute(AUTO_QUEUE_CONFIGS_TABLE_SQL)
    conn.execute(AUTO_QUEUE_RUNS_TABLE_SQL)
    conn.execute(CHAPTER_CHUNKS_TABLE_SQL)
    conn.execute(CHUNK_EMBEDDINGS_TABLE_SQL)
    conn.execute(VECTOR_INDEX_STATUS_TABLE_SQL)
    conn.execute(COST_BUDGETS_TABLE_SQL)
    conn.execute(MODEL_PRICE_POLICIES_TABLE_SQL)
    conn.execute(COST_CONTROL_RECEIPTS_TABLE_SQL)
    conn.execute(COST_CONTROL_AUDITS_TABLE_SQL)
    conn.execute(ANALYSIS_METRICS_TABLE_SQL)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_multi_chapter_work_id ON multi_chapter_sessions(work_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_multi_chapter_status ON multi_chapter_sessions(status)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_citations_candidate_version ON citation_links(candidate_version_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_citations_candidate_draft ON citation_links(candidate_draft_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_citations_source ON citation_links(source_type, source_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_style_profiles_work ON style_profiles(work_id, status)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_mentions_chapter ON chapter_mentions(chapter_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_mentions_entity ON chapter_mentions(entity_type, entity_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_mentions_work ON chapter_mentions(work_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_rewrite_chapter ON selection_rewrite_candidates(chapter_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_rewrite_chapter_status ON selection_rewrite_candidates(chapter_id, status)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_rewrite_work ON selection_rewrite_candidates(work_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_auto_queue_runs_work ON auto_queue_runs(work_id, status)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_chapter_chunks_work_id ON chapter_chunks(work_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_chapter_chunks_chapter_id ON chapter_chunks(work_id, chapter_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_chapter_chunks_stale_status ON chapter_chunks(work_id, stale_status)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_chunk_embeddings_chunk_id ON chunk_embeddings(chunk_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_chunk_embeddings_work_id ON chunk_embeddings(work_id)")
    _add_column_if_missing(conn, "auto_queue_runs", "job_id", "TEXT DEFAULT ''")
    _add_column_if_missing(conn, "auto_queue_runs", "stop_record_history_json", "TEXT DEFAULT '[]'")
    _add_column_if_missing(conn, "auto_queue_runs", "resume_allowed", "INTEGER NOT NULL DEFAULT 1")
    _add_column_if_missing(conn, "auto_queue_configs", "revision", "INTEGER NOT NULL DEFAULT 1")
    _add_column_if_missing(conn, "analysis_metrics", "stale", "INTEGER NOT NULL DEFAULT 0")

    _add_column_if_missing(conn, "llm_call_logs", "work_id", "TEXT NOT NULL DEFAULT ''")
    _add_column_if_missing(conn, "llm_call_logs", "trace_id", "TEXT NOT NULL DEFAULT ''")
    _add_column_if_missing(conn, "llm_call_logs", "session_id", "TEXT NOT NULL DEFAULT ''")
    _add_column_if_missing(conn, "llm_call_logs", "step_id", "TEXT NOT NULL DEFAULT ''")
    _add_column_if_missing(conn, "llm_call_logs", "job_id", "TEXT NOT NULL DEFAULT ''")
    _add_column_if_missing(conn, "llm_call_logs", "run_id", "TEXT NOT NULL DEFAULT ''")
    _add_column_if_missing(conn, "llm_call_logs", "estimated_cost", "REAL NOT NULL DEFAULT 0.0")
    _add_column_if_missing(conn, "llm_call_logs", "price_snapshot_json", "TEXT NOT NULL DEFAULT '{}'")
    _add_column_if_missing(conn, "llm_call_logs", "canonical_digest", "TEXT NOT NULL DEFAULT ''")
    _add_column_if_missing(conn, "llm_call_logs", "usage_status", "TEXT NOT NULL DEFAULT 'unknown'")
    _add_column_if_missing(conn, "llm_call_logs", "cost_status", "TEXT NOT NULL DEFAULT 'unknown'")
    _add_column_if_missing(conn, "llm_call_logs", "cost_currency", "TEXT NOT NULL DEFAULT ''")
    _add_column_if_missing(conn, "llm_call_logs", "estimated_cost_text", "TEXT")
    _add_column_if_missing(conn, "candidate_drafts", "applied_at", "TEXT DEFAULT NULL")
    _add_column_if_missing(conn, "candidate_drafts", "revision_count", "INTEGER NOT NULL DEFAULT 0")
    _add_column_if_missing(conn, "citation_links", "work_id", "TEXT NOT NULL DEFAULT ''")
    _add_column_if_missing(conn, "citation_links", "source_hash", "TEXT NOT NULL DEFAULT ''")
    _add_column_if_missing(conn, "selection_rewrite_candidates", "draft_text_hash", "TEXT NOT NULL DEFAULT ''")
    _add_column_if_missing(conn, "selection_rewrite_candidates", "draft_length", "INTEGER NOT NULL DEFAULT 0")

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
