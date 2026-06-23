from infrastructure.database.models import initialize_schema
from infrastructure.database.v1 import connect


def _table_columns(conn, table_name: str) -> set[str]:
    return {str(row[1]) for row in conn.execute(f"PRAGMA table_info({table_name})").fetchall()}


def test_runtime_schema_creates_p2_s0_ai_tables_and_columns(tmp_path):
    conn = connect(tmp_path / "runtime.db")

    initialize_schema(conn)
    initialize_schema(conn)

    table_names = {
        str(row[0])
        for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()
    }

    assert "llm_call_logs" in table_names
    assert "candidate_drafts" in table_names
    assert "citation_links" in table_names
    assert "multi_chapter_sessions" in table_names
    assert "chapter_chunks" in table_names
    assert "chunk_embeddings" in table_names
    assert "vector_index_status" in table_names
    assert {
        "request_id",
        "work_id",
        "trace_id",
        "session_id",
        "step_id",
        "provider_name",
        "model_name",
        "model_role",
        "estimated_cost",
        "price_snapshot_json",
        "started_at",
        "finished_at",
    }.issubset(_table_columns(conn, "llm_call_logs"))
    assert {
        "candidate_draft_id",
        "work_id",
        "chapter_id",
        "status",
        "applied_at",
        "revision_count",
        "created_at",
        "updated_at",
    }.issubset(_table_columns(conn, "candidate_drafts"))
    assert {
        "citation_id",
        "candidate_version_id",
        "candidate_draft_id",
        "source_type",
        "source_id",
        "source_name_snapshot",
        "source_excerpt",
        "verification_status",
        "verification_detail",
        "confidence",
        "verified_at",
        "created_at",
    }.issubset(_table_columns(conn, "citation_links"))
    assert {
        "session_id",
        "work_id",
        "start_chapter_id",
        "target_chapters",
        "current_index",
        "status",
        "per_chapter_status_json",
        "agent_session_ids_json",
        "candidate_draft_ids_json",
        "candidate_story_state_json",
        "queue_state_snapshots_json",
        "warning_codes_json",
        "error_code",
        "error_message",
        "paused_reason",
        "blocked_source",
        "blocked_reason_code",
        "request_id",
        "trace_id",
        "created_by",
        "created_at",
        "updated_at",
        "started_at",
        "finished_at",
        "auto_mode",
        "pending_pause",
        "metadata_json",
    }.issubset(_table_columns(conn, "multi_chapter_sessions"))
    assert {
        "chunk_id",
        "work_id",
        "chapter_id",
        "chapter_order",
        "chunk_index",
        "text_excerpt",
        "content_hash",
        "token_count",
        "start_offset",
        "end_offset",
        "source",
        "index_status",
        "stale_status",
        "created_at",
        "updated_at",
    }.issubset(_table_columns(conn, "chapter_chunks"))
    assert {
        "embedding_id",
        "chunk_id",
        "work_id",
        "chapter_id",
        "embedding_model",
        "embedding_provider",
        "embedding_version",
        "vector_id",
        "content_hash",
        "status",
        "created_at",
        "updated_at",
    }.issubset(_table_columns(conn, "chunk_embeddings"))
    assert {
        "work_id",
        "index_status",
        "stale_status",
        "chunk_count",
        "active_embedding_count",
        "updated_at",
    }.issubset(_table_columns(conn, "vector_index_status"))
    conn.close()
