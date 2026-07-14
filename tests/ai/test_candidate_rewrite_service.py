from __future__ import annotations

from pathlib import Path

from application.services.ai.ai_review_service import AIReviewApplicationService
from application.services.ai.candidate_rewrite_service import CandidateRewriteService
from application.services.v1.chapter_service import ChapterService
from application.services.v1.work_service import WorkService
from infrastructure.ai.providers.fake_reviewer import FakeReviewer
from infrastructure.ai.providers.fake_rewriter import FakeRewriter
from domain.entities.ai.models import (
    AIReviewResult,
    AIReviewRiskLevel,
    AIReviewStatus,
    CandidateDraft,
    CandidateDraftStatus,
    CandidateDraftValidationStatus,
    CandidateDraftVersion,
    CandidateDraftVersionStatus,
    RewriteRequestStatus,
    RewriteTriggerType,
    RevisionRoundStatus,
)
from infrastructure.database.repositories import ChapterRepo, WorkRepo
from infrastructure.database.repositories.ai.file_ai_review_store import FileAIReviewStore
from infrastructure.database.repositories.ai.file_candidate_draft_store import FileCandidateDraftStore


def _build_services(tmp_path: Path):
    work_repo = WorkRepo()
    chapter_repo = ChapterRepo()
    work_service = WorkService(work_repo=work_repo, chapter_repo=chapter_repo)
    chapter_service = ChapterService(chapter_repo=chapter_repo, work_repo=work_repo)
    candidate_store = FileCandidateDraftStore(tmp_path / "candidate_rewrite.json")
    review_store = FileAIReviewStore(tmp_path / "ai_reviews.json")
    rewrite_service = CandidateRewriteService(
        candidate_draft_repository=candidate_store,
        ai_review_repository=review_store,
        rewriter=FakeRewriter(),
    )
    return work_service, chapter_service, candidate_store, review_store, rewrite_service


def _seed_rewrite_context(tmp_path: Path):
    work_service, chapter_service, candidate_store, review_store, rewrite_service = _build_services(tmp_path)
    work = work_service.create_work("P1-S6 Rewrite", "作者")
    chapter = chapter_service.list_chapters(work.id)[0]
    chapter = chapter_service.update_chapter(
        chapter.id.value,
        title="第一章",
        content="顾迟在海边灯塔醒来。",
        expected_version=1,
    )
    draft = candidate_store.save(
        CandidateDraft(
            candidate_draft_id="cd_rewrite",
            work_id=work.id,
            chapter_id=chapter.id.value,
            agent_session_id="agent_session_writer",
            writing_task_id="wt_1",
            direction_plan_snapshot_id="snap_1",
            source_context_pack_id="cp_1",
            source_job_id="job_1",
            status=CandidateDraftStatus.PENDING_REVIEW,
            selected_version_id="ver_1",
            latest_version_no=1,
            revision_round=0,
            max_revision_rounds=1,
            content="v1 初稿：顾迟在海边灯塔醒来。",
            content_preview="v1 初稿：顾迟在海边灯塔醒来。",
            word_count=2,
            char_count=16,
            validation_status=CandidateDraftValidationStatus.PASSED,
            created_by="workflow",
            created_at="2026-05-21T00:00:00+00:00",
            updated_at="2026-05-21T00:00:00+00:00",
        )
    )
    candidate_store.save_version(
        CandidateDraftVersion(
            candidate_version_id="ver_1",
            candidate_draft_id=draft.candidate_draft_id,
            work_id=work.id,
            chapter_id=chapter.id.value,
            agent_session_id="agent_session_writer",
            version_no=1,
            status=CandidateDraftVersionStatus.REVIEW_COMPLETED,
            content="v1 初稿：顾迟在海边灯塔醒来。",
            content_summary="v1 摘要",
            word_count=2,
            writing_task_id="wt_1",
            direction_plan_snapshot_id="snap_1",
            source_context_pack_id="cp_1",
            created_by="writer_agent",
            created_at="2026-05-21T00:00:00+00:00",
            updated_at="2026-05-21T00:00:00+00:00",
        )
    )
    review_store.save(
        AIReviewResult(
            review_id="rv_1",
            work_id=work.id,
            chapter_id=chapter.id.value,
            candidate_draft_id=draft.candidate_draft_id,
            status=AIReviewStatus.COMPLETED,
            summary="建议加强父亲线索的明确性。",
            warnings=[],
            issues=[],
            suggestions=["加强父亲线索"],
            risk_level=AIReviewRiskLevel.MEDIUM,
            created_at="2026-05-21T00:05:00+00:00",
            metadata={},
        )
    )
    return work, chapter, candidate_store, review_store, rewrite_service


def test_candidate_rewrite_service_creates_rewrite_request_instruction_round_and_new_version(tmp_path: Path) -> None:
    _, _, candidate_store, _, rewrite_service = _seed_rewrite_context(tmp_path)

    result = rewrite_service.request_rewrite(
        candidate_draft_id="cd_rewrite",
        source_version_id="ver_1",
        trigger_type=RewriteTriggerType.REVIEW_BASED.value,
        review_report_id="rv_1",
        user_instruction="让父亲留下的海图更早出现。",
        user_id="user_1",
        user_action=True,
        idempotency_key="rewrite-review-1",
    )

    draft = candidate_store.get("cd_rewrite")
    versions = candidate_store.list_versions("cd_rewrite")
    rewrite_request = candidate_store.get_rewrite_request(result["rewrite_request_id"])
    instructions = candidate_store.list_rewrite_instructions(result["rewrite_request_id"])
    round_item = candidate_store.get_revision_round(result["revision_round_id"])

    assert draft.latest_version_no == 2
    assert draft.revision_round == 1
    assert draft.revision_count == 1
    assert draft.selected_version_id == "ver_2"
    assert draft.accepted_version_id == ""
    assert len(versions) == 2
    assert versions[-1].candidate_version_id == "ver_2"
    assert "父亲" in versions[-1].content
    assert rewrite_request.status == RewriteRequestStatus.COMPLETED
    assert rewrite_request.trigger_type == RewriteTriggerType.REVIEW_BASED
    assert instructions[0].instruction_source == "review+user_instruction"
    assert round_item.target_version_id == "ver_2"
    assert round_item.status == RevisionRoundStatus.COMPLETED


def test_candidate_rewrite_service_blocks_when_revision_round_limit_exceeded(tmp_path: Path) -> None:
    _, _, candidate_store, _, rewrite_service = _seed_rewrite_context(tmp_path)
    candidate_store.save(
        candidate_store.get("cd_rewrite").model_copy(
            update={"revision_round": 1, "max_revision_rounds": 1}
        )
    )

    try:
        rewrite_service.request_rewrite(
            candidate_draft_id="cd_rewrite",
            source_version_id="ver_1",
            trigger_type=RewriteTriggerType.USER_INSTRUCTION.value,
            user_instruction="再修一版。",
            user_id="user_1",
            user_action=True,
            idempotency_key="rewrite-limit-1",
        )
    except ValueError as exc:
        assert str(exc) == "max_revision_rounds_exceeded"
    else:
        raise AssertionError("rewrite beyond round limit should fail")


def test_candidate_rewrite_service_rejects_specific_version_without_rejecting_container(tmp_path: Path) -> None:
    _, _, candidate_store, _, rewrite_service = _seed_rewrite_context(tmp_path)

    draft = rewrite_service.reject_candidate_version(
        candidate_draft_id="cd_rewrite",
        candidate_version_id="ver_1",
        user_id="user_1",
        reason="当前版本节奏太慢",
        user_action=True,
    )
    version = candidate_store.get_version("ver_1")

    assert version.status == CandidateDraftVersionStatus.REJECTED
    assert draft.status == CandidateDraftStatus.REVISION_REQUESTED
    assert draft.applied_version_id == ""
