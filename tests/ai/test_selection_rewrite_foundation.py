from __future__ import annotations

from infrastructure.database.models import initialize_schema
from infrastructure.database.v1 import connect
from domain.entities.ai import models as ai_models


def test_selection_rewrite_models_expose_draft_snapshot_fields() -> None:
    mode = ai_models.SelectionRewriteMode.REWRITE
    status = ai_models.SelectionRewriteStatus.PENDING
    candidate = ai_models.SelectionRewriteCandidate(
        rewrite_id="srw_001",
        chapter_id="chapter_001",
        work_id="work_001",
        rewrite_mode=mode,
        source_text="他走进房间",
        source_hash="hash_source",
        source_start_pos=3,
        source_end_pos=8,
        rewritten_text="他缓步走进房间",
        applied_text="",
        word_count_before=5,
        word_count_after=7,
        diff_summary="补充了动作细节",
        status=status,
        model_role="rewriter",
        chapter_revision=3,
        draft_revision=12,
        draft_text_hash="hash_draft",
        draft_length=120,
        edited_before_apply=False,
        context_before="前文",
        context_after="后文",
        error_code="",
        error_message="",
        request_id="req_001",
        trace_id="trace_001",
        created_at="2026-07-03T12:00:00Z",
        applied_at="",
    )

    assert mode.value == "rewrite"
    assert status.value == "pending"
    assert candidate.draft_text_hash == "hash_draft"
    assert candidate.draft_length == 120


def test_initialize_schema_creates_selection_rewrite_table_with_draft_snapshot_columns(tmp_path) -> None:
    db_path = tmp_path / "selection_rewrite.db"
    conn = connect(db_path)
    try:
        initialize_schema(conn)
        columns = {
            str(row[1])
            for row in conn.execute("PRAGMA table_info(selection_rewrite_candidates)").fetchall()
        }
    finally:
        conn.close()

    assert "rewrite_id" in columns
    assert "draft_text_hash" in columns
    assert "draft_length" in columns
