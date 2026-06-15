from __future__ import annotations

import time
from pathlib import Path

from application.services.ai.ai_job_service import AIJobService
from application.services.ai.continuation_workflow import MinimalContinuationWorkflow
from application.services.ai.multi_chapter_service import MultiChapterContinuationService
from application.services.ai.tool_facade import CoreToolFacade
from infrastructure.ai.providers.fake_writer import FakeWriter
from application.services.v1.chapter_service import ChapterService
from application.services.v1.work_service import WorkService
from domain.entities.ai.models import (
    ChapterAdvanceDecision,
    MultiChapterStatus,
    PerChapterStatus,
)
from infrastructure.database.repositories import ChapterRepo, WorkRepo
from infrastructure.database.repositories.ai.file_ai_job_store import FileAIJobStore
from infrastructure.database.repositories.ai.file_candidate_draft_store import FileCandidateDraftStore
from infrastructure.database.repositories.ai.file_context_pack_store import FileContextPackStore
from infrastructure.database.repositories.ai.file_initialization_store import FileInitializationStore
from infrastructure.database.repositories.ai.file_story_memory_store import FileStoryMemoryStore
from infrastructure.database.repositories.ai.file_story_state_store import FileStoryStateStore
from infrastructure.persistence.sqlite_multi_chapter_session_repo import SQLiteMultiChapterSessionRepository


def _build_work_services() -> tuple[WorkService, ChapterService]:
    work_repo = WorkRepo()
    chapter_repo = ChapterRepo()
    return (
        WorkService(work_repo=work_repo, chapter_repo=chapter_repo),
        ChapterService(chapter_repo=chapter_repo, work_repo=work_repo),
    )


def _build_initialized_context(tmp_path: Path):
    from application.services.ai.context_pack_service import ContextPackService
    from application.services.ai.initialization_service import InitializationApplicationService

    work_service, chapter_service = _build_work_services()
    job_store = FileAIJobStore(tmp_path / "jobs.json")
    init_store = FileInitializationStore(tmp_path / "initializations.json")
    memory_store = FileStoryMemoryStore(tmp_path / "memory.json")
    state_store = FileStoryStateStore(tmp_path / "state.json")
    context_store = FileContextPackStore(tmp_path / "context_packs.json")

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
    context_pack_service = ContextPackService(
        chapter_service=chapter_service,
        initialization_repository=init_store,
        story_memory_repository=memory_store,
        story_state_repository=state_store,
        context_pack_repository=context_store,
    )
    return work_service, chapter_service, init_service, context_pack_service, job_store


def _create_initialized_work(tmp_path: Path):
    work_service, chapter_service, init_service, context_pack_service, job_store = _build_initialized_context(tmp_path)
    work = work_service.create_work("P2-S1 多章续写作品", "作者")
    chapter = chapter_service.list_chapters(work.id)[0]
    chapter = chapter_service.update_chapter(
        chapter.id.value,
        title="第一章",
        content="顾迟在海边灯塔醒来，怀疑父亲留下的航海图藏着更深的秘密。",
        expected_version=1,
    )
    init_service.start_initialization(work.id, created_by="user_action")
    return work_service, chapter_service, context_pack_service, job_store, work, chapter


def _build_multi_chapter_service(tmp_path: Path):
    work_service, chapter_service, context_pack_service, job_store, work, chapter = _create_initialized_work(tmp_path)
    candidate_store = FileCandidateDraftStore(tmp_path / "candidate_drafts.json")
    tool_facade = CoreToolFacade(
        context_pack_service=context_pack_service,
        candidate_draft_repository=candidate_store,
        writer=FakeWriter(),
    )
    continuation_workflow = MinimalContinuationWorkflow(
        work_service=work_service,
        chapter_service=chapter_service,
        tool_facade=tool_facade,
        candidate_draft_repository=candidate_store,
        job_repository=job_store,
        step_repository=job_store,
        attempt_repository=job_store,
    )
    service = MultiChapterContinuationService(
        chapter_service=chapter_service,
        continuation_workflow=continuation_workflow,
        candidate_draft_repository=candidate_store,
        multi_chapter_repository=SQLiteMultiChapterSessionRepository(tmp_path / "runtime.db"),
        job_service=AIJobService(job_repository=job_store, step_repository=job_store, attempt_repository=job_store),
    )
    return service, candidate_store, work, chapter, chapter_service


def _wait_for_status(service: MultiChapterContinuationService, session_id: str, expected: MultiChapterStatus, timeout: float = 5.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        progress = service.get_progress(session_id)
        if progress.status == expected:
            return progress
        time.sleep(0.05)
    raise AssertionError(f"session {session_id} did not reach {expected.value}")


def test_multi_chapter_service_starts_and_generates_first_candidate_then_waits_for_user(tmp_path: Path) -> None:
    service, _, work, chapter, chapter_service = _build_multi_chapter_service(tmp_path)

    session = service.start(
        work_id=work.id,
        start_chapter_id=chapter.id.value,
        target_chapters=2,
        user_instruction="继续推进灯塔谜团。",
        caller_type="user_action",
    )
    progress = _wait_for_status(service, session.session_id, MultiChapterStatus.WAITING_USER_DECISION)

    stored = service.get_session(session.session_id)

    assert stored.status == MultiChapterStatus.WAITING_USER_DECISION
    assert progress.current_index == 1
    assert progress.target_chapters == 2
    assert progress.per_chapter[0].status == PerChapterStatus.READY
    assert progress.per_chapter[0].candidate_draft_id.startswith("cd_")
    assert len(chapter_service.list_chapters(work.id)) == 3


def test_multi_chapter_service_advances_to_next_chapter_and_preserves_previous_candidate(tmp_path: Path) -> None:
    service, candidate_store, work, chapter, _ = _build_multi_chapter_service(tmp_path)

    session = service.start(
        work_id=work.id,
        start_chapter_id=chapter.id.value,
        target_chapters=2,
        user_instruction="继续推进灯塔谜团。",
        caller_type="user_action",
    )
    first_progress = _wait_for_status(service, session.session_id, MultiChapterStatus.WAITING_USER_DECISION)
    first_candidate_id = first_progress.per_chapter[0].candidate_draft_id

    advanced = service.advance_to_next_chapter(
        session.session_id,
        decision=ChapterAdvanceDecision.CONTINUE_WITHOUT_APPLY,
    )
    assert advanced.current_index == 2

    second_progress = _wait_for_status(service, session.session_id, MultiChapterStatus.WAITING_USER_DECISION)
    assert second_progress.current_index == 2
    assert second_progress.per_chapter[1].status == PerChapterStatus.READY
    assert second_progress.per_chapter[1].candidate_draft_id.startswith("cd_")
    drafts = candidate_store.list_by_work(work.id)
    assert len(drafts) == 2
    assert any(item.candidate_draft_id == first_candidate_id for item in drafts)


def test_multi_chapter_service_cancel_keeps_generated_candidate_drafts(tmp_path: Path) -> None:
    service, candidate_store, work, chapter, _ = _build_multi_chapter_service(tmp_path)

    session = service.start(
        work_id=work.id,
        start_chapter_id=chapter.id.value,
        target_chapters=2,
        user_instruction="继续推进灯塔谜团。",
        caller_type="user_action",
    )
    progress = _wait_for_status(service, session.session_id, MultiChapterStatus.WAITING_USER_DECISION)

    cancelled = service.cancel(session.session_id)

    assert cancelled.status == MultiChapterStatus.CANCELLED
    assert progress.per_chapter[0].candidate_draft_id
    assert len(candidate_store.list_by_work(work.id)) == 1
