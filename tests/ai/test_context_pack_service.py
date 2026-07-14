from __future__ import annotations

from application.services.ai.context_pack_service import ContextPackService
from application.services.ai.initialization_service import InitializationApplicationService
from application.services.v1.chapter_service import ChapterService
from application.services.v1.work_service import WorkService
from domain.entities.ai.models import (
    ContextItem,
    ContextPackBuildRequest,
    ContextPackStatus,
    StyleProfile,
    StyleProfileSourceType,
    StyleProfileStatus,
)
from infrastructure.database.repositories import ChapterRepo, WorkRepo
from infrastructure.database.repositories.ai.file_context_pack_store import FileContextPackStore
from infrastructure.database.repositories.ai.file_ai_job_store import FileAIJobStore
from infrastructure.database.repositories.ai.file_initialization_store import FileInitializationStore
from infrastructure.database.repositories.ai.file_plot_arc_store import FilePlotArcStore
from infrastructure.database.repositories.ai.file_story_memory_store import FileStoryMemoryStore
from infrastructure.database.repositories.ai.file_story_state_store import FileStoryStateStore
from infrastructure.persistence.sqlite_style_profile_repo import SQLiteStyleProfileRepository
from tests.ai.initialization_test_support import build_initialization_analysis_dependencies


class _StubVectorIndexRepository:
    def __init__(self, status: dict[str, object] | None = None) -> None:
        self._status = dict(status or {})

    def get_index_status_by_work(self, work_id: str) -> dict[str, object] | None:
        _ = work_id
        return dict(self._status) if self._status else None


class _SpyVectorRecallService:
    def __init__(self, items: list[dict[str, object]] | None = None) -> None:
        self._items = list(items or [])
        self.calls: list[dict[str, object]] = []

    def recall(self, query):  # noqa: ANN001
        self.calls.append(
            {
                "allow_stale": getattr(query, "allow_stale", None),
                "query_text": getattr(query, "query_text", ""),
            }
        )
        return list(self._items)


def _build_services(
    *,
    vector_recall_service=None,
    vector_index_repository=None,
    style_profile_repository=None,
) -> tuple[ContextPackService, InitializationApplicationService, WorkService, ChapterService, FilePlotArcStore]:
    work_repo = WorkRepo()
    chapter_repo = ChapterRepo()
    work_service = WorkService(work_repo=work_repo, chapter_repo=chapter_repo)
    chapter_service = ChapterService(chapter_repo=chapter_repo, work_repo=work_repo)
    job_store = FileAIJobStore()
    plot_arc_store = FilePlotArcStore()
    init_service = InitializationApplicationService(
        work_service=work_service,
        chapter_service=chapter_service,
        job_repository=job_store,
        step_repository=job_store,
        attempt_repository=job_store,
        initialization_repository=FileInitializationStore(),
        story_memory_repository=FileStoryMemoryStore(),
        story_state_repository=FileStoryStateStore(),
        plot_arc_repository=plot_arc_store,
        **build_initialization_analysis_dependencies(),
    )
    cp_service = ContextPackService(
        chapter_service=chapter_service,
        initialization_repository=FileInitializationStore(),
        story_memory_repository=FileStoryMemoryStore(),
        story_state_repository=FileStoryStateStore(),
        context_pack_repository=FileContextPackStore(),
        plot_arc_repository=plot_arc_store,
        vector_recall_service=vector_recall_service,
        vector_index_repository=vector_index_repository,
        style_profile_repository=style_profile_repository,
    )
    return cp_service, init_service, work_service, chapter_service, plot_arc_store


def test_context_pack_ready_with_story_memory_and_state() -> None:
    cp_service, init_service, work_service, chapter_service, _plot_arc_store = _build_services()
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
    assert any(item.source_type == "plot_arc_master" for item in snapshot.context_items)
    assert any(item.source_type == "plot_arc_volume" for item in snapshot.context_items)
    assert any(item.source_type == "plot_arc_sequence" for item in snapshot.context_items)
    assert any(item.source_type == "plot_arc_immediate" for item in snapshot.context_items)


def test_context_pack_includes_active_style_profile_as_optional_lowest_layer(tmp_path) -> None:
    style_repo = SQLiteStyleProfileRepository(tmp_path / "style-profile.db")
    profile = StyleProfile(
        profile_id="sp_active_001",
        work_id="work_001",
        source_type=StyleProfileSourceType.USER_UPLOAD,
        source_ref="upload_001",
        source_text_hash="sha256:style001",
        source_text_length=2200,
        confidence=0.48,
        low_confidence_reason="source_text_too_short",
        avg_sentence_length=14.0,
        sentence_length_variance=3.0,
        short_sentence_ratio=0.31,
        long_sentence_ratio=0.06,
        compound_sentence_ratio=0.22,
        avg_paragraph_length=66.0,
        paragraph_length_variance=9.0,
        dialogue_ratio=0.41,
        psychological_ratio=0.12,
        action_ratio=0.26,
        description_ratio=0.21,
        narrative_perspective="third_person_limited",
        tense_preference="past",
        style_summary="对白占比高，句式简洁。",
        style_tags=["简洁", "对白驱动"],
        version=1,
        status=StyleProfileStatus.ACTIVE,
        created_at="2026-06-23T10:00:00Z",
        updated_at="2026-06-23T10:00:00Z",
        confirmed_at="2026-06-23T10:05:00Z",
    )
    style_repo.save(profile)
    cp_service, init_service, work_service, chapter_service, _plot_arc_store = _build_services(
        style_profile_repository=style_repo
    )
    work = work_service.create_work("风格画像作品", "作者")
    chapter = chapter_service.list_chapters(work.id)[0]
    chapter_service.update_chapter(chapter.id.value, title="第一章", content="顾迟沿着灯塔台阶向上，脚步压得很轻。", expected_version=1)
    init_service.start_initialization(work.id, created_by="user_action")

    # Align the stored profile to the created work.
    style_repo.save(profile.model_copy(update={"work_id": work.id}))

    snapshot = cp_service.build_and_save(ContextPackBuildRequest(work_id=work.id, chapter_id=chapter.id.value))

    style_items = [item for item in snapshot.context_items if item.source_type == "style_dna" and item.included]
    assert style_items
    assert style_items[0].priority == ContextPackService.PRIORITY_STYLE_DNA
    assert style_items[0].metadata["low_confidence_reason"] == "source_text_too_short"
    assert "风格特征" in style_items[0].content_text


def test_context_pack_immediate_window_includes_scene_details_from_story_memory() -> None:
    cp_service, init_service, work_service, chapter_service, _plot_arc_store = _build_services()
    work = work_service.create_work("场景上下文作品", "作者")
    chapter = chapter_service.list_chapters(work.id)[0]
    chapter_service.update_chapter(
        chapter.id.value,
        title="第一章",
        content="夜里，顾迟在灯塔顶层翻看旧航海图。沈砚守在楼梯口。海雾里忽然传来钟声，顾迟意识到父亲留下的标记就在地图夹层。",
        expected_version=1,
    )

    init_service.start_initialization(work.id, created_by="user_action")
    readiness = cp_service.evaluate_readiness(work.id, chapter_id=chapter.id.value)

    scene_details = readiness["plot_arc_summary"]["immediate_window"]["scene_details"]

    assert scene_details
    assert scene_details[0]["location"] != ""
    assert "顾迟" in scene_details[0]["characters_present"]
    assert scene_details[0]["reveal_points"]


def test_context_pack_blocked_when_no_story_memory() -> None:
    cp_service, _, work_service, chapter_service, _plot_arc_store = _build_services()
    work = work_service.create_work("无记忆作品", "作者")
    chapter = chapter_service.list_chapters(work.id)[0]
    chapter_service.update_chapter(chapter.id.value, title="第一章", content="测试内容。", expected_version=1)

    request = ContextPackBuildRequest(work_id=work.id, chapter_id=chapter.id.value)
    snapshot = cp_service.build_and_save(request)

    assert snapshot.status == ContextPackStatus.BLOCKED
    assert "initialization_not_completed" in snapshot.blocked_reason or snapshot.blocked_reason != ""


def test_context_pack_blocked_when_initialization_not_completed() -> None:
    cp_service, _, work_service, _, _plot_arc_store = _build_services()
    work = work_service.create_work("未初始化作品", "作者")

    request = ContextPackBuildRequest(work_id=work.id)
    snapshot = cp_service.build_and_save(request)

    assert snapshot.status == ContextPackStatus.BLOCKED
    assert "initialization_not_completed" in snapshot.blocked_reason


def test_context_pack_degraded_when_story_memory_or_state_stale() -> None:
    cp_service, init_service, work_service, chapter_service, _plot_arc_store = _build_services()
    work = work_service.create_work("过时作品", "作者")
    chapter = chapter_service.list_chapters(work.id)[0]
    chapter_service.update_chapter(chapter.id.value, title="第一章", content="沈砚在雨夜回到旧城。", expected_version=1)

    init_service.start_initialization(work.id, created_by="user_action")
    init_service.mark_stale(work.id, reason="chapter_updated")

    request = ContextPackBuildRequest(work_id=work.id, chapter_id=chapter.id.value)
    snapshot = cp_service.build_and_save(request)

    assert snapshot.status == ContextPackStatus.DEGRADED
    assert snapshot.stale is True
    assert snapshot.blocked_reason == ""
    assert "stale" in snapshot.degraded_reason
    assert any("stale" in warning for warning in snapshot.warnings)


def test_context_pack_readiness_returns_plot_arc_projection_summary() -> None:
    cp_service, init_service, work_service, chapter_service, _plot_arc_store = _build_services()
    work = work_service.create_work("轨道作品", "作者")
    chapter = chapter_service.list_chapters(work.id)[0]
    chapter_service.update_chapter(
        chapter.id.value,
        title="第一章",
        content="顾迟在灯塔里发现旧地图，意识到海雾背后藏着更大的秘密。",
        expected_version=1,
    )

    init_service.start_initialization(work.id, created_by="user_action")

    readiness = cp_service.evaluate_readiness(work.id, chapter_id=chapter.id.value)

    assert readiness["status"] == "degraded"
    assert "plot_arc_statuses" in readiness
    assert readiness["plot_arc_statuses"]["master_arc"]["status"] in {"ready", "degraded"}
    assert readiness["plot_arc_statuses"]["volume_arc"]["status"] in {"pending", "degraded", "empty"}
    assert readiness["plot_arc_statuses"]["sequence_arc"]["status"] in {"pending", "degraded", "empty"}
    assert readiness["plot_arc_statuses"]["immediate_window"]["status"] in {"ready", "degraded"}
    assert "plot_arc_summary" in readiness
    assert readiness["plot_arc_summary"]["master_arc"]["arc_title"] != ""
    assert "recent_chapters_summary" in readiness["plot_arc_summary"]["immediate_window"]


def test_context_pack_uses_model_character_state_for_track_summary() -> None:
    cp_service, init_service, work_service, chapter_service, _plot_arc_store = _build_services()
    work = work_service.create_work("人物轨道清洗作品", "作者")
    chapter = chapter_service.list_chapters(work.id)[0]
    chapter_service.update_chapter(
        chapter.id.value,
        title="第一章",
        content="孔凡圣推门进来。宋成这时候也沉默了。宋成沉思片刻，宋成说先等等。",
        expected_version=1,
    )

    init_service.start_initialization(work.id, created_by="user_action")
    readiness = cp_service.evaluate_readiness(work.id, chapter_id=chapter.id.value)

    summary = readiness["plot_arc_summary"]
    assert summary["volume_arc"]["key_characters"] == ["孔凡圣", "宋成"]
    assert [
        item["character_name"] for item in summary["immediate_window"]["character_current_states"]
    ] == ["孔凡圣", "宋成"]
    assert {
        item["current_status"] for item in summary["immediate_window"]["character_current_states"]
    } == {"出现在本章"}
    assert {
        item["location"] for item in summary["immediate_window"]["character_current_states"]
    } == {"当前场景"}


def test_context_pack_uses_model_analysis_without_non_character_tokens() -> None:
    cp_service, init_service, work_service, chapter_service, _plot_arc_store = _build_services()
    work = work_service.create_work("人物污染清理作品", "作者")
    chapter = chapter_service.list_chapters(work.id)[0]
    chapter_service.update_chapter(
        chapter.id.value,
        title="第一章",
        content=(
            "孔凡圣收起家法宝和宗法器，包裹起来后看向宋成。"
            "毕竟周围的房间里还有许多金丹，宋成说先离开。"
        ),
        expected_version=1,
    )

    init_service.start_initialization(work.id, created_by="user_action")
    readiness = cp_service.evaluate_readiness(work.id, chapter_id=chapter.id.value)

    summary = readiness["plot_arc_summary"]
    assert summary["volume_arc"]["key_characters"] == ["孔凡圣", "宋成"]
    assert summary["immediate_window"]["active_plot_threads"] == []
    assert summary["immediate_window"]["recent_chapters_summary"] == ["第一章已完成结构化章节分析。"]
    serialized = str(summary)
    assert "家法宝" not in serialized
    assert "宗法器" not in serialized
    assert "包裹起" not in serialized
    assert "已完成最小分析" not in serialized


def test_context_pack_degraded_when_vector_recall_unavailable() -> None:
    cp_service, init_service, work_service, chapter_service, _plot_arc_store = _build_services()
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
    cp_service, init_service, work_service, chapter_service, _plot_arc_store = _build_services()
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


def test_initialization_persists_master_and_volume_arcs_for_independent_reads() -> None:
    cp_service, init_service, work_service, chapter_service, plot_arc_store = _build_services()
    work = work_service.create_work("持久化轨道作品", "作者")
    chapter = chapter_service.list_chapters(work.id)[0]
    chapter_service.update_chapter(
        chapter.id.value,
        title="第一章",
        content="顾迟在海边灯塔醒来，决定追查父亲失踪与旧城海雾的关系。",
        expected_version=1,
    )

    initialization = init_service.start_initialization(work.id, created_by="user_action")
    master_arc = plot_arc_store.get_master_arc(work.id)
    volume_arc = plot_arc_store.get_active_volume_arc(work.id, chapter_no=1)
    sequence_arc = plot_arc_store.get_active_sequence_arc(work.id, chapter_no=1)

    assert initialization.status.value == "completed"
    assert master_arc is not None
    assert master_arc.source_initialization_id == initialization.initialization_id
    assert master_arc.version == 1
    assert master_arc.built_by == "memory_agent"
    assert master_arc.last_updated_by == "memory_agent"
    assert master_arc.protagonist_motivation != ""
    assert volume_arc is not None
    assert volume_arc.version == 1
    assert volume_arc.built_by == "planner_agent"
    assert volume_arc.chapter_range["from_chapter"] == 1
    assert "to_chapter_estimate" in volume_arc.chapter_range
    assert sequence_arc is None
    assert cp_service.evaluate_readiness(work.id, chapter_id=chapter.id.value)["plot_arc_summary"]["master_arc"]["arc_title"] != ""


def test_context_pack_prefers_repository_plot_arcs_over_dynamic_fallback() -> None:
    cp_service, init_service, work_service, chapter_service, plot_arc_store = _build_services()
    work = work_service.create_work("仓储优先轨道作品", "作者")
    chapter = chapter_service.list_chapters(work.id)[0]
    chapter_service.update_chapter(
        chapter.id.value,
        title="第一章",
        content="顾迟在灯塔中看见一张旧地图，海雾里传来熟悉的钟声。",
        expected_version=1,
    )

    initialization = init_service.start_initialization(work.id, created_by="user_action")
    master_arc = plot_arc_store.get_master_arc(work.id)
    volume_arc = plot_arc_store.get_active_volume_arc(work.id, chapter_no=1)

    plot_arc_store.save_master_arc(
        master_arc.model_copy(
            update={
                "arc_title": "持久化主线标题",
                "ultimate_goal": "找到海雾源头",
                "current_stage": "灯塔调查",
            }
        )
    )
    plot_arc_store.save_volume_arc(
        volume_arc.model_copy(
            update={
                "status": "ready",
                "quality_level": "minimal",
                "stage_goal": "锁定守夜人留下的真相",
                "core_conflict": "顾迟与守夜人旧誓约的冲突",
            }
        )
    )

    readiness = cp_service.evaluate_readiness(work.id, chapter_id=chapter.id.value)

    assert initialization.status.value == "completed"
    assert readiness["plot_arc_summary"]["master_arc"]["arc_title"] == "持久化主线标题"
    assert readiness["plot_arc_summary"]["master_arc"]["ultimate_goal"] == "找到海雾源头"
    assert readiness["plot_arc_summary"]["volume_arc"]["stage_goal"] == "锁定守夜人留下的真相"
    assert readiness["plot_arc_statuses"]["volume_arc"]["status"] == "ready"


def test_context_pack_compresses_required_plot_arcs_and_marks_arc_trimmed() -> None:
    cp_service, _init_service, _work_service, _chapter_service, _plot_arc_store = _build_services()
    items = [
        ContextItem(
            item_id="immediate",
            source_type="plot_arc_immediate",
            priority=cp_service.PRIORITY_PLOT_ARC_IMMEDIATE,
            content_text="即时窗口完整上下文",
            token_estimate=220,
            required=True,
        ),
        ContextItem(
            item_id="sequence",
            source_type="plot_arc_sequence",
            priority=cp_service.PRIORITY_PLOT_ARC_SEQUENCE,
            content_text="序列轨道完整内容",
            token_estimate=180,
            required=True,
        ),
        ContextItem(
            item_id="volume",
            source_type="plot_arc_volume",
            priority=cp_service.PRIORITY_PLOT_ARC_VOLUME,
            content_text="卷轨道完整内容",
            token_estimate=160,
            required=True,
        ),
        ContextItem(
            item_id="master",
            source_type="plot_arc_master",
            priority=cp_service.PRIORITY_PLOT_ARC_MASTER,
            content_text="主线轨道完整内容",
            token_estimate=140,
            required=True,
        ),
    ]

    fitted_items, trimmed_items, warnings, overflow = cp_service._fit_required_items_with_budget(  # noqa: SLF001
        items,
        max_context_tokens=520,
    )

    assert overflow == 0
    assert "arc_trimmed" in warnings
    assert next(item for item in fitted_items if item.source_type == "plot_arc_immediate").included is True
    assert next(item for item in fitted_items if item.source_type == "plot_arc_master").included is True
    assert [item.source_type for item in trimmed_items] == [
        "plot_arc_sequence",
        "plot_arc_volume",
    ]


def test_context_pack_readiness_does_not_persist_snapshot() -> None:
    cp_service, init_service, work_service, chapter_service, _plot_arc_store = _build_services()
    work = work_service.create_work("只读就绪性作品", "作者")
    chapter = chapter_service.list_chapters(work.id)[0]
    chapter_service.update_chapter(chapter.id.value, title="第一章", content="陆川在档案馆里发现旧地图。", expected_version=1)

    init_service.start_initialization(work.id, created_by="user_action")

    assert cp_service.list_by_work(work.id) == []

    readiness = cp_service.evaluate_readiness(work.id, chapter_id=chapter.id.value)

    assert readiness["status"] in {"ready", "degraded"}
    assert cp_service.list_by_work(work.id) == []


def test_context_pack_evaluate_readiness_returns_status() -> None:
    cp_service, init_service, work_service, chapter_service, _plot_arc_store = _build_services()
    work = work_service.create_work("就绪作品", "作者")
    chapter = chapter_service.list_chapters(work.id)[0]
    chapter_service.update_chapter(chapter.id.value, title="第一章", content="顾宁站在塔顶俯瞰整个城市。", expected_version=1)

    init_service.start_initialization(work.id, created_by="user_action")

    readiness = cp_service.evaluate_readiness(work.id, chapter_id=chapter.id.value)

    assert readiness["status"] in {"ready", "degraded"}
    assert "context_pack_id" in readiness
    assert "estimated_token_count" in readiness


def test_context_pack_query_text_build_failure_degrades_and_skips_rag(monkeypatch) -> None:
    cp_service, init_service, work_service, chapter_service, _plot_arc_store = _build_services()
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

    cp_service, init_service, work_service, chapter_service, _plot_arc_store = _build_services()
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


def test_context_pack_degrades_when_vector_index_failed_without_calling_recall() -> None:
    vector_recall = _SpyVectorRecallService(
        items=[
            {
                "item_id": "recall_1",
                "source_id": "chapter_1",
                "content_text": "召回片段: 海雾背后另有真相。",
            }
        ]
    )
    cp_service, init_service, work_service, chapter_service, _plot_arc_store = _build_services(
        vector_recall_service=vector_recall,
        vector_index_repository=_StubVectorIndexRepository(
            {
                "work_id": "unused",
                "index_status": "failed",
                "stale_status": "fresh",
            }
        ),
    )
    work = work_service.create_work("索引失败作品", "作者")
    chapter = chapter_service.list_chapters(work.id)[0]
    chapter_service.update_chapter(chapter.id.value, title="第一章", content="顾迟在旧灯塔里翻出残缺海图。", expected_version=1)
    init_service.start_initialization(work.id, created_by="user_action")

    snapshot = cp_service.build_and_save(ContextPackBuildRequest(work_id=work.id, chapter_id=chapter.id.value))

    assert snapshot.status == ContextPackStatus.DEGRADED
    assert snapshot.vector_recall_status == "degraded"
    assert "vector_index_unavailable" in snapshot.warnings
    assert not any(item.source_type == "vector_recall" for item in snapshot.context_items)
    assert vector_recall.calls == []


def test_context_pack_degrades_when_vector_index_is_partial_stale_by_default() -> None:
    vector_recall = _SpyVectorRecallService(
        items=[
            {
                "item_id": "recall_1",
                "source_id": "chapter_1",
                "content_text": "召回片段: 海雾背后另有真相。",
                "stale_status": "stale",
                "metadata": {"source": "confirmed_chapter"},
            }
        ]
    )
    cp_service, init_service, work_service, chapter_service, _plot_arc_store = _build_services(
        vector_recall_service=vector_recall,
        vector_index_repository=_StubVectorIndexRepository(
            {
                "work_id": "unused",
                "index_status": "stale",
                "stale_status": "partial_stale",
            }
        ),
    )
    work = work_service.create_work("索引过期作品", "作者")
    chapter = chapter_service.list_chapters(work.id)[0]
    chapter_service.update_chapter(chapter.id.value, title="第一章", content="顾迟在旧灯塔里翻出残缺海图。", expected_version=1)
    init_service.start_initialization(work.id, created_by="user_action")

    snapshot = cp_service.build_and_save(ContextPackBuildRequest(work_id=work.id, chapter_id=chapter.id.value))

    assert snapshot.status == ContextPackStatus.DEGRADED
    assert snapshot.vector_recall_status == "degraded"
    assert "vector_index_stale_warning" in snapshot.warnings
    assert not any(item.source_type == "vector_recall" for item in snapshot.context_items)
    assert vector_recall.calls == []


def test_context_pack_allows_stale_vector_only_when_explicitly_enabled() -> None:
    vector_recall = _SpyVectorRecallService(
        items=[
            {
                "item_id": "recall_1",
                "source_id": "chapter_1",
                "content_text": "召回片段: 海雾背后另有真相。",
                "stale_status": "stale",
                "metadata": {"source": "confirmed_chapter"},
            }
        ]
    )
    cp_service, init_service, work_service, chapter_service, _plot_arc_store = _build_services(
        vector_recall_service=vector_recall,
        vector_index_repository=_StubVectorIndexRepository(
            {
                "work_id": "unused",
                "index_status": "stale",
                "stale_status": "partial_stale",
            }
        ),
    )
    work = work_service.create_work("允许陈旧召回作品", "作者")
    chapter = chapter_service.list_chapters(work.id)[0]
    chapter_service.update_chapter(chapter.id.value, title="第一章", content="顾迟在旧灯塔里翻出残缺海图。", expected_version=1)
    init_service.start_initialization(work.id, created_by="user_action")

    snapshot = cp_service.build_and_save(
        ContextPackBuildRequest(
            work_id=work.id,
            chapter_id=chapter.id.value,
            allow_stale_vector=True,
        )
    )

    assert snapshot.status == ContextPackStatus.DEGRADED
    assert any(item.source_type == "vector_recall" for item in snapshot.context_items)
    assert "vector_index_stale_warning" in snapshot.warnings
    assert vector_recall.calls and vector_recall.calls[0]["allow_stale"] is True


def test_context_pack_filters_illegal_recall_source_and_degrades() -> None:
    vector_recall = _SpyVectorRecallService(
        items=[
            {
                "item_id": "recall_1",
                "source_id": "draft_1",
                "content_text": "召回片段: 未确认候选稿内容。",
                "metadata": {"source": "candidate_draft"},
            }
        ]
    )
    cp_service, init_service, work_service, chapter_service, _plot_arc_store = _build_services(
        vector_recall_service=vector_recall,
        vector_index_repository=_StubVectorIndexRepository(
            {
                "work_id": "unused",
                "index_status": "ready",
                "stale_status": "fresh",
            }
        ),
    )
    work = work_service.create_work("非法来源作品", "作者")
    chapter = chapter_service.list_chapters(work.id)[0]
    chapter_service.update_chapter(chapter.id.value, title="第一章", content="顾迟在旧灯塔里翻出残缺海图。", expected_version=1)
    init_service.start_initialization(work.id, created_by="user_action")

    snapshot = cp_service.build_and_save(ContextPackBuildRequest(work_id=work.id, chapter_id=chapter.id.value))

    assert snapshot.status == ContextPackStatus.DEGRADED
    assert not any(item.source_type == "vector_recall" for item in snapshot.context_items)
    assert "illegal_recall_source" in snapshot.warnings
    assert "recall_result_empty_after_filter" in snapshot.warnings
