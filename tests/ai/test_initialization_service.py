from __future__ import annotations

from application.services.ai.initialization_service import InitializationApplicationService
from application.services.v1.chapter_service import ChapterService
from application.services.v1.work_service import WorkService
from infrastructure.database.repositories import ChapterRepo, WorkRepo
from infrastructure.database.repositories.ai.file_ai_job_store import FileAIJobStore
from infrastructure.database.repositories.ai.file_initialization_store import FileInitializationStore
from infrastructure.database.repositories.ai.file_story_memory_store import FileStoryMemoryStore
from infrastructure.database.repositories.ai.file_story_state_store import FileStoryStateStore


def _build_service() -> tuple[InitializationApplicationService, WorkService, ChapterService]:
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
