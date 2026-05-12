from __future__ import annotations

from pathlib import Path

from application.services.ai.ai_review_service import AIReviewApplicationService
from application.services.ai.candidate_review_service import CandidateReviewService
from application.services.ai.continuation_workflow import MinimalContinuationWorkflow
from application.services.ai.context_pack_service import ContextPackService
from application.services.ai.initialization_service import InitializationApplicationService
from application.services.v1.chapter_service import ChapterService
from application.services.v1.work_service import WorkService
from domain.entities.ai.models import CandidateDraftStatus
from infrastructure.ai.providers.fake_reviewer import FailingReviewer
from infrastructure.ai.providers.fake_writer import FakeWriter
from infrastructure.database.repositories import ChapterRepo, WorkRepo
from infrastructure.database.repositories.ai.file_ai_job_store import FileAIJobStore
from infrastructure.database.repositories.ai.file_ai_review_store import FileAIReviewStore
from infrastructure.database.repositories.ai.file_candidate_draft_store import FileCandidateDraftStore
from infrastructure.database.repositories.ai.file_context_pack_store import FileContextPackStore
from infrastructure.database.repositories.ai.file_initialization_store import FileInitializationStore
from infrastructure.database.repositories.ai.file_story_memory_store import FileStoryMemoryStore
from infrastructure.database.repositories.ai.file_story_state_store import FileStoryStateStore


class _ShortOutputWriter(FakeWriter):
    def generate_candidate_text(self, *, context_pack, writing_task):
        payload = super().generate_candidate_text(context_pack=context_pack, writing_task=writing_task)
        payload["content"] = "todo"
        return payload


def _build_services(tmp_path: Path):
    work_repo = WorkRepo()
    chapter_repo = ChapterRepo()
    work_service = WorkService(work_repo=work_repo, chapter_repo=chapter_repo)
    chapter_service = ChapterService(chapter_repo=chapter_repo, work_repo=work_repo)
    job_store = FileAIJobStore(tmp_path / "jobs.json")
    candidate_store = FileCandidateDraftStore(tmp_path / "candidate_drafts.json")
    init_store = FileInitializationStore(tmp_path / "initializations.json")
    memory_store = FileStoryMemoryStore(tmp_path / "memory.json")
    state_store = FileStoryStateStore(tmp_path / "state.json")
    context_store = FileContextPackStore(tmp_path / "context_packs.json")
    review_store = FileAIReviewStore(tmp_path / "reviews.json")
    init_service = InitializationApplicationService(
        work_service=work_service,
        chapter_service=chapter_service,
        job_repository=job_store,
        step_repository=job_store,
        attempt_repository=job_store,
        initialization_repository=init_store,
        story_memory_repository=memory_store,
        story_state_repository=state_store,
    )
    context_service = ContextPackService(
        chapter_service=chapter_service,
        initialization_repository=init_store,
        story_memory_repository=memory_store,
        story_state_repository=state_store,
        context_pack_repository=context_store,
    )
    review_service = CandidateReviewService(
        candidate_draft_repository=candidate_store,
        chapter_service=chapter_service,
        initialization_service=init_service,
    )
    ai_review_service = AIReviewApplicationService(
        work_service=work_service,
        chapter_service=chapter_service,
        candidate_draft_repository=candidate_store,
        ai_review_repository=review_store,
        reviewer=FailingReviewer(),
        initialization_repository=init_store,
        story_memory_repository=memory_store,
        story_state_repository=state_store,
    )
    return (
        work_service,
        chapter_service,
        job_store,
        candidate_store,
        init_service,
        context_service,
        review_service,
        ai_review_service,
    )


def _seed_initialized_work(tmp_path: Path):
    (
        work_service,
        chapter_service,
        job_store,
        candidate_store,
        init_service,
        context_service,
        review_service,
        ai_review_service,
    ) = _build_services(tmp_path)
    work = work_service.create_work("P0 Regression 作品", "作者")
    chapter = chapter_service.list_chapters(work.id)[0]
    chapter = chapter_service.update_chapter(
        chapter.id.value,
        title="第一章",
        content="沈砚在雨夜回到旧城，决定追查港口里失踪的灯船。",
        expected_version=1,
    )
    initialization = init_service.start_initialization(work.id, created_by="user_action")
    return (
        work,
        chapter,
        initialization,
        job_store,
        candidate_store,
        init_service,
        context_service,
        review_service,
        ai_review_service,
        work_service,
        chapter_service,
    )


def test_cancelled_initialization_ignores_late_results_and_does_not_write_snapshots(tmp_path: Path) -> None:
    (
        work,
        _chapter,
        initialization,
        _job_store,
        _candidate_store,
        init_service,
        _context_service,
        _review_service,
        _ai_review_service,
        work_service,
        chapter_service,
    ) = _seed_initialized_work(tmp_path)

    new_work = work_service.create_work("取消回归作品", "作者")
    chapter = chapter_service.list_chapters(new_work.id)[0]
    chapter_service.update_chapter(
        chapter.id.value,
        title="第一章",
        content="陆川在档案馆里发现一张被撕去半角的旧地图。",
        expected_version=1,
    )
    pending = init_service.start_initialization(new_work.id, created_by="user_action", auto_run=False)
    init_service.cancel_job(pending.job_id, reason="user_cancelled")

    ignored = init_service.run_initialization(pending.initialization_id)

    assert ignored.status.value == "cancelled"
    assert ignored.completion_status.value == "ignored"
    assert init_service.get_latest_story_memory(new_work.id) is None
    assert init_service.get_latest_story_state(new_work.id) is None
    assert init_service.get_job(pending.job_id).status.value == "cancelled"
    assert initialization.work_id == work.id


def test_validation_failed_continuation_does_not_persist_candidate_draft(tmp_path: Path) -> None:
    (
        work,
        chapter,
        _initialization,
        job_store,
        candidate_store,
        _init_service,
        context_service,
        _review_service,
        _ai_review_service,
        work_service,
        chapter_service,
    ) = _seed_initialized_work(tmp_path)
    workflow = MinimalContinuationWorkflow(
        work_service=work_service,
        chapter_service=chapter_service,
        context_pack_service=context_service,
        candidate_draft_repository=candidate_store,
        writer=_ShortOutputWriter(),
        job_repository=job_store,
        step_repository=job_store,
        attempt_repository=job_store,
    )

    result = workflow.start_continuation(work.id, chapter.id.value, user_instruction="继续")

    assert result.status == "validation_failed"
    assert result.candidate_draft_id == ""
    assert workflow.list_candidate_drafts(work.id) == []


def test_ai_review_failure_does_not_auto_apply_and_does_not_block_manual_apply(tmp_path: Path) -> None:
    (
        work,
        chapter,
        _initialization,
        job_store,
        candidate_store,
        _init_service,
        context_service,
        review_service,
        ai_review_service,
        work_service,
        chapter_service,
    ) = _seed_initialized_work(tmp_path)
    workflow = MinimalContinuationWorkflow(
        work_service=work_service,
        chapter_service=chapter_service,
        context_pack_service=context_service,
        candidate_draft_repository=candidate_store,
        writer=FakeWriter(),
        job_repository=job_store,
        step_repository=job_store,
        attempt_repository=job_store,
    )

    continuation = workflow.start_continuation(work.id, chapter.id.value, user_instruction="继续推进港口线索。")
    candidate_id = continuation.candidate_draft_id
    before_apply = chapter_service.list_chapters(work.id)[0]

    review = ai_review_service.review_candidate_draft(candidate_id, created_by="user_action", user_instruction="只看逻辑")
    after_review = workflow.get_candidate_draft(candidate_id)

    assert review.status.value == "failed"
    assert after_review.status == CandidateDraftStatus.GENERATED
    assert chapter_service.list_chapters(work.id)[0].content == before_apply.content

    applied = review_service.apply_candidate_to_draft(
        candidate_id,
        user_id="u1",
        expected_chapter_version=before_apply.version,
        user_action=True,
    )
    chapter_after_apply = chapter_service.list_chapters(work.id)[0]

    assert applied["status"] == "applied"
    assert chapter_after_apply.version == before_apply.version + 1
