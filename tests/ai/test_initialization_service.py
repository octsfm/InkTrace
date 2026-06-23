from __future__ import annotations

from types import SimpleNamespace

from application.services.ai.initialization_service import InitializationApplicationService
from application.services.v1.chapter_service import ChapterService
from application.services.v1.work_service import WorkService
from domain.entities.ai.models import AIJobStatus, InitializationStatus, VectorIndexBuildResult
from infrastructure.database.repositories import ChapterRepo, WorkRepo
from infrastructure.database.repositories.ai.file_ai_job_store import FileAIJobStore
from infrastructure.database.repositories.ai.file_initialization_store import FileInitializationStore
from infrastructure.database.repositories.ai.file_story_memory_store import FileStoryMemoryStore
from infrastructure.database.repositories.ai.file_story_state_store import FileStoryStateStore


class _StubVectorIndexService:
    def __init__(self, result: VectorIndexBuildResult | None = None, *, error: Exception | None = None) -> None:
        self._result = result or VectorIndexBuildResult(index_status="ready", indexed_chapter_count=1, indexed_chunk_count=1)
        self._error = error
        self.calls: list[str] = []
        self.last_status_seen: str = ""

    def build_initial_index(self, work_id: str, should_continue=None) -> VectorIndexBuildResult:  # noqa: ANN001
        self.calls.append(work_id)
        if self._error is not None:
            raise self._error
        if callable(should_continue):
            should_continue()
        return self._result


class _CancellingVectorIndexService(_StubVectorIndexService):
    def __init__(self, cancel_callback) -> None:  # noqa: ANN001
        super().__init__(VectorIndexBuildResult(index_status="failed", failed_chunk_count=1, degraded_reason="index_build_failed"))
        self._cancel_callback = cancel_callback

    def build_initial_index(self, work_id: str, should_continue=None) -> VectorIndexBuildResult:  # noqa: ANN001
        self.calls.append(work_id)
        self._cancel_callback()
        if callable(should_continue):
            should_continue()
        return self._result


def _build_service(
    *,
    vector_index_service: _StubVectorIndexService | None = None,
) -> tuple[InitializationApplicationService, WorkService, ChapterService]:
    work_repo = WorkRepo()
    chapter_repo = ChapterRepo()
    work_service = WorkService(work_repo=work_repo, chapter_repo=chapter_repo)
    chapter_service = ChapterService(chapter_repo=chapter_repo, work_repo=work_repo)
    job_store = FileAIJobStore()
    initialization_service = InitializationApplicationService(
        work_service=work_service,
        chapter_service=chapter_service,
        job_repository=job_store,
        step_repository=job_store,
        attempt_repository=job_store,
        initialization_repository=FileInitializationStore(),
        story_memory_repository=FileStoryMemoryStore(),
        story_state_repository=FileStoryStateStore(),
        vector_index_service=vector_index_service,
    )
    return initialization_service, work_service, chapter_service


def test_start_initialization_creates_job_and_snapshots_for_confirmed_chapters() -> None:
    service, work_service, chapter_service = _build_service()
    work = work_service.create_work("初始化作品", "作者")
    chapter = chapter_service.list_chapters(work.id)[0]
    chapter_service.update_chapter(chapter.id.value, title="第一章", content="林舟来到白塔城，遇见顾宁。", expected_version=1)

    initialization = service.start_initialization(work.id, created_by="user_action")
    latest_memory = service.get_latest_story_memory(work.id)
    latest_state = service.get_latest_story_state(work.id)
    job = service.get_job(initialization.job_id)

    assert initialization.work_id == work.id
    assert initialization.job_id.startswith("job_")
    assert initialization.status == "completed"
    assert initialization.completion_status == "succeeded"
    assert initialization.analyzed_chapter_count == 1
    assert latest_memory.global_summary
    assert latest_state.current_position_summary
    assert job.status.value == "completed"


def test_initialization_builds_story_memory_with_scene_details() -> None:
    service, work_service, chapter_service = _build_service()
    work = work_service.create_work("场景初始化作品", "作者")
    chapter = chapter_service.list_chapters(work.id)[0]
    chapter_service.update_chapter(
        chapter.id.value,
        title="第一章",
        content="夜里，顾迟在灯塔顶层翻看旧航海图。沈砚守在楼梯口。海雾里忽然传来钟声，顾迟意识到父亲留下的标记就在地图夹层。",
        expected_version=1,
    )

    initialization = service.start_initialization(work.id, created_by="user_action")
    latest_memory = service.get_latest_story_memory(work.id)

    assert initialization.status == "completed"
    assert latest_memory is not None
    assert latest_memory.scene_details
    first_scene = latest_memory.scene_details[0]
    assert first_scene.chapter_id == chapter.id.value
    assert first_scene.location
    assert "顾迟" in first_scene.characters_present
    assert first_scene.reveal_points


def test_finalize_initialization_marks_partial_success_for_empty_chapter() -> None:
    service, work_service, chapter_service = _build_service()
    work = work_service.create_work("部分成功作品", "作者")
    first = chapter_service.list_chapters(work.id)[0]
    second = chapter_service.create_chapter(work.id, title="第二章")
    chapter_service.update_chapter(first.id.value, title="第一章", content="沈砚在雨夜回到旧城。", expected_version=1)

    initialization = service.start_initialization(work.id, created_by="user_action")

    assert initialization.status == "completed"
    assert initialization.completion_status == "partial_success"
    assert initialization.analyzed_chapter_count == 1
    assert initialization.empty_chapter_count == 1
    assert initialization.total_confirmed_chapter_count == 2
    assert initialization.source_chapter_versions[second.id.value] == 1


def test_finalize_initialization_fails_when_no_effective_confirmed_chapters() -> None:
    service, work_service, _ = _build_service()
    work = work_service.create_work("空作品", "作者")

    initialization = service.start_initialization(work.id, created_by="user_action")

    assert initialization.status == "failed"
    assert initialization.completion_status == "failed"
    assert initialization.error_code == "work_empty"
    assert service.get_latest_story_memory(work.id) is None
    assert service.get_latest_story_state(work.id) is None


def test_cancelled_job_ignores_late_finalize_and_does_not_write_snapshots() -> None:
    service, work_service, chapter_service = _build_service()
    work = work_service.create_work("取消作品", "作者")
    chapter = chapter_service.list_chapters(work.id)[0]
    chapter_service.update_chapter(chapter.id.value, title="第一章", content="陆川在档案馆里发现旧地图。", expected_version=1)

    initialization = service.start_initialization(work.id, created_by="user_action", auto_run=False)
    service.cancel_job(initialization.job_id, reason="user_cancelled")
    ignored = service.run_initialization(initialization.initialization_id)

    assert ignored.status == "cancelled"
    assert ignored.completion_status == "ignored"
    assert service.get_latest_story_memory(work.id) is None
    assert service.get_latest_story_state(work.id) is None
    assert service.get_job(initialization.job_id).status.value == "cancelled"


def test_mark_stale_updates_latest_initialization_and_snapshots() -> None:
    service, work_service, chapter_service = _build_service()
    work = work_service.create_work("过期作品", "作者")
    chapter = chapter_service.list_chapters(work.id)[0]
    chapter_service.update_chapter(chapter.id.value, title="第一章", content="温遥离开港口，前往群岛。", expected_version=1)

    completed = service.start_initialization(work.id, created_by="user_action")
    stale = service.mark_stale(work.id, reason="chapter_updated")
    latest_memory = service.get_latest_story_memory(work.id)
    latest_state = service.get_latest_story_state(work.id)

    assert completed.status == "completed"
    assert stale.status == "stale"
    assert stale.stale is True
    assert stale.stale_reason == "chapter_updated"
    assert service.is_stale(work.id) is True
    assert latest_memory.stale_status == "stale"
    assert latest_state.stale_status == "stale"


def test_initialization_creates_and_completes_build_vector_index_step() -> None:
    vector_service = _StubVectorIndexService(
        VectorIndexBuildResult(
            index_status="ready",
            indexed_chapter_count=1,
            indexed_chunk_count=2,
        )
    )
    service, work_service, chapter_service = _build_service(vector_index_service=vector_service)
    work = work_service.create_work("向量初始化作品", "作者")
    chapter = chapter_service.list_chapters(work.id)[0]
    chapter_service.update_chapter(chapter.id.value, title="第一章", content="顾迟在旧灯塔里发现父亲留下的海图残页。", expected_version=1)

    initialization = service.start_initialization(work.id, created_by="user_action")
    job = service.get_job(initialization.job_id)
    steps = {step.step_type: step for step in service.get_job(initialization.job_id).progress and service._job_service.get_job_steps(initialization.job_id)}

    assert vector_service.calls == [work.id]
    assert initialization.status == "completed"
    assert "build_vector_index" in steps
    assert steps["build_vector_index"].status.value == "completed"
    assert "indexed_chunks=2" in steps["build_vector_index"].summary
    assert job.progress.warning_count == 0


def test_initialization_keeps_completed_when_build_vector_index_fails() -> None:
    vector_service = _StubVectorIndexService(error=RuntimeError("embedding_provider_missing"))
    service, work_service, chapter_service = _build_service(vector_index_service=vector_service)
    work = work_service.create_work("向量降级作品", "作者")
    chapter = chapter_service.list_chapters(work.id)[0]
    chapter_service.update_chapter(chapter.id.value, title="第一章", content="顾迟在旧灯塔里发现父亲留下的海图残页。", expected_version=1)

    initialization = service.start_initialization(work.id, created_by="user_action")
    job = service.get_job(initialization.job_id)
    steps = {step.step_type: step for step in service._job_service.get_job_steps(initialization.job_id)}

    assert vector_service.calls == [work.id]
    assert initialization.status == "completed"
    assert initialization.completion_status == "succeeded"
    assert initialization.partial_success_reason == ""
    assert "build_vector_index" in steps
    assert steps["build_vector_index"].status.value == "failed"
    assert steps["build_vector_index"].error_code == "vector_index_build_failed"
    assert job.progress.warning_count == 1
    assert job.progress.failed_step_count == 1
    assert job.result_summary["vector_index_warning"] == "embedding_provider_missing"


def test_initialization_stops_finalize_when_job_cancelled_during_build_vector_index() -> None:
    service, work_service, chapter_service = _build_service()
    work = work_service.create_work("初始化取消作品", "作者")
    chapter = chapter_service.list_chapters(work.id)[0]
    chapter_service.update_chapter(chapter.id.value, title="第一章", content="顾迟在旧灯塔里发现父亲留下的海图残页。", expected_version=1)
    initialization = service.start_initialization(work.id, created_by="user_action", auto_run=False)
    service._vector_index_service = _CancellingVectorIndexService(
        lambda: service.cancel_job(initialization.job_id, reason="user_cancelled")
    )

    result = service.run_initialization(initialization.initialization_id)
    job = service.get_job(initialization.job_id)
    steps = {step.step_type: step for step in service._job_service.get_job_steps(initialization.job_id)}

    assert result.status == InitializationStatus.CANCELLED
    assert result.completion_status.value == "ignored"
    assert job.status == AIJobStatus.CANCELLED
    assert steps["build_vector_index"].status.value in {"running", "pending"}
    assert steps["finalize_initialization"].status.value == "running"
