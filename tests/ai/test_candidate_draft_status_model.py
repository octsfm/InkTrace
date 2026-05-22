from __future__ import annotations

from domain.entities.ai.models import CandidateDraft, CandidateDraftStatus, CandidateDraftVersion, CandidateDraftVersionStatus


def test_candidate_draft_status_includes_stale_and_legacy_failure_states_are_not_formal_members() -> None:
    assert CandidateDraftStatus.STALE.value == "stale"
    assert "APPLY_FAILED" not in CandidateDraftStatus.__members__
    assert "VALIDATION_FAILED" not in CandidateDraftStatus.__members__
    assert "SAVE_FAILED" not in CandidateDraftStatus.__members__


def test_candidate_draft_compat_reads_legacy_failure_status_as_stale() -> None:
    draft = CandidateDraft(
        candidate_draft_id="cd_legacy",
        work_id="work_1",
        chapter_id="chapter_1",
        source_context_pack_id="cp_1",
        source_job_id="job_1",
        status="apply_failed",
        content="测试内容",
    )

    assert draft.status == CandidateDraftStatus.STALE


def test_p1s6_candidate_draft_and_version_expose_three_pointers_and_version_chain_fields() -> None:
    draft = CandidateDraft(
        candidate_draft_id="cd_p1s6",
        work_id="work_1",
        chapter_id="chapter_1",
        source_context_pack_id="cp_1",
        source_job_id="job_1",
        status=CandidateDraftStatus.PENDING_REVIEW,
        content="候选稿内容",
    )
    version = CandidateDraftVersion(
        candidate_version_id="ver_1",
        candidate_draft_id="cd_p1s6",
        work_id="work_1",
        chapter_id="chapter_1",
        agent_session_id="agent_session_1",
        version_no=1,
        status="generated",
        content="候选稿内容",
        content_summary="候选稿摘要",
        word_count=4,
        writing_task_id="wt_1",
        direction_plan_snapshot_id="snap_1",
        source_context_pack_id="cp_1",
    )

    assert draft.selected_version_id == ""
    assert draft.accepted_version_id == ""
    assert draft.applied_version_id == ""
    assert draft.latest_version_no == 0
    assert draft.revision_round == 0
    assert draft.max_revision_rounds == 1
    assert version.status == CandidateDraftVersionStatus.GENERATED
    assert version.parent_version_id == ""
