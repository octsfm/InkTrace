from __future__ import annotations

from pathlib import Path

from application.services.ai.context_pack_service import ContextPackService
from application.services.ai.initialization_service import InitializationApplicationService
from application.services.ai.continuation_workflow import MinimalContinuationWorkflow
from application.services.v1.chapter_service import ChapterService
from application.services.v1.work_service import WorkService
from domain.entities.ai.models import ContextPackBuildRequest, ContextPackSnapshot, ContextPackStatus
from infrastructure.database.repositories import ChapterRepo, WorkRepo
from infrastructure.database.repositories.ai.file_ai_job_store import FileAIJobStore
from infrastructure.database.repositories.ai.file_candidate_draft_store import FileCandidateDraftStore
from infrastructure.database.repositories.ai.file_context_pack_store import FileContextPackStore
from infrastructure.database.repositories.ai.file_initialization_store import FileInitializationStore
from infrastructure.database.repositories.ai.file_story_memory_store import FileStoryMemoryStore
from infrastructure.database.repositories.ai.file_story_state_store import FileStoryStateStore


class _StubWriter:
    def __init__(self, output: str = "暮色沉下来后，顾迟沿着灯塔台阶继续向上走去。") -> None:
        self.output = output
        self.calls = 0

    def generate_candidate_text(self, *, context_pack, writing_task):
        self.calls += 1
        return {
            "content": self.output,
            "provider_name": "fake",
            "model_name": "fake-writer",
            "model_role": "writer",
        }


class _StaticContextPackService:
    def __init__(self, snapshot: ContextPackSnapshot) -> None:
        self.snapshot = snapshot
        self.calls = 0

    def build_and_save(self, request: ContextPackBuildRequest) -> ContextPackSnapshot:
        self.calls += 1
        return self.snapshot.model_copy(update={"work_id": request.work_id, "chapter_id": request.chapter_id})


class _FailingCandidateDraftStore(FileCandidateDraftStore):
    def save(self, draft):
        raise RuntimeError("candidate_save_failed")


def _build_work_services() -> tuple[WorkService, ChapterService]:
    work_repo = WorkRepo()
    chapter_repo = ChapterRepo()
    return (
        WorkService(work_repo=work_repo, chapter_repo=chapter_repo),
        ChapterService(chapter_repo=chapter_repo, work_repo=work_repo),
    )


def _build_initialized_context(tmp_path: Path):
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
    work = work_service.create_work("S5 作品", "作者")
    chapter = chapter_service.list_chapters(work.id)[0]
    chapter = chapter_service.update_chapter(
        chapter.id.value,
        title="第一章",
        content="顾迟在海边灯塔醒来，发现潮声比记忆更近。",
        expected_version=1,
    )
    init_service.start_initialization(work.id, created_by="user_action")
    return work_service, chapter_service, init_service, context_pack_service, job_store, work, chapter


def test_start_continuation_saves_candidate_draft_when_context_pack_ready(tmp_path: Path) -> None:
    work_service, chapter_service, init_service, _, job_store, work, chapter = _create_initialized_work(tmp_path)
    memory_before = init_service.get_latest_story_memory(work.id)
    state_before = init_service.get_latest_story_state(work.id)
    writer = _StubWriter()
    static_context_pack = _StaticContextPackService(
        ContextPackSnapshot(
            context_pack_id="cp_ready",
            work_id=work.id,
            chapter_id=chapter.id.value,
            status=ContextPackStatus.READY,
            summary="ready context",
            created_at="2026-05-11T00:00:00+00:00",
        )
    )
    candidate_store = FileCandidateDraftStore(tmp_path / "candidate_drafts.json")
    workflow = MinimalContinuationWorkflow(
        work_service=work_service,
        chapter_service=chapter_service,
        context_pack_service=static_context_pack,
        candidate_draft_repository=candidate_store,
        writer=writer,
        job_repository=job_store,
        step_repository=job_store,
        attempt_repository=job_store,
    )

    result = workflow.start_continuation(work.id, chapter.id.value, user_instruction="继续写下去")

    draft = workflow.get_candidate_draft(result.candidate_draft_id)
    chapter_after = chapter_service.list_chapters(work.id)[0]

    assert result.status == "completed_with_candidate"
    assert result.candidate_draft_id.startswith("cd_")
    assert writer.calls == 1
    assert draft.status == "generated"
    assert draft.content == writer.output
    assert chapter_after.content == chapter.content
    assert init_service.get_latest_story_memory(work.id).snapshot_id == memory_before.snapshot_id
    assert init_service.get_latest_story_state(work.id).story_state_id == state_before.story_state_id


def test_start_continuation_allows_degraded_context_pack_and_records_warning(tmp_path: Path) -> None:
    work_service, chapter_service, _, _, job_store, work, chapter = _create_initialized_work(tmp_path)
    writer = _StubWriter()
    static_context_pack = _StaticContextPackService(
        ContextPackSnapshot(
            context_pack_id="cp_degraded",
            work_id=work.id,
            chapter_id=chapter.id.value,
            status=ContextPackStatus.DEGRADED,
            degraded_reason="vector_recall_unavailable",
            warnings=["vector_recall_unavailable"],
            summary="degraded context",
            created_at="2026-05-11T00:00:00+00:00",
        )
    )
    candidate_store = FileCandidateDraftStore(tmp_path / "candidate_drafts.json")
    workflow = MinimalContinuationWorkflow(
        work_service=work_service,
        chapter_service=chapter_service,
        context_pack_service=static_context_pack,
        candidate_draft_repository=candidate_store,
        writer=writer,
        job_repository=job_store,
        step_repository=job_store,
        attempt_repository=job_store,
    )

    result = workflow.start_continuation(work.id, chapter.id.value, user_instruction="继续")
    draft = workflow.get_candidate_draft(result.candidate_draft_id)

    assert result.status == "degraded_completed"
    assert "vector_recall_unavailable" in result.warnings
    assert draft.metadata["context_pack_status"] == "degraded"
    assert draft.metadata["degraded_reason"] == "vector_recall_unavailable"


def test_start_continuation_stops_when_context_pack_blocked(tmp_path: Path) -> None:
    work_service, chapter_service, _, _, job_store, work, chapter = _create_initialized_work(tmp_path)
    writer = _StubWriter()
    static_context_pack = _StaticContextPackService(
        ContextPackSnapshot(
            context_pack_id="cp_blocked",
            work_id=work.id,
            chapter_id=chapter.id.value,
            status=ContextPackStatus.BLOCKED,
            blocked_reason="initialization_not_completed",
            warnings=["initialization_not_completed"],
            created_at="2026-05-11T00:00:00+00:00",
        )
    )
    candidate_store = FileCandidateDraftStore(tmp_path / "candidate_drafts.json")
    workflow = MinimalContinuationWorkflow(
        work_service=work_service,
        chapter_service=chapter_service,
        context_pack_service=static_context_pack,
        candidate_draft_repository=candidate_store,
        writer=writer,
        job_repository=job_store,
        step_repository=job_store,
        attempt_repository=job_store,
    )

    result = workflow.start_continuation(work.id, chapter.id.value, user_instruction="继续")

    assert result.status == "blocked"
    assert result.candidate_draft_id == ""
    assert result.error_code == "context_pack_blocked"
    assert writer.calls == 0
    assert workflow.list_candidate_drafts(work.id) == []


def test_start_continuation_does_not_save_candidate_when_validation_fails(tmp_path: Path) -> None:
    work_service, chapter_service, _, context_pack_service, job_store, work, chapter = _create_initialized_work(tmp_path)
    writer = _StubWriter(output="error: provider_auth_failed")
    candidate_store = FileCandidateDraftStore(tmp_path / "candidate_drafts.json")
    workflow = MinimalContinuationWorkflow(
        work_service=work_service,
        chapter_service=chapter_service,
        context_pack_service=context_pack_service,
        candidate_draft_repository=candidate_store,
        writer=writer,
        job_repository=job_store,
        step_repository=job_store,
        attempt_repository=job_store,
    )

    result = workflow.start_continuation(work.id, chapter.id.value, user_instruction="继续")

    assert result.status == "validation_failed"
    assert result.candidate_draft_id == ""
    assert result.error_code == "writer_output_invalid"
    assert workflow.list_candidate_drafts(work.id) == []


def test_start_continuation_reports_candidate_save_failed_without_writing_chapter(tmp_path: Path) -> None:
    work_service, chapter_service, _, context_pack_service, job_store, work, chapter = _create_initialized_work(tmp_path)
    original_content = chapter.content
    writer = _StubWriter()
    workflow = MinimalContinuationWorkflow(
        work_service=work_service,
        chapter_service=chapter_service,
        context_pack_service=context_pack_service,
        candidate_draft_repository=_FailingCandidateDraftStore(tmp_path / "candidate_drafts.json"),
        writer=writer,
        job_repository=job_store,
        step_repository=job_store,
        attempt_repository=job_store,
    )

    result = workflow.start_continuation(work.id, chapter.id.value, user_instruction="继续")
    chapter_after = chapter_service.list_chapters(work.id)[0]

    assert result.status == "candidate_save_failed"
    assert result.candidate_draft_id == ""
    assert result.error_code == "candidate_save_failed"
    assert chapter_after.content == original_content
