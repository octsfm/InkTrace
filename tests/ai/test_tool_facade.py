from __future__ import annotations

from tests.ai.initialization_test_support import build_initialization_analysis_dependencies

from pathlib import Path

from application.services.ai.context_pack_service import ContextPackService
from application.services.ai.initialization_service import InitializationApplicationService
from application.services.ai.continuation_workflow import MinimalContinuationWorkflow
from application.services.ai.ai_job_service import AIJobService
from application.services.ai.tool_facade import CoreToolFacade, ToolDefinition, ToolError, ToolExecutionContext, ToolRegistry
from application.services.v1.chapter_service import ChapterService
from application.services.v1.work_service import WorkService
from domain.entities.ai.models import (
    AISuggestionActionType,
    AISuggestionStatus,
    AISuggestionType,
    ArcRef,
    CandidateDraftStatus,
    CandidateDraftVersionStatus,
    ChapterPlan,
    DirectionOption,
    DirectionPlanStatus,
    DirectionProposal,
    DirectionScore,
    DirectionSelection,
    PlanConfirmation,
    WritingTask,
    WritingTaskStatus,
)
from infrastructure.database.repositories import ChapterRepo, WorkRepo
from infrastructure.database.repositories.ai.file_ai_job_store import FileAIJobStore
from infrastructure.database.repositories.ai.file_ai_suggestion_store import FileAISuggestionStore
from infrastructure.database.repositories.ai.file_candidate_draft_store import FileCandidateDraftStore
from infrastructure.database.repositories.ai.file_chapter_plan_store import FileChapterPlanStore
from infrastructure.database.repositories.ai.file_context_pack_store import FileContextPackStore
from infrastructure.database.repositories.ai.file_direction_plan_store import FileDirectionPlanStore
from infrastructure.database.repositories.ai.file_initialization_store import FileInitializationStore
from infrastructure.database.repositories.ai.file_plot_arc_store import FilePlotArcStore
from infrastructure.database.repositories.ai.file_story_memory_store import FileStoryMemoryStore
from infrastructure.database.repositories.ai.file_story_state_store import FileStoryStateStore


class _StubWriter:
    def __init__(self, output: str = "暮色沉下来后，顾迟沿着灯塔台阶继续向上走去。") -> None:
        self.output = output

    def generate_candidate_text(self, *, context_pack, writing_task):
        return {
            "content": self.output,
            "provider_name": "fake",
            "model_name": "fake-writer",
            "model_role": "writer",
        }


def _build_context(tmp_path: Path):
    work_repo = WorkRepo()
    chapter_repo = ChapterRepo()
    work_service = WorkService(work_repo=work_repo, chapter_repo=chapter_repo)
    chapter_service = ChapterService(chapter_repo=chapter_repo, work_repo=work_repo)
    job_store = FileAIJobStore(tmp_path / "jobs.json")
    candidate_store = FileCandidateDraftStore(tmp_path / "candidate_drafts.json")
    chapter_plan_store = FileChapterPlanStore(tmp_path / "chapter_plans.json")
    direction_plan_store = FileDirectionPlanStore(tmp_path / "direction_plans.json")
    init_store = FileInitializationStore(tmp_path / "initializations.json")
    memory_store = FileStoryMemoryStore(tmp_path / "memory.json")
    state_store = FileStoryStateStore(tmp_path / "state.json")
    context_store = FileContextPackStore(tmp_path / "context_packs.json")
    plot_arc_store = FilePlotArcStore(tmp_path / "plot_arcs.json")
    init_service = InitializationApplicationService(
        work_service=work_service,
        chapter_service=chapter_service,
        job_repository=job_store,
        step_repository=job_store,
        attempt_repository=job_store,
        initialization_repository=init_store,
        story_memory_repository=memory_store,
        story_state_repository=state_store,
        plot_arc_repository=plot_arc_store,
        **build_initialization_analysis_dependencies(),
    )
    context_pack_service = ContextPackService(
        chapter_service=chapter_service,
        initialization_repository=init_store,
        story_memory_repository=memory_store,
        story_state_repository=state_store,
        context_pack_repository=context_store,
        plot_arc_repository=plot_arc_store,
    )
    work = work_service.create_work("ToolFacade 作品", "作者")
    chapter = chapter_service.list_chapters(work.id)[0]
    chapter = chapter_service.update_chapter(
        chapter.id.value,
        title="第一章",
        content="顾迟在海边灯塔醒来，发现潮声比记忆更近。",
        expected_version=1,
    )
    init_service.start_initialization(work.id, created_by="user_action")
    tool_facade = CoreToolFacade(
        context_pack_service=context_pack_service,
        candidate_draft_repository=candidate_store,
        chapter_plan_repository=chapter_plan_store,
        direction_plan_repository=direction_plan_store,
        story_memory_repository=memory_store,
        story_state_repository=state_store,
        writer=_StubWriter(),
    )
    return work_service, chapter_service, job_store, candidate_store, tool_facade, work, chapter


def test_writer_agent_tool_generates_and_persists_candidate_without_formal_chapter_write(tmp_path: Path) -> None:
    _, chapter_service, _, candidate_store, tool_facade, work, chapter = _build_context(tmp_path)
    context_result = tool_facade.call(
        "build_context_pack",
        context=ToolExecutionContext(
            caller_type="workflow",
            work_id=work.id,
            chapter_id=chapter.id.value,
            request_id="req_writer_context",
            trace_id="trace_writer_context",
            side_effect_level="plan_write",
        ),
        payload={
            "work_id": work.id,
            "chapter_id": chapter.id.value,
            "user_instruction": "继续写下去",
            "continuation_mode": "continue_chapter",
            "model_role": "writer",
        },
    )
    context_pack = context_result.payload["context_pack"]
    task = WritingTask(
        writing_task_id="wt_agent_writer_1",
        work_id=work.id,
        chapter_id=chapter.id.value,
        target_chapter_id=chapter.id.value,
        status=WritingTaskStatus.READY,
        writing_goal="让顾迟继续调查灯塔",
        user_instruction="继续写下去",
        created_by="user_action",
    )
    tool_facade._direction_plan_repository.save_writing_task(task)  # noqa: SLF001
    original_content = next(item for item in chapter_service.list_chapters(work.id) if item.id.value == chapter.id.value).content
    writer_context = ToolExecutionContext(
        caller_type="agent",
        work_id=work.id,
        chapter_id=chapter.id.value,
        request_id="req_agent_writer",
        trace_id="trace_agent_writer",
        agent_session_id="agent_session_writer_real",
        agent_step_id="agent_step_writer_real",
        agent_type="writer",
        session_status="running",
        step_status="waiting_observation",
        resource_scope_refs=[f"work:{work.id}", f"chapter:{chapter.id.value}"],
        side_effect_level="safe_write_candidate",
    )

    result = tool_facade.call(
        "run_writer_step",
        context=writer_context,
        payload={
            "work_id": work.id,
            "chapter_id": chapter.id.value,
            "context_pack_id": context_pack.context_pack_id,
            "writing_task_id": task.writing_task_id,
            "source_job_id": "job_agent_writer_real",
        },
    )

    assert result.ok is True
    assert result.payload["result_ref"].startswith("candidate_draft:cd_")
    candidate_id = result.payload["result_ref"].split(":", 1)[1]
    draft = candidate_store.get(candidate_id)
    assert draft.content == _StubWriter().output
    assert draft.agent_session_id == "agent_session_writer_real"
    assert draft.source_context_pack_id == context_pack.context_pack_id
    current_chapter = next(item for item in chapter_service.list_chapters(work.id) if item.id.value == chapter.id.value)
    assert current_chapter.content == original_content


def test_memory_read_tools_return_persisted_refs_instead_of_fabricated_ids(tmp_path: Path) -> None:
    _, _, _, _, tool_facade, work, chapter = _build_context(tmp_path)
    context = ToolExecutionContext(
        caller_type="agent",
        work_id=work.id,
        chapter_id=chapter.id.value,
        request_id="req_memory_read",
        trace_id="trace_memory_read",
        agent_session_id="session_memory_read",
        agent_step_id="step_memory_read",
        agent_type="memory",
        session_status="running",
        step_status="running",
        resource_scope_refs=[f"work:{work.id}", f"chapter:{chapter.id.value}"],
        side_effect_level="read_only",
    )

    memory = tool_facade.call(
        "get_story_memory_snapshot",
        context=context,
        payload={"work_id": work.id},
    )
    state = tool_facade.call(
        "get_story_state_baseline",
        context=context,
        payload={"work_id": work.id},
    )
    memory_again = tool_facade.call(
        "get_story_memory_snapshot",
        context=context,
        payload={"work_id": work.id},
    )

    assert memory.ok is True
    assert memory.payload["result_ref"].startswith("memory_context:memory_")
    assert memory.payload["story_memory_ref"].startswith("story_memory:memory_")
    assert memory.payload["result_ref"] == memory_again.payload["result_ref"]
    assert state.ok is True
    assert state.payload["result_ref"].startswith("story_state:state_")
    assert "story_memory" not in memory.payload
    assert "story_state" not in state.payload


def test_memory_read_tools_fail_when_persisted_state_is_missing(tmp_path: Path) -> None:
    _, _, _, _, tool_facade, _, _ = _build_context(tmp_path)
    context = ToolExecutionContext(
        caller_type="agent",
        work_id="missing-work",
        request_id="req_memory_missing",
        trace_id="trace_memory_missing",
        agent_session_id="session_memory_missing",
        agent_step_id="step_memory_missing",
        agent_type="memory",
        session_status="running",
        step_status="running",
        resource_scope_refs=["work:missing-work"],
        side_effect_level="read_only",
    )

    memory = tool_facade.call("get_story_memory_snapshot", context=context, payload={"work_id": "missing-work"})
    state = tool_facade.call("get_story_state_baseline", context=context, payload={"work_id": "missing-work"})

    assert memory.ok is False
    assert memory.error_code == "story_memory_not_found"
    assert state.ok is False
    assert state.error_code == "story_state_not_found"


def test_tool_facade_blocks_agent_user_action_and_formal_write(tmp_path: Path) -> None:
    _, _, _, _, tool_facade, work, chapter = _build_context(tmp_path)
    context = ToolExecutionContext(
        caller_type="workflow",
        work_id=work.id,
        chapter_id=chapter.id.value,
        request_id="req_test",
        trace_id="trace_test",
    )

    denied_user_action = tool_facade.call(
        "apply_candidate_to_draft",
        context=context,
        payload={"candidate_draft_id": "cd_1", "user_action": True},
    )
    denied_formal_write = tool_facade.call(
        "formal_chapter_write",
        context=context,
        payload={"chapter_id": chapter.id.value},
    )

    assert denied_user_action.ok is False
    assert denied_user_action.error_code == "tool_permission_denied"
    assert denied_formal_write.ok is False
    assert denied_formal_write.error_code == "tool_permission_denied"


def test_tool_registry_register_disable_and_unregistered_behavior() -> None:
    registry = ToolRegistry()
    registry.register(
        ToolDefinition(
            tool_name="demo_tool",
            allowed_callers={"workflow"},
            side_effect_level="read_only",
            enabled=True,
        )
    )

    assert registry.get("demo_tool").tool_name == "demo_tool"

    registry.register(
        ToolDefinition(
            tool_name="disabled_tool",
            allowed_callers={"workflow"},
            side_effect_level="read_only",
            enabled=False,
        )
    )
    assert registry.get("disabled_tool").enabled is False
    assert registry.get("missing_tool") is None


def test_tool_facade_returns_structured_tool_error_for_disabled_and_unknown_tools(tmp_path: Path) -> None:
    _, _, job_store, _, tool_facade, work, chapter = _build_context(tmp_path)
    tool_facade.register_tool(
        ToolDefinition(
            tool_name="disabled_tool",
            allowed_callers={"workflow"},
            side_effect_level="read_only",
            enabled=False,
        ),
        lambda payload: {"ok": True},
    )
    context = ToolExecutionContext(
        caller_type="workflow",
        work_id=work.id,
        chapter_id=chapter.id.value,
        request_id="req_tool_error",
        trace_id="trace_tool_error",
    )

    disabled = tool_facade.call("disabled_tool", context=context, payload={})
    missing = tool_facade.call("missing_tool", context=context, payload={})

    for result, expected_code in ((disabled, "tool_disabled"), (missing, "tool_not_registered")):
        assert result.ok is False
        assert isinstance(result.error, ToolError)
        assert result.error.error_code == expected_code
        assert result.error.safe_message
        assert result.error.retryable is False
        assert result.error.user_visible is True
        assert result.error.debug_ref
        assert result.error.source_tool
        assert result.error.source_service
        assert result.error.occurred_at


def test_tool_facade_rejects_agent_call_without_required_runtime_context(tmp_path: Path) -> None:
    _, _, _, _, tool_facade, work, chapter = _build_context(tmp_path)
    tool_facade.register_tool(
        ToolDefinition(
            tool_name="agent_read_tool",
            allowed_callers={"agent"},
            side_effect_level="read_only",
            enabled=True,
        ),
        lambda payload: {"ok": True},
    )
    context = ToolExecutionContext(
        caller_type="agent",
        work_id=work.id,
        chapter_id=chapter.id.value,
        request_id="req_agent_invalid",
        trace_id="trace_agent_invalid",
        agent_type="writer",
        session_status="running",
        step_status="waiting_observation",
    )

    result = tool_facade.call("agent_read_tool", context=context, payload={})

    assert result.ok is False
    assert result.error_code == "tool_context_invalid"


def test_tool_facade_accepts_agent_call_with_runtime_context(tmp_path: Path) -> None:
    _, _, _, _, tool_facade, work, chapter = _build_context(tmp_path)
    tool_facade.register_tool(
        ToolDefinition(
            tool_name="agent_read_tool",
            allowed_callers={"agent"},
            side_effect_level="read_only",
            enabled=True,
        ),
        lambda payload: {"echo": payload["value"]},
    )
    context = ToolExecutionContext(
        caller_type="agent",
        work_id=work.id,
        chapter_id=chapter.id.value,
        request_id="req_agent_ok",
        trace_id="trace_agent_ok",
        agent_session_id="agent_session_1",
        agent_step_id="agent_step_1",
        agent_type="writer",
        session_status="running",
        step_status="waiting_observation",
        resource_scope_refs=[f"work:{work.id}", f"chapter:{chapter.id.value}"],
        side_effect_level="read_only",
    )

    result = tool_facade.call("agent_read_tool", context=context, payload={"value": "ok"})

    assert result.ok is True
    assert result.payload["echo"] == "ok"


def test_tool_facade_rejects_agent_call_with_missing_resource_scope(tmp_path: Path) -> None:
    _, _, _, _, tool_facade, work, chapter = _build_context(tmp_path)
    tool_facade.register_tool(
        ToolDefinition(
            tool_name="agent_read_tool",
            allowed_callers={"agent"},
            side_effect_level="read_only",
            enabled=True,
        ),
        lambda payload: {"echo": "ok"},
    )
    context = ToolExecutionContext(
        caller_type="agent",
        work_id=work.id,
        chapter_id=chapter.id.value,
        request_id="req_agent_scope",
        trace_id="trace_agent_scope",
        agent_session_id="agent_session_1",
        agent_step_id="agent_step_1",
        agent_type="writer",
        session_status="running",
        step_status="waiting_observation",
        resource_scope_refs=[],
        side_effect_level="read_only",
    )

    result = tool_facade.call("agent_read_tool", context=context, payload={})

    assert result.ok is False
    assert result.error_code == "tool_context_invalid"


def test_tool_facade_rejects_agent_call_with_side_effect_mismatch(tmp_path: Path) -> None:
    _, _, _, _, tool_facade, work, chapter = _build_context(tmp_path)
    tool_facade.register_tool(
        ToolDefinition(
            tool_name="agent_read_tool",
            allowed_callers={"agent"},
            side_effect_level="read_only",
            enabled=True,
        ),
        lambda payload: {"echo": "ok"},
    )
    context = ToolExecutionContext(
        caller_type="agent",
        work_id=work.id,
        chapter_id=chapter.id.value,
        request_id="req_agent_side_effect",
        trace_id="trace_agent_side_effect",
        agent_session_id="agent_session_1",
        agent_step_id="agent_step_1",
        agent_type="writer",
        session_status="running",
        step_status="waiting_observation",
        resource_scope_refs=[f"work:{work.id}"],
        side_effect_level="draft_write",
    )

    result = tool_facade.call("agent_read_tool", context=context, payload={})

    assert result.ok is False
    assert result.error_code == "tool_context_invalid"


def test_tool_facade_agent_matrix_allows_memory_planner_reviewer_rewriter_tools(tmp_path: Path) -> None:
    _, _, _, _, tool_facade, work, chapter = _build_context(tmp_path)
    shared = {
        "work_id": work.id,
        "chapter_id": chapter.id.value,
        "request_id": "req_matrix_ok",
        "trace_id": "trace_matrix_ok",
        "agent_session_id": "agent_session_ok",
        "agent_step_id": "agent_step_ok",
        "session_status": "running",
        "step_status": "waiting_observation",
        "resource_scope_refs": [f"work:{work.id}", f"chapter:{chapter.id.value}"],
    }

    planner_result = tool_facade.call(
        "create_direction_proposal",
        context=ToolExecutionContext(caller_type="agent", agent_type="planner", side_effect_level="plan_write", **shared),
        payload={"proposal_id": "dir_1"},
    )
    memory_result = tool_facade.call(
        "create_memory_update_suggestion",
        context=ToolExecutionContext(caller_type="agent", agent_type="memory", side_effect_level="safe_write_suggestion", **shared),
        payload={"suggestion_id": "mem_1"},
    )
    reviewer_result = tool_facade.call(
        "create_review_report",
        context=ToolExecutionContext(caller_type="agent", agent_type="reviewer", side_effect_level="safe_write_review", **shared),
        payload={"review_id": "rev_1"},
    )
    rewriter_result = tool_facade.call(
        "create_candidate_version",
        context=ToolExecutionContext(caller_type="agent", agent_type="rewriter", side_effect_level="safe_write_candidate", **shared),
        payload={"candidate_version_id": "ver_1"},
    )

    assert planner_result.ok is True
    assert planner_result.payload["result_ref"] == "direction:dir_1"
    assert memory_result.ok is True
    assert memory_result.payload["result_ref"] == "memory_update_suggestion:mem_1"
    assert reviewer_result.ok is True
    assert reviewer_result.payload["result_ref"] == "review_report:rev_1"
    assert rewriter_result.ok is True
    assert rewriter_result.payload["result_ref"] == "candidate_version:ver_1"


def test_tool_facade_create_chapter_plan_persists_formal_plan_record(tmp_path: Path) -> None:
    _, _, _, _, tool_facade, work, chapter = _build_context(tmp_path)
    context = ToolExecutionContext(
        caller_type="agent",
        work_id=work.id,
        chapter_id=chapter.id.value,
        request_id="req_plan_persist",
        trace_id="trace_plan_persist",
        agent_session_id="agent_session_plan",
        agent_step_id="agent_step_plan",
        agent_type="planner",
        session_status="running",
        step_status="waiting_observation",
        resource_scope_refs=[f"work:{work.id}", f"chapter:{chapter.id.value}"],
        side_effect_level="plan_write",
    )

    result = tool_facade.call(
        "create_chapter_plan",
        context=context,
        payload={
            "chapter_plan_id": "plan_1",
            "work_id": work.id,
            "chapter_id": chapter.id.value,
            "direction_proposal_id": "dir_1",
            "selected_option_id": "opt_a",
            "selection_id": "sel_1",
            "agent_session_id": "agent_session_plan",
            "source_context_pack_id": "cp_1",
            "status": "waiting_for_confirmation",
            "version": 1,
            "plan_summary": "接下来两章推进灯塔调查并逼近海雾真相。",
            "total_estimated_chapters": 1,
            "created_by": "planner_agent",
            "stale_status": "fresh",
            "created_at": "2026-05-20T00:00:00+00:00",
            "updated_at": "2026-05-20T00:00:00+00:00",
            "plan_items": [
                {
                    "item_id": "plan_item_1",
                    "plan_order": 1,
                    "chapter_goal": "潜入灯塔档案室取得旧航海图。",
                    "key_events": [
                        {
                            "beat_order": 1,
                            "beat_name": "潜入档案室",
                            "beat_description": "顾迟避开守夜人进入档案室。",
                            "beat_type": "development",
                        }
                    ],
                    "conflict_progression": "顾迟必须在守夜人赶到前拿到线索。",
                    "forbidden_items": ["不要提前揭示父亲真相"],
                    "required_beats": ["取得航海图"],
                    "arc_alignment": [
                        {
                            "arc_type": "sequence",
                            "arc_id": "sa_seed",
                            "arc_summary": "近期序列聚焦灯塔调查",
                            "arc_status_at_generation": "pending",
                        }
                    ],
                }
            ],
        },
    )
    plan = tool_facade._chapter_plan_repository.get("plan_1")  # noqa: SLF001

    assert result.ok is True
    assert result.payload["result_ref"] == "chapter_plan:plan_1"
    assert plan.plan_summary == "接下来两章推进灯塔调查并逼近海雾真相。"
    assert plan.plan_items[0].chapter_goal == "潜入灯塔档案室取得旧航海图。"
    assert plan.plan_items[0].key_events[0].beat_name == "潜入档案室"


def test_tool_facade_candidate_draft_and_rewriter_version_persist_p1s6_version_chain(tmp_path: Path) -> None:
    _, _, _, candidate_store, tool_facade, work, chapter = _build_context(tmp_path)
    context = ToolExecutionContext(
        caller_type="agent",
        work_id=work.id,
        chapter_id=chapter.id.value,
        request_id="req_candidate_version_chain",
        trace_id="trace_candidate_version_chain",
        agent_session_id="agent_session_writer",
        agent_step_id="agent_step_writer",
        agent_type="writer",
        session_status="running",
        step_status="waiting_observation",
        resource_scope_refs=[f"work:{work.id}", f"chapter:{chapter.id.value}"],
        side_effect_level="safe_write_candidate",
    )

    saved_result = tool_facade.call(
        "save_candidate_draft",
        context=context,
        payload={
            "candidate_draft_id": "cd_chain",
            "work_id": work.id,
            "chapter_id": chapter.id.value,
            "agent_session_id": "agent_session_writer",
            "writing_task_id": "wt_1",
            "direction_plan_snapshot_id": "snap_1",
            "source_context_pack_id": "cp_1",
            "source_job_id": "job_1",
            "candidate_version_id": "ver_1",
            "content": "v1 初稿：顾迟推门看见灯塔旧档案。",
            "writer_model_role": "writer",
            "provider_name": "fake",
            "model_name": "fake-writer",
            "created_by": "workflow",
            "metadata": {"chapter_version": 2},
        },
    )
    rewriter_result = tool_facade.call(
        "create_candidate_version",
        context=ToolExecutionContext(
            caller_type="agent",
            work_id=work.id,
            chapter_id=chapter.id.value,
            request_id="req_candidate_version_chain_2",
            trace_id="trace_candidate_version_chain_2",
            agent_session_id="agent_session_rewriter",
            agent_step_id="agent_step_rewriter",
            agent_type="rewriter",
            session_status="running",
            step_status="waiting_observation",
            resource_scope_refs=[f"work:{work.id}", f"chapter:{chapter.id.value}"],
            side_effect_level="safe_write_candidate",
        ),
        payload={
            "candidate_version_id": "ver_2",
            "candidate_draft_id": "cd_chain",
            "work_id": work.id,
            "chapter_id": chapter.id.value,
            "agent_session_id": "agent_session_rewriter",
            "source_candidate_draft_id": "cd_chain",
            "source_version_id": "ver_1",
            "parent_version_id": "ver_1",
            "version_no": 2,
            "status": "generated",
            "content": "v2 修订稿：顾迟在旧档案里找到父亲留下的坐标。",
            "content_summary": "v2 修订稿摘要",
            "word_count": 2,
            "writing_task_id": "wt_1",
            "direction_plan_snapshot_id": "snap_1",
            "source_context_pack_id": "cp_1",
            "created_by": "rewriter_agent",
        },
    )

    draft = candidate_store.get("cd_chain")
    version_1 = candidate_store.get_version("ver_1")
    version_2 = candidate_store.get_version("ver_2")

    assert saved_result.ok is True
    assert saved_result.payload["candidate_draft"].candidate_draft_id == "cd_chain"
    assert rewriter_result.ok is True
    assert rewriter_result.payload["result_ref"] == "candidate_version:ver_2"
    assert draft.selected_version_id == "ver_1"
    assert draft.latest_version_no == 2
    assert version_1.status == CandidateDraftVersionStatus.GENERATED
    assert version_2.parent_version_id == "ver_1"
    assert version_2.status == CandidateDraftVersionStatus.GENERATED


def test_tool_facade_create_ai_suggestion_persists_formal_record(tmp_path: Path) -> None:
    _, _, _, _, tool_facade, work, chapter = _build_context(tmp_path)
    suggestion_store = FileAISuggestionStore(tmp_path / "ai_suggestions_tool.json")
    tool_facade._ai_suggestion_repository = suggestion_store  # noqa: SLF001
    context = ToolExecutionContext(
        caller_type="agent",
        work_id=work.id,
        chapter_id=chapter.id.value,
        request_id="req_tool_suggestion",
        trace_id="trace_tool_suggestion",
        agent_session_id="agent_session_review",
        agent_step_id="agent_step_review",
        agent_type="reviewer",
        session_status="running",
        step_status="waiting_observation",
        resource_scope_refs=[f"work:{work.id}", f"chapter:{chapter.id.value}"],
        side_effect_level="safe_write_suggestion",
    )

    result = tool_facade.call(
        "create_ai_suggestion",
        context=context,
        payload={
            "suggestion_id": "ais_1",
            "work_id": work.id,
            "chapter_id": chapter.id.value,
            "agent_session_id": "agent_session_review",
            "source": {
                "source_type": "review_issue",
                "source_ref_id": "issue_1",
                "source_agent_type": "reviewer",
                "source_agent_session_id": "agent_session_review",
                "source_version_id": "ver_1",
            },
            "target": {
                "target_type": "candidate_draft_version",
                "target_ref_id": "ver_1",
                "target_scope": "version",
                "target_snapshot_ref": "snap_1",
            },
            "suggestion_type": "rewrite_suggestion",
            "severity": "high",
            "priority": "high",
            "title": "建议收紧灯塔段落",
            "summary": "把守夜人动机写得更明确。",
            "rationale": "审稿报告指出人物动机跳跃。",
            "proposed_action": "转化为 RewriteInstruction",
            "status": "generated",
            "created_by": "reviewer_agent",
            "request_id": "review_1",
            "trace_id": "trace_tool_suggestion",
            "action": {
                "action_type": "convert_to_rewrite_instruction",
                "requires_user_action": True,
                "action_status": "pending",
            },
            "metadata": {"review_id": "review_1"},
        },
    )
    items = suggestion_store.list_suggestions(work_id=work.id, chapter_id=chapter.id.value)

    assert result.ok is True
    assert result.payload["result_ref"] == "ai_suggestion:ais_1"
    assert len(items) == 1
    assert items[0].suggestion_id == "ais_1"
    assert items[0].suggestion_type == AISuggestionType.REWRITE_SUGGESTION
    assert items[0].status == AISuggestionStatus.GENERATED
    assert items[0].source.source_agent_type == "reviewer"
    assert items[0].target.target_ref_id == "ver_1"
    assert items[0].action.action_type == AISuggestionActionType.CONVERT_TO_REWRITE_INSTRUCTION
    assert items[0].metadata == {"review_id": "review_1"}


def test_tool_facade_create_direction_proposal_and_writing_task_persist_formal_records(tmp_path: Path) -> None:
    _, _, _, _, tool_facade, work, chapter = _build_context(tmp_path)
    direction_store = FileDirectionPlanStore(tmp_path / "direction_plan_tool.json")
    tool_facade._direction_plan_repository = direction_store  # noqa: SLF001
    context = ToolExecutionContext(
        caller_type="agent",
        work_id=work.id,
        chapter_id=chapter.id.value,
        request_id="req_direction_task_persist",
        trace_id="trace_direction_task_persist",
        agent_session_id="agent_session_plan",
        agent_step_id="agent_step_plan",
        agent_type="planner",
        session_status="running",
        step_status="waiting_observation",
        resource_scope_refs=[f"work:{work.id}", f"chapter:{chapter.id.value}"],
        side_effect_level="plan_write",
    )

    direction_result = tool_facade.call(
        "create_direction_proposal",
        context=context,
        payload={
            "direction_proposal_id": "dp_1",
            "work_id": work.id,
            "chapter_id": chapter.id.value,
            "agent_session_id": "agent_session_plan",
            "source_context_pack_id": "cp_1",
            "source_arc_refs": [
                {
                    "arc_type": "master",
                    "arc_id": "ma_1",
                    "arc_summary": "寻找海雾真相",
                    "arc_status_at_generation": "ready",
                }
            ],
            "source_memory_refs": ["memory_1"],
            "status": "waiting_for_selection",
            "version": 1,
            "generation_metadata": {"prompt_key": "direction_proposal_generation"},
            "created_by": "planner_agent",
            "created_at": "2026-05-20T00:00:00+00:00",
            "updated_at": "2026-05-20T00:00:00+00:00",
            "options": [
                {
                    "option_id": "do_1_a",
                    "direction_proposal_id": "dp_1",
                    "label": "A",
                    "plot_summary": "主角沿着钟声追查灯塔真相。",
                    "narrative_premise": "沿着父亲留下的线索逼近真相。",
                    "estimated_chapters": 3,
                    "chapter_preview": ["追查钟声", "发现旧誓约", "遭遇守夜人"],
                    "base_arc_refs": [
                        {
                            "arc_type": "master",
                            "arc_id": "ma_1",
                            "arc_summary": "寻找海雾真相",
                            "arc_status_at_generation": "ready",
                        }
                    ],
                    "score": {
                        "total_score": 86,
                        "consistency_score": 88,
                        "conflict_density_score": 84,
                        "satisfaction_rhythm_score": 82,
                        "foreshadow_progress_score": 87,
                        "risk_controllability_score": 83,
                    },
                }
            ],
        },
    )
    task_result = tool_facade.call(
        "create_writing_task",
        context=context,
        payload={
            "writing_task_id": "wt_1",
            "work_id": work.id,
            "chapter_id": chapter.id.value,
            "direction_proposal_id": "dp_1",
            "selected_option_id": "do_1_a",
            "chapter_plan_id": "plan_1",
            "plan_item_id": "item_1",
            "agent_session_id": "agent_session_plan",
            "status": "ready",
            "version": 1,
            "writing_goal": "写出主角进入灯塔后的第一次真相碰撞。",
            "must_include": ["钟声", "旧标记"],
            "must_not_include": ["直接揭晓终局"],
            "arc_constraints": [
                {
                    "arc_type": "sequence",
                    "arc_id": "sa_1",
                    "arc_summary": "近期序列聚焦灯塔调查",
                    "arc_status_at_generation": "ready",
                }
            ],
            "direction_summary": "方向 A：追查钟声来源",
            "plan_summary": "第 1 章：进入灯塔内部调查",
            "generated_by": "planner_agent",
            "created_at": "2026-05-20T00:10:00+00:00",
            "updated_at": "2026-05-20T00:10:00+00:00",
        },
    )

    proposal = direction_store.get_direction_proposal("dp_1")
    task = direction_store.get_writing_task("wt_1")

    assert direction_result.ok is True
    assert direction_result.payload["result_ref"] == "direction:dp_1"
    assert proposal.options[0].label == "A"
    assert task_result.ok is True
    assert task_result.payload["result_ref"] == "writing_task:wt_1"
    assert task.status == WritingTaskStatus.READY
    assert task.direction_summary == "方向 A：追查钟声来源"


def test_tool_facade_regenerated_chapter_plan_supersedes_old_plan_and_stales_writing_task(tmp_path: Path) -> None:
    _, _, _, _, tool_facade, work, chapter = _build_context(tmp_path)
    chapter_plan_store = FileChapterPlanStore(tmp_path / "chapter_plans_regen.json")
    direction_store = FileDirectionPlanStore(tmp_path / "direction_plan_regen.json")
    tool_facade._chapter_plan_repository = chapter_plan_store  # noqa: SLF001
    tool_facade._direction_plan_repository = direction_store  # noqa: SLF001
    chapter_plan_store.save(
        ChapterPlan(
            chapter_plan_id="plan_1",
            work_id=work.id,
            chapter_id=chapter.id.value,
            direction_proposal_id="dir_1",
            selected_option_id="opt_a",
            selection_id="sel_1",
            agent_session_id="agent_session_old",
            source_context_pack_id="cp_1",
            status=DirectionPlanStatus.WAITING_FOR_CONFIRMATION,
            version=1,
            plan_summary="旧计划摘要",
            total_estimated_chapters=1,
            created_by="planner_agent",
            stale_status="fresh",
            created_at="2026-05-20T00:00:00+00:00",
            updated_at="2026-05-20T00:00:00+00:00",
            plan_items=[
                {
                    "item_id": "item_1",
                    "chapter_plan_id": "plan_1",
                    "plan_order": 1,
                    "chapter_goal": "旧章节目标",
                    "conflict_progression": "旧冲突推进",
                }
            ],
        )
    )
    direction_store.save_writing_task(
        WritingTask(
            writing_task_id="wt_old",
            work_id=work.id,
            chapter_id=chapter.id.value,
            direction_proposal_id="dir_1",
            selected_option_id="opt_a",
            chapter_plan_id="plan_1",
            plan_item_id="item_1",
            agent_session_id="agent_session_old",
            status=WritingTaskStatus.READY,
            version=1,
            writing_goal="旧写作任务",
            direction_summary="旧方向",
            plan_summary="旧计划摘要",
            stale_status="fresh",
            generated_by="planner_agent",
            created_at="2026-05-20T00:05:00+00:00",
            updated_at="2026-05-20T00:05:00+00:00",
        )
    )
    context = ToolExecutionContext(
        caller_type="agent",
        work_id=work.id,
        chapter_id=chapter.id.value,
        request_id="req_plan_regenerated",
        trace_id="trace_plan_regenerated",
        agent_session_id="agent_session_plan",
        agent_step_id="agent_step_plan",
        agent_type="planner",
        session_status="running",
        step_status="waiting_observation",
        resource_scope_refs=[f"work:{work.id}", f"chapter:{chapter.id.value}"],
        side_effect_level="plan_write",
    )

    result = tool_facade.call(
        "create_chapter_plan",
        context=context,
        payload={
            "chapter_plan_id": "plan_2",
            "work_id": work.id,
            "chapter_id": chapter.id.value,
            "direction_proposal_id": "dir_1",
            "selected_option_id": "opt_a",
            "selection_id": "sel_1",
            "agent_session_id": "agent_session_plan",
            "source_context_pack_id": "cp_2",
            "status": "waiting_for_confirmation",
            "version": 2,
            "plan_summary": "新计划摘要",
            "total_estimated_chapters": 1,
            "created_by": "planner_agent",
            "stale_status": "fresh",
            "created_at": "2026-05-20T01:00:00+00:00",
            "updated_at": "2026-05-20T01:00:00+00:00",
            "plan_items": [
                {
                    "item_id": "item_2",
                    "plan_order": 1,
                    "chapter_goal": "新章节目标",
                    "conflict_progression": "新冲突推进",
                }
            ],
        },
    )

    old_plan = chapter_plan_store.get("plan_1")
    new_plan = chapter_plan_store.get("plan_2")
    old_task = direction_store.get_writing_task("wt_old")

    assert result.ok is True
    assert old_plan.status == DirectionPlanStatus.SUPERSEDED
    assert old_plan.stale_status == "stale"
    assert old_plan.stale_reason == "chapter_plan_regenerated"
    assert new_plan.status == DirectionPlanStatus.WAITING_FOR_CONFIRMATION
    assert old_task.status == WritingTaskStatus.STALE
    assert old_task.stale_status == "stale"
    assert old_task.stale_reason == "chapter_plan_regenerated"


def test_tool_facade_regenerated_direction_supersedes_related_plan_and_stales_writing_task(tmp_path: Path) -> None:
    _, _, _, _, tool_facade, work, chapter = _build_context(tmp_path)
    chapter_plan_store = FileChapterPlanStore(tmp_path / "chapter_plans_direction_regen.json")
    direction_store = FileDirectionPlanStore(tmp_path / "direction_plan_direction_regen.json")
    tool_facade._chapter_plan_repository = chapter_plan_store  # noqa: SLF001
    tool_facade._direction_plan_repository = direction_store  # noqa: SLF001
    direction_store.save_direction_proposal(
        DirectionProposal(
            direction_proposal_id="dp_1",
            work_id=work.id,
            chapter_id=chapter.id.value,
            agent_session_id="agent_session_old",
            source_context_pack_id="cp_1",
            source_arc_refs=[],
            source_memory_refs=["memory_1"],
            status=DirectionPlanStatus.WAITING_FOR_SELECTION,
            version=1,
            options=[
                DirectionOption(
                    option_id="do_1_a",
                    direction_proposal_id="dp_1",
                    label="A",
                    plot_summary="旧方向摘要",
                    narrative_premise="旧方向前提",
                    estimated_chapters=3,
                    chapter_preview=["旧预告"],
                    base_arc_refs=[],
                    score=DirectionScore(
                        total_score=80,
                        consistency_score=80,
                        conflict_density_score=80,
                        satisfaction_rhythm_score=80,
                        foreshadow_progress_score=80,
                        risk_controllability_score=80,
                    ),
                )
            ],
            created_by="planner_agent",
            created_at="2026-05-20T00:00:00+00:00",
            updated_at="2026-05-20T00:00:00+00:00",
        )
    )
    chapter_plan_store.save(
        ChapterPlan(
            chapter_plan_id="plan_1",
            work_id=work.id,
            chapter_id=chapter.id.value,
            direction_proposal_id="dp_1",
            selected_option_id="do_1_a",
            selection_id="sel_1",
            agent_session_id="agent_session_old",
            source_context_pack_id="cp_1",
            status=DirectionPlanStatus.CONFIRMED,
            version=1,
            plan_summary="旧计划摘要",
            total_estimated_chapters=1,
            confirmed_by="user_action",
            created_by="planner_agent",
            stale_status="fresh",
            created_at="2026-05-20T00:10:00+00:00",
            updated_at="2026-05-20T00:10:00+00:00",
            plan_items=[
                {
                    "item_id": "item_1",
                    "chapter_plan_id": "plan_1",
                    "plan_order": 1,
                    "chapter_goal": "旧章节目标",
                    "conflict_progression": "旧冲突推进",
                }
            ],
        )
    )
    direction_store.save_writing_task(
        WritingTask(
            writing_task_id="wt_old",
            work_id=work.id,
            chapter_id=chapter.id.value,
            direction_proposal_id="dp_1",
            selected_option_id="do_1_a",
            chapter_plan_id="plan_1",
            plan_item_id="item_1",
            agent_session_id="agent_session_old",
            status=WritingTaskStatus.READY,
            version=1,
            writing_goal="旧写作任务",
            direction_summary="旧方向",
            plan_summary="旧计划摘要",
            stale_status="fresh",
            generated_by="planner_agent",
            created_at="2026-05-20T00:15:00+00:00",
            updated_at="2026-05-20T00:15:00+00:00",
        )
    )
    context = ToolExecutionContext(
        caller_type="agent",
        work_id=work.id,
        chapter_id=chapter.id.value,
        request_id="req_direction_regenerated",
        trace_id="trace_direction_regenerated",
        agent_session_id="agent_session_plan",
        agent_step_id="agent_step_plan",
        agent_type="planner",
        session_status="running",
        step_status="waiting_observation",
        resource_scope_refs=[f"work:{work.id}", f"chapter:{chapter.id.value}"],
        side_effect_level="plan_write",
    )

    result = tool_facade.call(
        "create_direction_proposal",
        context=context,
        payload={
            "direction_proposal_id": "dp_2",
            "work_id": work.id,
            "chapter_id": chapter.id.value,
            "agent_session_id": "agent_session_plan",
            "source_context_pack_id": "cp_2",
            "source_arc_refs": [],
            "source_memory_refs": ["memory_2"],
            "status": "waiting_for_selection",
            "version": 2,
            "created_by": "planner_agent",
            "created_at": "2026-05-20T01:00:00+00:00",
            "updated_at": "2026-05-20T01:00:00+00:00",
            "options": [
                {
                    "option_id": "do_2_a",
                    "label": "A",
                    "plot_summary": "新方向摘要",
                    "narrative_premise": "新方向前提",
                    "estimated_chapters": 3,
                    "chapter_preview": ["新预告"],
                    "base_arc_refs": [],
                    "score": {
                        "total_score": 90,
                        "consistency_score": 90,
                        "conflict_density_score": 90,
                        "satisfaction_rhythm_score": 90,
                        "foreshadow_progress_score": 90,
                        "risk_controllability_score": 90,
                    },
                }
            ],
        },
    )

    old_proposal = direction_store.get_direction_proposal("dp_1")
    new_proposal = direction_store.get_direction_proposal("dp_2")
    old_plan = chapter_plan_store.get("plan_1")
    old_task = direction_store.get_writing_task("wt_old")

    assert result.ok is True
    assert old_proposal.status == DirectionPlanStatus.SUPERSEDED
    assert old_proposal.stale_status == "stale"
    assert old_proposal.stale_reason == "direction_regenerated"
    assert new_proposal.status == DirectionPlanStatus.WAITING_FOR_SELECTION
    assert old_plan.status == DirectionPlanStatus.SUPERSEDED
    assert old_plan.stale_status == "stale"
    assert old_plan.stale_reason == "direction_regenerated"
    assert old_task.status == WritingTaskStatus.STALE
    assert old_task.stale_status == "stale"
    assert old_task.stale_reason == "direction_regenerated"


def test_direction_plan_store_persists_formal_planning_entities(tmp_path: Path) -> None:
    store = FileDirectionPlanStore(tmp_path / "direction_plan.json")
    arc_refs = [
        ArcRef(
            arc_type="master",
            arc_id="ma_1",
            arc_summary="寻找海雾真相",
            arc_status_at_generation="ready",
        )
    ]
    option = DirectionOption(
        option_id="do_1_a",
        direction_proposal_id="dp_1",
        label="A",
        plot_summary="主角继续追查灯塔钟声。",
        narrative_premise="沿着父亲留下的线索逼近真相。",
        estimated_chapters=3,
        chapter_preview=["追查钟声", "发现旧誓约", "守夜人反扑"],
        base_arc_refs=arc_refs,
        score=DirectionScore(
            total_score=86,
            consistency_score=88,
            conflict_density_score=84,
            satisfaction_rhythm_score=82,
            foreshadow_progress_score=87,
            risk_controllability_score=83,
        ),
    )
    proposal = DirectionProposal(
        direction_proposal_id="dp_1",
        work_id="work_1",
        chapter_id="chapter_1",
        agent_session_id="session_1",
        source_context_pack_id="cp_1",
        source_arc_refs=arc_refs,
        source_memory_refs=["memory_1"],
        status=DirectionPlanStatus.WAITING_FOR_SELECTION,
        options=[option],
        generation_metadata={"prompt_key": "direction_proposal_generation"},
        created_at="2026-05-20T00:00:00Z",
        updated_at="2026-05-20T00:00:00Z",
    )
    selection = DirectionSelection(
        selection_id="ds_1",
        direction_proposal_id="dp_1",
        selected_option_id="do_1_a",
        work_id="work_1",
        chapter_id="chapter_1",
        agent_session_id="session_1",
        selection_type="direct_select",
        user_id="user_action",
        created_at="2026-05-20T00:01:00Z",
    )
    confirmation = PlanConfirmation(
        confirmation_id="pc_1",
        chapter_plan_id="cp_1",
        direction_proposal_id="dp_1",
        work_id="work_1",
        chapter_id="chapter_1",
        agent_session_id="session_1",
        confirmation_type="direct_confirm",
        user_id="user_action",
        created_at="2026-05-20T00:02:00Z",
    )
    task = WritingTask(
        writing_task_id="wt_1",
        work_id="work_1",
        chapter_id="chapter_2",
        direction_proposal_id="dp_1",
        selected_option_id="do_1_a",
        chapter_plan_id="cp_1",
        plan_item_id="item_1",
        agent_session_id="session_1",
        status=WritingTaskStatus.READY,
        writing_goal="写出主角进入灯塔后的第一次真相碰撞。",
        must_include=["钟声", "旧标记"],
        must_not_include=["直接揭晓终局"],
        arc_constraints=arc_refs,
        direction_summary="方向 A：追查钟声来源",
        plan_summary="第 2 章：进入灯塔内部调查",
        created_at="2026-05-20T00:03:00Z",
        updated_at="2026-05-20T00:03:00Z",
    )

    store.save_direction_proposal(proposal)
    store.save_direction_selection(selection)
    store.save_plan_confirmation(confirmation)
    store.save_writing_task(task)

    assert store.get_direction_proposal("dp_1").direction_proposal_id == "dp_1"
    assert store.get_direction_selection("ds_1").selected_option_id == "do_1_a"
    assert store.get_plan_confirmation("pc_1").confirmation_type == "direct_confirm"
    assert store.get_writing_task("wt_1").status == WritingTaskStatus.READY
    assert store.list_direction_proposals("work_1")[0].direction_proposal_id == "dp_1"


def test_tool_facade_agent_matrix_rejects_cross_agent_write_tools(tmp_path: Path) -> None:
    _, _, _, _, tool_facade, work, chapter = _build_context(tmp_path)
    shared = {
        "caller_type": "agent",
        "work_id": work.id,
        "chapter_id": chapter.id.value,
        "request_id": "req_matrix_deny",
        "trace_id": "trace_matrix_deny",
        "agent_session_id": "agent_session_deny",
        "agent_step_id": "agent_step_deny",
        "session_status": "running",
        "step_status": "waiting_observation",
        "resource_scope_refs": [f"work:{work.id}"],
    }

    reviewer_calls_writer = tool_facade.call(
        "run_writer_step",
        context=ToolExecutionContext(agent_type="reviewer", side_effect_level="safe_write_candidate", **shared),
        payload={"writing_task": {}, "context_pack": {}},
    )
    writer_calls_review = tool_facade.call(
        "create_review_report",
        context=ToolExecutionContext(agent_type="writer", side_effect_level="safe_write_review", **shared),
        payload={"review_id": "rev_2"},
    )
    planner_calls_apply = tool_facade.call(
        "apply_candidate_to_draft",
        context=ToolExecutionContext(agent_type="planner", side_effect_level="plan_write", **shared),
        payload={"candidate_draft_id": "cd_1"},
    )

    assert reviewer_calls_writer.ok is False
    assert reviewer_calls_writer.error_code == "tool_permission_denied"
    assert writer_calls_review.ok is False
    assert writer_calls_review.error_code == "tool_permission_denied"
    assert planner_calls_apply.ok is False
    assert planner_calls_apply.error_code == "tool_permission_denied"


def test_tool_facade_agent_matrix_allows_shared_trace_and_conflict_tools(tmp_path: Path) -> None:
    _, _, _, _, tool_facade, work, chapter = _build_context(tmp_path)
    shared = {
        "caller_type": "agent",
        "work_id": work.id,
        "chapter_id": chapter.id.value,
        "request_id": "req_shared_tools",
        "trace_id": "trace_shared_tools",
        "agent_session_id": "agent_session_shared",
        "agent_step_id": "agent_step_shared",
        "session_status": "running",
        "step_status": "waiting_observation",
        "resource_scope_refs": [f"work:{work.id}", f"chapter:{chapter.id.value}"],
    }

    conflict_result = tool_facade.call(
        "request_conflict_check",
        context=ToolExecutionContext(agent_type="writer", side_effect_level="read_only", **shared),
        payload={"target_ref": "candidate_draft:cd_1"},
    )
    observation_result = tool_facade.call(
        "create_agent_observation",
        context=ToolExecutionContext(agent_type="planner", side_effect_level="trace_only", **shared),
        payload={"observation_id": "obs_1"},
    )
    trace_result = tool_facade.call(
        "create_agent_trace_event",
        context=ToolExecutionContext(agent_type="reviewer", side_effect_level="trace_only", **shared),
        payload={"trace_event_id": "trace_evt_1"},
    )

    assert conflict_result.ok is True
    assert conflict_result.payload["result_ref"] == "conflict_status:candidate_draft:cd_1"
    assert observation_result.ok is True
    assert observation_result.payload["result_ref"] == "agent_observation:obs_1"
    assert trace_result.ok is True
    assert trace_result.payload["result_ref"] == "agent_trace_event:trace_evt_1"


def test_continuation_workflow_runs_through_tool_facade_only(tmp_path: Path) -> None:
    work_service, chapter_service, job_store, candidate_store, tool_facade, work, chapter = _build_context(tmp_path)
    workflow = MinimalContinuationWorkflow(
        work_service=work_service,
        chapter_service=chapter_service,
        tool_facade=tool_facade,
        candidate_draft_repository=candidate_store,
        job_repository=job_store,
        step_repository=job_store,
        attempt_repository=job_store,
    )

    result = workflow.start_continuation(work.id, chapter.id.value, user_instruction="继续写下去")
    draft = workflow.get_candidate_draft(result.candidate_draft_id)

    assert result.status == "pending_review"
    assert draft.status == CandidateDraftStatus.PENDING_REVIEW
    assert [entry["tool_name"] for entry in tool_facade.audit_logs] == [
        "update_job_step_progress",
        "build_context_pack",
        "mark_job_step_completed",
        "update_job_step_progress",
        "run_writer_step",
        "mark_job_step_completed",
        "update_job_step_progress",
        "validate_writer_output",
        "mark_job_step_completed",
        "update_job_step_progress",
        "save_candidate_draft",
        "mark_job_step_completed",
        "mark_job_completed",
    ]


def test_continuation_workflow_job_step_progress_uses_tool_facade_instead_of_direct_mark_calls(tmp_path: Path) -> None:
    work_service, chapter_service, job_store, candidate_store, tool_facade, work, chapter = _build_context(tmp_path)
    tool_facade_with_jobs = CoreToolFacade(
        context_pack_service=tool_facade._context_pack_service,  # noqa: SLF001
        candidate_draft_repository=candidate_store,
        writer=_StubWriter(),
        job_service=AIJobService(
            job_repository=job_store,
            step_repository=job_store,
            attempt_repository=job_store,
        ),
    )
    workflow = MinimalContinuationWorkflow(
        work_service=work_service,
        chapter_service=chapter_service,
        tool_facade=tool_facade_with_jobs,
        candidate_draft_repository=candidate_store,
        job_repository=job_store,
        step_repository=job_store,
        attempt_repository=job_store,
    )

    def _boom(*args, **kwargs):
        raise AssertionError("direct_job_mark_call_forbidden")

    workflow._job_service.mark_step_running = _boom  # type: ignore[method-assign]  # noqa: SLF001
    workflow._job_service.mark_step_failed = _boom  # type: ignore[method-assign]  # noqa: SLF001
    workflow._job_service.mark_step_completed = _boom  # type: ignore[method-assign]  # noqa: SLF001
    workflow._job_service.mark_step_skipped = _boom  # type: ignore[method-assign]  # noqa: SLF001
    workflow._job_service.mark_job_failed = _boom  # type: ignore[method-assign]  # noqa: SLF001
    workflow._job_service.mark_job_completed = _boom  # type: ignore[method-assign]  # noqa: SLF001

    result = workflow.start_continuation(work.id, chapter.id.value, user_instruction="继续写下去")

    assert result.status == "pending_review"
