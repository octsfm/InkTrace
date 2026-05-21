from __future__ import annotations

from pathlib import Path

from application.services.ai.context_pack_service import ContextPackService
from application.services.ai.initialization_service import InitializationApplicationService
from application.services.ai.continuation_workflow import MinimalContinuationWorkflow
from application.services.ai.ai_job_service import AIJobService
from application.services.ai.tool_facade import CoreToolFacade, ToolDefinition, ToolError, ToolExecutionContext, ToolRegistry
from application.services.v1.chapter_service import ChapterService
from application.services.v1.work_service import WorkService
from domain.entities.ai.models import CandidateDraftStatus
from infrastructure.database.repositories import ChapterRepo, WorkRepo
from infrastructure.database.repositories.ai.file_ai_job_store import FileAIJobStore
from infrastructure.database.repositories.ai.file_candidate_draft_store import FileCandidateDraftStore
from infrastructure.database.repositories.ai.file_chapter_plan_store import FileChapterPlanStore
from infrastructure.database.repositories.ai.file_context_pack_store import FileContextPackStore
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
        writer=_StubWriter(),
    )
    return work_service, chapter_service, job_store, candidate_store, tool_facade, work, chapter


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
