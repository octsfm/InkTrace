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
from infrastructure.database.repositories.ai.file_context_pack_store import FileContextPackStore
from infrastructure.database.repositories.ai.file_initialization_store import FileInitializationStore
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
