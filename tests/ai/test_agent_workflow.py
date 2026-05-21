from __future__ import annotations

import pytest

from application.services.ai.agent_runtime_service import AgentRuntimeService
from application.services.ai.ai_job_service import AIJobService
from application.services.ai.tool_facade import CoreToolFacade
from domain.entities.ai.models import (
    ArcQualityLevel,
    ArcStatus,
    AgentObservation,
    AgentObservationType,
    AgentSessionStatus,
    AgentStepStatus,
    AgentWorkflowType,
    ChapterBeat,
    ChapterPlan,
    ChapterPlanItem,
    MasterArc,
    VolumeArc,
    WorkflowDecision,
    WorkflowStageName,
    WorkflowType,
)
from infrastructure.database.repositories.ai.file_agent_runtime_store import FileAgentRuntimeStore
from infrastructure.database.repositories.ai.file_ai_job_store import FileAIJobStore
from infrastructure.database.repositories.ai.file_chapter_plan_store import FileChapterPlanStore
from infrastructure.database.repositories.ai.file_plot_arc_store import FilePlotArcStore


class _StubContextPackService:
    def create_context_pack(self, request):
        raise NotImplementedError


class _StubCandidateDraftRepository:
    def save(self, draft):
        return draft

    def get(self, candidate_draft_id: str):
        raise KeyError(candidate_draft_id)


class _StubWriter:
    def generate_candidate_text(self, *, context_pack, writing_task):
        return {
            "content": "stub",
            "provider_name": "stub",
            "model_name": "stub",
            "model_role": "writer",
        }


def _build_runtime(tmp_path) -> AgentRuntimeService:
    agent_store = FileAgentRuntimeStore(tmp_path / "agent_runtime.json")
    job_store = FileAIJobStore(tmp_path / "ai_jobs.json")
    job_service = AIJobService(job_repository=job_store, step_repository=job_store, attempt_repository=job_store)
    tool_facade = CoreToolFacade(
        context_pack_service=_StubContextPackService(),
        candidate_draft_repository=_StubCandidateDraftRepository(),
        writer=_StubWriter(),
        job_service=job_service,
    )
    return AgentRuntimeService(
        session_repository=agent_store,
        step_repository=agent_store,
        observation_repository=agent_store,
        ai_job_service=job_service,
        tool_facade=tool_facade,
    )


def _fail_current_step(runtime: AgentRuntimeService, session_id: str, *, safe_message: str = "step failed") -> str:
    session = runtime.get_session(session_id)
    step_id = session.current_step_id
    runtime.record_observation(
        step_id,
        AgentObservation(
            observation_id=f"obs_fail_{step_id}",
            session_id=session_id,
            step_id=step_id,
            observation_type=AgentObservationType.TOOL_RESULT,
            source_type="system",
            status="failed",
            safe_message=safe_message,
            decision="fail_step",
            decision_reason=safe_message,
            error_code="stage_failed",
            error_message=safe_message,
            request_id=session.request_id,
            trace_id=session.trace_id,
        ),
    )
    return step_id


def _last_stage_record_with_reason_code(run, reason_code: str):
    for record in reversed(run.stage_history):
        if record.metadata.get("reason_code") == reason_code:
            return record
    raise AssertionError(f"stage_history_missing_reason_code:{reason_code}")


def test_workflow_definition_registry_registers_required_p1_s2_definitions() -> None:
    from application.services.ai.agent_workflow import AgentWorkflowDefinitionRegistry

    definitions = AgentWorkflowDefinitionRegistry.list_definitions()

    assert {
        WorkflowType.CONTINUATION_WORKFLOW,
        WorkflowType.REVISION_WORKFLOW,
        WorkflowType.PLANNING_WORKFLOW,
        WorkflowType.MEMORY_UPDATE_WORKFLOW,
        WorkflowType.REVIEW_WORKFLOW,
        WorkflowType.FULL_WORKFLOW,
    }.issubset(set(definitions))

    continuation = AgentWorkflowDefinitionRegistry.get_definition(WorkflowType.CONTINUATION_WORKFLOW)
    assert [stage.stage_name for stage in continuation.stages[:5]] == [
        WorkflowStageName.SESSION_INIT,
        WorkflowStageName.MEMORY_CONTEXT_PREPARE,
        WorkflowStageName.PLANNING_PREPARE,
        WorkflowStageName.DIRECTION_SELECTION_WAITING,
        WorkflowStageName.CHAPTER_PLAN_CONFIRM_WAITING,
    ]
    assert continuation.default_policy.formal_write_allowed is False
    assert continuation.default_policy.auto_apply_allowed is False


def test_agent_orchestrator_start_workflow_forces_hard_safety_policy_flags_false(tmp_path) -> None:
    from application.services.ai.agent_workflow import AgentOrchestrator

    runtime = _build_runtime(tmp_path)
    orchestrator = AgentOrchestrator(runtime_service=runtime)

    run = orchestrator.start_workflow(
        work_id="work-1",
        chapter_id="chapter-1",
        workflow_type=WorkflowType.CONTINUATION_WORKFLOW,
        user_instruction="继续写这一章",
        caller_type="user_action",
        policy_overrides={"formal_write_allowed": True, "auto_apply_allowed": True},
    )

    assert run.policy.formal_write_allowed is False
    assert run.policy.auto_apply_allowed is False


def test_agent_orchestrator_start_continuation_workflow_enters_memory_stage_and_persists_checkpoint(tmp_path) -> None:
    from application.services.ai.agent_workflow import AgentOrchestrator

    runtime = _build_runtime(tmp_path)
    orchestrator = AgentOrchestrator(runtime_service=runtime)

    run = orchestrator.start_workflow(
        work_id="work-1",
        chapter_id="chapter-1",
        workflow_type=WorkflowType.CONTINUATION_WORKFLOW,
        user_instruction="继续写这一章",
        caller_type="user_action",
    )
    session = runtime.get_session(run.session_id)
    step = runtime.get_step(session.current_step_id)

    assert session.workflow_type == AgentWorkflowType.CONTINUATION
    assert run.current_stage == WorkflowStageName.MEMORY_CONTEXT_PREPARE
    assert step.action == WorkflowStageName.MEMORY_CONTEXT_PREPARE.value
    assert step.metadata["model_role"] == "analysis"
    assert step.metadata["output_schema_key"] == "memory_context"
    assert step.metadata["formal_write_forbidden"] is True
    assert run.checkpoints[-1].current_stage == WorkflowStageName.MEMORY_CONTEXT_PREPARE
    assert session.metadata["workflow_run"]["current_stage"] == WorkflowStageName.MEMORY_CONTEXT_PREPARE.value
    assert run.stage_history[0].metadata["reason_code"] == "session_started"


def test_agent_orchestrator_continuation_enters_direction_waiting_without_auto_skip(tmp_path) -> None:
    from application.services.ai.agent_workflow import AgentOrchestrator

    runtime = _build_runtime(tmp_path)
    orchestrator = AgentOrchestrator(runtime_service=runtime)
    run = orchestrator.start_workflow(
        work_id="work-1",
        chapter_id="chapter-1",
        workflow_type=WorkflowType.CONTINUATION_WORKFLOW,
        user_instruction="继续写这一章",
        caller_type="user_action",
    )

    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="memory_context:mem_1",
        safe_message="memory ready",
    )
    assert run.current_stage == WorkflowStageName.PLANNING_PREPARE

    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="direction:dir_1",
        safe_message="planning ready",
    )
    session = runtime.get_session(run.session_id)
    step = runtime.get_step(session.current_step_id)

    assert run.current_stage == WorkflowStageName.DIRECTION_SELECTION_WAITING
    assert session.status == AgentSessionStatus.WAITING_FOR_USER
    assert step.status == AgentStepStatus.WAITING_USER
    planning_step = runtime.get_step(run.checkpoints[-2].current_step_id)
    assert planning_step.metadata["model_role"] == "planning"
    assert planning_step.metadata["output_schema_key"] == "chapter_plan"
    assert run.checkpoints[-1].waiting_for_user_reason == "direction_selection"
    assert run.stage_history[-1].metadata["reason_code"] == "planning_prepare_success"


def test_agent_orchestrator_result_refs_record_source_agent_type_for_main_handoff_chain(tmp_path) -> None:
    from application.services.ai.agent_workflow import AgentOrchestrator

    runtime = _build_runtime(tmp_path)
    orchestrator = AgentOrchestrator(runtime_service=runtime)
    run = orchestrator.start_workflow(
        work_id="work-1",
        chapter_id="chapter-1",
        workflow_type=WorkflowType.CONTINUATION_WORKFLOW,
        user_instruction="继续写这一章",
        caller_type="user_action",
    )

    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="memory_context:mem_1",
        safe_message="memory ready",
    )
    assert any(item.ref_type == "memory_context" and item.source_agent_type == "memory" for item in run.result_refs)

    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="direction:dir_1",
        safe_message="planning ready",
    )
    assert any(item.ref_type == "direction" and item.source_agent_type == "planner" for item in run.result_refs)

    run = orchestrator.submit_user_decision(
        run.session_id,
        user_decision="confirm_direction",
        safe_message="direction confirmed",
        request_id="req_chain_direction",
        metadata={"selected_direction_id": "dir_1"},
    )
    run = orchestrator.submit_user_decision(
        run.session_id,
        user_decision="confirm_chapter_plan",
        safe_message="chapter plan confirmed",
        request_id="req_chain_plan",
        metadata={"selected_chapter_plan_id": "plan_1"},
    )
    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="writing_task:task_1",
        safe_message="writing ready",
    )
    assert any(item.ref_type == "writing_task" and item.source_agent_type == "planner" for item in run.result_refs)

    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="candidate_draft:draft_1",
        safe_message="draft ready",
    )
    assert any(item.ref_type == "candidate_draft" and item.source_agent_type == "writer" for item in run.result_refs)

    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="review_report:review_1",
        safe_message="review ready",
    )
    assert any(item.ref_type == "review_report" and item.source_agent_type == "reviewer" for item in run.result_refs)


def test_agent_orchestrator_user_direction_decision_advances_to_plan_confirmation(tmp_path) -> None:
    from application.services.ai.agent_workflow import AgentOrchestrator

    runtime = _build_runtime(tmp_path)
    orchestrator = AgentOrchestrator(runtime_service=runtime)
    run = orchestrator.start_workflow(
        work_id="work-1",
        chapter_id="chapter-1",
        workflow_type=WorkflowType.CONTINUATION_WORKFLOW,
        user_instruction="继续写这一章",
        caller_type="user_action",
    )
    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="memory_context:mem_1",
        safe_message="memory ready",
    )
    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="direction:dir_1",
        safe_message="planning ready",
    )

    run = orchestrator.submit_user_decision(
        run.session_id,
        user_decision="confirm_direction",
        safe_message="direction confirmed",
        request_id="req_user_direction",
        metadata={"selected_direction_id": "dir_1"},
    )
    session = runtime.get_session(run.session_id)

    assert run.current_stage == WorkflowStageName.CHAPTER_PLAN_CONFIRM_WAITING
    assert session.status == AgentSessionStatus.WAITING_FOR_USER
    assert run.checkpoints[-1].selected_direction_id == "dir_1"
    assert run.checkpoints[-1].waiting_for_user_reason == "chapter_plan_confirmation"


def test_agent_orchestrator_direction_selection_waiting_uses_workflow_step_agent_type(tmp_path) -> None:
    from application.services.ai.agent_workflow import AgentOrchestrator

    runtime = _build_runtime(tmp_path)
    orchestrator = AgentOrchestrator(runtime_service=runtime)
    run = orchestrator.start_workflow(
        work_id="work-1",
        chapter_id="chapter-1",
        workflow_type=WorkflowType.CONTINUATION_WORKFLOW,
        user_instruction="继续写这一章",
        caller_type="user_action",
    )
    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="memory_context:mem_1",
        safe_message="memory ready",
    )
    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="direction:dir_1",
        safe_message="planning ready",
    )
    session = runtime.get_session(run.session_id)
    step = runtime.get_step(session.current_step_id)

    assert run.current_stage == WorkflowStageName.DIRECTION_SELECTION_WAITING
    assert step.agent_type == "workflow"
    assert step.step_type == "wait_user_decision"
    assert run.checkpoints[-1].waiting_for_user_reason == "direction_selection"


def test_agent_orchestrator_revision_workflow_stops_rewriter_loop_at_max_rounds(tmp_path) -> None:
    from application.services.ai.agent_workflow import AgentOrchestrator

    runtime = _build_runtime(tmp_path)
    orchestrator = AgentOrchestrator(runtime_service=runtime)
    run = orchestrator.start_workflow(
        work_id="work-1",
        chapter_id="chapter-1",
        workflow_type=WorkflowType.REVISION_WORKFLOW,
        user_instruction="修订这一稿",
        caller_type="user_action",
        policy_overrides={"max_revision_rounds": 1},
    )

    assert run.current_stage == WorkflowStageName.WRITING_PREPARE

    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="writing_context:ctx_1",
        safe_message="revision input ready",
    )
    assert run.current_stage == WorkflowStageName.REWRITING
    assert run.revision_round == 1

    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.RETURN_TO_REVIEWER,
        result_ref="candidate_version:ver_1",
        safe_message="rewrite ready",
    )
    assert run.current_stage == WorkflowStageName.REVIEWING

    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.ENTER_REWRITER,
        result_ref="review_report:review_1",
        safe_message="review complete",
    )

    assert run.current_stage == WorkflowStageName.CANDIDATE_READY
    assert run.revision_round == 1


def test_agent_orchestrator_continuation_apply_enters_memory_review_waiting(tmp_path) -> None:
    from application.services.ai.agent_workflow import AgentOrchestrator

    runtime = _build_runtime(tmp_path)
    orchestrator = AgentOrchestrator(runtime_service=runtime)
    run = orchestrator.start_workflow(
        work_id="work-1",
        chapter_id="chapter-1",
        workflow_type=WorkflowType.CONTINUATION_WORKFLOW,
        user_instruction="继续写这一章",
        caller_type="user_action",
    )
    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="memory_context:mem_1",
        safe_message="memory ready",
    )
    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="direction:dir_1",
        safe_message="planning ready",
    )
    run = orchestrator.submit_user_decision(
        run.session_id,
        user_decision="confirm_direction",
        safe_message="direction confirmed",
        request_id="req_user_direction",
        metadata={"selected_direction_id": "dir_1"},
    )
    run = orchestrator.submit_user_decision(
        run.session_id,
        user_decision="confirm_chapter_plan",
        safe_message="chapter plan confirmed",
        request_id="req_user_plan",
        metadata={"selected_chapter_plan_id": "plan_1"},
    )
    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="writing_task:task_1",
        safe_message="writing context ready",
    )
    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="candidate_draft:draft_1",
        safe_message="draft ready",
    )
    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="review_report:review_1",
        safe_message="review ready",
    )

    assert run.current_stage == WorkflowStageName.CANDIDATE_READY

    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="candidate_draft:draft_1",
        safe_message="candidate ready",
    )
    session = runtime.get_session(run.session_id)
    assert run.current_stage == WorkflowStageName.HUMAN_REVIEW_WAITING
    assert session.status == AgentSessionStatus.WAITING_FOR_USER

    run = orchestrator.submit_user_decision(
        run.session_id,
        user_decision="apply",
        safe_message="candidate applied",
        request_id="req_apply",
    )
    assert run.current_stage == WorkflowStageName.MEMORY_SUGGESTION

    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="memory_update_suggestion:mem_upd_1",
        safe_message="memory suggestion ready",
    )
    session = runtime.get_session(run.session_id)

    assert run.current_stage == WorkflowStageName.MEMORY_REVIEW_WAITING
    assert session.status == AgentSessionStatus.WAITING_FOR_USER


def test_agent_orchestrator_apply_records_reason_code_metadata(tmp_path) -> None:
    from application.services.ai.agent_workflow import AgentOrchestrator

    runtime = _build_runtime(tmp_path)
    orchestrator = AgentOrchestrator(runtime_service=runtime)
    run = orchestrator.start_workflow(
        work_id="work-1",
        chapter_id="chapter-1",
        workflow_type=WorkflowType.CONTINUATION_WORKFLOW,
        user_instruction="继续写这一章",
        caller_type="user_action",
    )
    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="memory_context:mem_1",
        safe_message="memory ready",
    )
    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="direction:dir_1",
        safe_message="planning ready",
    )
    run = orchestrator.submit_user_decision(
        run.session_id,
        user_decision="confirm_direction",
        safe_message="direction confirmed",
        request_id="req_apply_reason_direction",
        metadata={"selected_direction_id": "dir_1"},
    )
    run = orchestrator.submit_user_decision(
        run.session_id,
        user_decision="confirm_chapter_plan",
        safe_message="chapter plan confirmed",
        request_id="req_apply_reason_plan",
        metadata={"selected_chapter_plan_id": "plan_1"},
    )
    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="writing_task:task_1",
        safe_message="writing context ready",
    )
    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="candidate_draft:draft_1",
        safe_message="draft ready",
    )
    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="review_report:review_1",
        safe_message="review ready",
    )
    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="candidate_draft:draft_1",
        safe_message="candidate ready",
    )

    run = orchestrator.submit_user_decision(
        run.session_id,
        user_decision="apply",
        safe_message="candidate applied",
        request_id="req_apply_reason",
    )

    assert _last_stage_record_with_reason_code(run, "user_applied_candidate").metadata["reason_code"] == "user_applied_candidate"
    assert any(item.ref_type == "review_decision" and item.ref_id == "apply" for item in run.result_refs)


def test_agent_orchestrator_reject_candidate_records_reason_code_metadata(tmp_path) -> None:
    from application.services.ai.agent_workflow import AgentOrchestrator

    runtime = _build_runtime(tmp_path)
    orchestrator = AgentOrchestrator(runtime_service=runtime)
    run = orchestrator.start_workflow(
        work_id="work-1",
        chapter_id="chapter-1",
        workflow_type=WorkflowType.CONTINUATION_WORKFLOW,
        user_instruction="继续写这一章",
        caller_type="user_action",
    )
    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="memory_context:mem_1",
        safe_message="memory ready",
    )
    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="direction:dir_1",
        safe_message="planning ready",
    )
    run = orchestrator.submit_user_decision(
        run.session_id,
        user_decision="confirm_direction",
        safe_message="direction confirmed",
        request_id="req_reject_reason_direction",
        metadata={"selected_direction_id": "dir_1"},
    )
    run = orchestrator.submit_user_decision(
        run.session_id,
        user_decision="confirm_chapter_plan",
        safe_message="chapter plan confirmed",
        request_id="req_reject_reason_plan",
        metadata={"selected_chapter_plan_id": "plan_1"},
    )
    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="writing_task:task_1",
        safe_message="writing context ready",
    )
    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="candidate_draft:draft_1",
        safe_message="draft ready",
    )
    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="review_report:review_1",
        safe_message="review ready",
    )
    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="candidate_draft:draft_1",
        safe_message="candidate ready",
    )

    run = orchestrator.submit_user_decision(
        run.session_id,
        user_decision="reject",
        safe_message="candidate rejected",
        request_id="req_reject_reason",
    )

    assert _last_stage_record_with_reason_code(run, "user_rejected_candidate").metadata["reason_code"] == "user_rejected_candidate"


def test_agent_orchestrator_accept_candidate_records_reason_code_metadata(tmp_path) -> None:
    from application.services.ai.agent_workflow import AgentOrchestrator

    runtime = _build_runtime(tmp_path)
    orchestrator = AgentOrchestrator(runtime_service=runtime)
    run = orchestrator.start_workflow(
        work_id="work-1",
        chapter_id="chapter-1",
        workflow_type=WorkflowType.CONTINUATION_WORKFLOW,
        user_instruction="继续写这一章",
        caller_type="user_action",
    )
    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="memory_context:mem_1",
        safe_message="memory ready",
    )
    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="direction:dir_1",
        safe_message="planning ready",
    )
    run = orchestrator.submit_user_decision(
        run.session_id,
        user_decision="confirm_direction",
        safe_message="direction confirmed",
        request_id="req_accept_reason_direction",
        metadata={"selected_direction_id": "dir_1"},
    )
    run = orchestrator.submit_user_decision(
        run.session_id,
        user_decision="confirm_chapter_plan",
        safe_message="chapter plan confirmed",
        request_id="req_accept_reason_plan",
        metadata={"selected_chapter_plan_id": "plan_1"},
    )
    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="writing_task:task_1",
        safe_message="writing context ready",
    )
    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="candidate_draft:draft_1",
        safe_message="draft ready",
    )
    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="review_report:review_1",
        safe_message="review ready",
    )
    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="candidate_draft:draft_1",
        safe_message="candidate ready",
    )

    run = orchestrator.submit_user_decision(
        run.session_id,
        user_decision="accept",
        safe_message="candidate accepted",
        request_id="req_accept_reason",
    )

    assert _last_stage_record_with_reason_code(run, "user_accepted_candidate").metadata["reason_code"] == "user_accepted_candidate"


def test_agent_orchestrator_memory_review_confirmation_completes_workflow(tmp_path) -> None:
    from application.services.ai.agent_workflow import AgentOrchestrator

    runtime = _build_runtime(tmp_path)
    orchestrator = AgentOrchestrator(runtime_service=runtime)
    run = orchestrator.start_workflow(
        work_id="work-1",
        chapter_id="chapter-1",
        workflow_type=WorkflowType.MEMORY_UPDATE_WORKFLOW,
        user_instruction="同步记忆",
        caller_type="user_action",
    )
    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="memory_context:mem_1",
        safe_message="memory context ready",
    )
    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="memory_update_suggestion:mem_upd_1",
        safe_message="memory suggestion ready",
    )

    assert run.current_stage == WorkflowStageName.MEMORY_REVIEW_WAITING

    run = orchestrator.submit_user_decision(
        run.session_id,
        user_decision="confirm_memory_update",
        safe_message="memory confirmed",
        request_id="req_memory_review",
    )
    session = runtime.get_session(run.session_id)

    assert run.current_stage == WorkflowStageName.COMPLETED
    assert session.status == AgentSessionStatus.COMPLETED


def test_agent_orchestrator_confirm_memory_update_records_reason_code_metadata(tmp_path) -> None:
    from application.services.ai.agent_workflow import AgentOrchestrator

    runtime = _build_runtime(tmp_path)
    orchestrator = AgentOrchestrator(runtime_service=runtime)
    run = orchestrator.start_workflow(
        work_id="work-1",
        chapter_id="chapter-1",
        workflow_type=WorkflowType.MEMORY_UPDATE_WORKFLOW,
        user_instruction="同步记忆",
        caller_type="user_action",
    )
    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="memory_context:mem_1",
        safe_message="memory context ready",
    )
    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="memory_update_suggestion:mem_upd_1",
        safe_message="memory suggestion ready",
    )

    run = orchestrator.submit_user_decision(
        run.session_id,
        user_decision="confirm_memory_update",
        safe_message="memory update confirmed",
        request_id="req_reason_memory_confirm",
    )

    assert _last_stage_record_with_reason_code(run, "user_confirmed_memory_update").metadata["reason_code"] == "user_confirmed_memory_update"
    assert any(
        item.ref_type == "memory_review_decision" and item.ref_id == "confirm_memory_update" for item in run.result_refs
    )


def test_agent_orchestrator_reject_memory_update_records_reason_code_metadata(tmp_path) -> None:
    from application.services.ai.agent_workflow import AgentOrchestrator

    runtime = _build_runtime(tmp_path)
    orchestrator = AgentOrchestrator(runtime_service=runtime)
    run = orchestrator.start_workflow(
        work_id="work-1",
        chapter_id="chapter-1",
        workflow_type=WorkflowType.MEMORY_UPDATE_WORKFLOW,
        user_instruction="同步记忆",
        caller_type="user_action",
    )
    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="memory_context:mem_1",
        safe_message="memory context ready",
    )
    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="memory_update_suggestion:mem_upd_1",
        safe_message="memory suggestion ready",
    )

    run = orchestrator.submit_user_decision(
        run.session_id,
        user_decision="reject",
        safe_message="memory update rejected",
        request_id="req_reason_memory_reject",
    )

    assert _last_stage_record_with_reason_code(run, "user_rejected_memory_update").metadata["reason_code"] == "user_rejected_memory_update"


def test_agent_orchestrator_memory_review_waiting_uses_workflow_step_agent_type(tmp_path) -> None:
    from application.services.ai.agent_workflow import AgentOrchestrator

    runtime = _build_runtime(tmp_path)
    orchestrator = AgentOrchestrator(runtime_service=runtime)
    run = orchestrator.start_workflow(
        work_id="work-1",
        chapter_id="chapter-1",
        workflow_type=WorkflowType.MEMORY_UPDATE_WORKFLOW,
        user_instruction="更新记忆",
        caller_type="user_action",
    )
    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="memory_context:mem_1",
        safe_message="memory context ready",
    )
    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="memory_update_suggestion:mem_upd_1",
        safe_message="memory suggestion ready",
    )
    session = runtime.get_session(run.session_id)
    step = runtime.get_step(session.current_step_id)

    assert run.current_stage == WorkflowStageName.MEMORY_REVIEW_WAITING
    assert step.agent_type == "workflow"
    assert step.step_type == "wait_user_decision"
    assert run.checkpoints[-1].waiting_for_user_reason == "memory_review"


def test_agent_orchestrator_planning_workflow_user_cancel_completes_without_draft(tmp_path) -> None:
    from application.services.ai.agent_workflow import AgentOrchestrator

    runtime = _build_runtime(tmp_path)
    orchestrator = AgentOrchestrator(runtime_service=runtime)
    run = orchestrator.start_workflow(
        work_id="work-1",
        chapter_id="chapter-1",
        workflow_type=WorkflowType.PLANNING_WORKFLOW,
        user_instruction="只做规划",
        caller_type="user_action",
    )
    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="memory_context:mem_1",
        safe_message="memory ready",
    )
    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="direction:dir_1",
        safe_message="planning ready",
    )

    run = orchestrator.submit_user_decision(
        run.session_id,
        user_decision="cancel",
        safe_message="user cancelled planning",
        request_id="req_plan_cancel",
    )
    session = runtime.get_session(run.session_id)

    assert run.current_stage == WorkflowStageName.COMPLETED
    assert session.status == AgentSessionStatus.COMPLETED
    assert run.metadata.get("current_candidate_draft_id", "") == ""
    assert run.stage_history[-1].stage_name == WorkflowStageName.COMPLETED
    assert run.stage_history[-1].status == AgentSessionStatus.COMPLETED.value
    assert run.stage_history[-1].decision == WorkflowDecision.COMPLETE_WORKFLOW.value
    assert run.stage_history[-1].metadata["reason_code"] == "workflow_completed"


def test_agent_orchestrator_mark_partial_success_requires_deliverable_result_ref(tmp_path) -> None:
    from application.services.ai.agent_workflow import AgentOrchestrator

    runtime = _build_runtime(tmp_path)
    orchestrator = AgentOrchestrator(runtime_service=runtime)
    run = orchestrator.start_workflow(
        work_id="work-1",
        chapter_id="chapter-1",
        workflow_type=WorkflowType.CONTINUATION_WORKFLOW,
        user_instruction="继续写这一章",
        caller_type="user_action",
    )
    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="memory_context:mem_1",
        safe_message="memory ready",
    )
    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="direction:dir_1",
        safe_message="planning ready",
    )
    run = orchestrator.submit_user_decision(
        run.session_id,
        user_decision="confirm_direction",
        safe_message="direction confirmed",
        request_id="req_user_direction",
        metadata={"selected_direction_id": "dir_1"},
    )
    run = orchestrator.submit_user_decision(
        run.session_id,
        user_decision="confirm_chapter_plan",
        safe_message="chapter plan confirmed",
        request_id="req_user_plan",
        metadata={"selected_chapter_plan_id": "plan_1"},
    )
    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="writing_task:task_1",
        safe_message="writing context ready",
    )

    with pytest.raises(ValueError, match="partial_success_requires_deliverable_result_ref"):
        orchestrator.advance_workflow(
            run.session_id,
            decision=WorkflowDecision.MARK_PARTIAL_SUCCESS,
            safe_message="review failed after draft",
        )


def test_agent_orchestrator_mark_partial_success_allows_candidate_draft_delivery(tmp_path) -> None:
    from application.services.ai.agent_workflow import AgentOrchestrator

    runtime = _build_runtime(tmp_path)
    orchestrator = AgentOrchestrator(runtime_service=runtime)
    run = orchestrator.start_workflow(
        work_id="work-1",
        chapter_id="chapter-1",
        workflow_type=WorkflowType.CONTINUATION_WORKFLOW,
        user_instruction="继续写这一章",
        caller_type="user_action",
    )
    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="memory_context:mem_1",
        safe_message="memory ready",
    )
    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="direction:dir_1",
        safe_message="planning ready",
    )
    run = orchestrator.submit_user_decision(
        run.session_id,
        user_decision="confirm_direction",
        safe_message="direction confirmed",
        request_id="req_user_direction",
        metadata={"selected_direction_id": "dir_1"},
    )
    run = orchestrator.submit_user_decision(
        run.session_id,
        user_decision="confirm_chapter_plan",
        safe_message="chapter plan confirmed",
        request_id="req_user_plan",
        metadata={"selected_chapter_plan_id": "plan_1"},
    )
    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="writing_task:task_1",
        safe_message="writing context ready",
    )
    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="candidate_draft:draft_1",
        safe_message="draft ready",
    )

    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.MARK_PARTIAL_SUCCESS,
        safe_message="review failed after draft",
        warning_codes=["review_failed"],
    )
    session = runtime.get_session(run.session_id)

    assert run.current_stage == WorkflowStageName.PARTIAL_SUCCESS
    assert session.status == AgentSessionStatus.PARTIAL_SUCCESS
    assert run.stage_history[-1].stage_name == WorkflowStageName.PARTIAL_SUCCESS
    assert run.stage_history[-1].status == AgentSessionStatus.PARTIAL_SUCCESS.value
    assert run.stage_history[-1].decision == WorkflowDecision.MARK_PARTIAL_SUCCESS.value
    assert any(item.ref_type == "candidate_draft" and item.ref_id == "draft_1" for item in run.stage_history[-1].result_refs)
    assert run.stage_history[-1].metadata["reason_code"] == "workflow_partial_success"


def test_agent_orchestrator_mark_partial_success_rejected_when_policy_disables_it(tmp_path) -> None:
    from application.services.ai.agent_workflow import AgentOrchestrator

    runtime = _build_runtime(tmp_path)
    orchestrator = AgentOrchestrator(runtime_service=runtime)
    run = orchestrator.start_workflow(
        work_id="work-1",
        chapter_id="chapter-1",
        workflow_type=WorkflowType.CONTINUATION_WORKFLOW,
        user_instruction="继续写这一章",
        caller_type="user_action",
        policy_overrides={"allow_partial_success": False},
    )
    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="memory_context:mem_1",
        safe_message="memory ready",
    )
    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="direction:dir_1",
        safe_message="planning ready",
    )
    run = orchestrator.submit_user_decision(
        run.session_id,
        user_decision="confirm_direction",
        safe_message="direction confirmed",
        request_id="req_user_direction_policy_off",
        metadata={"selected_direction_id": "dir_1"},
    )
    run = orchestrator.submit_user_decision(
        run.session_id,
        user_decision="confirm_chapter_plan",
        safe_message="chapter plan confirmed",
        request_id="req_user_plan_policy_off",
        metadata={"selected_chapter_plan_id": "plan_1"},
    )
    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="writing_task:task_1",
        safe_message="writing context ready",
    )
    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="candidate_draft:draft_1",
        safe_message="draft ready",
    )

    with pytest.raises(ValueError, match="partial_success_policy_forbidden"):
        orchestrator.advance_workflow(
            run.session_id,
            decision=WorkflowDecision.MARK_PARTIAL_SUCCESS,
            safe_message="review failed after draft",
            warning_codes=["review_failed"],
        )


def test_agent_orchestrator_writing_prepare_rejects_degraded_progress_when_policy_disables_it(tmp_path) -> None:
    from application.services.ai.agent_workflow import AgentOrchestrator

    runtime = _build_runtime(tmp_path)
    orchestrator = AgentOrchestrator(runtime_service=runtime)
    run = orchestrator.start_workflow(
        work_id="work-1",
        chapter_id="chapter-1",
        workflow_type=WorkflowType.CONTINUATION_WORKFLOW,
        user_instruction="继续写这一章",
        caller_type="user_action",
        policy_overrides={
            "allow_degraded": False,
            "require_direction_confirmation": False,
            "require_chapter_plan_confirmation": False,
        },
    )
    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="memory_context:mem_1",
        safe_message="memory ready",
    )
    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="chapter_plan:plan_1",
        safe_message="plan ready",
    )

    with pytest.raises(ValueError, match="degraded_policy_forbidden"):
        orchestrator.advance_workflow(
            run.session_id,
            decision=WorkflowDecision.CONTINUE,
            result_ref="writing_task:task_1",
            safe_message="writing context degraded",
            warning_codes=["context_pack_degraded"],
        )


def test_agent_orchestrator_writing_prepare_allows_degraded_progress_when_policy_enabled(tmp_path) -> None:
    from application.services.ai.agent_workflow import AgentOrchestrator

    runtime = _build_runtime(tmp_path)
    orchestrator = AgentOrchestrator(runtime_service=runtime)
    run = orchestrator.start_workflow(
        work_id="work-1",
        chapter_id="chapter-1",
        workflow_type=WorkflowType.CONTINUATION_WORKFLOW,
        user_instruction="继续写这一章",
        caller_type="user_action",
        policy_overrides={
            "allow_degraded": True,
            "require_direction_confirmation": False,
            "require_chapter_plan_confirmation": False,
        },
    )
    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="memory_context:mem_1",
        safe_message="memory ready",
    )
    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="chapter_plan:plan_1",
        safe_message="plan ready",
    )

    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="writing_task:task_1",
        safe_message="writing context degraded",
        warning_codes=["context_pack_degraded"],
    )

    assert run.current_stage == WorkflowStageName.DRAFTING
    assert "context_pack_degraded" in run.warning_codes


def test_agent_orchestrator_reviewing_allows_non_degraded_warning_codes(tmp_path) -> None:
    from application.services.ai.agent_workflow import AgentOrchestrator

    runtime = _build_runtime(tmp_path)
    orchestrator = AgentOrchestrator(runtime_service=runtime)
    run = orchestrator.start_workflow(
        work_id="work-1",
        chapter_id="chapter-1",
        workflow_type=WorkflowType.CONTINUATION_WORKFLOW,
        user_instruction="继续写这一章",
        caller_type="user_action",
    )
    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="memory_context:mem_1",
        safe_message="memory ready",
    )
    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="direction:dir_1",
        safe_message="planning ready",
    )
    run = orchestrator.submit_user_decision(
        run.session_id,
        user_decision="confirm_direction",
        safe_message="direction confirmed",
        request_id="req_direction_review_warning",
        metadata={"selected_direction_id": "dir_1"},
    )
    run = orchestrator.submit_user_decision(
        run.session_id,
        user_decision="confirm_chapter_plan",
        safe_message="chapter plan confirmed",
        request_id="req_plan_review_warning",
        metadata={"selected_chapter_plan_id": "plan_1"},
    )
    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="writing_task:task_1",
        safe_message="writing context ready",
    )
    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="candidate_draft:draft_1",
        safe_message="draft ready",
    )

    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="review_report:review_1",
        safe_message="review ready with advisory warning",
        warning_codes=["style_warning"],
    )

    assert run.current_stage == WorkflowStageName.CANDIDATE_READY
    assert "style_warning" in run.warning_codes


def test_agent_orchestrator_reviewing_allows_degraded_warning_when_policy_enabled(tmp_path) -> None:
    from application.services.ai.agent_workflow import AgentOrchestrator

    runtime = _build_runtime(tmp_path)
    orchestrator = AgentOrchestrator(runtime_service=runtime)
    run = orchestrator.start_workflow(
        work_id="work-1",
        chapter_id="chapter-1",
        workflow_type=WorkflowType.CONTINUATION_WORKFLOW,
        user_instruction="继续写这一章",
        caller_type="user_action",
        policy_overrides={"allow_degraded": True},
    )
    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="memory_context:mem_1",
        safe_message="memory ready",
    )
    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="direction:dir_1",
        safe_message="planning ready",
    )
    run = orchestrator.submit_user_decision(
        run.session_id,
        user_decision="confirm_direction",
        safe_message="direction confirmed",
        request_id="req_direction_review_degraded",
        metadata={"selected_direction_id": "dir_1"},
    )
    run = orchestrator.submit_user_decision(
        run.session_id,
        user_decision="confirm_chapter_plan",
        safe_message="chapter plan confirmed",
        request_id="req_plan_review_degraded",
        metadata={"selected_chapter_plan_id": "plan_1"},
    )
    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="writing_task:task_1",
        safe_message="writing context ready",
    )
    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="candidate_draft:draft_1",
        safe_message="draft ready",
    )

    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="review_report:review_1",
        safe_message="review ready with degraded context",
        warning_codes=["review_context_degraded"],
    )

    assert run.current_stage == WorkflowStageName.CANDIDATE_READY
    assert "review_context_degraded" in run.warning_codes


def test_agent_orchestrator_reviewing_rejects_degraded_warning_when_policy_disabled(tmp_path) -> None:
    from application.services.ai.agent_workflow import AgentOrchestrator

    runtime = _build_runtime(tmp_path)
    orchestrator = AgentOrchestrator(runtime_service=runtime)
    run = orchestrator.start_workflow(
        work_id="work-1",
        chapter_id="chapter-1",
        workflow_type=WorkflowType.CONTINUATION_WORKFLOW,
        user_instruction="继续写这一章",
        caller_type="user_action",
        policy_overrides={"allow_degraded": False},
    )
    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="memory_context:mem_1",
        safe_message="memory ready",
    )
    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="direction:dir_1",
        safe_message="planning ready",
    )
    run = orchestrator.submit_user_decision(
        run.session_id,
        user_decision="confirm_direction",
        safe_message="direction confirmed",
        request_id="req_direction_review_degraded_off",
        metadata={"selected_direction_id": "dir_1"},
    )
    run = orchestrator.submit_user_decision(
        run.session_id,
        user_decision="confirm_chapter_plan",
        safe_message="chapter plan confirmed",
        request_id="req_plan_review_degraded_off",
        metadata={"selected_chapter_plan_id": "plan_1"},
    )
    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="writing_task:task_1",
        safe_message="writing context ready",
    )
    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="candidate_draft:draft_1",
        safe_message="draft ready",
    )

    with pytest.raises(ValueError, match="degraded_policy_forbidden"):
        orchestrator.advance_workflow(
            run.session_id,
            decision=WorkflowDecision.CONTINUE,
            result_ref="review_report:review_1",
            safe_message="review ready with degraded context",
            warning_codes=["review_context_degraded"],
        )


def test_agent_orchestrator_rewriting_allows_degraded_warning_when_policy_enabled(tmp_path) -> None:
    from application.services.ai.agent_workflow import AgentOrchestrator

    runtime = _build_runtime(tmp_path)
    orchestrator = AgentOrchestrator(runtime_service=runtime)
    run = orchestrator.start_workflow(
        work_id="work-1",
        chapter_id="chapter-1",
        workflow_type=WorkflowType.REVISION_WORKFLOW,
        user_instruction="修订当前稿件",
        caller_type="user_action",
        policy_overrides={"allow_degraded": True},
    )
    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="writing_context:ctx_1",
        safe_message="revision input ready",
    )

    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="candidate_version:ver_1",
        safe_message="rewrite ready with degraded context",
        warning_codes=["rewrite_context_degraded"],
    )

    assert run.current_stage == WorkflowStageName.REVIEWING
    assert "rewrite_context_degraded" in run.warning_codes


def test_agent_orchestrator_rewriting_rejects_degraded_warning_when_policy_disabled(tmp_path) -> None:
    from application.services.ai.agent_workflow import AgentOrchestrator

    runtime = _build_runtime(tmp_path)
    orchestrator = AgentOrchestrator(runtime_service=runtime)
    run = orchestrator.start_workflow(
        work_id="work-1",
        chapter_id="chapter-1",
        workflow_type=WorkflowType.REVISION_WORKFLOW,
        user_instruction="修订当前稿件",
        caller_type="user_action",
        policy_overrides={"allow_degraded": False},
    )
    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="writing_context:ctx_1",
        safe_message="revision input ready",
    )

    with pytest.raises(ValueError, match="degraded_policy_forbidden"):
        orchestrator.advance_workflow(
            run.session_id,
            decision=WorkflowDecision.CONTINUE,
            result_ref="candidate_version:ver_1",
            safe_message="rewrite ready with degraded context",
            warning_codes=["rewrite_context_degraded"],
        )


def test_agent_orchestrator_candidate_ready_checkpoint_preserves_degraded_warning_codes(tmp_path) -> None:
    from application.services.ai.agent_workflow import AgentOrchestrator

    runtime = _build_runtime(tmp_path)
    orchestrator = AgentOrchestrator(runtime_service=runtime)
    run = orchestrator.start_workflow(
        work_id="work-1",
        chapter_id="chapter-1",
        workflow_type=WorkflowType.CONTINUATION_WORKFLOW,
        user_instruction="继续写这一章",
        caller_type="user_action",
        policy_overrides={"allow_degraded": True},
    )
    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="memory_context:mem_1",
        safe_message="memory ready",
    )
    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="direction:dir_1",
        safe_message="planning ready",
    )
    run = orchestrator.submit_user_decision(
        run.session_id,
        user_decision="confirm_direction",
        safe_message="direction confirmed",
        request_id="req_direction_candidate_degraded",
        metadata={"selected_direction_id": "dir_1"},
    )
    run = orchestrator.submit_user_decision(
        run.session_id,
        user_decision="confirm_chapter_plan",
        safe_message="chapter plan confirmed",
        request_id="req_plan_candidate_degraded",
        metadata={"selected_chapter_plan_id": "plan_1"},
    )
    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="writing_task:task_1",
        safe_message="writing context degraded",
        warning_codes=["context_pack_degraded"],
    )
    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="candidate_draft:draft_1",
        safe_message="draft ready",
    )
    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="review_report:review_1",
        safe_message="review ready",
    )

    assert run.current_stage == WorkflowStageName.CANDIDATE_READY
    assert "context_pack_degraded" in run.warning_codes
    assert "context_pack_degraded" in run.checkpoints[-1].warning_codes


def test_agent_orchestrator_candidate_ready_appends_candidate_result_ref_for_continuation(tmp_path) -> None:
    from application.services.ai.agent_workflow import AgentOrchestrator

    runtime = _build_runtime(tmp_path)
    orchestrator = AgentOrchestrator(runtime_service=runtime)
    run = orchestrator.start_workflow(
        work_id="work-1",
        chapter_id="chapter-1",
        workflow_type=WorkflowType.CONTINUATION_WORKFLOW,
        user_instruction="继续写这一章",
        caller_type="user_action",
        policy_overrides={"allow_degraded": True},
    )
    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="memory_context:mem_1",
        safe_message="memory ready",
    )
    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="direction:dir_1",
        safe_message="planning ready",
    )
    run = orchestrator.submit_user_decision(
        run.session_id,
        user_decision="confirm_direction",
        safe_message="direction confirmed",
        request_id="req_direction_candidate_ref",
        metadata={"selected_direction_id": "dir_1"},
    )
    run = orchestrator.submit_user_decision(
        run.session_id,
        user_decision="confirm_chapter_plan",
        safe_message="chapter plan confirmed",
        request_id="req_plan_candidate_ref",
        metadata={"selected_chapter_plan_id": "plan_1"},
    )
    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="writing_task:task_1",
        safe_message="writing context ready",
    )
    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="candidate_draft:draft_1",
        safe_message="draft ready",
    )
    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="review_report:review_1",
        safe_message="review ready",
    )

    assert run.current_stage == WorkflowStageName.CANDIDATE_READY
    assert any(item.ref_type == "candidate" and item.ref_id == "draft_1" for item in run.result_refs)
    assert any(item.ref_type == "candidate" and item.ref_id == "draft_1" for item in run.checkpoints[-1].result_refs)


def test_agent_orchestrator_candidate_ready_appends_candidate_result_ref_for_revision(tmp_path) -> None:
    from application.services.ai.agent_workflow import AgentOrchestrator

    runtime = _build_runtime(tmp_path)
    orchestrator = AgentOrchestrator(runtime_service=runtime)
    run = orchestrator.start_workflow(
        work_id="work-1",
        chapter_id="chapter-1",
        workflow_type=WorkflowType.REVISION_WORKFLOW,
        user_instruction="修订当前稿件",
        caller_type="user_action",
        policy_overrides={"allow_degraded": True},
    )
    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="writing_context:ctx_1",
        safe_message="revision input ready",
    )
    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="candidate_version:ver_1",
        safe_message="rewrite ready",
    )
    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="review_report:review_1",
        safe_message="review ready",
    )

    assert run.current_stage == WorkflowStageName.CANDIDATE_READY
    assert any(item.ref_type == "candidate" and item.ref_id == "ver_1" for item in run.result_refs)
    assert any(item.ref_type == "candidate" and item.ref_id == "ver_1" for item in run.checkpoints[-1].result_refs)


def test_agent_orchestrator_human_review_waiting_checkpoint_preserves_degraded_warning_codes(tmp_path) -> None:
    from application.services.ai.agent_workflow import AgentOrchestrator

    runtime = _build_runtime(tmp_path)
    orchestrator = AgentOrchestrator(runtime_service=runtime)
    run = orchestrator.start_workflow(
        work_id="work-1",
        chapter_id="chapter-1",
        workflow_type=WorkflowType.CONTINUATION_WORKFLOW,
        user_instruction="继续写这一章",
        caller_type="user_action",
        policy_overrides={"allow_degraded": True},
    )
    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="memory_context:mem_1",
        safe_message="memory ready",
    )
    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="direction:dir_1",
        safe_message="planning ready",
    )
    run = orchestrator.submit_user_decision(
        run.session_id,
        user_decision="confirm_direction",
        safe_message="direction confirmed",
        request_id="req_direction_hr_degraded",
        metadata={"selected_direction_id": "dir_1"},
    )
    run = orchestrator.submit_user_decision(
        run.session_id,
        user_decision="confirm_chapter_plan",
        safe_message="chapter plan confirmed",
        request_id="req_plan_hr_degraded",
        metadata={"selected_chapter_plan_id": "plan_1"},
    )
    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="writing_task:task_1",
        safe_message="writing context degraded",
        warning_codes=["context_pack_degraded"],
    )
    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="candidate_draft:draft_1",
        safe_message="draft ready",
    )
    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="review_report:review_1",
        safe_message="review ready",
    )
    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="candidate_draft:draft_1",
        safe_message="candidate ready",
    )

    assert run.current_stage == WorkflowStageName.HUMAN_REVIEW_WAITING
    assert "context_pack_degraded" in run.warning_codes
    assert "context_pack_degraded" in run.checkpoints[-1].warning_codes


def test_agent_orchestrator_human_review_waiting_uses_workflow_wait_user_decision_metadata(tmp_path) -> None:
    from application.services.ai.agent_workflow import AgentOrchestrator

    runtime = _build_runtime(tmp_path)
    orchestrator = AgentOrchestrator(runtime_service=runtime)
    run = orchestrator.start_workflow(
        work_id="work-1",
        chapter_id="chapter-1",
        workflow_type=WorkflowType.CONTINUATION_WORKFLOW,
        user_instruction="继续写这一章",
        caller_type="user_action",
        policy_overrides={"allow_degraded": True},
    )
    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="memory_context:mem_1",
        safe_message="memory ready",
    )
    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="direction:dir_1",
        safe_message="planning ready",
    )
    run = orchestrator.submit_user_decision(
        run.session_id,
        user_decision="confirm_direction",
        safe_message="direction confirmed",
        request_id="req_direction_hr_wait_metadata",
        metadata={"selected_direction_id": "dir_1"},
    )
    run = orchestrator.submit_user_decision(
        run.session_id,
        user_decision="confirm_chapter_plan",
        safe_message="chapter plan confirmed",
        request_id="req_plan_hr_wait_metadata",
        metadata={"selected_chapter_plan_id": "plan_1"},
    )
    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="writing_task:task_1",
        safe_message="writing context degraded",
        warning_codes=["context_pack_degraded"],
    )
    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="candidate_draft:draft_1",
        safe_message="draft ready",
    )
    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="review_report:review_1",
        safe_message="review ready",
    )
    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="candidate_draft:draft_1",
        safe_message="candidate ready",
    )
    session = runtime.get_session(run.session_id)
    step = runtime.get_step(session.current_step_id)

    assert run.current_stage == WorkflowStageName.HUMAN_REVIEW_WAITING
    assert step.agent_type == "workflow"
    assert step.step_type == "wait_user_decision"
    assert run.checkpoints[-1].waiting_for_user_reason == "human_review"


def test_agent_orchestrator_drafting_allows_degraded_warning_when_policy_enabled(tmp_path) -> None:
    from application.services.ai.agent_workflow import AgentOrchestrator

    runtime = _build_runtime(tmp_path)
    orchestrator = AgentOrchestrator(runtime_service=runtime)
    run = orchestrator.start_workflow(
        work_id="work-1",
        chapter_id="chapter-1",
        workflow_type=WorkflowType.CONTINUATION_WORKFLOW,
        user_instruction="继续写这一章",
        caller_type="user_action",
        policy_overrides={
            "allow_degraded": True,
            "require_direction_confirmation": False,
            "require_chapter_plan_confirmation": False,
        },
    )
    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="memory_context:mem_1",
        safe_message="memory ready",
    )
    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="chapter_plan:plan_1",
        safe_message="plan ready",
    )
    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="writing_task:task_1",
        safe_message="writing context ready",
    )

    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="candidate_draft:draft_1",
        safe_message="draft ready with degraded context",
        warning_codes=["writer_context_degraded"],
    )

    assert run.current_stage == WorkflowStageName.REVIEWING
    assert "writer_context_degraded" in run.warning_codes


def test_agent_orchestrator_drafting_rejects_degraded_warning_when_policy_disabled(tmp_path) -> None:
    from application.services.ai.agent_workflow import AgentOrchestrator

    runtime = _build_runtime(tmp_path)
    orchestrator = AgentOrchestrator(runtime_service=runtime)
    run = orchestrator.start_workflow(
        work_id="work-1",
        chapter_id="chapter-1",
        workflow_type=WorkflowType.CONTINUATION_WORKFLOW,
        user_instruction="继续写这一章",
        caller_type="user_action",
        policy_overrides={
            "allow_degraded": False,
            "require_direction_confirmation": False,
            "require_chapter_plan_confirmation": False,
        },
    )
    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="memory_context:mem_1",
        safe_message="memory ready",
    )
    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="chapter_plan:plan_1",
        safe_message="plan ready",
    )
    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="writing_task:task_1",
        safe_message="writing context ready",
    )

    with pytest.raises(ValueError, match="degraded_policy_forbidden"):
        orchestrator.advance_workflow(
            run.session_id,
            decision=WorkflowDecision.CONTINUE,
            result_ref="candidate_draft:draft_1",
            safe_message="draft ready with degraded context",
            warning_codes=["writer_context_degraded"],
        )


def test_agent_orchestrator_retry_step_uses_runtime_retry_on_failed_current_step(tmp_path) -> None:
    from application.services.ai.agent_workflow import AgentOrchestrator

    runtime = _build_runtime(tmp_path)
    orchestrator = AgentOrchestrator(runtime_service=runtime)
    run = orchestrator.start_workflow(
        work_id="work-1",
        chapter_id="chapter-1",
        workflow_type=WorkflowType.CONTINUATION_WORKFLOW,
        user_instruction="继续写这一章",
        caller_type="user_action",
    )
    failed_step_id = _fail_current_step(runtime, run.session_id)

    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.RETRY_STEP,
        safe_message="retry memory step",
    )
    step = runtime.get_step(failed_step_id)

    assert run.current_stage == WorkflowStageName.MEMORY_CONTEXT_PREPARE
    assert step.status == AgentStepStatus.PENDING
    assert step.attempt_count == 1


def test_agent_orchestrator_retry_stage_reenters_same_stage_once_then_blocks(tmp_path) -> None:
    from application.services.ai.agent_workflow import AgentOrchestrator

    runtime = _build_runtime(tmp_path)
    orchestrator = AgentOrchestrator(runtime_service=runtime)
    run = orchestrator.start_workflow(
        work_id="work-1",
        chapter_id="chapter-1",
        workflow_type=WorkflowType.CONTINUATION_WORKFLOW,
        user_instruction="继续写这一章",
        caller_type="user_action",
    )
    first_step_id = _fail_current_step(runtime, run.session_id, safe_message="memory failed")

    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.RETRY_STAGE,
        safe_message="retry memory stage",
    )
    retried_step_id = runtime.get_session(run.session_id).current_step_id

    assert run.current_stage == WorkflowStageName.MEMORY_CONTEXT_PREPARE
    assert retried_step_id != first_step_id

    _fail_current_step(runtime, run.session_id, safe_message="memory failed again")
    with pytest.raises(ValueError, match="stage_retry_limit_reached"):
        orchestrator.advance_workflow(
            run.session_id,
            decision=WorkflowDecision.RETRY_STAGE,
            safe_message="retry memory stage again",
        )


def test_agent_orchestrator_skip_optional_rewriting_stage_when_policy_allows(tmp_path) -> None:
    from application.services.ai.agent_workflow import AgentOrchestrator

    runtime = _build_runtime(tmp_path)
    orchestrator = AgentOrchestrator(runtime_service=runtime)
    run = orchestrator.start_workflow(
        work_id="work-1",
        chapter_id="chapter-1",
        workflow_type=WorkflowType.REVISION_WORKFLOW,
        user_instruction="修订这一稿",
        caller_type="user_action",
        policy_overrides={"allow_skip_rewriter": True},
    )
    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="writing_context:ctx_1",
        safe_message="revision input ready",
    )

    assert run.current_stage == WorkflowStageName.REWRITING

    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.SKIP_OPTIONAL_STAGE,
        safe_message="skip rewriting",
    )

    assert run.current_stage == WorkflowStageName.REVIEWING


def test_agent_orchestrator_fail_workflow_enters_failed_terminal(tmp_path) -> None:
    from application.services.ai.agent_workflow import AgentOrchestrator

    runtime = _build_runtime(tmp_path)
    orchestrator = AgentOrchestrator(runtime_service=runtime)
    run = orchestrator.start_workflow(
        work_id="work-1",
        chapter_id="chapter-1",
        workflow_type=WorkflowType.CONTINUATION_WORKFLOW,
        user_instruction="继续写这一章",
        caller_type="user_action",
    )

    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.FAIL_WORKFLOW,
        safe_message="memory blocked",
        error_code="memory_blocked",
    )
    session = runtime.get_session(run.session_id)

    assert run.current_stage == WorkflowStageName.FAILED
    assert session.status == AgentSessionStatus.FAILED
    assert run.stage_history[-1].stage_name == WorkflowStageName.FAILED
    assert run.stage_history[-1].status == AgentSessionStatus.FAILED.value
    assert run.stage_history[-1].decision == WorkflowDecision.FAIL_WORKFLOW.value
    assert run.stage_history[-1].metadata["reason_code"] == "memory_blocked"


def test_agent_orchestrator_continuation_cancel_from_direction_waiting_enters_cancelled(tmp_path) -> None:
    from application.services.ai.agent_workflow import AgentOrchestrator

    runtime = _build_runtime(tmp_path)
    orchestrator = AgentOrchestrator(runtime_service=runtime)
    run = orchestrator.start_workflow(
        work_id="work-1",
        chapter_id="chapter-1",
        workflow_type=WorkflowType.CONTINUATION_WORKFLOW,
        user_instruction="继续写这一章",
        caller_type="user_action",
    )
    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="memory_context:mem_1",
        safe_message="memory ready",
    )
    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="direction:dir_1",
        safe_message="planning ready",
    )

    run = orchestrator.submit_user_decision(
        run.session_id,
        user_decision="cancel",
        safe_message="user cancelled continuation",
        request_id="req_cancel",
    )
    session = runtime.get_session(run.session_id)

    assert run.current_stage == WorkflowStageName.CANCELLED
    assert session.status == AgentSessionStatus.CANCELLED
    assert run.stage_history[-1].stage_name == WorkflowStageName.CANCELLED
    assert run.stage_history[-1].status == AgentSessionStatus.CANCELLED.value
    assert run.stage_history[-1].decision == WorkflowDecision.CANCEL_WORKFLOW.value
    assert run.stage_history[-1].metadata["reason_code"] == "workflow_cancelled"


def test_agent_orchestrator_cancel_from_direction_waiting_records_reason_code_metadata(tmp_path) -> None:
    from application.services.ai.agent_workflow import AgentOrchestrator

    runtime = _build_runtime(tmp_path)
    orchestrator = AgentOrchestrator(runtime_service=runtime)
    run = orchestrator.start_workflow(
        work_id="work-1",
        chapter_id="chapter-1",
        workflow_type=WorkflowType.CONTINUATION_WORKFLOW,
        user_instruction="继续写这一章",
        caller_type="user_action",
    )
    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="memory_context:mem_1",
        safe_message="memory ready",
    )
    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="direction:dir_1",
        safe_message="planning ready",
    )

    run = orchestrator.submit_user_decision(
        run.session_id,
        user_decision="cancel",
        safe_message="user cancelled",
        request_id="req_reason_cancel",
    )

    assert _last_stage_record_with_reason_code(run, "user_cancelled_workflow").metadata["reason_code"] == "user_cancelled_workflow"


def test_agent_orchestrator_skip_optional_stage_rejects_required_stage(tmp_path) -> None:
    from application.services.ai.agent_workflow import AgentOrchestrator

    runtime = _build_runtime(tmp_path)
    orchestrator = AgentOrchestrator(runtime_service=runtime)
    run = orchestrator.start_workflow(
        work_id="work-1",
        chapter_id="chapter-1",
        workflow_type=WorkflowType.CONTINUATION_WORKFLOW,
        user_instruction="继续写这一章",
        caller_type="user_action",
    )

    with pytest.raises(ValueError, match="stage_not_skippable"):
        orchestrator.advance_workflow(
            run.session_id,
            decision=WorkflowDecision.SKIP_OPTIONAL_STAGE,
            safe_message="skip memory prepare",
        )


def test_agent_orchestrator_skip_optional_reviewer_requires_policy_enable(tmp_path) -> None:
    from application.services.ai.agent_workflow import AgentOrchestrator

    runtime = _build_runtime(tmp_path)
    orchestrator = AgentOrchestrator(runtime_service=runtime)
    run = orchestrator.start_workflow(
        work_id="work-1",
        chapter_id="chapter-1",
        workflow_type=WorkflowType.CONTINUATION_WORKFLOW,
        user_instruction="继续写这一章",
        caller_type="user_action",
        policy_overrides={"allow_skip_reviewer": False},
    )
    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="memory_context:mem_1",
        safe_message="memory ready",
    )
    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="direction:dir_1",
        safe_message="planning ready",
    )
    run = orchestrator.submit_user_decision(
        run.session_id,
        user_decision="confirm_direction",
        safe_message="direction confirmed",
        request_id="req_user_direction",
        metadata={"selected_direction_id": "dir_1"},
    )
    run = orchestrator.submit_user_decision(
        run.session_id,
        user_decision="confirm_chapter_plan",
        safe_message="chapter plan confirmed",
        request_id="req_user_plan",
        metadata={"selected_chapter_plan_id": "plan_1"},
    )
    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="writing_task:task_1",
        safe_message="writing context ready",
    )
    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="candidate_draft:draft_1",
        safe_message="draft ready",
    )

    assert run.current_stage == WorkflowStageName.REVIEWING

    with pytest.raises(ValueError, match="stage_skip_policy_forbidden"):
        orchestrator.advance_workflow(
            run.session_id,
            decision=WorkflowDecision.SKIP_OPTIONAL_STAGE,
            safe_message="skip reviewer",
        )


def test_agent_orchestrator_review_workflow_completes_after_review_stage(tmp_path) -> None:
    from application.services.ai.agent_workflow import AgentOrchestrator

    runtime = _build_runtime(tmp_path)
    orchestrator = AgentOrchestrator(runtime_service=runtime)
    run = orchestrator.start_workflow(
        work_id="work-1",
        chapter_id="chapter-1",
        workflow_type=WorkflowType.REVIEW_WORKFLOW,
        user_instruction="审阅当前候选稿",
        caller_type="user_action",
    )

    assert run.current_stage == WorkflowStageName.REVIEWING

    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="review_report:review_1",
        safe_message="review ready",
    )
    session = runtime.get_session(run.session_id)

    assert run.current_stage == WorkflowStageName.COMPLETED
    assert session.status == AgentSessionStatus.COMPLETED


def test_agent_orchestrator_full_workflow_apply_and_memory_review_complete(tmp_path) -> None:
    from application.services.ai.agent_workflow import AgentOrchestrator

    runtime = _build_runtime(tmp_path)
    orchestrator = AgentOrchestrator(runtime_service=runtime)
    run = orchestrator.start_workflow(
        work_id="work-1",
        chapter_id="chapter-1",
        workflow_type=WorkflowType.FULL_WORKFLOW,
        user_instruction="全流程执行",
        caller_type="user_action",
    )
    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="memory_context:mem_1",
        safe_message="memory ready",
    )
    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="direction:dir_1",
        safe_message="planning ready",
    )
    run = orchestrator.submit_user_decision(
        run.session_id,
        user_decision="confirm_direction",
        safe_message="direction confirmed",
        request_id="req_user_direction",
        metadata={"selected_direction_id": "dir_1"},
    )
    run = orchestrator.submit_user_decision(
        run.session_id,
        user_decision="confirm_chapter_plan",
        safe_message="chapter plan confirmed",
        request_id="req_user_plan",
        metadata={"selected_chapter_plan_id": "plan_1"},
    )
    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="writing_task:task_1",
        safe_message="writing context ready",
    )
    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="candidate_draft:draft_1",
        safe_message="draft ready",
    )
    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="review_report:review_1",
        safe_message="review ready",
    )
    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="candidate_draft:draft_1",
        safe_message="candidate ready",
    )
    run = orchestrator.submit_user_decision(
        run.session_id,
        user_decision="apply",
        safe_message="candidate applied",
        request_id="req_apply",
    )
    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="memory_update_suggestion:mem_upd_1",
        safe_message="memory suggestion ready",
    )
    run = orchestrator.submit_user_decision(
        run.session_id,
        user_decision="confirm_memory_update",
        safe_message="memory confirmed",
        request_id="req_memory_review",
    )
    session = runtime.get_session(run.session_id)

    assert run.current_stage == WorkflowStageName.COMPLETED
    assert session.status == AgentSessionStatus.COMPLETED


def test_agent_orchestrator_continuation_apply_completes_when_memory_suggestion_policy_disabled(tmp_path) -> None:
    from application.services.ai.agent_workflow import AgentOrchestrator

    runtime = _build_runtime(tmp_path)
    orchestrator = AgentOrchestrator(runtime_service=runtime)
    run = orchestrator.start_workflow(
        work_id="work-1",
        chapter_id="chapter-1",
        workflow_type=WorkflowType.CONTINUATION_WORKFLOW,
        user_instruction="继续写这一章",
        caller_type="user_action",
        policy_overrides={"allow_memory_suggestion_after_apply": False},
    )
    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="memory_context:mem_1",
        safe_message="memory ready",
    )
    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="direction:dir_1",
        safe_message="planning ready",
    )
    run = orchestrator.submit_user_decision(
        run.session_id,
        user_decision="confirm_direction",
        safe_message="direction confirmed",
        request_id="req_user_direction_no_memory",
        metadata={"selected_direction_id": "dir_1"},
    )
    run = orchestrator.submit_user_decision(
        run.session_id,
        user_decision="confirm_chapter_plan",
        safe_message="chapter plan confirmed",
        request_id="req_user_plan_no_memory",
        metadata={"selected_chapter_plan_id": "plan_1"},
    )
    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="writing_task:task_1",
        safe_message="writing context ready",
    )
    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="candidate_draft:draft_1",
        safe_message="draft ready",
    )
    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="review_report:review_1",
        safe_message="review ready",
    )
    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="candidate_draft:draft_1",
        safe_message="candidate ready",
    )

    run = orchestrator.submit_user_decision(
        run.session_id,
        user_decision="apply",
        safe_message="candidate applied",
        request_id="req_apply_no_memory",
    )
    session = runtime.get_session(run.session_id)

    assert run.current_stage == WorkflowStageName.COMPLETED
    assert session.status == AgentSessionStatus.COMPLETED


def test_agent_orchestrator_full_workflow_apply_completes_when_memory_suggestion_policy_disabled(tmp_path) -> None:
    from application.services.ai.agent_workflow import AgentOrchestrator

    runtime = _build_runtime(tmp_path)
    orchestrator = AgentOrchestrator(runtime_service=runtime)
    run = orchestrator.start_workflow(
        work_id="work-1",
        chapter_id="chapter-1",
        workflow_type=WorkflowType.FULL_WORKFLOW,
        user_instruction="全流程执行",
        caller_type="user_action",
        policy_overrides={"allow_memory_suggestion_after_apply": False},
    )
    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="memory_context:mem_1",
        safe_message="memory ready",
    )
    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="direction:dir_1",
        safe_message="planning ready",
    )
    run = orchestrator.submit_user_decision(
        run.session_id,
        user_decision="confirm_direction",
        safe_message="direction confirmed",
        request_id="req_full_direction_no_memory",
        metadata={"selected_direction_id": "dir_1"},
    )
    run = orchestrator.submit_user_decision(
        run.session_id,
        user_decision="confirm_chapter_plan",
        safe_message="chapter plan confirmed",
        request_id="req_full_plan_no_memory",
        metadata={"selected_chapter_plan_id": "plan_1"},
    )
    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="writing_task:task_1",
        safe_message="writing context ready",
    )
    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="candidate_draft:draft_1",
        safe_message="draft ready",
    )
    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="review_report:review_1",
        safe_message="review ready",
    )
    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="candidate_draft:draft_1",
        safe_message="candidate ready",
    )

    run = orchestrator.submit_user_decision(
        run.session_id,
        user_decision="apply",
        safe_message="candidate applied",
        request_id="req_full_apply_no_memory",
    )
    session = runtime.get_session(run.session_id)

    assert run.current_stage == WorkflowStageName.COMPLETED
    assert session.status == AgentSessionStatus.COMPLETED


def test_agent_orchestrator_pause_workflow_persists_checkpoint(tmp_path) -> None:
    from application.services.ai.agent_workflow import AgentOrchestrator

    runtime = _build_runtime(tmp_path)
    orchestrator = AgentOrchestrator(runtime_service=runtime)
    run = orchestrator.start_workflow(
        work_id="work-1",
        chapter_id="chapter-1",
        workflow_type=WorkflowType.CONTINUATION_WORKFLOW,
        user_instruction="继续写这一章",
        caller_type="user_action",
    )

    paused = orchestrator.pause_workflow(run.session_id, reason="user_paused")
    session = runtime.get_session(run.session_id)

    assert paused.current_stage == WorkflowStageName.MEMORY_CONTEXT_PREPARE
    assert session.status == AgentSessionStatus.PAUSED
    assert paused.checkpoints[-1].current_stage == WorkflowStageName.MEMORY_CONTEXT_PREPARE
    assert paused.stage_history[-1].decision == "pause_session"
    assert paused.stage_history[-1].metadata["reason_code"] == "user_paused"


def test_agent_orchestrator_resume_workflow_restores_running_session_from_checkpoint(tmp_path) -> None:
    from application.services.ai.agent_workflow import AgentOrchestrator

    runtime = _build_runtime(tmp_path)
    orchestrator = AgentOrchestrator(runtime_service=runtime)
    run = orchestrator.start_workflow(
        work_id="work-1",
        chapter_id="chapter-1",
        workflow_type=WorkflowType.CONTINUATION_WORKFLOW,
        user_instruction="继续写这一章",
        caller_type="user_action",
    )
    current_step_id = runtime.get_session(run.session_id).current_step_id
    orchestrator.pause_workflow(run.session_id, reason="user_paused")

    resumed = orchestrator.resume_workflow(run.session_id)
    session = runtime.get_session(run.session_id)

    assert resumed.current_stage == WorkflowStageName.MEMORY_CONTEXT_PREPARE
    assert session.status == AgentSessionStatus.RUNNING
    assert session.current_step_id == current_step_id
    assert resumed.checkpoints[-1].current_step_id == current_step_id
    assert resumed.stage_history[-1].decision == "resume_session"
    assert resumed.stage_history[-1].metadata["reason_code"] == "resume_requested"


def test_agent_orchestrator_resume_workflow_rejects_waiting_user_checkpoint(tmp_path) -> None:
    from application.services.ai.agent_workflow import AgentOrchestrator

    runtime = _build_runtime(tmp_path)
    orchestrator = AgentOrchestrator(runtime_service=runtime)
    run = orchestrator.start_workflow(
        work_id="work-1",
        chapter_id="chapter-1",
        workflow_type=WorkflowType.CONTINUATION_WORKFLOW,
        user_instruction="继续写这一章",
        caller_type="user_action",
    )
    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="memory_context:mem_1",
        safe_message="memory ready",
    )
    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="direction:dir_1",
        safe_message="planning ready",
    )
    orchestrator.pause_workflow(run.session_id, reason="paused_while_waiting")

    with pytest.raises(ValueError, match="waiting_user_decision_required"):
        orchestrator.resume_workflow(run.session_id)


def test_agent_orchestrator_recover_after_restart_pauses_running_workflow_and_returns_run(tmp_path) -> None:
    from application.services.ai.agent_workflow import AgentOrchestrator

    runtime = _build_runtime(tmp_path)
    orchestrator = AgentOrchestrator(runtime_service=runtime)
    run = orchestrator.start_workflow(
        work_id="work-1",
        chapter_id="chapter-1",
        workflow_type=WorkflowType.CONTINUATION_WORKFLOW,
        user_instruction="继续写这一章",
        caller_type="user_action",
    )

    recovered_runs = orchestrator.recover_after_restart()
    session = runtime.get_session(run.session_id)

    assert len(recovered_runs) == 1
    assert recovered_runs[0].session_id == run.session_id
    assert session.status == AgentSessionStatus.PAUSED
    assert session.status_reason == "service_restarted"
    assert recovered_runs[0].checkpoints[-1].current_stage == WorkflowStageName.MEMORY_CONTEXT_PREPARE
    assert recovered_runs[0].stage_history[-1].decision == "service_restarted"
    assert recovered_runs[0].stage_history[-1].metadata["reason_code"] == "service_restarted"


def test_agent_orchestrator_resume_workflow_rejects_stale_checkpoint_results(tmp_path) -> None:
    from application.services.ai.agent_workflow import AgentOrchestrator

    runtime = _build_runtime(tmp_path)
    orchestrator = AgentOrchestrator(runtime_service=runtime)
    run = orchestrator.start_workflow(
        work_id="work-1",
        chapter_id="chapter-1",
        workflow_type=WorkflowType.CONTINUATION_WORKFLOW,
        user_instruction="继续写这一章",
        caller_type="user_action",
    )
    orchestrator.pause_workflow(run.session_id, reason="user_paused")
    run = orchestrator._load_run(run.session_id)
    run.metadata["stale_result_refs"] = ["memory_context:mem_1"]
    runtime.update_session_metadata(
        run.session_id,
        metadata_updates={"workflow_run": run.model_dump(mode="json")},
    )

    with pytest.raises(ValueError, match="checkpoint_result_stale"):
        orchestrator.resume_workflow(run.session_id)


def test_agent_orchestrator_resume_workflow_derives_next_stage_from_completed_checkpoint(tmp_path) -> None:
    from application.services.ai.agent_workflow import AgentOrchestrator

    runtime = _build_runtime(tmp_path)
    orchestrator = AgentOrchestrator(runtime_service=runtime)
    run = orchestrator.start_workflow(
        work_id="work-1",
        chapter_id="chapter-1",
        workflow_type=WorkflowType.CONTINUATION_WORKFLOW,
        user_instruction="继续写这一章",
        caller_type="user_action",
    )
    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="memory_context:mem_1",
        safe_message="memory ready",
    )
    orchestrator.pause_workflow(run.session_id, reason="user_paused")
    session = runtime.get_session(run.session_id)
    runtime._session_repository.save_session(
        session.model_copy(
            update={
                "status": AgentSessionStatus.PAUSED,
                "current_step_id": "",
                "current_agent_type": "",
            }
        )
    )
    run = orchestrator._load_run(run.session_id)
    run.current_stage = WorkflowStageName.MEMORY_CONTEXT_PREPARE
    runtime.update_session_metadata(
        run.session_id,
        metadata_updates={"workflow_run": run.model_dump(mode="json")},
    )

    resumed = orchestrator.resume_workflow(run.session_id)
    session = runtime.get_session(run.session_id)

    assert resumed.current_stage == WorkflowStageName.PLANNING_PREPARE
    assert session.status == AgentSessionStatus.RUNNING
    assert session.current_step_id != ""
    assert resumed.stage_history[-1].decision == WorkflowDecision.CONTINUE.value
    assert resumed.stage_history[-1].metadata["reason_code"] == "checkpoint_stage_completed"


def test_agent_orchestrator_resume_workflow_rejects_missing_result_refs(tmp_path) -> None:
    from application.services.ai.agent_workflow import AgentOrchestrator

    runtime = _build_runtime(tmp_path)
    orchestrator = AgentOrchestrator(runtime_service=runtime)
    run = orchestrator.start_workflow(
        work_id="work-1",
        chapter_id="chapter-1",
        workflow_type=WorkflowType.CONTINUATION_WORKFLOW,
        user_instruction="继续写这一章",
        caller_type="user_action",
    )
    orchestrator.pause_workflow(run.session_id, reason="user_paused")
    run = orchestrator._load_run(run.session_id)
    run.metadata["recovery_reason_code"] = "result_ref_missing"
    runtime.update_session_metadata(
        run.session_id,
        metadata_updates={"workflow_run": run.model_dump(mode="json")},
    )

    with pytest.raises(ValueError, match="result_ref_missing"):
        orchestrator.resume_workflow(run.session_id)


def test_agent_orchestrator_resume_workflow_rejects_version_conflict(tmp_path) -> None:
    from application.services.ai.agent_workflow import AgentOrchestrator

    runtime = _build_runtime(tmp_path)
    orchestrator = AgentOrchestrator(runtime_service=runtime)
    run = orchestrator.start_workflow(
        work_id="work-1",
        chapter_id="chapter-1",
        workflow_type=WorkflowType.CONTINUATION_WORKFLOW,
        user_instruction="继续写这一章",
        caller_type="user_action",
    )
    orchestrator.pause_workflow(run.session_id, reason="user_paused")
    run = orchestrator._load_run(run.session_id)
    run.metadata["recovery_reason_code"] = "version_conflict"
    runtime.update_session_metadata(
        run.session_id,
        metadata_updates={"workflow_run": run.model_dump(mode="json")},
    )

    with pytest.raises(ValueError, match="version_conflict"):
        orchestrator.resume_workflow(run.session_id)


def test_agent_orchestrator_resume_workflow_can_rerun_previous_stage_with_reason_code(tmp_path) -> None:
    from application.services.ai.agent_workflow import AgentOrchestrator

    runtime = _build_runtime(tmp_path)
    orchestrator = AgentOrchestrator(runtime_service=runtime)
    run = orchestrator.start_workflow(
        work_id="work-1",
        chapter_id="chapter-1",
        workflow_type=WorkflowType.CONTINUATION_WORKFLOW,
        user_instruction="继续写这一章",
        caller_type="user_action",
    )
    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="memory_context:mem_1",
        safe_message="memory ready",
    )
    orchestrator.pause_workflow(run.session_id, reason="user_paused")
    run = orchestrator._load_run(run.session_id)
    run.current_stage = WorkflowStageName.PLANNING_PREPARE
    run.metadata["recovery_reason_code"] = "result_ref_missing"
    run.metadata["recovery_rerun_stage"] = WorkflowStageName.MEMORY_CONTEXT_PREPARE.value
    runtime.update_session_metadata(
        run.session_id,
        metadata_updates={"workflow_run": run.model_dump(mode="json")},
    )

    resumed = orchestrator.resume_workflow(run.session_id)
    session = runtime.get_session(run.session_id)

    assert resumed.current_stage == WorkflowStageName.MEMORY_CONTEXT_PREPARE
    assert session.status == AgentSessionStatus.RUNNING
    assert resumed.stage_history[-1].decision_reason == "result_ref_missing"


def test_agent_orchestrator_resume_workflow_rejects_corrupted_result_refs(tmp_path) -> None:
    from application.services.ai.agent_workflow import AgentOrchestrator

    runtime = _build_runtime(tmp_path)
    orchestrator = AgentOrchestrator(runtime_service=runtime)
    run = orchestrator.start_workflow(
        work_id="work-1",
        chapter_id="chapter-1",
        workflow_type=WorkflowType.CONTINUATION_WORKFLOW,
        user_instruction="继续写这一章",
        caller_type="user_action",
    )
    orchestrator.pause_workflow(run.session_id, reason="user_paused")
    run = orchestrator._load_run(run.session_id)
    run.metadata["recovery_reason_code"] = "result_ref_corrupted"
    runtime.update_session_metadata(
        run.session_id,
        metadata_updates={"workflow_run": run.model_dump(mode="json")},
    )

    with pytest.raises(ValueError, match="result_ref_corrupted"):
        orchestrator.resume_workflow(run.session_id)


def test_agent_orchestrator_review_workflow_can_complete_after_resume(tmp_path) -> None:
    from application.services.ai.agent_workflow import AgentOrchestrator

    runtime = _build_runtime(tmp_path)
    orchestrator = AgentOrchestrator(runtime_service=runtime)
    run = orchestrator.start_workflow(
        work_id="work-1",
        chapter_id="chapter-1",
        workflow_type=WorkflowType.REVIEW_WORKFLOW,
        user_instruction="审阅当前候选稿",
        caller_type="user_action",
    )
    orchestrator.pause_workflow(run.session_id, reason="user_paused")

    resumed = orchestrator.resume_workflow(run.session_id)
    completed = orchestrator.advance_workflow(
        resumed.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="review_report:review_resume_1",
        safe_message="review ready after resume",
    )
    session = runtime.get_session(run.session_id)

    assert completed.current_stage == WorkflowStageName.COMPLETED
    assert session.status == AgentSessionStatus.COMPLETED


def test_agent_orchestrator_full_workflow_can_complete_after_rerun_recovery(tmp_path) -> None:
    from application.services.ai.agent_workflow import AgentOrchestrator

    runtime = _build_runtime(tmp_path)
    orchestrator = AgentOrchestrator(runtime_service=runtime)
    run = orchestrator.start_workflow(
        work_id="work-1",
        chapter_id="chapter-1",
        workflow_type=WorkflowType.FULL_WORKFLOW,
        user_instruction="全流程执行",
        caller_type="user_action",
    )
    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="memory_context:mem_1",
        safe_message="memory ready",
    )
    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="direction:dir_1",
        safe_message="planning ready",
    )
    run = orchestrator.submit_user_decision(
        run.session_id,
        user_decision="confirm_direction",
        safe_message="direction confirmed",
        request_id="req_user_direction_resume",
        metadata={"selected_direction_id": "dir_1"},
    )
    run = orchestrator.submit_user_decision(
        run.session_id,
        user_decision="confirm_chapter_plan",
        safe_message="chapter plan confirmed",
        request_id="req_user_plan_resume",
        metadata={"selected_chapter_plan_id": "plan_1"},
    )
    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="writing_task:task_1",
        safe_message="writing context ready",
    )
    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="candidate_draft:draft_1",
        safe_message="draft ready",
    )
    orchestrator.pause_workflow(run.session_id, reason="user_paused")
    run = orchestrator._load_run(run.session_id)
    run.metadata["recovery_reason_code"] = "result_ref_missing"
    run.metadata["recovery_rerun_stage"] = WorkflowStageName.DRAFTING.value
    runtime.update_session_metadata(
        run.session_id,
        metadata_updates={"workflow_run": run.model_dump(mode="json")},
    )

    resumed = orchestrator.resume_workflow(run.session_id)
    resumed = orchestrator.advance_workflow(
        resumed.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="candidate_draft:draft_2",
        safe_message="draft regenerated",
    )
    resumed = orchestrator.advance_workflow(
        resumed.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="review_report:review_1",
        safe_message="review ready",
    )
    resumed = orchestrator.advance_workflow(
        resumed.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="candidate_draft:draft_2",
        safe_message="candidate ready",
    )
    resumed = orchestrator.submit_user_decision(
        resumed.session_id,
        user_decision="apply",
        safe_message="candidate applied",
        request_id="req_apply_resume",
    )
    resumed = orchestrator.advance_workflow(
        resumed.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="memory_update_suggestion:mem_upd_2",
        safe_message="memory suggestion ready",
    )
    resumed = orchestrator.submit_user_decision(
        resumed.session_id,
        user_decision="confirm_memory_update",
        safe_message="memory confirmed",
        request_id="req_memory_review_resume",
    )
    session = runtime.get_session(run.session_id)

    assert resumed.current_stage == WorkflowStageName.COMPLETED
    assert session.status == AgentSessionStatus.COMPLETED


def test_agent_orchestrator_recovered_waiting_gate_allows_user_decision_without_resume(tmp_path) -> None:
    from application.services.ai.agent_workflow import AgentOrchestrator

    runtime = _build_runtime(tmp_path)
    orchestrator = AgentOrchestrator(runtime_service=runtime)
    run = orchestrator.start_workflow(
        work_id="work-1",
        chapter_id="chapter-1",
        workflow_type=WorkflowType.CONTINUATION_WORKFLOW,
        user_instruction="继续写这一章",
        caller_type="user_action",
    )
    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="memory_context:mem_1",
        safe_message="memory ready",
    )
    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="direction:dir_1",
        safe_message="planning ready",
    )

    recovered = orchestrator.recover_after_restart()
    recovered_run = next(item for item in recovered if item.session_id == run.session_id)
    checkpoint = recovered_run.checkpoints[-1]
    session = runtime.get_session(run.session_id)

    assert recovered_run.current_stage == WorkflowStageName.DIRECTION_SELECTION_WAITING
    assert checkpoint.waiting_for_user_reason == "direction_selection"
    assert session.status == AgentSessionStatus.PAUSED

    resumed = orchestrator.submit_user_decision(
        run.session_id,
        user_decision="confirm_direction",
        safe_message="direction confirmed after restart",
        request_id="req_direction_after_restart",
        metadata={"selected_direction_id": "dir_1"},
    )

    assert resumed.current_stage == WorkflowStageName.CHAPTER_PLAN_CONFIRM_WAITING
    assert resumed.checkpoints[-1].selected_direction_id == "dir_1"


def test_agent_orchestrator_resume_reviewing_at_revision_limit_stays_out_of_rewriter(tmp_path) -> None:
    from application.services.ai.agent_workflow import AgentOrchestrator

    runtime = _build_runtime(tmp_path)
    orchestrator = AgentOrchestrator(runtime_service=runtime)
    run = orchestrator.start_workflow(
        work_id="work-1",
        chapter_id="chapter-1",
        workflow_type=WorkflowType.REVISION_WORKFLOW,
        user_instruction="修订当前候选稿",
        caller_type="user_action",
        policy_overrides={"max_revision_rounds": 1},
    )
    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="writing_context:ctx_1",
        safe_message="revision input ready",
    )
    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="candidate_version:cv_1",
        safe_message="rewrite ready",
    )
    assert run.current_stage == WorkflowStageName.REVIEWING
    assert run.revision_round == 1

    orchestrator.pause_workflow(run.session_id, reason="user_paused")
    resumed = orchestrator.resume_workflow(run.session_id)
    resumed = orchestrator.advance_workflow(
        resumed.session_id,
        decision=WorkflowDecision.ENTER_REWRITER,
        result_ref="review_report:review_limit_1",
        safe_message="review suggests rewrite again",
    )

    assert resumed.current_stage == WorkflowStageName.CANDIDATE_READY
    assert resumed.revision_round == 1


def test_agent_orchestrator_memory_update_workflow_can_complete_after_restart_recovery(tmp_path) -> None:
    from application.services.ai.agent_workflow import AgentOrchestrator

    runtime = _build_runtime(tmp_path)
    orchestrator = AgentOrchestrator(runtime_service=runtime)
    run = orchestrator.start_workflow(
        work_id="work-1",
        chapter_id="chapter-1",
        workflow_type=WorkflowType.MEMORY_UPDATE_WORKFLOW,
        user_instruction="更新记忆",
        caller_type="user_action",
    )
    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="memory_context:mem_1",
        safe_message="memory context ready",
    )
    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="memory_update_suggestion:mem_upd_1",
        safe_message="memory suggestion ready",
    )

    recovered = orchestrator.recover_after_restart()
    recovered_run = next(item for item in recovered if item.session_id == run.session_id)

    assert recovered_run.current_stage == WorkflowStageName.MEMORY_REVIEW_WAITING
    assert recovered_run.checkpoints[-1].waiting_for_user_reason == "memory_review"

    completed = orchestrator.submit_user_decision(
        run.session_id,
        user_decision="confirm_memory_update",
        safe_message="memory confirmed after restart",
        request_id="req_memory_after_restart",
    )
    session = runtime.get_session(run.session_id)

    assert completed.current_stage == WorkflowStageName.COMPLETED
    assert session.status == AgentSessionStatus.COMPLETED


def test_agent_orchestrator_checkpoint_persists_selected_chapter_plan_after_confirmation(tmp_path) -> None:
    from application.services.ai.agent_workflow import AgentOrchestrator

    runtime = _build_runtime(tmp_path)
    orchestrator = AgentOrchestrator(runtime_service=runtime)
    run = orchestrator.start_workflow(
        work_id="work-1",
        chapter_id="chapter-1",
        workflow_type=WorkflowType.CONTINUATION_WORKFLOW,
        user_instruction="继续写这一章",
        caller_type="user_action",
    )
    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="memory_context:mem_1",
        safe_message="memory ready",
    )
    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="direction:dir_1",
        safe_message="planning ready",
    )
    run = orchestrator.submit_user_decision(
        run.session_id,
        user_decision="confirm_direction",
        safe_message="direction confirmed",
        request_id="req_direction_checkpoint",
        metadata={"selected_direction_id": "dir_1"},
    )

    assert run.current_stage == WorkflowStageName.CHAPTER_PLAN_CONFIRM_WAITING
    assert run.checkpoints[-1].waiting_for_user_reason == "chapter_plan_confirmation"

    run = orchestrator.submit_user_decision(
        run.session_id,
        user_decision="confirm_chapter_plan",
        safe_message="chapter plan confirmed",
        request_id="req_plan_checkpoint",
        metadata={"selected_chapter_plan_id": "plan_1"},
    )

    assert run.checkpoints[-1].selected_chapter_plan_id == "plan_1"


def test_agent_orchestrator_confirmed_chapter_plan_persists_sequence_arc(tmp_path) -> None:
    from application.services.ai.agent_workflow import AgentOrchestrator

    runtime = _build_runtime(tmp_path)
    plot_arc_store = FilePlotArcStore(tmp_path / "plot_arcs.json")
    chapter_plan_store = FileChapterPlanStore(tmp_path / "chapter_plans.json")
    plot_arc_store.save_master_arc(
        MasterArc(
            master_arc_id="ma_work_1",
            work_id="work-1",
            arc_title="主线轨道",
            status=ArcStatus.READY,
            quality_level=ArcQualityLevel.MINIMAL,
            ultimate_goal="查明灯塔异变",
            current_stage="方向确认后推进近期剧情",
            source_initialization_id="init_1",
            built_by="memory_agent",
            last_updated_by="memory_agent",
            created_at="2026-05-20T00:00:00+00:00",
            updated_at="2026-05-20T00:00:00+00:00",
        )
    )
    plot_arc_store.save_volume_arc(
        VolumeArc(
            volume_arc_id="va_work_1_1",
            work_id="work-1",
            master_arc_id="ma_work_1",
            volume_no=1,
            status=ArcStatus.PENDING,
            quality_level=ArcQualityLevel.PLACEHOLDER,
            stage_goal="锁定近期主线推进范围",
            core_conflict="顾迟与海雾真相的冲突",
            chapter_range={"from_chapter": 1, "to_chapter_estimate": 3},
            source_initialization_id="init_1",
            built_by="planner_agent",
            last_updated_by="planner_agent",
            created_at="2026-05-20T00:00:00+00:00",
            updated_at="2026-05-20T00:00:00+00:00",
        )
    )
    chapter_plan_store.save(
        ChapterPlan(
            chapter_plan_id="plan_1",
            work_id="work-1",
            chapter_id="chapter-1",
            direction_proposal_id="dir_1",
            selected_option_id="opt_a",
            selection_id="sel_1",
            agent_session_id="agent_session_seed",
            source_context_pack_id="cp_1",
            source_arc_refs=[],
            source_memory_refs=[],
            status="waiting_for_confirmation",
            version=1,
            plan_summary="接下来两章推进灯塔调查并逼近海雾真相。",
            total_estimated_chapters=2,
            created_by="planner_agent",
            stale_status="fresh",
            created_at="2026-05-20T00:00:00+00:00",
            updated_at="2026-05-20T00:00:00+00:00",
            plan_items=[
                ChapterPlanItem(
                    item_id="plan_item_1",
                    chapter_plan_id="plan_1",
                    plan_order=1,
                    chapter_goal="潜入灯塔档案室取得旧航海图。",
                    key_events=[
                        ChapterBeat(
                            beat_order=1,
                            beat_name="潜入档案室",
                            beat_description="顾迟避开守夜人进入档案室。",
                            beat_type="development",
                        )
                    ],
                    conflict_progression="顾迟必须在守夜人赶到前拿到线索。",
                    forbidden_items=["不要提前揭示父亲真相"],
                    required_beats=["取得航海图"],
                    arc_alignment=[],
                    is_user_edited=False,
                    created_at="2026-05-20T00:00:00+00:00",
                )
            ],
        )
    )
    orchestrator = AgentOrchestrator(
        runtime_service=runtime,
        plot_arc_repository=plot_arc_store,
        chapter_plan_repository=chapter_plan_store,
    )
    run = orchestrator.start_workflow(
        work_id="work-1",
        chapter_id="chapter-1",
        workflow_type=WorkflowType.CONTINUATION_WORKFLOW,
        user_instruction="继续写这一章",
        caller_type="user_action",
    )
    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="memory_context:mem_1",
        safe_message="memory ready",
    )
    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="direction:dir_1",
        safe_message="planning ready",
    )
    run = orchestrator.submit_user_decision(
        run.session_id,
        user_decision="confirm_direction",
        safe_message="direction confirmed",
        request_id="req_direction_for_sequence_arc",
        metadata={"selected_direction_id": "dir_1"},
    )

    run = orchestrator.submit_user_decision(
        run.session_id,
        user_decision="confirm_chapter_plan",
        safe_message="chapter plan confirmed",
        request_id="req_plan_for_sequence_arc",
        metadata={"selected_chapter_plan_id": "plan_1"},
    )
    sequence_arc = plot_arc_store.get_active_sequence_arc("work-1", chapter_no=1)

    assert run.current_stage == WorkflowStageName.WRITING_PREPARE
    assert sequence_arc is not None
    assert sequence_arc.built_by == "planner_agent"
    assert sequence_arc.last_updated_by == "planner_agent"
    assert sequence_arc.source_initialization_id == "init_1"
    assert "chapter_plan:plan_1" in sequence_arc.source_refs
    assert sequence_arc.volume_arc_id == "va_work_1_1"
    assert sequence_arc.sequence_goal == "接下来两章推进灯塔调查并逼近海雾真相。"
    assert sequence_arc.key_events[0].event_name == "潜入档案室"
    assert sequence_arc.key_events[0].description == "顾迟避开守夜人进入档案室。"
    assert "不要提前揭示父亲真相" in sequence_arc.forbidden_items


def test_agent_orchestrator_direction_confirmation_records_reason_code_metadata(tmp_path) -> None:
    from application.services.ai.agent_workflow import AgentOrchestrator

    runtime = _build_runtime(tmp_path)
    orchestrator = AgentOrchestrator(runtime_service=runtime)
    run = orchestrator.start_workflow(
        work_id="work-1",
        chapter_id="chapter-1",
        workflow_type=WorkflowType.CONTINUATION_WORKFLOW,
        user_instruction="继续写这一章",
        caller_type="user_action",
    )
    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="memory_context:mem_1",
        safe_message="memory ready",
    )
    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="direction:dir_1",
        safe_message="planning ready",
    )

    run = orchestrator.submit_user_decision(
        run.session_id,
        user_decision="confirm_direction",
        safe_message="direction confirmed",
        request_id="req_reason_direction",
        metadata={"selected_direction_id": "dir_1"},
    )

    assert _last_stage_record_with_reason_code(run, "user_selected_direction").metadata["reason_code"] == "user_selected_direction"
    assert any(item.ref_type == "selected_direction" and item.ref_id == "dir_1" for item in run.result_refs)


def test_agent_orchestrator_chapter_plan_confirm_waiting_uses_workflow_step_agent_type(tmp_path) -> None:
    from application.services.ai.agent_workflow import AgentOrchestrator

    runtime = _build_runtime(tmp_path)
    orchestrator = AgentOrchestrator(runtime_service=runtime)
    run = orchestrator.start_workflow(
        work_id="work-1",
        chapter_id="chapter-1",
        workflow_type=WorkflowType.CONTINUATION_WORKFLOW,
        user_instruction="继续写这一章",
        caller_type="user_action",
    )
    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="memory_context:mem_1",
        safe_message="memory ready",
    )
    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="direction:dir_1",
        safe_message="planning ready",
    )
    run = orchestrator.submit_user_decision(
        run.session_id,
        user_decision="confirm_direction",
        safe_message="direction confirmed",
        request_id="req_direction_waiting_agent_type",
        metadata={"selected_direction_id": "dir_1"},
    )
    session = runtime.get_session(run.session_id)
    step = runtime.get_step(session.current_step_id)

    assert run.current_stage == WorkflowStageName.CHAPTER_PLAN_CONFIRM_WAITING
    assert step.agent_type == "workflow"
    assert step.step_type == "wait_user_decision"
    assert run.checkpoints[-1].waiting_for_user_reason == "chapter_plan_confirmation"


def test_agent_orchestrator_chapter_plan_confirmation_records_reason_code_metadata(tmp_path) -> None:
    from application.services.ai.agent_workflow import AgentOrchestrator

    runtime = _build_runtime(tmp_path)
    orchestrator = AgentOrchestrator(runtime_service=runtime)
    run = orchestrator.start_workflow(
        work_id="work-1",
        chapter_id="chapter-1",
        workflow_type=WorkflowType.CONTINUATION_WORKFLOW,
        user_instruction="继续写这一章",
        caller_type="user_action",
    )
    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="memory_context:mem_1",
        safe_message="memory ready",
    )
    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="direction:dir_1",
        safe_message="planning ready",
    )
    run = orchestrator.submit_user_decision(
        run.session_id,
        user_decision="confirm_direction",
        safe_message="direction confirmed",
        request_id="req_reason_direction_for_plan",
        metadata={"selected_direction_id": "dir_1"},
    )

    run = orchestrator.submit_user_decision(
        run.session_id,
        user_decision="confirm_chapter_plan",
        safe_message="chapter plan confirmed",
        request_id="req_reason_plan",
        metadata={"selected_chapter_plan_id": "plan_1"},
    )

    assert _last_stage_record_with_reason_code(run, "user_confirmed_chapter_plan").metadata["reason_code"] == "user_confirmed_chapter_plan"
    assert any(item.ref_type == "selected_chapter_plan" and item.ref_id == "plan_1" for item in run.result_refs)


def test_agent_orchestrator_retry_stage_count_persists_after_resume(tmp_path) -> None:
    from application.services.ai.agent_workflow import AgentOrchestrator

    runtime = _build_runtime(tmp_path)
    orchestrator = AgentOrchestrator(runtime_service=runtime)
    run = orchestrator.start_workflow(
        work_id="work-1",
        chapter_id="chapter-1",
        workflow_type=WorkflowType.CONTINUATION_WORKFLOW,
        user_instruction="继续写这一章",
        caller_type="user_action",
    )

    _fail_current_step(runtime, run.session_id, safe_message="memory failed once")
    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.RETRY_STAGE,
        safe_message="retry memory stage",
    )
    _fail_current_step(runtime, run.session_id, safe_message="memory failed twice")

    orchestrator.pause_workflow(run.session_id, reason="user_paused")
    orchestrator.resume_workflow(run.session_id)

    with pytest.raises(ValueError, match="stage_retry_limit_reached"):
        orchestrator.advance_workflow(
            run.session_id,
            decision=WorkflowDecision.RETRY_STAGE,
            safe_message="retry memory stage again",
        )


def test_agent_orchestrator_revision_reviewing_rerun_replaces_old_review_report_result_ref(tmp_path) -> None:
    from application.services.ai.agent_workflow import AgentOrchestrator

    runtime = _build_runtime(tmp_path)
    orchestrator = AgentOrchestrator(runtime_service=runtime)
    run = orchestrator.start_workflow(
        work_id="work-1",
        chapter_id="chapter-1",
        workflow_type=WorkflowType.REVISION_WORKFLOW,
        user_instruction="修订后重新审阅",
        caller_type="user_action",
    )
    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="writing_context:ctx_1",
        safe_message="revision input ready",
    )
    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="candidate_version:cv_1",
        safe_message="rewrite ready",
    )
    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="review_report:review_old",
        safe_message="review ready",
    )
    orchestrator.pause_workflow(run.session_id, reason="user_paused")
    run = orchestrator._load_run(run.session_id)
    run.current_stage = WorkflowStageName.REVIEWING
    run.metadata["recovery_reason_code"] = "result_ref_missing"
    run.metadata["recovery_rerun_stage"] = WorkflowStageName.REVIEWING.value
    runtime.update_session_metadata(
        run.session_id,
        metadata_updates={"workflow_run": run.model_dump(mode="json")},
    )

    rerun = orchestrator.resume_workflow(run.session_id)
    rerun = orchestrator.advance_workflow(
        rerun.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="review_report:review_new",
        safe_message="review rerun ready",
    )

    review_refs = [f"{item.ref_type}:{item.ref_id}" for item in rerun.result_refs if item.ref_type == "review_report"]
    assert review_refs == ["review_report:review_new"]
    assert _last_stage_record_with_reason_code(rerun, "result_ref_missing").metadata["reason_code"] == "result_ref_missing"
    assert rerun.current_stage == WorkflowStageName.CANDIDATE_READY


def test_agent_orchestrator_memory_update_rerun_replaces_old_memory_suggestion_result_ref(tmp_path) -> None:
    from application.services.ai.agent_workflow import AgentOrchestrator

    runtime = _build_runtime(tmp_path)
    orchestrator = AgentOrchestrator(runtime_service=runtime)
    run = orchestrator.start_workflow(
        work_id="work-1",
        chapter_id="chapter-1",
        workflow_type=WorkflowType.MEMORY_UPDATE_WORKFLOW,
        user_instruction="更新记忆",
        caller_type="user_action",
    )
    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="memory_context:mem_1",
        safe_message="memory context ready",
    )
    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="memory_update_suggestion:mem_upd_old",
        safe_message="memory suggestion ready",
    )
    orchestrator.pause_workflow(run.session_id, reason="user_paused")
    run = orchestrator._load_run(run.session_id)
    run.metadata["recovery_reason_code"] = "result_ref_corrupted"
    run.metadata["recovery_rerun_stage"] = WorkflowStageName.MEMORY_SUGGESTION.value
    runtime.update_session_metadata(
        run.session_id,
        metadata_updates={"workflow_run": run.model_dump(mode="json")},
    )

    rerun = orchestrator.resume_workflow(run.session_id)
    rerun = orchestrator.advance_workflow(
        rerun.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="memory_update_suggestion:mem_upd_new",
        safe_message="memory suggestion rerun ready",
    )

    memory_refs = [
        f"{item.ref_type}:{item.ref_id}" for item in rerun.result_refs if item.ref_type == "memory_update_suggestion"
    ]
    assert memory_refs == ["memory_update_suggestion:mem_upd_new"]
    assert _last_stage_record_with_reason_code(rerun, "result_ref_corrupted").metadata["reason_code"] == "result_ref_corrupted"
    assert rerun.current_stage == WorkflowStageName.MEMORY_REVIEW_WAITING


def test_agent_orchestrator_writing_prepare_rerun_replaces_old_writing_context_result_ref(tmp_path) -> None:
    from application.services.ai.agent_workflow import AgentOrchestrator

    runtime = _build_runtime(tmp_path)
    orchestrator = AgentOrchestrator(runtime_service=runtime)
    run = orchestrator.start_workflow(
        work_id="work-1",
        chapter_id="chapter-1",
        workflow_type=WorkflowType.REVISION_WORKFLOW,
        user_instruction="修订并重新准备写作上下文",
        caller_type="user_action",
    )
    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="writing_context:ctx_old",
        safe_message="revision input ready",
    )
    orchestrator.pause_workflow(run.session_id, reason="user_paused")
    run = orchestrator._load_run(run.session_id)
    run.current_stage = WorkflowStageName.REWRITING
    run.metadata["recovery_reason_code"] = "result_ref_missing"
    run.metadata["recovery_rerun_stage"] = WorkflowStageName.WRITING_PREPARE.value
    runtime.update_session_metadata(
        run.session_id,
        metadata_updates={"workflow_run": run.model_dump(mode="json")},
    )

    rerun = orchestrator.resume_workflow(run.session_id)
    rerun = orchestrator.advance_workflow(
        rerun.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="writing_context:ctx_new",
        safe_message="revision input rerun ready",
    )

    writing_context_refs = [
        f"{item.ref_type}:{item.ref_id}" for item in rerun.result_refs if item.ref_type == "writing_context"
    ]
    assert writing_context_refs == ["writing_context:ctx_new"]


def test_agent_orchestrator_writing_prepare_rerun_replaces_old_context_pack_result_ref(tmp_path) -> None:
    from application.services.ai.agent_workflow import AgentOrchestrator

    runtime = _build_runtime(tmp_path)
    orchestrator = AgentOrchestrator(runtime_service=runtime)
    run = orchestrator.start_workflow(
        work_id="work-1",
        chapter_id="chapter-1",
        workflow_type=WorkflowType.CONTINUATION_WORKFLOW,
        user_instruction="继续写作",
        caller_type="user_action",
        policy_overrides={
            "require_direction_confirmation": False,
            "require_chapter_plan_confirmation": False,
        },
    )
    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="memory_context:mem_1",
        safe_message="memory ready",
    )
    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="chapter_plan:plan_1",
        safe_message="plan ready",
    )
    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="context_pack:cp_old",
        safe_message="context pack ready",
    )
    orchestrator.pause_workflow(run.session_id, reason="user_paused")
    run = orchestrator._load_run(run.session_id)
    run.current_stage = WorkflowStageName.DRAFTING
    run.metadata["recovery_reason_code"] = "result_ref_corrupted"
    run.metadata["recovery_rerun_stage"] = WorkflowStageName.WRITING_PREPARE.value
    runtime.update_session_metadata(
        run.session_id,
        metadata_updates={"workflow_run": run.model_dump(mode="json")},
    )

    rerun = orchestrator.resume_workflow(run.session_id)
    rerun = orchestrator.advance_workflow(
        rerun.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="context_pack:cp_new",
        safe_message="context pack rerun ready",
    )

    context_pack_refs = [f"{item.ref_type}:{item.ref_id}" for item in rerun.result_refs if item.ref_type == "context_pack"]
    assert context_pack_refs == ["context_pack:cp_new"]


def test_agent_orchestrator_review_stage_requires_review_report_result_ref(tmp_path) -> None:
    from application.services.ai.agent_workflow import AgentOrchestrator

    runtime = _build_runtime(tmp_path)
    orchestrator = AgentOrchestrator(runtime_service=runtime)
    run = orchestrator.start_workflow(
        work_id="work-1",
        chapter_id="chapter-1",
        workflow_type=WorkflowType.REVIEW_WORKFLOW,
        user_instruction="审阅候选稿",
        caller_type="user_action",
    )

    with pytest.raises(ValueError, match="expected_result_ref_missing"):
        orchestrator.advance_workflow(
            run.session_id,
            decision=WorkflowDecision.CONTINUE,
            safe_message="review done without report",
        )


def test_agent_orchestrator_memory_suggestion_stage_requires_memory_update_suggestion_result_ref(tmp_path) -> None:
    from application.services.ai.agent_workflow import AgentOrchestrator

    runtime = _build_runtime(tmp_path)
    orchestrator = AgentOrchestrator(runtime_service=runtime)
    run = orchestrator.start_workflow(
        work_id="work-1",
        chapter_id="chapter-1",
        workflow_type=WorkflowType.MEMORY_UPDATE_WORKFLOW,
        user_instruction="更新记忆",
        caller_type="user_action",
    )
    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="memory_context:mem_1",
        safe_message="memory context ready",
    )

    with pytest.raises(ValueError, match="expected_result_ref_missing"):
        orchestrator.advance_workflow(
            run.session_id,
            decision=WorkflowDecision.CONTINUE,
            safe_message="memory suggestion missing",
        )


def test_agent_orchestrator_drafting_stage_requires_candidate_draft_result_ref(tmp_path) -> None:
    from application.services.ai.agent_workflow import AgentOrchestrator

    runtime = _build_runtime(tmp_path)
    orchestrator = AgentOrchestrator(runtime_service=runtime)
    run = orchestrator.start_workflow(
        work_id="work-1",
        chapter_id="chapter-1",
        workflow_type=WorkflowType.CONTINUATION_WORKFLOW,
        user_instruction="继续写作",
        caller_type="user_action",
        policy_overrides={
            "require_direction_confirmation": False,
            "require_chapter_plan_confirmation": False,
        },
    )
    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="memory_context:mem_1",
        safe_message="memory ready",
    )
    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="chapter_plan:plan_1",
        safe_message="plan ready",
    )
    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="writing_task:task_1",
        safe_message="writing prepare ready",
    )

    with pytest.raises(ValueError, match="expected_result_ref_missing"):
        orchestrator.advance_workflow(
            run.session_id,
            decision=WorkflowDecision.CONTINUE,
            safe_message="draft missing",
        )


def test_agent_orchestrator_continuation_can_bypass_review_when_policy_disables_review_requirement(tmp_path) -> None:
    from application.services.ai.agent_workflow import AgentOrchestrator

    runtime = _build_runtime(tmp_path)
    orchestrator = AgentOrchestrator(runtime_service=runtime)
    run = orchestrator.start_workflow(
        work_id="work-1",
        chapter_id="chapter-1",
        workflow_type=WorkflowType.CONTINUATION_WORKFLOW,
        user_instruction="继续写作",
        caller_type="user_action",
        policy_overrides={
            "require_direction_confirmation": False,
            "require_chapter_plan_confirmation": False,
            "require_review_before_candidate_ready": False,
        },
    )
    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="memory_context:mem_1",
        safe_message="memory ready",
    )
    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="chapter_plan:plan_1",
        safe_message="plan ready",
    )
    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="writing_task:task_1",
        safe_message="writing context ready",
    )

    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="candidate_draft:draft_1",
        safe_message="draft ready",
    )

    assert run.current_stage == WorkflowStageName.CANDIDATE_READY


def test_agent_orchestrator_revision_can_bypass_review_when_policy_disables_review_requirement(tmp_path) -> None:
    from application.services.ai.agent_workflow import AgentOrchestrator

    runtime = _build_runtime(tmp_path)
    orchestrator = AgentOrchestrator(runtime_service=runtime)
    run = orchestrator.start_workflow(
        work_id="work-1",
        chapter_id="chapter-1",
        workflow_type=WorkflowType.REVISION_WORKFLOW,
        user_instruction="修订当前稿件",
        caller_type="user_action",
        policy_overrides={"require_review_before_candidate_ready": False},
    )
    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="writing_context:ctx_1",
        safe_message="revision input ready",
    )

    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="candidate_version:ver_1",
        safe_message="rewrite ready",
    )

    assert run.current_stage == WorkflowStageName.CANDIDATE_READY


def test_agent_orchestrator_allow_skip_reviewer_does_not_auto_skip_reviewing_stage(tmp_path) -> None:
    from application.services.ai.agent_workflow import AgentOrchestrator

    runtime = _build_runtime(tmp_path)
    orchestrator = AgentOrchestrator(runtime_service=runtime)
    run = orchestrator.start_workflow(
        work_id="work-1",
        chapter_id="chapter-1",
        workflow_type=WorkflowType.CONTINUATION_WORKFLOW,
        user_instruction="继续写作",
        caller_type="user_action",
        policy_overrides={
            "require_direction_confirmation": False,
            "require_chapter_plan_confirmation": False,
            "allow_skip_reviewer": True,
            "require_review_before_candidate_ready": True,
        },
    )
    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="memory_context:mem_1",
        safe_message="memory ready",
    )
    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="chapter_plan:plan_1",
        safe_message="plan ready",
    )
    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="writing_task:task_1",
        safe_message="writing context ready",
    )

    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="candidate_draft:draft_1",
        safe_message="draft ready",
    )

    assert run.current_stage == WorkflowStageName.REVIEWING



def test_agent_orchestrator_allow_skip_reviewer_supports_explicit_skip_to_candidate_ready(tmp_path) -> None:
    from application.services.ai.agent_workflow import AgentOrchestrator

    runtime = _build_runtime(tmp_path)
    orchestrator = AgentOrchestrator(runtime_service=runtime)
    run = orchestrator.start_workflow(
        work_id="work-1",
        chapter_id="chapter-1",
        workflow_type=WorkflowType.CONTINUATION_WORKFLOW,
        user_instruction="继续写作",
        caller_type="user_action",
        policy_overrides={
            "require_direction_confirmation": False,
            "require_chapter_plan_confirmation": False,
            "allow_skip_reviewer": True,
        },
    )
    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="memory_context:mem_1",
        safe_message="memory ready",
    )
    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="chapter_plan:plan_1",
        safe_message="plan ready",
    )
    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="writing_task:task_1",
        safe_message="writing context ready",
    )
    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="candidate_draft:draft_1",
        safe_message="draft ready",
    )

    assert run.current_stage == WorkflowStageName.REVIEWING

    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.SKIP_OPTIONAL_STAGE,
        safe_message="skip reviewer",
    )

    assert run.current_stage == WorkflowStageName.CANDIDATE_READY
    assert run.stage_history[-1].decision == WorkflowDecision.SKIP_OPTIONAL_STAGE.value
    assert run.stage_history[-1].metadata["reason_code"] == "workflow_optional_stage_skipped"
def test_agent_orchestrator_revision_writing_prepare_requires_result_ref(tmp_path) -> None:
    from application.services.ai.agent_workflow import AgentOrchestrator

    runtime = _build_runtime(tmp_path)
    orchestrator = AgentOrchestrator(runtime_service=runtime)
    run = orchestrator.start_workflow(
        work_id="work-1",
        chapter_id="chapter-1",
        workflow_type=WorkflowType.REVISION_WORKFLOW,
        user_instruction="修订当前稿件",
        caller_type="user_action",
    )

    with pytest.raises(ValueError, match="expected_result_ref_missing"):
        orchestrator.advance_workflow(
            run.session_id,
            decision=WorkflowDecision.CONTINUE,
            safe_message="writing prepare missing",
        )


def test_agent_orchestrator_rewriting_stage_requires_candidate_version_result_ref(tmp_path) -> None:
    from application.services.ai.agent_workflow import AgentOrchestrator

    runtime = _build_runtime(tmp_path)
    orchestrator = AgentOrchestrator(runtime_service=runtime)
    run = orchestrator.start_workflow(
        work_id="work-1",
        chapter_id="chapter-1",
        workflow_type=WorkflowType.REVISION_WORKFLOW,
        user_instruction="修订当前稿件",
        caller_type="user_action",
    )
    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="writing_context:ctx_1",
        safe_message="revision input ready",
    )

    with pytest.raises(ValueError, match="expected_result_ref_missing"):
        orchestrator.advance_workflow(
            run.session_id,
            decision=WorkflowDecision.CONTINUE,
            safe_message="rewriting output missing",
        )


def test_agent_orchestrator_resume_planning_failure_reuses_memory_context_ref(tmp_path) -> None:
    from application.services.ai.agent_workflow import AgentOrchestrator

    runtime = _build_runtime(tmp_path)
    orchestrator = AgentOrchestrator(runtime_service=runtime)
    run = orchestrator.start_workflow(
        work_id="work-1",
        chapter_id="chapter-1",
        workflow_type=WorkflowType.CONTINUATION_WORKFLOW,
        user_instruction="继续写作",
        caller_type="user_action",
        policy_overrides={
            "require_direction_confirmation": False,
            "require_chapter_plan_confirmation": False,
        },
    )
    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="memory_context:mem_1",
        safe_message="memory ready",
    )
    _fail_current_step(runtime, run.session_id, safe_message="planner_failed")
    orchestrator.pause_workflow(run.session_id, reason="user_paused")
    run = orchestrator._load_run(run.session_id)
    run.metadata["recovery_reason_code"] = "planner_failed"
    run.metadata["recovery_rerun_stage"] = WorkflowStageName.PLANNING_PREPARE.value
    runtime.update_session_metadata(
        run.session_id,
        metadata_updates={"workflow_run": run.model_dump(mode="json")},
    )

    resumed = orchestrator.resume_workflow(run.session_id)

    memory_refs = [f"{item.ref_type}:{item.ref_id}" for item in resumed.result_refs if item.ref_type == "memory_context"]
    assert memory_refs == ["memory_context:mem_1"]
    assert resumed.current_stage == WorkflowStageName.PLANNING_PREPARE
    assert resumed.checkpoints[-1].result_refs[-1].ref_type == "memory_context"


def test_agent_orchestrator_planning_prepare_requires_direction_or_chapter_plan_result_ref(tmp_path) -> None:
    from application.services.ai.agent_workflow import AgentOrchestrator

    runtime = _build_runtime(tmp_path)
    orchestrator = AgentOrchestrator(runtime_service=runtime)
    run = orchestrator.start_workflow(
        work_id="work-1",
        chapter_id="chapter-1",
        workflow_type=WorkflowType.CONTINUATION_WORKFLOW,
        user_instruction="继续写作",
        caller_type="user_action",
    )
    run = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="memory_context:mem_1",
        safe_message="memory ready",
    )

    with pytest.raises(ValueError, match="expected_result_ref_missing"):
        orchestrator.advance_workflow(
            run.session_id,
            decision=WorkflowDecision.CONTINUE,
            safe_message="planning missing",
        )


def test_agent_orchestrator_retry_step_records_reason_code_metadata(tmp_path) -> None:
    from application.services.ai.agent_workflow import AgentOrchestrator

    runtime = _build_runtime(tmp_path)
    orchestrator = AgentOrchestrator(runtime_service=runtime)
    run = orchestrator.start_workflow(
        work_id="work-1",
        chapter_id="chapter-1",
        workflow_type=WorkflowType.CONTINUATION_WORKFLOW,
        user_instruction="继续写作",
        caller_type="user_action",
    )

    _fail_current_step(runtime, run.session_id, safe_message="memory failed")
    retried = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.RETRY_STEP,
        safe_message="retry current step",
    )

    assert _last_stage_record_with_reason_code(retried, "retry_current_step").metadata["reason_code"] == "retry_current_step"


def test_agent_orchestrator_retry_stage_records_reason_code_and_checkpoint_consistency(tmp_path) -> None:
    from application.services.ai.agent_workflow import AgentOrchestrator

    runtime = _build_runtime(tmp_path)
    orchestrator = AgentOrchestrator(runtime_service=runtime)
    run = orchestrator.start_workflow(
        work_id="work-1",
        chapter_id="chapter-1",
        workflow_type=WorkflowType.REVIEW_WORKFLOW,
        user_instruction="审阅候选稿",
        caller_type="user_action",
    )

    _fail_current_step(runtime, run.session_id, safe_message="review failed")
    retried = orchestrator.advance_workflow(
        run.session_id,
        decision=WorkflowDecision.RETRY_STAGE,
        safe_message="retry review stage",
    )
    retried = orchestrator.advance_workflow(
        retried.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="review_report:review_retry_1",
        safe_message="review retry success",
    )

    assert _last_stage_record_with_reason_code(retried, "retry_current_stage").metadata["reason_code"] == "retry_current_stage"
    checkpoint_review_refs = [
        f"{item.ref_type}:{item.ref_id}" for item in retried.checkpoints[-1].result_refs if item.ref_type == "review_report"
    ]
    assert checkpoint_review_refs == ["review_report:review_retry_1"]
