from __future__ import annotations

from application.services.ai.context_pack_service import ContextPackService
from application.services.ai.initialization_service import InitializationApplicationService
from application.services.v1.chapter_service import ChapterService
from application.services.v1.work_service import WorkService
from domain.entities.ai.models import ContextPackBuildRequest, ContextPackStatus
from infrastructure.database.repositories import ChapterRepo, WorkRepo
from infrastructure.database.repositories.ai.file_context_pack_store import FileContextPackStore
from infrastructure.database.repositories.ai.file_ai_job_store import FileAIJobStore
from infrastructure.database.repositories.ai.file_initialization_store import FileInitializationStore
from infrastructure.database.repositories.ai.file_story_memory_store import FileStoryMemoryStore
from infrastructure.database.repositories.ai.file_story_state_store import FileStoryStateStore


def _build_services() -> tuple[ContextPackService, InitializationApplicationService, WorkService, ChapterService]:
    work_repo = WorkRepo()
    chapter_repo = ChapterRepo()
    work_service = WorkService(work_repo=work_repo, chapter_repo=chapter_repo)
    chapter_service = ChapterService(chapter_repo=chapter_repo, work_repo=work_repo)
    job_store = FileAIJobStore()
    init_service = InitializationApplicationService(
        work_service=work_service,
        chapter_service=chapter_service,
        job_repository=job_store,
        step_repository=job_store,
        attempt_repository=job_store,
        initialization_repository=FileInitializationStore(),
        story_memory_repository=FileStoryMemoryStore(),
        story_state_repository=FileStoryStateStore(),
    )
    cp_service = ContextPackService(
        chapter_service=chapter_service,
        initialization_repository=FileInitializationStore(),
        story_memory_repository=FileStoryMemoryStore(),
        story_state_repository=FileStoryStateStore(),
        context_pack_repository=FileContextPackStore(),
    )
    return cp_service, init_service, work_service, chapter_service


def test_context_pack_ready_with_story_memory_and_state() -> None:
    cp_service, init_service, work_service, chapter_service = _build_services()
    work = work_service.create_work("上下文作品", "作者")
    chapter = chapter_service.list_chapters(work.id)[0]
    chapter_service.update_chapter(chapter.id.value, title="第一章", content="顾迟在海边灯塔醒来，发现整个世界已不同。", expected_version=1)

    init_service.start_initialization(work.id, created_by="user_action")

    request = ContextPackBuildRequest(work_id=work.id, chapter_id=chapter.id.value, user_instruction="继续写下去")
    snapshot = cp_service.build_and_save(request)

    assert snapshot.status == ContextPackStatus.DEGRADED  # VectorRecall unavailable causes degraded
    assert snapshot.estimated_token_count > 0
    assert len(snapshot.context_items) > 0
    assert any(item.source_type == "story_state" for item in snapshot.context_items)
    assert any(item.source_type == "story_memory" for item in snapshot.context_items)
    assert any(item.source_type == "current_chapter" for item in snapshot.context_items)
    assert not any(item.source_type == "vector_recall" for item in snapshot.context_items)
    assert not any(item.source_type == "system_policy" for item in snapshot.context_items)
    assert snapshot.vector_recall_status == "degraded"


def test_context_pack_blocked_when_no_story_memory() -> None:
    cp_service, _, work_service, chapter_service = _build_services()
    work = work_service.create_work("无记忆作品", "作者")
    chapter = chapter_service.list_chapters(work.id)[0]
    chapter_service.update_chapter(chapter.id.value, title="第一章", content="测试内容。", expected_version=1)

    request = ContextPackBuildRequest(work_id=work.id, chapter_id=chapter.id.value)
    snapshot = cp_service.build_and_save(request)

    assert snapshot.status == ContextPackStatus.BLOCKED
    assert "initialization_not_completed" in snapshot.blocked_reason or snapshot.blocked_reason != ""


def test_context_pack_blocked_when_initialization_not_completed() -> None:
    cp_service, _, work_service, _ = _build_services()
    work = work_service.create_work("未初始化作品", "作者")

    request = ContextPackBuildRequest(work_id=work.id)
    snapshot = cp_service.build_and_save(request)

    assert snapshot.status == ContextPackStatus.BLOCKED
    assert "initialization_not_completed" in snapshot.blocked_reason


def test_context_pack_blocked_when_stale_and_not_quick_trial() -> None:
    cp_service, init_service, work_service, chapter_service = _build_services()
    work = work_service.create_work("过时作品", "作者")
    chapter = chapter_service.list_chapters(work.id)[0]
    chapter_service.update_chapter(chapter.id.value, title="第一章", content="沈砚在雨夜回到旧城。", expected_version=1)

    init_service.start_initialization(work.id, created_by="user_action")
    init_service.mark_stale(work.id, reason="chapter_updated")

    request = ContextPackBuildRequest(work_id=work.id, chapter_id=chapter.id.value)
    snapshot = cp_service.build_and_save(request)

    assert snapshot.status == ContextPackStatus.BLOCKED
    assert snapshot.stale is True
    assert "stale" in snapshot.blocked_reason
    assert any("stale" in warning for warning in snapshot.warnings)


def test_context_pack_degraded_when_vector_recall_unavailable() -> None:
    cp_service, init_service, work_service, chapter_service = _build_services()
    work = work_service.create_work("降级作品", "作者")
    chapter = chapter_service.list_chapters(work.id)[0]
    chapter_service.update_chapter(chapter.id.value, title="第一章", content="林舟来到白塔城，遇见顾宁。", expected_version=1)

    init_service.start_initialization(work.id, created_by="user_action")

    request = ContextPackBuildRequest(work_id=work.id, chapter_id=chapter.id.value, user_instruction="继续")
    snapshot = cp_service.build_and_save(request)

    assert snapshot.status == ContextPackStatus.DEGRADED
    assert "vector_recall_unavailable" in snapshot.degraded_reason
    assert any("vector_recall_unavailable" in warning for warning in snapshot.warnings)


def test_context_pack_trims_items_when_over_budget() -> None:
    cp_service, init_service, work_service, chapter_service = _build_services()
    work = work_service.create_work("预算作品", "作者")
    chapter = chapter_service.list_chapters(work.id)[0]
    chapter_service.update_chapter(chapter.id.value, title="第一章", content="温遥离开港口，前往群岛。", expected_version=1)

    init_service.start_initialization(work.id, created_by="user_action")

    request = ContextPackBuildRequest(work_id=work.id, chapter_id=chapter.id.value, max_context_tokens=80)
    snapshot = cp_service.build_and_save(request)

    assert snapshot.status in {ContextPackStatus.DEGRADED, ContextPackStatus.BLOCKED}
    if snapshot.trimmed_items:
        assert any(item.trim_reason == "token_budget_exceeded" for item in snapshot.trimmed_items)
    else:
        assert len(snapshot.context_items) > 0


def test_context_pack_readiness_does_not_persist_snapshot() -> None:
    cp_service, init_service, work_service, chapter_service = _build_services()
    work = work_service.create_work("只读就绪性作品", "作者")
    chapter = chapter_service.list_chapters(work.id)[0]
    chapter_service.update_chapter(chapter.id.value, title="第一章", content="陆川在档案馆里发现旧地图。", expected_version=1)

    init_service.start_initialization(work.id, created_by="user_action")

    assert cp_service.list_by_work(work.id) == []

    readiness = cp_service.evaluate_readiness(work.id, chapter_id=chapter.id.value)

    assert readiness["status"] in {"ready", "degraded"}
    assert cp_service.list_by_work(work.id) == []


def test_context_pack_evaluate_readiness_returns_status() -> None:
    cp_service, init_service, work_service, chapter_service = _build_services()
    work = work_service.create_work("就绪作品", "作者")
    chapter = chapter_service.list_chapters(work.id)[0]
    chapter_service.update_chapter(chapter.id.value, title="第一章", content="顾宁站在塔顶俯瞰整个城市。", expected_version=1)

    init_service.start_initialization(work.id, created_by="user_action")

    readiness = cp_service.evaluate_readiness(work.id, chapter_id=chapter.id.value)

    assert readiness["status"] in {"ready", "degraded"}
    assert "context_pack_id" in readiness
    assert "estimated_token_count" in readiness


def test_context_pack_query_text_build_failure_degrades_and_skips_rag(monkeypatch) -> None:
    cp_service, init_service, work_service, chapter_service = _build_services()
    cp_service._vector_recall_service = type("_NoopRecall", (), {"recall": lambda self, query: []})()  # type: ignore[attr-defined]
    work = work_service.create_work("查询失败作品", "作者")
    chapter = chapter_service.list_chapters(work.id)[0]
    chapter_service.update_chapter(chapter.id.value, title="第一章", content="顾宁在废墟边缘看见旧时代的回声。", expected_version=1)
    init_service.start_initialization(work.id, created_by="user_action")

    def _fail_build_query_text(self, request, chapter_text, story_memory, story_state):  # noqa: ANN001
        raise ValueError("query_text_build_failed")

    monkeypatch.setattr(
        ContextPackService,
        "_build_vector_query_text",
        _fail_build_query_text,
        raising=False,
    )

    snapshot = cp_service.build_and_save(
        ContextPackBuildRequest(work_id=work.id, chapter_id=chapter.id.value, user_instruction="继续")
    )

    assert snapshot.status == ContextPackStatus.DEGRADED
    assert snapshot.vector_recall_status == "skipped"
    assert "query_text_build_failed" in snapshot.warnings
    assert "rag_skipped" in snapshot.warnings


def test_context_pack_forwards_allow_stale_vector_to_vector_recall_service() -> None:
    calls: list[dict[str, object]] = []

    class _SpyVectorRecallService:
        def recall(self, query):  # noqa: ANN001
            calls.append({"allow_stale": getattr(query, "allow_stale", None), "query_text": getattr(query, "query_text", "")})
            return []

    cp_service, init_service, work_service, chapter_service = _build_services()
    cp_service._vector_recall_service = _SpyVectorRecallService()  # type: ignore[attr-defined]

    work = work_service.create_work("陈旧召回作品", "作者")
    chapter = chapter_service.list_chapters(work.id)[0]
    chapter_service.update_chapter(chapter.id.value, title="第一章", content="温遥从海雾中穿过，旧港的灯光忽明忽暗。", expected_version=1)
    init_service.start_initialization(work.id, created_by="user_action")

    snapshot = cp_service.build_and_save(
        ContextPackBuildRequest(
            work_id=work.id,
            chapter_id=chapter.id.value,
            user_instruction="继续",
            allow_stale_vector=True,
        )
    )

    assert snapshot.status == ContextPackStatus.DEGRADED
    assert snapshot.vector_recall_status == "degraded"
    assert calls and calls[0]["allow_stale"] is True
