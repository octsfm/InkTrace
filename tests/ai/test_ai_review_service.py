from __future__ import annotations

from pathlib import Path

import pytest

from application.services.ai.ai_review_service import AIReviewApplicationService
from application.services.v1.chapter_service import ChapterService
from application.services.v1.work_service import WorkService
from domain.entities.ai.models import (
    AIReviewRequest,
    AIReviewStatus,
    AIReviewTargetType,
    CandidateDraft,
    CandidateDraftStatus,
    CandidateDraftValidationStatus,
)
from infrastructure.ai.providers.fake_reviewer import FakeReviewer, FailingReviewer
from infrastructure.database.repositories import ChapterRepo, WorkRepo
from infrastructure.database.repositories.ai.file_ai_review_store import FileAIReviewStore
from infrastructure.database.repositories.ai.file_candidate_draft_store import FileCandidateDraftStore
from infrastructure.database.repositories.ai.file_initialization_store import FileInitializationStore
from infrastructure.database.repositories.ai.file_story_memory_store import FileStoryMemoryStore
from infrastructure.database.repositories.ai.file_story_state_store import FileStoryStateStore


def _build_services(tmp_path: Path):
    work_repo = WorkRepo()
    chapter_repo = ChapterRepo()
    work_service = WorkService(work_repo=work_repo, chapter_repo=chapter_repo)
    chapter_service = ChapterService(chapter_repo=chapter_repo, work_repo=work_repo)

    candidate_store = FileCandidateDraftStore(tmp_path / "candidate_drafts.json")
    review_store = FileAIReviewStore(tmp_path / "ai_reviews.json")
    init_store = FileInitializationStore(tmp_path / "initializations.json")
    memory_store = FileStoryMemoryStore(tmp_path / "memory.json")
    state_store = FileStoryStateStore(tmp_path / "state.json")

    return work_service, chapter_service, candidate_store, review_store, init_store, memory_store, state_store


def _seed_candidate(tmp_path: Path) -> tuple[str, str, str]:
    work_service, chapter_service, candidate_store, _, _, _, _ = _build_services(tmp_path)
    work = work_service.create_work("S8 作品", "作者")
    chapter = chapter_service.list_chapters(work.id)[0]
    chapter = chapter_service.update_chapter(
        chapter.id.value,
        title="第一章",
        content="顾迟在海边灯塔醒来，听见潮声像旧日誓言。",
        expected_version=1,
    )
    draft = CandidateDraft(
        candidate_draft_id="cd_test",
        work_id=work.id,
        chapter_id=chapter.id.value,
        source_context_pack_id="cp_x",
        source_job_id="job_x",
        status=CandidateDraftStatus.PENDING_REVIEW,
        content="续写候选稿：顾迟推开门，灯塔的光像呼吸一样明灭。",
        content_preview="续写候选稿：顾迟推开门，灯塔的光像呼吸一样明灭。",
        word_count=10,
        char_count=30,
        validation_status=CandidateDraftValidationStatus.PASSED,
        created_by="user_action",
        created_at="2026-05-11T00:00:00+00:00",
        updated_at="2026-05-11T00:00:00+00:00",
        metadata={},
    )
    candidate_store.save(draft)
    return work.id, chapter.id.value, draft.candidate_draft_id


def test_review_candidate_draft_creates_ai_review_result_without_modifying_candidate_or_chapter(tmp_path: Path) -> None:
    work_id, chapter_id, candidate_id = _seed_candidate(tmp_path)
    work_service, chapter_service, candidate_store, review_store, init_store, memory_store, state_store = _build_services(tmp_path)
    reviewer = FakeReviewer()
    service = AIReviewApplicationService(
        work_service=work_service,
        chapter_service=chapter_service,
        candidate_draft_repository=candidate_store,
        ai_review_repository=review_store,
        reviewer=reviewer,
        initialization_repository=init_store,
        story_memory_repository=memory_store,
        story_state_repository=state_store,
    )

    before_candidate = candidate_store.get(candidate_id)
    before_chapter = [c for c in chapter_service.list_chapters(work_id) if c.id.value == chapter_id][0]

    result = service.review_candidate_draft(candidate_id, created_by="user_action", user_instruction="关注逻辑一致性")

    review = service.get_ai_review(result.review_id)
    after_candidate = candidate_store.get(candidate_id)
    after_chapter = [c for c in chapter_service.list_chapters(work_id) if c.id.value == chapter_id][0]

    assert result.status == AIReviewStatus.COMPLETED.value
    assert review.review_id == result.review_id
    assert review.candidate_draft_id == candidate_id
    assert reviewer.calls == 1
    assert review.issues
    assert after_candidate.model_dump() == before_candidate.model_dump()
    assert after_chapter.content == before_chapter.content


def test_review_context_is_lightweight_and_does_not_require_context_pack(tmp_path: Path) -> None:
    _, _, candidate_id = _seed_candidate(tmp_path)
    work_service, chapter_service, candidate_store, review_store, init_store, memory_store, state_store = _build_services(tmp_path)
    reviewer = FakeReviewer()
    service = AIReviewApplicationService(
        work_service=work_service,
        chapter_service=chapter_service,
        candidate_draft_repository=candidate_store,
        ai_review_repository=review_store,
        reviewer=reviewer,
        initialization_repository=init_store,
        story_memory_repository=memory_store,
        story_state_repository=state_store,
    )

    ctx = service.build_review_context(candidate_id, review_mode="candidate_draft_review", user_instruction="")

    assert "candidate_draft_content" in ctx
    assert "context_pack" not in ctx
    assert len(ctx.get("candidate_draft_content", "")) <= 500


def test_reviewer_failure_returns_review_failed_and_still_persists_result(tmp_path: Path) -> None:
    _, _, candidate_id = _seed_candidate(tmp_path)
    work_service, chapter_service, candidate_store, review_store, init_store, memory_store, state_store = _build_services(tmp_path)
    reviewer = FailingReviewer()
    service = AIReviewApplicationService(
        work_service=work_service,
        chapter_service=chapter_service,
        candidate_draft_repository=candidate_store,
        ai_review_repository=review_store,
        reviewer=reviewer,
        initialization_repository=init_store,
        story_memory_repository=memory_store,
        story_state_repository=state_store,
    )

    result = service.review_candidate_draft(candidate_id, created_by="user_action", user_instruction="")

    assert result.status == AIReviewStatus.FAILED.value
    saved = service.get_ai_review(result.review_id)
    assert saved.status == AIReviewStatus.FAILED


def test_review_degraded_candidate_returns_completed_with_warnings(tmp_path: Path) -> None:
    _, _, candidate_id = _seed_candidate(tmp_path)
    work_service, chapter_service, candidate_store, review_store, init_store, memory_store, state_store = _build_services(tmp_path)
    reviewer = FakeReviewer()
    degraded = candidate_store.get(candidate_id).model_copy(
        update={
            "status": CandidateDraftStatus.PENDING_REVIEW,
            "metadata": {
                "context_pack_status": "degraded",
                "degraded_reason": "vector_recall_unavailable",
            },
        }
    )
    candidate_store.save(degraded)
    service = AIReviewApplicationService(
        work_service=work_service,
        chapter_service=chapter_service,
        candidate_draft_repository=candidate_store,
        ai_review_repository=review_store,
        reviewer=reviewer,
        initialization_repository=init_store,
        story_memory_repository=memory_store,
        story_state_repository=state_store,
    )

    result = service.review_candidate_draft(candidate_id, created_by="user_action", user_instruction="")

    assert result.status == AIReviewStatus.COMPLETED_WITH_WARNINGS.value
    assert "degraded_candidate_warning" in result.metadata["warnings"]


def test_list_ai_reviews_filters_by_work_and_candidate(tmp_path: Path) -> None:
    work_id, _, candidate_id = _seed_candidate(tmp_path)
    work_service, chapter_service, candidate_store, review_store, init_store, memory_store, state_store = _build_services(tmp_path)
    reviewer = FakeReviewer()
    service = AIReviewApplicationService(
        work_service=work_service,
        chapter_service=chapter_service,
        candidate_draft_repository=candidate_store,
        ai_review_repository=review_store,
        reviewer=reviewer,
        initialization_repository=init_store,
        story_memory_repository=memory_store,
        story_state_repository=state_store,
    )
    service.review_candidate_draft(candidate_id, created_by="user_action", user_instruction="")

    items = service.list_ai_reviews(work_id=work_id, candidate_draft_id=candidate_id)
    assert len(items) == 1


def test_validate_review_output_rejects_empty_payload(tmp_path: Path) -> None:
    _, _, candidate_id = _seed_candidate(tmp_path)
    work_service, chapter_service, candidate_store, review_store, init_store, memory_store, state_store = _build_services(tmp_path)
    reviewer = FakeReviewer()
    service = AIReviewApplicationService(
        work_service=work_service,
        chapter_service=chapter_service,
        candidate_draft_repository=candidate_store,
        ai_review_repository=review_store,
        reviewer=reviewer,
        initialization_repository=init_store,
        story_memory_repository=memory_store,
        story_state_repository=state_store,
    )

    with pytest.raises(ValueError, match="review_output_invalid"):
        service.validate_review_output({})


def test_review_request_struct_fields(tmp_path: Path) -> None:
    request = AIReviewRequest(
        work_id="w",
        chapter_id="c",
        candidate_draft_id="cd",
        review_target_type=AIReviewTargetType.CANDIDATE_DRAFT,
        review_target_ref="cd:cd",
        review_mode="candidate_draft_review",
        created_by="user_action",
    )
    assert request.review_mode == "candidate_draft_review"
    assert request.review_scope == "basic_quality+apply_risk"
