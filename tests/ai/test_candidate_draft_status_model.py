from __future__ import annotations

from domain.entities.ai.models import CandidateDraft, CandidateDraftStatus


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
