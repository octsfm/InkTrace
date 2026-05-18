from __future__ import annotations

import pytest
from pydantic import ValidationError

from application.services.ai.agent_runtime_service import AgentRuntimeService
from application.services.ai.tool_facade import CoreToolFacade, ToolDefinition
from domain.entities.ai.models import (
    AgentObservation,
    AgentObservationType,
    PPAOPhase,
    AgentRunContext,
    AgentSession,
    AgentSessionStatus,
    AgentStep,
    AgentStepStatus,
    AgentWorkflowType,
)
from infrastructure.database.repositories.ai.file_agent_runtime_store import FileAgentRuntimeStore
from infrastructure.database.repositories.ai.file_ai_job_store import FileAIJobStore
from application.services.ai.ai_job_service import AIJobService


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


def test_agent_step_accepts_legacy_step_order_alias() -> None:
    step = AgentStep.model_validate(
        {
            "step_id": "agent_step_alias",
            "session_id": "agent_session_alias",
            "job_id": "job_alias",
            "agent_type": "writer",
            "step_type": "call_tool",
            "action": "run_writer",
            "step_order": 3,
            "status": "pending",
        }
    )

    assert step.order_index == 3


def test_agent_runtime_service_create_and_start_session(tmp_path) -> None:
    runtime = _build_runtime(tmp_path)

    session = runtime.create_session(
        work_id="work-1",
        chapter_id="chapter-1",
        agent_workflow_type=AgentWorkflowType.CONTINUATION,
        user_instruction="继续写这一章",
        request_id="req_1",
        trace_id="trace_1",
        caller_type="user_action",
    )
    started = runtime.start_session(session.session_id)

    assert session.status == AgentSessionStatus.PENDING
    assert session.job_id
    assert started.status == AgentSessionStatus.RUNNING
    assert started.started_at


def test_agent_runtime_service_create_session_defaults_request_trace_and_allow_degraded(tmp_path) -> None:
    runtime = _build_runtime(tmp_path)

    session = runtime.create_session(
        work_id="work-1",
        chapter_id="chapter-1",
        agent_workflow_type=AgentWorkflowType.CONTINUATION,
        user_instruction="继续写这一章",
        caller_type="user_action",
    )
    job = runtime._ai_job_service.get_job(session.job_id)

    assert session.request_id.startswith("req_")
    assert session.trace_id.startswith("trace_")
    assert session.allow_degraded is True
    assert job.job_type == "agent_session"
    assert job.payload["request_id"] == session.request_id
    assert job.payload["trace_id"] == session.trace_id


def test_agent_runtime_service_create_session_persists_allow_degraded_false(tmp_path) -> None:
    runtime = _build_runtime(tmp_path)

    session = runtime.create_session(
        work_id="work-1",
        chapter_id="chapter-1",
        agent_workflow_type=AgentWorkflowType.CONTINUATION,
        user_instruction="继续写这一章",
        caller_type="user_action",
        allow_degraded=False,
    )

    run_context = runtime.build_run_context(
        session.session_id,
        current_agent_type="writer",
    )

    assert session.allow_degraded is False
    assert run_context.allow_degraded is False
    assert run_context.agent_workflow_type == AgentWorkflowType.CONTINUATION
    assert run_context.job_id == session.job_id
    assert run_context.caller_type == "user_action"


def test_agent_runtime_service_create_step_creates_ai_job_step_projection(tmp_path) -> None:
    runtime = _build_runtime(tmp_path)
    session = runtime.create_session(
        work_id="work-1",
        chapter_id="chapter-1",
        agent_workflow_type=AgentWorkflowType.CONTINUATION,
        user_instruction="继续写这一章",
        request_id="req_1a",
        trace_id="trace_1a",
        caller_type="user_action",
    )

    step = runtime.create_step(session.session_id, agent_type="writer", step_type="generate_candidate", action="run_writer")
    job_steps = runtime._ai_job_service.get_job_steps(session.job_id)

    assert step.job_step_id
    assert len(job_steps) == 1
    assert job_steps[0].step_id == step.job_step_id
    assert job_steps[0].step_type == "agent_step:writer:run_writer"
    assert step.tool_calls == []
    assert step.step_plan is None
    assert step.input_ref == ""
    assert step.output_refs == []
    assert step.retryable is True
    assert step.skippable is False
    assert step.requires_user_decision is False
    assert step.skip_reason == ""


def test_agent_runtime_service_create_step_marks_user_decision_step_requirements(tmp_path) -> None:
    runtime = _build_runtime(tmp_path)
    session = runtime.create_session(
        work_id="work-1",
        chapter_id="chapter-1",
        agent_workflow_type=AgentWorkflowType.CONTINUATION,
        user_instruction="继续写这一章",
        request_id="req_1aw",
        trace_id="trace_1aw",
        caller_type="user_action",
    )

    step = runtime.create_step(
        session.session_id,
        agent_type="planner",
        step_type="wait_user_decision",
        action="wait_direction_selection",
    )

    assert step.requires_user_decision is True
    assert step.retryable is True
    assert step.skippable is False


def test_agent_runtime_service_entering_planning_builds_step_plan_and_retryability(tmp_path) -> None:
    runtime = _build_runtime(tmp_path)
    session = runtime.create_session(
        work_id="work-1",
        chapter_id="chapter-1",
        agent_workflow_type=AgentWorkflowType.CONTINUATION,
        user_instruction="继续写这一章",
        request_id="req_1ap",
        trace_id="trace_1ap",
        caller_type="user_action",
    )
    runtime.start_session(session.session_id)
    step = runtime.create_step(
        session.session_id,
        agent_type="writer",
        step_type="call_tool",
        action="formal_chapter_write",
    )

    runtime.run_next_step(session.session_id)
    runtime.record_observation(
        step.step_id,
        AgentObservation(
            observation_id="obs_plan_1ap",
            session_id=session.session_id,
            step_id=step.step_id,
            observation_type=AgentObservationType.STATE_CHANGE,
            source_type="system",
            status="success",
            safe_message="进入 planning",
            decision="continue",
            trace_id=session.trace_id,
            request_id="req_1ap_plan",
        ),
    )

    refreshed_step = runtime.get_step(step.step_id)
    assert refreshed_step.step_phase == "planning"
    assert refreshed_step.retryable is False
    assert refreshed_step.step_plan is not None
    assert refreshed_step.step_plan.next_action_type == "call_tool"
    assert refreshed_step.step_plan.expected_observation_type == "tool_result"
    assert refreshed_step.step_plan.retryable is False
    assert refreshed_step.step_plan.requires_user_decision is False


def test_agent_runtime_models_match_p1_s1_acceptance_blockers() -> None:
    assert {item.value for item in AgentWorkflowType} == {
        "continuation",
        "revision",
        "planning",
        "memory_update",
        "full_workflow",
    }
    for field_name in ("current_agent_type", "allow_degraded"):
        assert field_name in AgentSession.model_fields
    for field_name in (
        "tool_calls",
        "step_plan",
        "input_ref",
        "output_refs",
        "retryable",
        "skippable",
        "requires_user_decision",
        "skip_reason",
    ):
        assert field_name in AgentStep.model_fields
    for field_name in (
        "source_ref",
        "summary",
        "decision_reason",
        "source_tool_call_id",
        "source_attempt_no",
        "error_message",
        "next_action_hint",
    ):
        assert field_name in AgentObservation.model_fields
    for field_name in (
        "job_id",
        "agent_workflow_type",
        "current_phase",
        "caller_type",
        "warning_codes",
        "resource_scope_refs",
        "prior_observation_refs",
        "execution_guard_flags",
    ):
        assert field_name in AgentRunContext.model_fields


def test_agent_runtime_models_reject_invalid_ppao_phase_values() -> None:
    with pytest.raises(ValidationError, match="current_phase"):
        AgentSession.model_validate(
            {
                "session_id": "agent_session_invalid",
                "job_id": "job_invalid",
                "work_id": "work-1",
                "agent_workflow_type": "continuation",
                "status": "pending",
                "current_phase": "invalid_phase",
            }
        )

    with pytest.raises(ValidationError, match="step_phase"):
        AgentStep.model_validate(
            {
                "step_id": "agent_step_invalid",
                "session_id": "agent_session_invalid",
                "job_id": "job_invalid",
                "agent_type": "writer",
                "step_type": "call_tool",
                "action": "run_writer",
                "order_index": 1,
                "status": "pending",
                "step_phase": "invalid_phase",
            }
        )


def test_agent_runtime_service_run_next_step_records_ai_job_attempt(tmp_path) -> None:
    runtime = _build_runtime(tmp_path)
    session = runtime.create_session(
        work_id="work-1",
        chapter_id="chapter-1",
        agent_workflow_type=AgentWorkflowType.CONTINUATION,
        user_instruction="继续写这一章",
        request_id="req_1a4",
        trace_id="trace_1a4",
        caller_type="user_action",
    )
    runtime.start_session(session.session_id)
    step = runtime.create_step(session.session_id, agent_type="writer", step_type="generate_candidate", action="run_writer")

    runtime.run_next_step(session.session_id)

    attempts = runtime._ai_job_service.list_attempts(step.job_step_id)
    refreshed_session = runtime.get_session(session.session_id)
    assert len(attempts) == 1
    assert attempts[0].request_id == "req_1a4"
    assert attempts[0].trace_id == "trace_1a4"
    assert attempts[0].status.value == "running"
    assert refreshed_session.current_agent_type == "writer"


def test_agent_runtime_service_run_next_step_rejects_when_no_pending_step(tmp_path) -> None:
    runtime = _build_runtime(tmp_path)
    session = runtime.create_session(
        work_id="work-1",
        chapter_id="chapter-1",
        agent_workflow_type=AgentWorkflowType.CONTINUATION,
        user_instruction="继续写这一章",
        request_id="req_1a2",
        trace_id="trace_1a2",
        caller_type="user_action",
    )
    runtime.start_session(session.session_id)

    with pytest.raises(ValueError, match="step_not_found"):
        runtime.run_next_step(session.session_id)


def test_agent_runtime_service_execute_tool_action_rejects_when_tool_facade_missing(tmp_path) -> None:
    agent_store = FileAgentRuntimeStore(tmp_path / "agent_runtime.json")
    job_store = FileAIJobStore(tmp_path / "ai_jobs.json")
    job_service = AIJobService(job_repository=job_store, step_repository=job_store, attempt_repository=job_store)
    runtime = AgentRuntimeService(
        session_repository=agent_store,
        step_repository=agent_store,
        observation_repository=agent_store,
        ai_job_service=job_service,
        tool_facade=None,
    )
    session = runtime.create_session(
        work_id="work-1",
        chapter_id="chapter-1",
        agent_workflow_type=AgentWorkflowType.CONTINUATION,
        user_instruction="继续写这一章",
        request_id="req_1a3",
        trace_id="trace_1a3",
        caller_type="user_action",
    )
    step = runtime.create_step(session.session_id, agent_type="writer", step_type="generate_candidate", action="run_writer")

    with pytest.raises(ValueError, match="tool_facade_not_configured"):
        runtime.execute_tool_action(
            session.session_id,
            step_id=step.step_id,
            agent_type="writer",
            tool_name="run_writer_step",
            payload={},
            side_effect_level="draft_write",
        )


def test_agent_runtime_service_syncs_job_step_status_on_run_and_complete(tmp_path) -> None:
    runtime = _build_runtime(tmp_path)
    session = runtime.create_session(
        work_id="work-1",
        chapter_id="chapter-1",
        agent_workflow_type=AgentWorkflowType.CONTINUATION,
        user_instruction="继续写这一章",
        request_id="req_1b",
        trace_id="trace_1b",
        caller_type="user_action",
    )
    runtime.start_session(session.session_id)
    step = runtime.create_step(session.session_id, agent_type="writer", step_type="generate_candidate", action="run_writer")

    runtime.run_next_step(session.session_id)
    running_job_step = runtime._ai_job_service.get_job_steps(session.job_id)[0]
    runtime.record_observation(
        step.step_id,
        AgentObservation(
            observation_id="obs_job_complete",
            session_id=session.session_id,
            step_id=step.step_id,
            observation_type=AgentObservationType.TOOL_RESULT,
            source_type="tool",
            status="success",
            safe_message="完成",
            decision="complete_step",
            trace_id=session.trace_id,
            request_id="req_1b2",
        ),
    )
    completed_job_step = runtime._ai_job_service.get_job_steps(session.job_id)[0]
    refreshed_session = runtime.get_session(session.session_id)
    refreshed_step = runtime.get_step(step.step_id)

    assert running_job_step.status.value == "running"
    assert completed_job_step.status.value == "completed"
    assert refreshed_session.current_step_id == step.step_id
    assert refreshed_session.current_phase == "observation"
    assert refreshed_step.step_phase == "observation"


def test_agent_runtime_service_run_next_step_syncs_ai_job_current_step_label_from_action(tmp_path) -> None:
    runtime = _build_runtime(tmp_path)
    session = runtime.create_session(
        work_id="work-1",
        chapter_id="chapter-1",
        agent_workflow_type=AgentWorkflowType.CONTINUATION,
        user_instruction="继续写这一章",
        request_id="req_1bb",
        trace_id="trace_1bb",
        caller_type="user_action",
    )
    runtime.start_session(session.session_id)
    runtime.create_step(session.session_id, agent_type="writer", step_type="generate_candidate", action="run_writer")

    runtime.run_next_step(session.session_id)

    refreshed_job = runtime._ai_job_service.get_job(session.job_id)
    assert refreshed_job.progress.current_step == "agent_step:writer:run_writer"
    assert refreshed_job.progress.current_step_label == "run_writer"


def test_agent_runtime_service_syncs_job_step_failed_and_cancelled_projection(tmp_path) -> None:
    runtime = _build_runtime(tmp_path)
    session = runtime.create_session(
        work_id="work-1",
        chapter_id="chapter-1",
        agent_workflow_type=AgentWorkflowType.CONTINUATION,
        user_instruction="继续写这一章",
        request_id="req_1c",
        trace_id="trace_1c",
        caller_type="user_action",
    )
    runtime.start_session(session.session_id)
    step = runtime.create_step(session.session_id, agent_type="writer", step_type="generate_candidate", action="run_writer")
    runtime.record_observation(
        step.step_id,
        AgentObservation(
            observation_id="obs_job_fail",
            session_id=session.session_id,
            step_id=step.step_id,
            observation_type=AgentObservationType.ERROR,
            source_type="tool",
            status="failed",
            safe_message="失败",
            decision="fail_step",
            error_code="provider_timeout",
            trace_id=session.trace_id,
            request_id="req_1c2",
        ),
    )
    failed_job_step = runtime._ai_job_service.get_job_steps(session.job_id)[0]
    runtime.cancel_session(session.session_id, reason="user_cancelled")
    cancelled_projection = runtime._ai_job_service.get_job_steps(session.job_id)[0]

    assert failed_job_step.status.value == "failed"
    assert failed_job_step.error_code == "provider_timeout"
    assert cancelled_projection.status.value == "failed"


def test_agent_runtime_service_records_waiting_for_user_observation(tmp_path) -> None:
    runtime = _build_runtime(tmp_path)
    session = runtime.create_session(
        work_id="work-1",
        chapter_id="chapter-1",
        agent_workflow_type=AgentWorkflowType.CONTINUATION,
        user_instruction="继续写这一章",
        request_id="req_2",
        trace_id="trace_2",
        caller_type="user_action",
    )
    runtime.start_session(session.session_id)
    step = runtime.create_step(session.session_id, agent_type="planner", step_type="wait_user_decision", action="confirm_direction")

    observation = AgentObservation(
        observation_id="obs_wait",
        session_id=session.session_id,
        step_id=step.step_id,
        observation_type=AgentObservationType.USER_DECISION,
        source_type="user",
        status="success",
        safe_message="等待用户选择方向",
        decision="wait_for_user",
        trace_id=session.trace_id,
        request_id="req_2b",
    )
    recorded = runtime.record_observation(step.step_id, observation)

    refreshed_session = runtime.get_session(session.session_id)
    refreshed_step = runtime.get_step(step.step_id)
    job = runtime._ai_job_service.get_job(session.job_id)
    assert recorded.decision == "wait_for_user"
    assert refreshed_session.status == AgentSessionStatus.WAITING_FOR_USER
    assert refreshed_step.status == AgentStepStatus.WAITING_USER
    assert job.status.value == "running"


def test_agent_runtime_service_pause_resume_and_cancel_session(tmp_path) -> None:
    runtime = _build_runtime(tmp_path)
    session = runtime.create_session(
        work_id="work-1",
        chapter_id="chapter-1",
        agent_workflow_type=AgentWorkflowType.CONTINUATION,
        user_instruction="继续写这一章",
        request_id="req_3",
        trace_id="trace_3",
        caller_type="user_action",
    )
    runtime.start_session(session.session_id)

    paused = runtime.pause_session(session.session_id)
    resumed = runtime.resume_session(session.session_id)
    cancelled = runtime.cancel_session(session.session_id, reason="user_cancelled")

    assert paused.status == AgentSessionStatus.PAUSED
    assert resumed.status == AgentSessionStatus.RUNNING
    assert cancelled.status == AgentSessionStatus.CANCELLED
    assert cancelled.status_reason == "user_cancelled"


def test_agent_runtime_service_retry_session_creates_new_session(tmp_path) -> None:
    runtime = _build_runtime(tmp_path)
    session = runtime.create_session(
        work_id="work-1",
        chapter_id="chapter-1",
        agent_workflow_type=AgentWorkflowType.CONTINUATION,
        user_instruction="继续写这一章",
        request_id="req_4",
        trace_id="trace_4",
        caller_type="user_action",
    )
    runtime.start_session(session.session_id)
    runtime.fail_session(session.session_id, error_code="writer_failed", error_message="writer failed")

    retried = runtime.retry_session(session.session_id)

    assert retried.session_id != session.session_id
    assert retried.status == AgentSessionStatus.PENDING
    assert retried.metadata["retry_of_session_id"] == session.session_id
    assert retried.trace_id != session.trace_id
    assert retried.request_id != session.request_id


def test_agent_runtime_service_rejects_start_for_terminal_session(tmp_path) -> None:
    runtime = _build_runtime(tmp_path)
    session = runtime.create_session(
        work_id="work-1",
        chapter_id="chapter-1",
        agent_workflow_type=AgentWorkflowType.CONTINUATION,
        user_instruction="继续写这一章",
        request_id="req_5",
        trace_id="trace_5",
        caller_type="user_action",
    )
    runtime.cancel_session(session.session_id, reason="user_cancelled")

    with pytest.raises(ValueError, match="session_not_startable"):
        runtime.start_session(session.session_id)


def test_agent_runtime_service_rejects_start_for_paused_session(tmp_path) -> None:
    runtime = _build_runtime(tmp_path)
    session = runtime.create_session(
        work_id="work-1",
        chapter_id="chapter-1",
        agent_workflow_type=AgentWorkflowType.CONTINUATION,
        user_instruction="继续写这一章",
        request_id="req_5a",
        trace_id="trace_5a",
        caller_type="user_action",
    )
    runtime.start_session(session.session_id)
    runtime.pause_session(session.session_id)

    with pytest.raises(ValueError, match="session_not_startable"):
        runtime.start_session(session.session_id)


def test_agent_runtime_service_rejects_cancel_for_completed_session(tmp_path) -> None:
    runtime = _build_runtime(tmp_path)
    session = runtime.create_session(
        work_id="work-1",
        chapter_id="chapter-1",
        agent_workflow_type=AgentWorkflowType.CONTINUATION,
        user_instruction="继续写这一章",
        request_id="req_5b",
        trace_id="trace_5b",
        caller_type="user_action",
    )
    runtime.start_session(session.session_id)
    step = runtime.create_step(session.session_id, agent_type="writer", step_type="generate_candidate", action="run_writer")
    runtime._step_repository.save_step(
        runtime.get_step(step.step_id).model_copy(update={"status": AgentStepStatus.SUCCEEDED, "finished_at": "2026-05-15T00:00:00Z"})
    )
    runtime.complete_session(session.session_id, result_ref="candidate_draft:cd_5b")

    with pytest.raises(ValueError, match="session_not_cancellable"):
        runtime.cancel_session(session.session_id, reason="user_cancelled")


def test_agent_runtime_service_rejects_complete_for_terminal_session(tmp_path) -> None:
    runtime = _build_runtime(tmp_path)
    session = runtime.create_session(
        work_id="work-1",
        chapter_id="chapter-1",
        agent_workflow_type=AgentWorkflowType.CONTINUATION,
        user_instruction="继续写这一章",
        request_id="req_5c",
        trace_id="trace_5c",
        caller_type="user_action",
    )
    runtime.start_session(session.session_id)
    step = runtime.create_step(session.session_id, agent_type="writer", step_type="generate_candidate", action="run_writer")
    runtime._step_repository.save_step(
        runtime.get_step(step.step_id).model_copy(update={"status": AgentStepStatus.SUCCEEDED, "finished_at": "2026-05-15T00:00:00Z"})
    )
    runtime.complete_session(session.session_id, result_ref="candidate_draft:cd_5c")

    with pytest.raises(ValueError, match="session_not_completable"):
        runtime.complete_session(session.session_id, result_ref="candidate_draft:cd_5c_v2")


def test_agent_runtime_service_rejects_fail_for_completed_session(tmp_path) -> None:
    runtime = _build_runtime(tmp_path)
    session = runtime.create_session(
        work_id="work-1",
        chapter_id="chapter-1",
        agent_workflow_type=AgentWorkflowType.CONTINUATION,
        user_instruction="继续写这一章",
        request_id="req_5d",
        trace_id="trace_5d",
        caller_type="user_action",
    )
    runtime.start_session(session.session_id)
    step = runtime.create_step(session.session_id, agent_type="writer", step_type="generate_candidate", action="run_writer")
    runtime._step_repository.save_step(
        runtime.get_step(step.step_id).model_copy(update={"status": AgentStepStatus.SUCCEEDED, "finished_at": "2026-05-15T00:00:00Z"})
    )
    runtime.complete_session(session.session_id, result_ref="candidate_draft:cd_5d")

    with pytest.raises(ValueError, match="session_not_failable"):
        runtime.fail_session(session.session_id, error_code="writer_failed", error_message="writer failed")


def test_agent_runtime_service_ignores_late_observation_after_cancel(tmp_path) -> None:
    runtime = _build_runtime(tmp_path)
    session = runtime.create_session(
        work_id="work-1",
        chapter_id="chapter-1",
        agent_workflow_type=AgentWorkflowType.CONTINUATION,
        user_instruction="继续写这一章",
        request_id="req_6",
        trace_id="trace_6",
        caller_type="user_action",
    )
    runtime.start_session(session.session_id)
    step = runtime.create_step(session.session_id, agent_type="writer", step_type="generate_candidate", action="run_writer")
    runtime.cancel_session(session.session_id, reason="user_cancelled")

    late_observation = AgentObservation(
        observation_id="obs_late",
        session_id=session.session_id,
        step_id=step.step_id,
        observation_type=AgentObservationType.TOOL_RESULT,
        source_type="tool",
        status="success",
        safe_message="迟到结果已忽略",
        decision="continue",
        trace_id=session.trace_id,
        request_id="req_6b",
    )

    runtime.record_observation(step.step_id, late_observation)

    refreshed_session = runtime.get_session(session.session_id)
    refreshed_step = runtime.get_step(step.step_id)
    assert refreshed_session.status == AgentSessionStatus.CANCELLED
    assert refreshed_step.status == AgentStepStatus.IGNORED_LATE_RESULT
    assert refreshed_step.status_reason == "ignored_late_result"


def test_agent_runtime_service_marks_partial_success_and_maps_job_completed(tmp_path) -> None:
    runtime = _build_runtime(tmp_path)
    session = runtime.create_session(
        work_id="work-1",
        chapter_id="chapter-1",
        agent_workflow_type=AgentWorkflowType.CONTINUATION,
        user_instruction="继续写这一章",
        request_id="req_7",
        trace_id="trace_7",
        caller_type="user_action",
    )
    runtime.start_session(session.session_id)

    completed = runtime.complete_session(
        session.session_id,
        result_ref="candidate_draft:1",
        warning_codes=["review_failed"],
        partial_success=True,
    )
    job = runtime._ai_job_service.get_job(completed.job_id)

    assert completed.status == AgentSessionStatus.PARTIAL_SUCCESS
    assert completed.result_ref == "candidate_draft:1"
    assert completed.warning_codes == ["review_failed"]
    assert job.status.value == "completed"
    assert job.result_ref == "candidate_draft:1"
    assert job.result_summary["completion_mode"] == "partial_success"


def test_agent_runtime_service_rejects_partial_success_when_all_steps_succeeded_without_warnings(tmp_path) -> None:
    runtime = _build_runtime(tmp_path)
    session = runtime.create_session(
        work_id="work-1",
        chapter_id="chapter-1",
        agent_workflow_type=AgentWorkflowType.CONTINUATION,
        user_instruction="继续写这一章",
        request_id="req_7b",
        trace_id="trace_7b",
        caller_type="user_action",
    )
    runtime.start_session(session.session_id)
    step = runtime.create_step(session.session_id, agent_type="writer", step_type="generate_candidate", action="run_writer")
    runtime._step_repository.save_step(
        runtime.get_step(step.step_id).model_copy(
            update={"status": AgentStepStatus.SUCCEEDED, "finished_at": "2026-05-15T00:00:00Z"}
        )
    )

    with pytest.raises(ValueError, match="partial_success_not_applicable"):
        runtime.complete_session(
            session.session_id,
            result_ref="candidate_draft:partial_should_fail",
            partial_success=True,
        )


def test_agent_runtime_service_allows_partial_success_when_some_steps_failed(tmp_path) -> None:
    runtime = _build_runtime(tmp_path)
    session = runtime.create_session(
        work_id="work-1",
        chapter_id="chapter-1",
        agent_workflow_type=AgentWorkflowType.CONTINUATION,
        user_instruction="继续写这一章",
        request_id="req_7c",
        trace_id="trace_7c",
        caller_type="user_action",
    )
    runtime.start_session(session.session_id)
    succeeded_step = runtime.create_step(
        session.session_id, agent_type="writer", step_type="generate_candidate", action="run_writer"
    )
    failed_step = runtime.create_step(
        session.session_id, agent_type="reviewer", step_type="review_candidate", action="review"
    )
    runtime._step_repository.save_step(
        runtime.get_step(succeeded_step.step_id).model_copy(
            update={"status": AgentStepStatus.SUCCEEDED, "finished_at": "2026-05-15T00:00:00Z"}
        )
    )
    runtime._step_repository.save_step(
        runtime.get_step(failed_step.step_id).model_copy(
            update={
                "status": AgentStepStatus.FAILED,
                "finished_at": "2026-05-15T00:01:00Z",
                "error_code": "review_failed",
                "error_message": "review failed",
            }
        )
    )

    completed = runtime.complete_session(
        session.session_id,
        result_ref="candidate_draft:cd_7c",
        partial_success=True,
    )

    assert completed.status == AgentSessionStatus.PARTIAL_SUCCESS
    assert completed.result_ref == "candidate_draft:cd_7c"


def test_agent_runtime_service_rejects_completed_when_any_step_failed(tmp_path) -> None:
    runtime = _build_runtime(tmp_path)
    session = runtime.create_session(
        work_id="work-1",
        chapter_id="chapter-1",
        agent_workflow_type=AgentWorkflowType.CONTINUATION,
        user_instruction="继续写这一章",
        request_id="req_7d",
        trace_id="trace_7d",
        caller_type="user_action",
    )
    runtime.start_session(session.session_id)
    succeeded_step = runtime.create_step(
        session.session_id, agent_type="writer", step_type="generate_candidate", action="run_writer"
    )
    failed_step = runtime.create_step(
        session.session_id, agent_type="reviewer", step_type="review_candidate", action="review"
    )
    runtime._step_repository.save_step(
        runtime.get_step(succeeded_step.step_id).model_copy(
            update={"status": AgentStepStatus.SUCCEEDED, "finished_at": "2026-05-15T00:00:00Z"}
        )
    )
    runtime._step_repository.save_step(
        runtime.get_step(failed_step.step_id).model_copy(
            update={
                "status": AgentStepStatus.FAILED,
                "finished_at": "2026-05-15T00:01:00Z",
                "error_code": "review_failed",
                "error_message": "review failed",
            }
        )
    )

    with pytest.raises(ValueError, match="session_not_completable"):
        runtime.complete_session(
            session.session_id,
            result_ref="candidate_draft:cd_7d",
        )


def test_agent_runtime_service_allows_completed_when_all_steps_succeeded(tmp_path) -> None:
    runtime = _build_runtime(tmp_path)
    session = runtime.create_session(
        work_id="work-1",
        chapter_id="chapter-1",
        agent_workflow_type=AgentWorkflowType.CONTINUATION,
        user_instruction="继续写这一章",
        request_id="req_7e",
        trace_id="trace_7e",
        caller_type="user_action",
    )
    runtime.start_session(session.session_id)
    step = runtime.create_step(session.session_id, agent_type="writer", step_type="generate_candidate", action="run_writer")
    runtime._step_repository.save_step(
        runtime.get_step(step.step_id).model_copy(
            update={"status": AgentStepStatus.SUCCEEDED, "finished_at": "2026-05-15T00:00:00Z"}
        )
    )

    completed = runtime.complete_session(
        session.session_id,
        result_ref="candidate_draft:cd_7e",
    )

    assert completed.status == AgentSessionStatus.COMPLETED
    assert completed.result_ref == "candidate_draft:cd_7e"


def test_agent_runtime_service_rejects_completed_when_any_step_skipped(tmp_path) -> None:
    runtime = _build_runtime(tmp_path)
    session = runtime.create_session(
        work_id="work-1",
        chapter_id="chapter-1",
        agent_workflow_type=AgentWorkflowType.CONTINUATION,
        user_instruction="继续写这一章",
        request_id="req_7f",
        trace_id="trace_7f",
        caller_type="user_action",
    )
    runtime.start_session(session.session_id)
    succeeded_step = runtime.create_step(
        session.session_id, agent_type="writer", step_type="generate_candidate", action="run_writer"
    )
    skipped_step = runtime.create_step(
        session.session_id, agent_type="reviewer", step_type="review_candidate", action="review"
    )
    runtime._step_repository.save_step(
        runtime.get_step(succeeded_step.step_id).model_copy(
            update={"status": AgentStepStatus.SUCCEEDED, "finished_at": "2026-05-15T00:00:00Z"}
        )
    )
    runtime._step_repository.save_step(
        runtime.get_step(skipped_step.step_id).model_copy(
            update={"status": AgentStepStatus.SKIPPED, "finished_at": "2026-05-15T00:01:00Z", "status_reason": "workflow_skipped"}
        )
    )

    with pytest.raises(ValueError, match="session_not_completable"):
        runtime.complete_session(
            session.session_id,
            result_ref="candidate_draft:cd_7f",
        )


def test_agent_runtime_service_allows_partial_success_when_some_steps_skipped(tmp_path) -> None:
    runtime = _build_runtime(tmp_path)
    session = runtime.create_session(
        work_id="work-1",
        chapter_id="chapter-1",
        agent_workflow_type=AgentWorkflowType.CONTINUATION,
        user_instruction="继续写这一章",
        request_id="req_7g",
        trace_id="trace_7g",
        caller_type="user_action",
    )
    runtime.start_session(session.session_id)
    succeeded_step = runtime.create_step(
        session.session_id, agent_type="writer", step_type="generate_candidate", action="run_writer"
    )
    skipped_step = runtime.create_step(
        session.session_id, agent_type="reviewer", step_type="review_candidate", action="review"
    )
    runtime._step_repository.save_step(
        runtime.get_step(succeeded_step.step_id).model_copy(
            update={"status": AgentStepStatus.SUCCEEDED, "finished_at": "2026-05-15T00:00:00Z"}
        )
    )
    runtime._step_repository.save_step(
        runtime.get_step(skipped_step.step_id).model_copy(
            update={"status": AgentStepStatus.SKIPPED, "finished_at": "2026-05-15T00:01:00Z", "status_reason": "workflow_skipped"}
        )
    )

    completed = runtime.complete_session(
        session.session_id,
        result_ref="candidate_draft:cd_7g",
        partial_success=True,
    )

    assert completed.status == AgentSessionStatus.PARTIAL_SUCCESS
    assert completed.result_ref == "candidate_draft:cd_7g"


def test_agent_runtime_service_rejects_retry_for_cancelled_session(tmp_path) -> None:
    runtime = _build_runtime(tmp_path)
    session = runtime.create_session(
        work_id="work-1",
        chapter_id="chapter-1",
        agent_workflow_type=AgentWorkflowType.CONTINUATION,
        user_instruction="继续写这一章",
        request_id="req_8",
        trace_id="trace_8",
        caller_type="user_action",
    )
    runtime.cancel_session(session.session_id, reason="user_cancelled")

    with pytest.raises(ValueError, match="session_not_retryable"):
        runtime.retry_session(session.session_id)


def test_agent_runtime_service_maps_complete_step_observation_to_succeeded(tmp_path) -> None:
    runtime = _build_runtime(tmp_path)
    session = runtime.create_session(
        work_id="work-1",
        chapter_id="chapter-1",
        agent_workflow_type=AgentWorkflowType.CONTINUATION,
        user_instruction="继续写这一章",
        request_id="req_9",
        trace_id="trace_9",
        caller_type="user_action",
    )
    runtime.start_session(session.session_id)
    step = runtime.create_step(session.session_id, agent_type="writer", step_type="generate_candidate", action="run_writer")

    observation = AgentObservation(
        observation_id="obs_complete",
        session_id=session.session_id,
        step_id=step.step_id,
        observation_type=AgentObservationType.TOOL_RESULT,
        source_type="tool",
        status="success",
        safe_message="候选稿已生成",
        decision="complete_step",
        trace_id=session.trace_id,
        request_id="req_9b",
    )
    runtime.record_observation(step.step_id, observation)

    refreshed_session = runtime.get_session(session.session_id)
    refreshed_step = runtime.get_step(step.step_id)
    assert refreshed_session.status == AgentSessionStatus.RUNNING
    assert refreshed_step.status == AgentStepStatus.SUCCEEDED


def test_agent_runtime_service_maps_fail_step_observation_to_failed(tmp_path) -> None:
    runtime = _build_runtime(tmp_path)
    session = runtime.create_session(
        work_id="work-1",
        chapter_id="chapter-1",
        agent_workflow_type=AgentWorkflowType.CONTINUATION,
        user_instruction="继续写这一章",
        request_id="req_10",
        trace_id="trace_10",
        caller_type="user_action",
    )
    runtime.start_session(session.session_id)
    step = runtime.create_step(session.session_id, agent_type="writer", step_type="generate_candidate", action="run_writer")

    observation = AgentObservation(
        observation_id="obs_fail",
        session_id=session.session_id,
        step_id=step.step_id,
        observation_type=AgentObservationType.ERROR,
        source_type="tool",
        status="failed",
        safe_message="模型调用失败",
        decision="fail_step",
        error_code="provider_timeout",
        trace_id=session.trace_id,
        request_id="req_10b",
    )
    runtime.record_observation(step.step_id, observation)

    refreshed_step = runtime.get_step(step.step_id)
    assert refreshed_step.status == AgentStepStatus.FAILED
    assert refreshed_step.error_code == "provider_timeout"


def test_agent_runtime_service_retry_step_reuses_same_step_and_increments_attempt(tmp_path) -> None:
    runtime = _build_runtime(tmp_path)
    session = runtime.create_session(
        work_id="work-1",
        chapter_id="chapter-1",
        agent_workflow_type=AgentWorkflowType.CONTINUATION,
        user_instruction="继续写这一章",
        request_id="req_11",
        trace_id="trace_11",
        caller_type="user_action",
    )
    runtime.start_session(session.session_id)
    step = runtime.create_step(session.session_id, agent_type="writer", step_type="generate_candidate", action="run_writer")
    failed_observation = AgentObservation(
        observation_id="obs_retry_source",
        session_id=session.session_id,
        step_id=step.step_id,
        observation_type=AgentObservationType.ERROR,
        source_type="tool",
        status="failed",
        safe_message="第一次失败",
        decision="fail_step",
        error_code="provider_timeout",
        trace_id=session.trace_id,
        request_id="req_11b",
    )
    runtime.record_observation(step.step_id, failed_observation)

    retried = runtime.retry_step(step.step_id, request_id="req_11c")

    assert retried.step_id == step.step_id
    assert retried.status == AgentStepStatus.PENDING
    assert retried.attempt_count == 1
    assert retried.request_id == "req_11c"
    assert retried.trace_id == session.trace_id


def test_agent_runtime_service_retry_step_moves_current_observation_to_history(tmp_path) -> None:
    runtime = _build_runtime(tmp_path)
    session = runtime.create_session(
        work_id="work-1",
        chapter_id="chapter-1",
        agent_workflow_type=AgentWorkflowType.CONTINUATION,
        user_instruction="继续写这一章",
        request_id="req_11d",
        trace_id="trace_11d",
        caller_type="user_action",
    )
    runtime.start_session(session.session_id)
    step = runtime.create_step(session.session_id, agent_type="writer", step_type="generate_candidate", action="run_writer")
    runtime.record_observation(
        step.step_id,
        AgentObservation(
            observation_id="obs_retry_hist_source",
            session_id=session.session_id,
            step_id=step.step_id,
            observation_type=AgentObservationType.ERROR,
            source_type="tool",
            status="failed",
            safe_message="第一次失败",
            decision="fail_step",
            error_code="provider_timeout",
            trace_id=session.trace_id,
            request_id="req_11d2",
        ),
    )

    retried = runtime.retry_step(step.step_id, request_id="req_11d3")

    assert retried.status == AgentStepStatus.PENDING
    assert retried.observation_id == ""
    assert retried.prior_observation_refs == ["obs_retry_hist_source"]


def test_agent_runtime_service_retry_step_clears_started_at_for_new_attempt(tmp_path) -> None:
    runtime = _build_runtime(tmp_path)
    session = runtime.create_session(
        work_id="work-1",
        chapter_id="chapter-1",
        agent_workflow_type=AgentWorkflowType.CONTINUATION,
        user_instruction="继续写这一章",
        request_id="req_11e",
        trace_id="trace_11e",
        caller_type="user_action",
    )
    runtime.start_session(session.session_id)
    step = runtime.create_step(session.session_id, agent_type="writer", step_type="generate_candidate", action="run_writer")
    runtime.record_observation(
        step.step_id,
        AgentObservation(
            observation_id="obs_retry_started_at_source",
            session_id=session.session_id,
            step_id=step.step_id,
            observation_type=AgentObservationType.ERROR,
            source_type="tool",
            status="failed",
            safe_message="第一次失败",
            decision="fail_step",
            error_code="provider_timeout",
            trace_id=session.trace_id,
            request_id="req_11e1",
        ),
    )
    failed_step = runtime.get_step(step.step_id)
    runtime._step_repository.save_step(
        failed_step.model_copy(
            update={
                "started_at": "2026-05-15T00:00:00Z",
                "finished_at": "2026-05-15T00:05:00Z",
                "step_phase": PPAOPhase.OBSERVATION,
            }
        )
    )

    retried = runtime.retry_step(step.step_id, request_id="req_11e2")

    assert retried.status == AgentStepStatus.PENDING
    assert retried.started_at == ""
    assert retried.finished_at == ""
    assert retried.step_phase == ""


def test_agent_runtime_service_run_next_step_after_retry_sets_new_started_at(tmp_path) -> None:
    runtime = _build_runtime(tmp_path)
    session = runtime.create_session(
        work_id="work-1",
        chapter_id="chapter-1",
        agent_workflow_type=AgentWorkflowType.CONTINUATION,
        user_instruction="继续写这一章",
        request_id="req_11f",
        trace_id="trace_11f",
        caller_type="user_action",
    )
    runtime.start_session(session.session_id)
    step = runtime.create_step(session.session_id, agent_type="writer", step_type="generate_candidate", action="run_writer")
    runtime.record_observation(
        step.step_id,
        AgentObservation(
            observation_id="obs_retry_started_again_11f",
            session_id=session.session_id,
            step_id=step.step_id,
            observation_type=AgentObservationType.ERROR,
            source_type="tool",
            status="failed",
            safe_message="第一次失败",
            decision="fail_step",
            error_code="provider_timeout",
            trace_id=session.trace_id,
            request_id="req_11f_fail",
        ),
    )
    runtime.retry_step(step.step_id, request_id="req_11f_retry")

    rerun = runtime.run_next_step(session.session_id)

    assert rerun.status == AgentStepStatus.RUNNING
    assert rerun.started_at
    assert rerun.started_at != "2026-05-15T00:00:00Z"
    assert rerun.step_phase == "perception"
    assert rerun.request_id == "req_11f_retry"


def test_agent_runtime_service_run_next_step_moves_to_running_perception(tmp_path) -> None:
    runtime = _build_runtime(tmp_path)
    session = runtime.create_session(
        work_id="work-1",
        chapter_id="chapter-1",
        agent_workflow_type=AgentWorkflowType.CONTINUATION,
        user_instruction="继续写这一章",
        request_id="req_12",
        trace_id="trace_12",
        caller_type="user_action",
    )
    runtime.start_session(session.session_id)
    step = runtime.create_step(session.session_id, agent_type="writer", step_type="generate_candidate", action="run_writer")

    running = runtime.run_next_step(session.session_id)

    refreshed_session = runtime.get_session(session.session_id)
    refreshed_step = runtime.get_step(step.step_id)
    assert running.step_id == step.step_id
    assert refreshed_step.status == AgentStepStatus.RUNNING
    assert refreshed_step.step_phase == "perception"
    assert refreshed_step.status_reason == "step_started"
    assert refreshed_session.current_phase == "perception"


def test_agent_runtime_service_maps_skip_step_observation_to_skipped(tmp_path) -> None:
    runtime = _build_runtime(tmp_path)
    session = runtime.create_session(
        work_id="work-1",
        chapter_id="chapter-1",
        agent_workflow_type=AgentWorkflowType.CONTINUATION,
        user_instruction="继续写这一章",
        request_id="req_13",
        trace_id="trace_13",
        caller_type="user_action",
    )
    runtime.start_session(session.session_id)
    step = runtime.create_step(session.session_id, agent_type="reviewer", step_type="review_candidate", action="review")

    observation = AgentObservation(
        observation_id="obs_skip",
        session_id=session.session_id,
        step_id=step.step_id,
        observation_type=AgentObservationType.SYSTEM_EVENT,
        source_type="system",
        status="success",
        safe_message="当前步骤可跳过",
        decision="skip_step",
        trace_id=session.trace_id,
        request_id="req_13b",
    )
    runtime.record_observation(step.step_id, observation)

    refreshed_step = runtime.get_step(step.step_id)
    assert refreshed_step.status == AgentStepStatus.SKIPPED
    assert refreshed_step.status_reason == "workflow_skipped"


def test_agent_runtime_service_skip_step_records_skip_reason(tmp_path) -> None:
    runtime = _build_runtime(tmp_path)
    session = runtime.create_session(
        work_id="work-1",
        chapter_id="chapter-1",
        agent_workflow_type=AgentWorkflowType.CONTINUATION,
        user_instruction="继续写这一章",
        request_id="req_13c",
        trace_id="trace_13c",
        caller_type="user_action",
    )
    runtime.start_session(session.session_id)
    step = runtime.create_step(session.session_id, agent_type="reviewer", step_type="review_candidate", action="review")

    runtime.record_observation(
        step.step_id,
        AgentObservation(
            observation_id="obs_skip_reason",
            session_id=session.session_id,
            step_id=step.step_id,
            observation_type=AgentObservationType.SYSTEM_EVENT,
            source_type="system",
            status="success",
            safe_message="当前步骤可跳过",
            decision="skip_step",
            trace_id=session.trace_id,
            request_id="req_13c2",
            metadata={"skip_reason": "workflow_skipped"},
        ),
    )

    refreshed_step = runtime.get_step(step.step_id)
    job_step = runtime._ai_job_service.get_job_steps(session.job_id)[0]
    assert refreshed_step.status == AgentStepStatus.SKIPPED
    assert refreshed_step.status_reason == "workflow_skipped"
    assert job_step.status.value == "skipped"
    assert job_step.status_reason == "workflow_skipped"


def test_agent_runtime_service_maps_pause_session_observation_to_paused(tmp_path) -> None:
    runtime = _build_runtime(tmp_path)
    session = runtime.create_session(
        work_id="work-1",
        chapter_id="chapter-1",
        agent_workflow_type=AgentWorkflowType.CONTINUATION,
        user_instruction="继续写这一章",
        request_id="req_14",
        trace_id="trace_14",
        caller_type="user_action",
    )
    runtime.start_session(session.session_id)
    step = runtime.create_step(session.session_id, agent_type="planner", step_type="confirm_plan", action="plan")

    observation = AgentObservation(
        observation_id="obs_pause",
        session_id=session.session_id,
        step_id=step.step_id,
        observation_type=AgentObservationType.SYSTEM_EVENT,
        source_type="system",
        status="success",
        safe_message="暂停会话",
        decision="pause_session",
        trace_id=session.trace_id,
        request_id="req_14b",
    )
    runtime.record_observation(step.step_id, observation)

    refreshed_session = runtime.get_session(session.session_id)
    assert refreshed_session.status == AgentSessionStatus.PAUSED


def test_agent_runtime_service_rejects_retry_step_when_attempt_limit_reached(tmp_path) -> None:
    runtime = _build_runtime(tmp_path)
    session = runtime.create_session(
        work_id="work-1",
        chapter_id="chapter-1",
        agent_workflow_type=AgentWorkflowType.CONTINUATION,
        user_instruction="继续写这一章",
        request_id="req_15",
        trace_id="trace_15",
        caller_type="user_action",
    )
    runtime.start_session(session.session_id)
    step = runtime.create_step(session.session_id, agent_type="writer", step_type="generate_candidate", action="run_writer")
    failed = runtime.get_step(step.step_id).model_copy(update={"status": AgentStepStatus.FAILED, "attempt_count": 3})
    runtime._step_repository.save_step(failed)

    with pytest.raises(ValueError, match="step_attempt_limit_reached"):
        runtime.retry_step(step.step_id, request_id="req_15b")


@pytest.mark.parametrize(
    ("step_type", "action"),
    [
        ("formal_write", "formal_chapter_write"),
        ("apply_candidate", "apply_candidate_to_draft"),
        ("memory_formalize", "memory_formalize"),
    ],
)
def test_agent_runtime_service_rejects_retry_for_formal_or_apply_steps(
    tmp_path,
    step_type: str,
    action: str,
) -> None:
    runtime = _build_runtime(tmp_path)
    session = runtime.create_session(
        work_id="work-1",
        chapter_id="chapter-1",
        agent_workflow_type=AgentWorkflowType.CONTINUATION,
        user_instruction="继续写这一章",
        request_id="req_15c",
        trace_id="trace_15c",
        caller_type="user_action",
    )
    runtime.start_session(session.session_id)
    step = runtime.create_step(session.session_id, agent_type="writer", step_type=step_type, action=action)
    failed_step = runtime.get_step(step.step_id).model_copy(update={"status": AgentStepStatus.FAILED})
    runtime._step_repository.save_step(failed_step)

    with pytest.raises(ValueError, match="step_retry_forbidden"):
        runtime.retry_step(step.step_id, request_id="req_15d")


def test_agent_runtime_service_cancel_session_marks_open_steps_cancelled(tmp_path) -> None:
    runtime = _build_runtime(tmp_path)
    session = runtime.create_session(
        work_id="work-1",
        chapter_id="chapter-1",
        agent_workflow_type=AgentWorkflowType.CONTINUATION,
        user_instruction="继续写这一章",
        request_id="req_16",
        trace_id="trace_16",
        caller_type="user_action",
    )
    runtime.start_session(session.session_id)
    pending_step = runtime.create_step(session.session_id, agent_type="writer", step_type="pending_step", action="run_writer")
    waiting_observation_step = runtime.create_step(
        session.session_id, agent_type="writer", step_type="waiting_obs_step", action="run_writer"
    )
    waiting_user_step = runtime.create_step(session.session_id, agent_type="planner", step_type="waiting_user_step", action="plan")
    runtime.run_next_step(session.session_id)
    runtime.record_observation(
        waiting_user_step.step_id,
        AgentObservation(
            observation_id="obs_wait_cancel",
            session_id=session.session_id,
            step_id=waiting_user_step.step_id,
            observation_type=AgentObservationType.USER_DECISION,
            source_type="user",
            status="success",
            safe_message="等待用户",
            decision="wait_for_user",
            trace_id=session.trace_id,
            request_id="req_16b",
        ),
    )

    cancelled = runtime.cancel_session(session.session_id, reason="user_cancelled")

    refreshed_pending = runtime.get_step(pending_step.step_id)
    refreshed_waiting_obs = runtime.get_step(waiting_observation_step.step_id)
    refreshed_waiting_user = runtime.get_step(waiting_user_step.step_id)
    assert cancelled.status == AgentSessionStatus.CANCELLED
    assert cancelled.cancelling_at
    assert cancelled.cancelled_at
    assert refreshed_pending.status == AgentStepStatus.CANCELLED
    assert refreshed_waiting_obs.status == AgentStepStatus.CANCELLED
    assert refreshed_waiting_user.status == AgentStepStatus.CANCELLED


def test_agent_runtime_service_cancel_session_marks_job_steps_failed_with_step_cancelled(tmp_path) -> None:
    runtime = _build_runtime(tmp_path)
    session = runtime.create_session(
        work_id="work-1",
        chapter_id="chapter-1",
        agent_workflow_type=AgentWorkflowType.CONTINUATION,
        user_instruction="继续写这一章",
        request_id="req_16b2",
        trace_id="trace_16b2",
        caller_type="user_action",
    )
    runtime.start_session(session.session_id)
    step = runtime.create_step(session.session_id, agent_type="writer", step_type="generate_candidate", action="run_writer")
    runtime.run_next_step(session.session_id)

    runtime.cancel_session(session.session_id, reason="user_cancelled")

    job_step = next(
        item
        for item in runtime._ai_job_service.get_job_steps(session.job_id)
        if item.step_id == runtime.get_step(step.step_id).job_step_id
    )
    assert job_step.status.value == "failed"
    assert job_step.error_code == "step_cancelled"


def test_agent_runtime_service_cancel_session_marks_waiting_observation_job_step_failed(tmp_path) -> None:
    runtime = _build_runtime(tmp_path)
    session = runtime.create_session(
        work_id="work-1",
        chapter_id="chapter-1",
        agent_workflow_type=AgentWorkflowType.CONTINUATION,
        user_instruction="继续写这一章",
        request_id="req_16b3",
        trace_id="trace_16b3",
        caller_type="user_action",
    )
    runtime.start_session(session.session_id)
    first_step = runtime.create_step(session.session_id, agent_type="writer", step_type="step1", action="run_writer")
    second_step = runtime.create_step(session.session_id, agent_type="writer", step_type="step2", action="run_writer")
    runtime.run_next_step(session.session_id)

    runtime.cancel_session(session.session_id, reason="user_cancelled")

    job_step = next(
        item
        for item in runtime._ai_job_service.get_job_steps(session.job_id)
        if item.step_id == runtime.get_step(second_step.step_id).job_step_id
    )
    assert runtime.get_step(second_step.step_id).status == AgentStepStatus.CANCELLED
    assert job_step.status.value == "failed"
    assert job_step.error_code == "step_cancelled"


def test_agent_runtime_service_fail_session_marks_waiting_user_job_step_failed(tmp_path) -> None:
    runtime = _build_runtime(tmp_path)
    session = runtime.create_session(
        work_id="work-1",
        chapter_id="chapter-1",
        agent_workflow_type=AgentWorkflowType.CONTINUATION,
        user_instruction="继续写这一章",
        request_id="req_20g",
        trace_id="trace_20g",
        caller_type="user_action",
    )
    runtime.start_session(session.session_id)
    step = runtime.create_step(session.session_id, agent_type="planner", step_type="direction_selection", action="wait_direction")
    runtime.record_observation(
        step.step_id,
        AgentObservation(
            observation_id="obs_wait_fail_job_20g",
            session_id=session.session_id,
            step_id=step.step_id,
            observation_type=AgentObservationType.USER_DECISION,
            source_type="user",
            status="success",
            safe_message="等待用户",
            decision="wait_for_user",
            trace_id=session.trace_id,
            request_id="req_20g_wait",
        ),
    )

    runtime.fail_session(session.session_id, error_code="planner_failed", error_message="planner failed")

    job_step = next(
        item
        for item in runtime._ai_job_service.get_job_steps(session.job_id)
        if item.step_id == runtime.get_step(step.step_id).job_step_id
    )
    assert job_step.status.value == "failed"
    assert job_step.error_code == "planner_failed"


def test_agent_runtime_service_cancel_session_clears_current_step_and_phase(tmp_path) -> None:
    runtime = _build_runtime(tmp_path)
    session = runtime.create_session(
        work_id="work-1",
        chapter_id="chapter-1",
        agent_workflow_type=AgentWorkflowType.CONTINUATION,
        user_instruction="继续写这一章",
        request_id="req_16c",
        trace_id="trace_16c",
        caller_type="user_action",
    )
    runtime.start_session(session.session_id)
    step = runtime.create_step(session.session_id, agent_type="writer", step_type="generate_candidate", action="run_writer")
    runtime.run_next_step(session.session_id)

    cancelled = runtime.cancel_session(session.session_id, reason="user_cancelled")

    assert cancelled.current_step_id == ""
    assert cancelled.current_phase == ""


def test_agent_runtime_service_cancel_session_builds_cancelled_result_container(tmp_path) -> None:
    runtime = _build_runtime(tmp_path)
    session = runtime.create_session(
        work_id="work-1",
        chapter_id="chapter-1",
        agent_workflow_type=AgentWorkflowType.CONTINUATION,
        user_instruction="继续写这一章",
        request_id="req_16d",
        trace_id="trace_16d",
        caller_type="user_action",
    )
    runtime.start_session(session.session_id)
    step = runtime.create_step(session.session_id, agent_type="writer", step_type="generate_candidate", action="run_writer")
    runtime.record_observation(
        step.step_id,
        AgentObservation(
            observation_id="obs_cancel_warn_16d",
            session_id=session.session_id,
            step_id=step.step_id,
            observation_type=AgentObservationType.WARNING,
            source_type="validation",
            status="warning",
            safe_message="上下文降级",
            decision="complete_step",
            warning_codes=["context_degraded"],
            trace_id=session.trace_id,
            request_id="req_16d_obs",
        ),
    )

    cancelled = runtime.cancel_session(session.session_id, reason="user_cancelled")

    assert cancelled.result is not None
    assert cancelled.result.status == "cancelled"
    assert cancelled.result.result_refs == []
    assert cancelled.result.warning_codes == ["context_degraded"]
    assert cancelled.result.finished_at


def test_agent_runtime_service_partial_success_requires_result_ref(tmp_path) -> None:
    runtime = _build_runtime(tmp_path)
    session = runtime.create_session(
        work_id="work-1",
        chapter_id="chapter-1",
        agent_workflow_type=AgentWorkflowType.CONTINUATION,
        user_instruction="继续写这一章",
        request_id="req_17",
        trace_id="trace_17",
        caller_type="user_action",
    )
    runtime.start_session(session.session_id)

    with pytest.raises(ValueError, match="partial_success_requires_result_ref"):
        runtime.complete_session(session.session_id, partial_success=True)


def test_agent_runtime_service_builds_agent_run_context_with_safe_refs(tmp_path) -> None:
    runtime = _build_runtime(tmp_path)
    session = runtime.create_session(
        work_id="work-1",
        chapter_id="chapter-1",
        agent_workflow_type=AgentWorkflowType.CONTINUATION,
        user_instruction="继续写这一章",
        request_id="req_18",
        trace_id="trace_18",
        caller_type="user_action",
    )
    step = runtime.create_step(session.session_id, agent_type="writer", step_type="generate_candidate", action="run_writer")

    run_context = runtime.build_run_context(
        session.session_id,
        step_id=step.step_id,
        current_agent_type="writer",
        context_refs=["context_pack:cp_1", "candidate_draft:cd_1"],
        allow_degraded=False,
    )

    assert run_context.session_id == session.session_id
    assert run_context.current_agent_type == "writer"
    assert run_context.step_id == step.step_id
    assert run_context.work_id == "work-1"
    assert run_context.chapter_id == "chapter-1"
    assert run_context.context_refs == ["context_pack:cp_1", "candidate_draft:cd_1"]
    assert run_context.allow_degraded is False
    assert run_context.user_instruction == "继续写这一章"
    assert run_context.job_id == session.job_id
    assert run_context.agent_workflow_type == AgentWorkflowType.CONTINUATION
    assert run_context.current_phase == ""
    assert run_context.caller_type == "user_action"
    assert run_context.warning_codes == []
    assert run_context.resource_scope_refs == ["work:work-1", "chapter:chapter-1"]
    assert run_context.prior_observation_refs == []
    assert run_context.execution_guard_flags == {}


def test_agent_runtime_service_builds_run_context_with_retried_step_request_id(tmp_path) -> None:
    runtime = _build_runtime(tmp_path)
    session = runtime.create_session(
        work_id="work-1",
        chapter_id="chapter-1",
        agent_workflow_type=AgentWorkflowType.CONTINUATION,
        user_instruction="继续写这一章",
        request_id="req_18d",
        trace_id="trace_18d",
        caller_type="user_action",
    )
    runtime.start_session(session.session_id)
    step = runtime.create_step(session.session_id, agent_type="writer", step_type="generate_candidate", action="run_writer")
    runtime.record_observation(
        step.step_id,
        AgentObservation(
            observation_id="obs_retry_run_ctx_18d",
            session_id=session.session_id,
            step_id=step.step_id,
            observation_type=AgentObservationType.ERROR,
            source_type="tool",
            status="failed",
            safe_message="第一次失败",
            decision="fail_step",
            error_code="provider_timeout",
            trace_id=session.trace_id,
            request_id="req_18d_fail",
        ),
    )
    runtime.retry_step(step.step_id, request_id="req_18d_retry")

    run_context = runtime.build_run_context(
        session.session_id,
        step_id=step.step_id,
        current_agent_type="writer",
        context_refs=["context_pack:cp_18d"],
    )

    assert run_context.request_id == "req_18d_retry"
    assert run_context.trace_id == session.trace_id


def test_agent_runtime_service_builds_tool_execution_context_for_agent_calls(tmp_path) -> None:
    runtime = _build_runtime(tmp_path)
    session = runtime.create_session(
        work_id="work-1",
        chapter_id="chapter-1",
        agent_workflow_type=AgentWorkflowType.CONTINUATION,
        user_instruction="继续写这一章",
        request_id="req_18a",
        trace_id="trace_18a",
        caller_type="user_action",
    )
    runtime.start_session(session.session_id)
    step = runtime.create_step(session.session_id, agent_type="writer", step_type="generate_candidate", action="run_writer")
    runtime.run_next_step(session.session_id)

    tool_context = runtime.build_tool_execution_context(
        session.session_id,
        step_id=step.step_id,
        agent_type="writer",
        side_effect_level="read_only",
        resource_scope_refs=["work:work-1", "chapter:chapter-1"],
    )

    assert tool_context.caller_type == "agent"
    assert tool_context.agent_session_id == session.session_id
    assert tool_context.agent_step_id == step.step_id
    assert tool_context.agent_type == "writer"
    assert tool_context.session_status == "running"
    assert tool_context.step_status == "running"
    assert tool_context.resource_scope_refs == ["work:work-1", "chapter:chapter-1"]
    assert tool_context.idempotency_key == f"{step.step_id}:req_18a"


def test_agent_runtime_service_builds_tool_execution_context_with_default_scope_refs(tmp_path) -> None:
    runtime = _build_runtime(tmp_path)
    session = runtime.create_session(
        work_id="work-1",
        chapter_id="chapter-1",
        agent_workflow_type=AgentWorkflowType.CONTINUATION,
        user_instruction="继续写这一章",
        request_id="req_18aa",
        trace_id="trace_18aa",
        caller_type="user_action",
    )
    runtime.start_session(session.session_id)
    step = runtime.create_step(session.session_id, agent_type="writer", step_type="generate_candidate", action="run_writer")
    runtime.run_next_step(session.session_id)

    tool_context = runtime.build_tool_execution_context(
        session.session_id,
        step_id=step.step_id,
        agent_type="writer",
        side_effect_level="read_only",
    )

    assert tool_context.resource_scope_refs == ["work:work-1", "chapter:chapter-1"]


def test_agent_runtime_service_builds_tool_execution_context_with_retried_step_request_id(tmp_path) -> None:
    runtime = _build_runtime(tmp_path)
    session = runtime.create_session(
        work_id="work-1",
        chapter_id="chapter-1",
        agent_workflow_type=AgentWorkflowType.CONTINUATION,
        user_instruction="继续写这一章",
        request_id="req_18c",
        trace_id="trace_18c",
        caller_type="user_action",
    )
    runtime.start_session(session.session_id)
    step = runtime.create_step(session.session_id, agent_type="writer", step_type="generate_candidate", action="run_writer")
    runtime.record_observation(
        step.step_id,
        AgentObservation(
            observation_id="obs_retry_context_18c",
            session_id=session.session_id,
            step_id=step.step_id,
            observation_type=AgentObservationType.ERROR,
            source_type="tool",
            status="failed",
            safe_message="第一次失败",
            decision="fail_step",
            error_code="provider_timeout",
            trace_id=session.trace_id,
            request_id="req_18c_fail",
        ),
    )
    runtime.retry_step(step.step_id, request_id="req_18c_retry")
    runtime.run_next_step(session.session_id)

    tool_context = runtime.build_tool_execution_context(
        session.session_id,
        step_id=step.step_id,
        agent_type="writer",
        side_effect_level="read_only",
        resource_scope_refs=["work:work-1", "chapter:chapter-1"],
    )

    assert tool_context.request_id == "req_18c_retry"
    assert tool_context.trace_id == session.trace_id


def test_agent_runtime_service_continue_observation_advances_to_next_ppao_phase(tmp_path) -> None:
    runtime = _build_runtime(tmp_path)
    session = runtime.create_session(
        work_id="work-1",
        chapter_id="chapter-1",
        agent_workflow_type=AgentWorkflowType.CONTINUATION,
        user_instruction="继续写这一章",
        request_id="req_18b",
        trace_id="trace_18b",
        caller_type="user_action",
    )
    runtime.start_session(session.session_id)
    step = runtime.create_step(session.session_id, agent_type="writer", step_type="generate_candidate", action="run_writer")
    runtime.run_next_step(session.session_id)

    runtime.record_observation(
        step.step_id,
        AgentObservation(
            observation_id="obs_phase_continue",
            session_id=session.session_id,
            step_id=step.step_id,
            observation_type=AgentObservationType.STATE_CHANGE,
            source_type="system",
            status="success",
            safe_message="感知完成",
            decision="continue",
            trace_id=session.trace_id,
            request_id="req_18b2",
        ),
    )

    refreshed_session = runtime.get_session(session.session_id)
    refreshed_step = runtime.get_step(step.step_id)
    assert refreshed_step.status == AgentStepStatus.RUNNING
    assert refreshed_step.step_phase == "planning"
    assert refreshed_step.observation_id == "obs_phase_continue"
    assert refreshed_session.current_phase == "planning"


def test_agent_runtime_service_complete_session_builds_agent_result_container(tmp_path) -> None:
    runtime = _build_runtime(tmp_path)
    session = runtime.create_session(
        work_id="work-1",
        chapter_id="chapter-1",
        agent_workflow_type=AgentWorkflowType.CONTINUATION,
        user_instruction="继续写这一章",
        request_id="req_19",
        trace_id="trace_19",
        caller_type="user_action",
    )
    runtime.start_session(session.session_id)

    completed = runtime.complete_session(
        session.session_id,
        result_ref="candidate_draft:cd_19",
        warning_codes=["context_degraded"],
    )

    assert completed.result is not None
    assert completed.result.status == "success"
    assert len(completed.result.result_refs) == 1
    assert completed.result.result_refs[0].ref_type == "candidate_draft"
    assert completed.result.result_refs[0].ref_id == "candidate_draft:cd_19"
    assert completed.result.result_refs[0].source_agent_type == ""
    assert completed.result.result_refs[0].source_step_id == ""
    assert completed.result.result_refs[0].status == "success"
    assert completed.result.warning_codes == ["context_degraded"]


def test_agent_runtime_service_complete_session_clears_current_step_and_phase(tmp_path) -> None:
    runtime = _build_runtime(tmp_path)
    session = runtime.create_session(
        work_id="work-1",
        chapter_id="chapter-1",
        agent_workflow_type=AgentWorkflowType.CONTINUATION,
        user_instruction="继续写这一章",
        request_id="req_19f",
        trace_id="trace_19f",
        caller_type="user_action",
    )
    runtime.start_session(session.session_id)
    step = runtime.create_step(session.session_id, agent_type="writer", step_type="generate_candidate", action="run_writer")
    runtime.run_next_step(session.session_id)
    runtime._step_repository.save_step(
        runtime.get_step(step.step_id).model_copy(
            update={"status": AgentStepStatus.SUCCEEDED, "finished_at": "2026-05-15T00:00:00Z"}
        )
    )

    completed = runtime.complete_session(
        session.session_id,
        result_ref="candidate_draft:cd_19f",
    )

    assert completed.current_step_id == ""
    assert completed.current_phase == ""


def test_agent_runtime_service_complete_session_clears_non_terminal_status_reason(tmp_path) -> None:
    runtime = _build_runtime(tmp_path)
    session = runtime.create_session(
        work_id="work-1",
        chapter_id="chapter-1",
        agent_workflow_type=AgentWorkflowType.CONTINUATION,
        user_instruction="继续写这一章",
        request_id="req_19g",
        trace_id="trace_19g",
        caller_type="user_action",
    )
    runtime.start_session(session.session_id)
    step = runtime.create_step(session.session_id, agent_type="writer", step_type="generate_candidate", action="run_writer")
    runtime.run_next_step(session.session_id)
    runtime._session_repository.save_session(
        runtime.get_session(session.session_id).model_copy(update={"status_reason": "service_restarted"})
    )
    runtime._step_repository.save_step(
        runtime.get_step(step.step_id).model_copy(
            update={"status": AgentStepStatus.SUCCEEDED, "finished_at": "2026-05-15T00:00:00Z"}
        )
    )

    completed = runtime.complete_session(
        session.session_id,
        result_ref="candidate_draft:cd_19g",
    )

    assert completed.status == AgentSessionStatus.COMPLETED
    assert completed.status_reason == ""


def test_agent_runtime_service_complete_session_builds_agent_result_summary_fields(tmp_path) -> None:
    runtime = _build_runtime(tmp_path)
    session = runtime.create_session(
        work_id="work-1",
        chapter_id="chapter-1",
        agent_workflow_type=AgentWorkflowType.CONTINUATION,
        user_instruction="继续写这一章",
        request_id="req_19b",
        trace_id="trace_19b",
        caller_type="user_action",
    )
    runtime.start_session(session.session_id)
    step = runtime.create_step(session.session_id, agent_type="writer", step_type="generate_candidate", action="run_writer")
    runtime._step_repository.save_step(
        runtime.get_step(step.step_id).model_copy(
            update={"status": AgentStepStatus.SUCCEEDED, "finished_at": "2026-05-15T00:00:00Z"}
        )
    )

    completed = runtime.complete_session(
        session.session_id,
        result_ref="candidate_draft:cd_19b",
        warning_codes=["context_degraded"],
    )

    assert completed.result is not None
    assert completed.result.primary_output_ref == "candidate_draft:cd_19b"
    assert completed.result.primary_output_type == "candidate_draft"
    assert completed.result.total_steps == 1
    assert completed.result.succeeded_steps == 1
    assert completed.result.failed_steps == 0
    assert completed.result.skipped_steps == 0
    assert completed.result.total_elapsed_ms >= 0
    assert completed.result.next_user_action == ""
    assert completed.result.finished_at


def test_agent_runtime_service_complete_session_builds_safe_step_summary(tmp_path) -> None:
    runtime = _build_runtime(tmp_path)
    session = runtime.create_session(
        work_id="work-1",
        chapter_id="chapter-1",
        agent_workflow_type=AgentWorkflowType.CONTINUATION,
        user_instruction="继续写这一章",
        request_id="req_19bb",
        trace_id="trace_19bb",
        caller_type="user_action",
    )
    runtime.start_session(session.session_id)
    step = runtime.create_step(session.session_id, agent_type="writer", step_type="generate_candidate", action="run_writer")
    runtime.run_next_step(session.session_id)
    runtime.record_observation(
        step.step_id,
        AgentObservation(
            observation_id="obs_complete_19bb",
            session_id=session.session_id,
            step_id=step.step_id,
            observation_type=AgentObservationType.TOOL_RESULT,
            source_type="tool",
            status="success",
            safe_message="生成候选稿",
            decision="complete_step",
            trace_id=session.trace_id,
            request_id="req_19bb_obs",
        ),
    )

    completed = runtime.complete_session(session.session_id, result_ref="candidate_draft:cd_19bb")

    assert completed.result is not None
    assert completed.result.step_summary is not None
    assert len(completed.result.step_summary.steps) == 1
    summary_step = completed.result.step_summary.steps[0]
    assert summary_step.step_id == step.step_id
    assert summary_step.agent_type == "writer"
    assert summary_step.action == "run_writer"
    assert summary_step.status == "succeeded"
    assert summary_step.safe_message == "生成候选稿"


def test_agent_runtime_service_complete_session_result_ref_tracks_source_step(tmp_path) -> None:
    runtime = _build_runtime(tmp_path)
    session = runtime.create_session(
        work_id="work-1",
        chapter_id="chapter-1",
        agent_workflow_type=AgentWorkflowType.CONTINUATION,
        user_instruction="继续写这一章",
        request_id="req_19ba",
        trace_id="trace_19ba",
        caller_type="user_action",
    )
    runtime.start_session(session.session_id)
    step = runtime.create_step(session.session_id, agent_type="writer", step_type="generate_candidate", action="run_writer")
    runtime.run_next_step(session.session_id)
    runtime.record_observation(
        step.step_id,
        AgentObservation(
            observation_id="obs_complete_19ba",
            session_id=session.session_id,
            step_id=step.step_id,
            observation_type=AgentObservationType.TOOL_RESULT,
            source_type="tool",
            status="success",
            safe_message="生成候选稿",
            decision="complete_step",
            trace_id=session.trace_id,
            request_id="req_19ba_obs",
        ),
    )

    completed = runtime.complete_session(session.session_id, result_ref="candidate_draft:cd_19ba")

    assert completed.result is not None
    assert completed.result.result_refs[0].source_agent_type == "writer"
    assert completed.result.result_refs[0].source_step_id == step.step_id


def test_agent_runtime_service_complete_session_inherits_session_warning_codes(tmp_path) -> None:
    runtime = _build_runtime(tmp_path)
    session = runtime.create_session(
        work_id="work-1",
        chapter_id="chapter-1",
        agent_workflow_type=AgentWorkflowType.CONTINUATION,
        user_instruction="继续写这一章",
        request_id="req_19d",
        trace_id="trace_19d",
        caller_type="user_action",
    )
    runtime.start_session(session.session_id)
    step = runtime.create_step(session.session_id, agent_type="writer", step_type="generate_candidate", action="run_writer")
    runtime.record_observation(
        step.step_id,
        AgentObservation(
            observation_id="obs_complete_warn_19d",
            session_id=session.session_id,
            step_id=step.step_id,
            observation_type=AgentObservationType.WARNING,
            source_type="validation",
            status="warning",
            safe_message="上下文降级",
            decision="complete_step",
            warning_codes=["context_degraded"],
            trace_id=session.trace_id,
            request_id="req_19d_obs",
        ),
    )

    completed = runtime.complete_session(
        session.session_id,
        result_ref="candidate_draft:cd_19d",
    )

    assert completed.warning_codes == ["context_degraded"]
    assert completed.result is not None
    assert completed.result.warning_codes == ["context_degraded"]


def test_agent_runtime_service_complete_session_merges_session_and_input_warning_codes(tmp_path) -> None:
    runtime = _build_runtime(tmp_path)
    session = runtime.create_session(
        work_id="work-1",
        chapter_id="chapter-1",
        agent_workflow_type=AgentWorkflowType.CONTINUATION,
        user_instruction="继续写这一章",
        request_id="req_19e",
        trace_id="trace_19e",
        caller_type="user_action",
    )
    runtime.start_session(session.session_id)
    step = runtime.create_step(session.session_id, agent_type="writer", step_type="generate_candidate", action="run_writer")
    runtime.record_observation(
        step.step_id,
        AgentObservation(
            observation_id="obs_complete_warn_19e",
            session_id=session.session_id,
            step_id=step.step_id,
            observation_type=AgentObservationType.WARNING,
            source_type="validation",
            status="warning",
            safe_message="上下文降级",
            decision="complete_step",
            warning_codes=["context_degraded"],
            trace_id=session.trace_id,
            request_id="req_19e_obs",
        ),
    )

    completed = runtime.complete_session(
        session.session_id,
        result_ref="candidate_draft:cd_19e",
        warning_codes=["review_failed", "context_degraded"],
    )

    assert completed.warning_codes == ["context_degraded", "review_failed"]
    assert completed.result is not None
    assert completed.result.warning_codes == ["context_degraded", "review_failed"]


def test_agent_runtime_service_partial_success_builds_agent_result_step_counts(tmp_path) -> None:
    runtime = _build_runtime(tmp_path)
    session = runtime.create_session(
        work_id="work-1",
        chapter_id="chapter-1",
        agent_workflow_type=AgentWorkflowType.CONTINUATION,
        user_instruction="继续写这一章",
        request_id="req_19c",
        trace_id="trace_19c",
        caller_type="user_action",
    )
    runtime.start_session(session.session_id)
    succeeded_step = runtime.create_step(
        session.session_id, agent_type="writer", step_type="generate_candidate", action="run_writer"
    )
    failed_step = runtime.create_step(
        session.session_id, agent_type="reviewer", step_type="review_candidate", action="review"
    )
    runtime._step_repository.save_step(
        runtime.get_step(succeeded_step.step_id).model_copy(
            update={"status": AgentStepStatus.SUCCEEDED, "finished_at": "2026-05-15T00:00:00Z"}
        )
    )
    runtime._step_repository.save_step(
        runtime.get_step(failed_step.step_id).model_copy(
            update={
                "status": AgentStepStatus.FAILED,
                "finished_at": "2026-05-15T00:01:00Z",
                "error_code": "review_failed",
                "error_message": "review failed",
            }
        )
    )

    completed = runtime.complete_session(
        session.session_id,
        result_ref="candidate_draft:cd_19c",
        partial_success=True,
    )

    assert completed.result is not None
    assert completed.result.status == "partial_success"
    assert completed.result.primary_output_ref == "candidate_draft:cd_19c"
    assert completed.result.primary_output_type == "candidate_draft"
    assert completed.result.total_steps == 2
    assert completed.result.succeeded_steps == 1
    assert completed.result.failed_steps == 1
    assert completed.result.skipped_steps == 0


def test_agent_runtime_service_partial_success_clears_non_terminal_status_reason(tmp_path) -> None:
    runtime = _build_runtime(tmp_path)
    session = runtime.create_session(
        work_id="work-1",
        chapter_id="chapter-1",
        agent_workflow_type=AgentWorkflowType.CONTINUATION,
        user_instruction="继续写这一章",
        request_id="req_19h",
        trace_id="trace_19h",
        caller_type="user_action",
    )
    runtime.start_session(session.session_id)
    succeeded_step = runtime.create_step(
        session.session_id, agent_type="writer", step_type="generate_candidate", action="run_writer"
    )
    failed_step = runtime.create_step(
        session.session_id, agent_type="reviewer", step_type="review_candidate", action="review"
    )
    runtime._session_repository.save_session(
        runtime.get_session(session.session_id).model_copy(update={"status_reason": "service_restarted"})
    )
    runtime._step_repository.save_step(
        runtime.get_step(succeeded_step.step_id).model_copy(
            update={"status": AgentStepStatus.SUCCEEDED, "finished_at": "2026-05-15T00:00:00Z"}
        )
    )
    runtime._step_repository.save_step(
        runtime.get_step(failed_step.step_id).model_copy(
            update={
                "status": AgentStepStatus.FAILED,
                "finished_at": "2026-05-15T00:01:00Z",
                "error_code": "review_failed",
                "error_message": "review failed",
            }
        )
    )

    completed = runtime.complete_session(
        session.session_id,
        result_ref="candidate_draft:cd_19h",
        partial_success=True,
    )

    assert completed.status == AgentSessionStatus.PARTIAL_SUCCESS
    assert completed.status_reason == ""


def test_agent_runtime_service_partial_success_step_summary_records_failed_step_error(tmp_path) -> None:
    runtime = _build_runtime(tmp_path)
    session = runtime.create_session(
        work_id="work-1",
        chapter_id="chapter-1",
        agent_workflow_type=AgentWorkflowType.CONTINUATION,
        user_instruction="继续写这一章",
        request_id="req_19ha",
        trace_id="trace_19ha",
        caller_type="user_action",
    )
    runtime.start_session(session.session_id)
    succeeded_step = runtime.create_step(
        session.session_id, agent_type="writer", step_type="generate_candidate", action="run_writer"
    )
    failed_step = runtime.create_step(
        session.session_id, agent_type="reviewer", step_type="review_candidate", action="review"
    )
    runtime._step_repository.save_step(
        runtime.get_step(succeeded_step.step_id).model_copy(
            update={"status": AgentStepStatus.SUCCEEDED, "finished_at": "2026-05-15T00:00:00Z"}
        )
    )
    runtime._step_repository.save_step(
        runtime.get_step(failed_step.step_id).model_copy(
            update={
                "status": AgentStepStatus.FAILED,
                "finished_at": "2026-05-15T00:01:00Z",
                "error_code": "review_failed",
                "error_message": "review failed",
                "status_reason": "review_failed",
            }
        )
    )

    completed = runtime.complete_session(
        session.session_id,
        result_ref="candidate_draft:cd_19ha",
        partial_success=True,
    )

    assert completed.result is not None
    assert completed.result.step_summary is not None
    failed_summary = next(item for item in completed.result.step_summary.steps if item.step_id == failed_step.step_id)
    assert failed_summary.status == "failed"
    assert failed_summary.error_code == "review_failed"
    assert failed_summary.error_message == "review failed"


def test_agent_runtime_service_fail_session_builds_failed_agent_result(tmp_path) -> None:
    runtime = _build_runtime(tmp_path)
    session = runtime.create_session(
        work_id="work-1",
        chapter_id="chapter-1",
        agent_workflow_type=AgentWorkflowType.CONTINUATION,
        user_instruction="继续写这一章",
        request_id="req_20",
        trace_id="trace_20",
        caller_type="user_action",
    )
    runtime.start_session(session.session_id)

    failed = runtime.fail_session(session.session_id, error_code="writer_failed", error_message="writer failed")

    assert failed.result is not None
    assert failed.result.status == "failed"
    assert failed.result.error_code == "writer_failed"
    assert failed.result.result_refs == []


def test_agent_runtime_service_fail_session_clears_current_step_and_phase(tmp_path) -> None:
    runtime = _build_runtime(tmp_path)
    session = runtime.create_session(
        work_id="work-1",
        chapter_id="chapter-1",
        agent_workflow_type=AgentWorkflowType.CONTINUATION,
        user_instruction="继续写这一章",
        request_id="req_20d",
        trace_id="trace_20d",
        caller_type="user_action",
    )
    runtime.start_session(session.session_id)
    step = runtime.create_step(session.session_id, agent_type="writer", step_type="generate_candidate", action="run_writer")
    runtime.run_next_step(session.session_id)

    failed = runtime.fail_session(session.session_id, error_code="writer_failed", error_message="writer failed")

    assert failed.current_step_id == ""
    assert failed.current_phase == ""



def test_agent_runtime_service_fail_session_builds_failed_result_summary_fields(tmp_path) -> None:
    runtime = _build_runtime(tmp_path)
    session = runtime.create_session(
        work_id="work-1",
        chapter_id="chapter-1",
        agent_workflow_type=AgentWorkflowType.CONTINUATION,
        user_instruction="继续写这一章",
        request_id="req_20a",
        trace_id="trace_20a",
        caller_type="user_action",
    )
    runtime.start_session(session.session_id)
    step = runtime.create_step(session.session_id, agent_type="writer", step_type="generate_candidate", action="run_writer")
    runtime.run_next_step(session.session_id)

    failed = runtime.fail_session(session.session_id, error_code="writer_failed", error_message="writer failed")

    assert failed.result is not None
    assert failed.result.error_code == "writer_failed"
    assert failed.result.error_message == "writer failed"
    assert failed.result.total_steps == 1
    assert failed.result.succeeded_steps == 0
    assert failed.result.failed_steps == 1
    assert failed.result.skipped_steps == 0
    assert failed.result.finished_at


def test_agent_runtime_service_retry_step_records_new_ai_job_attempt(tmp_path) -> None:
    runtime = _build_runtime(tmp_path)
    session = runtime.create_session(
        work_id="work-1",
        chapter_id="chapter-1",
        agent_workflow_type=AgentWorkflowType.CONTINUATION,
        user_instruction="继续写这一章",
        request_id="req_19x",
        trace_id="trace_19x",
        caller_type="user_action",
    )
    runtime.start_session(session.session_id)
    step = runtime.create_step(session.session_id, agent_type="writer", step_type="generate_candidate", action="run_writer")
    runtime.run_next_step(session.session_id)
    runtime.record_observation(
        step.step_id,
        AgentObservation(
            observation_id="obs_19x_fail",
            session_id=session.session_id,
            step_id=step.step_id,
            observation_type=AgentObservationType.ERROR,
            source_type="tool",
            status="failed",
            safe_message="第一次失败",
            decision="fail_step",
            error_code="provider_timeout",
            trace_id=session.trace_id,
            request_id="req_19x_fail",
        ),
    )
    runtime.retry_step(step.step_id, request_id="req_19x_retry")
    runtime.run_next_step(session.session_id)

    attempts = runtime._ai_job_service.list_attempts(step.job_step_id)
    assert len(attempts) == 2
    assert attempts[0].status.value == "failed"
    assert attempts[0].error_code == "provider_timeout"
    assert attempts[1].status.value == "running"
    assert attempts[1].request_id == "req_19x_retry"


def test_agent_runtime_service_complete_step_finishes_ai_job_attempt_and_clears_metadata(tmp_path) -> None:
    runtime = _build_runtime(tmp_path)
    session = runtime.create_session(
        work_id="work-1",
        chapter_id="chapter-1",
        agent_workflow_type=AgentWorkflowType.CONTINUATION,
        user_instruction="继续写这一章",
        request_id="req_19y",
        trace_id="trace_19y",
        caller_type="user_action",
    )
    runtime.start_session(session.session_id)
    step = runtime.create_step(session.session_id, agent_type="writer", step_type="generate_candidate", action="run_writer")
    runtime.run_next_step(session.session_id)

    runtime.record_observation(
        step.step_id,
        AgentObservation(
            observation_id="obs_19y_complete",
            session_id=session.session_id,
            step_id=step.step_id,
            observation_type=AgentObservationType.TOOL_RESULT,
            source_type="tool",
            status="success",
            safe_message="生成完成",
            decision="complete_step",
            trace_id=session.trace_id,
            request_id="req_19y_obs",
        ),
    )

    refreshed_step = runtime.get_step(step.step_id)
    attempts = runtime._ai_job_service.list_attempts(step.job_step_id)
    assert refreshed_step.metadata.get("current_job_attempt_id") is None
    assert attempts[0].status.value == "completed"
    assert attempts[0].finished_at


def test_agent_runtime_service_skip_step_ignores_ai_job_attempt_and_clears_metadata(tmp_path) -> None:
    runtime = _build_runtime(tmp_path)
    session = runtime.create_session(
        work_id="work-1",
        chapter_id="chapter-1",
        agent_workflow_type=AgentWorkflowType.CONTINUATION,
        user_instruction="继续写这一章",
        request_id="req_19z",
        trace_id="trace_19z",
        caller_type="user_action",
    )
    runtime.start_session(session.session_id)
    step = runtime.create_step(session.session_id, agent_type="reviewer", step_type="review_candidate", action="review")
    runtime.run_next_step(session.session_id)

    runtime.record_observation(
        step.step_id,
        AgentObservation(
            observation_id="obs_19z_skip",
            session_id=session.session_id,
            step_id=step.step_id,
            observation_type=AgentObservationType.SYSTEM_EVENT,
            source_type="system",
            status="success",
            safe_message="当前步骤跳过",
            decision="skip_step",
            trace_id=session.trace_id,
            request_id="req_19z_obs",
            metadata={"skip_reason": "workflow_skipped"},
        ),
    )

    refreshed_step = runtime.get_step(step.step_id)
    attempts = runtime._ai_job_service.list_attempts(step.job_step_id)
    assert refreshed_step.metadata.get("current_job_attempt_id") is None
    assert attempts[0].status.value == "ignored"
    assert attempts[0].retry_reason == "workflow_skipped"


def test_agent_runtime_service_fail_session_inherits_session_warning_codes(tmp_path) -> None:
    runtime = _build_runtime(tmp_path)
    session = runtime.create_session(
        work_id="work-1",
        chapter_id="chapter-1",
        agent_workflow_type=AgentWorkflowType.CONTINUATION,
        user_instruction="继续写这一章",
        request_id="req_20e",
        trace_id="trace_20e",
        caller_type="user_action",
    )
    runtime.start_session(session.session_id)
    step = runtime.create_step(session.session_id, agent_type="writer", step_type="generate_candidate", action="run_writer")
    runtime.record_observation(
        step.step_id,
        AgentObservation(
            observation_id="obs_fail_warn_20e",
            session_id=session.session_id,
            step_id=step.step_id,
            observation_type=AgentObservationType.WARNING,
            source_type="validation",
            status="warning",
            safe_message="上下文降级",
            decision="fail_step",
            warning_codes=["context_degraded"],
            trace_id=session.trace_id,
            request_id="req_20e_obs",
        ),
    )

    failed = runtime.fail_session(session.session_id, error_code="writer_failed", error_message="writer failed")

    assert failed.warning_codes == ["context_degraded"]
    assert failed.result is not None
    assert failed.result.warning_codes == ["context_degraded"]



def test_agent_runtime_service_fail_session_marks_running_step_failed(tmp_path) -> None:
    runtime = _build_runtime(tmp_path)
    session = runtime.create_session(
        work_id="work-1",
        chapter_id="chapter-1",
        agent_workflow_type=AgentWorkflowType.CONTINUATION,
        user_instruction="继续写这一章",
        request_id="req_20b",
        trace_id="trace_20b",
        caller_type="user_action",
    )
    runtime.start_session(session.session_id)
    step = runtime.create_step(session.session_id, agent_type="writer", step_type="generate_candidate", action="run_writer")
    runtime.run_next_step(session.session_id)

    failed = runtime.fail_session(session.session_id, error_code="writer_failed", error_message="writer failed")

    refreshed_step = runtime.get_step(step.step_id)
    assert failed.status == AgentSessionStatus.FAILED
    assert refreshed_step.status == AgentStepStatus.FAILED
    assert refreshed_step.error_code == "writer_failed"
    assert refreshed_step.status_reason == "session_failed"


def test_agent_runtime_service_fail_session_marks_waiting_user_step_failed(tmp_path) -> None:
    runtime = _build_runtime(tmp_path)
    session = runtime.create_session(
        work_id="work-1",
        chapter_id="chapter-1",
        agent_workflow_type=AgentWorkflowType.CONTINUATION,
        user_instruction="继续写这一章",
        request_id="req_20c",
        trace_id="trace_20c",
        caller_type="user_action",
    )
    runtime.start_session(session.session_id)
    step = runtime.create_step(session.session_id, agent_type="planner", step_type="direction_selection", action="wait_direction")
    runtime.record_observation(
        step.step_id,
        AgentObservation(
            observation_id="obs_wait_fail_20c",
            session_id=session.session_id,
            step_id=step.step_id,
            observation_type=AgentObservationType.USER_DECISION,
            source_type="user",
            status="success",
            safe_message="等待用户",
            decision="wait_for_user",
            trace_id=session.trace_id,
            request_id="req_20c_wait",
        ),
    )

    failed = runtime.fail_session(session.session_id, error_code="planner_failed", error_message="planner failed")

    refreshed_step = runtime.get_step(step.step_id)
    assert failed.status == AgentSessionStatus.FAILED
    assert refreshed_step.status == AgentStepStatus.FAILED
    assert refreshed_step.error_code == "planner_failed"
    assert refreshed_step.status_reason == "session_failed"


def test_agent_runtime_service_fail_session_clears_non_failed_status_reason(tmp_path) -> None:
    runtime = _build_runtime(tmp_path)
    session = runtime.create_session(
        work_id="work-1",
        chapter_id="chapter-1",
        agent_workflow_type=AgentWorkflowType.CONTINUATION,
        user_instruction="继续写这一章",
        request_id="req_20f",
        trace_id="trace_20f",
        caller_type="user_action",
    )
    runtime.start_session(session.session_id)
    runtime.pause_session(session.session_id, reason="pause_requested")

    failed = runtime.fail_session(session.session_id, error_code="writer_failed", error_message="writer failed")

    assert failed.status == AgentSessionStatus.FAILED
    assert failed.status_reason == ""


def test_agent_runtime_service_execute_tool_action_records_success_observation(tmp_path) -> None:
    runtime = _build_runtime(tmp_path)
    observed_waiting_at: str = ""
    observed_status: AgentStepStatus | None = None
    observed_phase: str = ""
    session = runtime.create_session(
        work_id="work-1",
        chapter_id="chapter-1",
        agent_workflow_type=AgentWorkflowType.CONTINUATION,
        user_instruction="继续写这一章",
        request_id="req_21",
        trace_id="trace_21",
        caller_type="user_action",
    )
    runtime.start_session(session.session_id)
    step = runtime.create_step(session.session_id, agent_type="writer", step_type="read_context", action="call_tool")

    def _read_tool(payload):
        nonlocal observed_waiting_at, observed_status, observed_phase
        current_step = runtime.get_step(step.step_id)
        observed_waiting_at = current_step.waiting_at
        observed_status = current_step.status
        observed_phase = current_step.step_phase
        return {"result_ref": "memory_context:mc_1"}

    runtime._tool_facade.register_tool(
        ToolDefinition(
            tool_name="agent_read_tool",
            allowed_callers={"agent"},
            side_effect_level="read_only",
            enabled=True,
        ),
        _read_tool,
    )
    runtime.run_next_step(session.session_id)
    runtime.record_observation(
        step.step_id,
        AgentObservation(
            observation_id="obs_to_planning",
            session_id=session.session_id,
            step_id=step.step_id,
            observation_type=AgentObservationType.STATE_CHANGE,
            source_type="system",
            status="success",
            safe_message="进入 planning",
            decision="continue",
            trace_id=session.trace_id,
            request_id="req_21p",
        ),
    )
    runtime.record_observation(
        step.step_id,
        AgentObservation(
            observation_id="obs_to_action",
            session_id=session.session_id,
            step_id=step.step_id,
            observation_type=AgentObservationType.STATE_CHANGE,
            source_type="system",
            status="success",
            safe_message="进入 action",
            decision="continue",
            trace_id=session.trace_id,
            request_id="req_21a",
        ),
    )

    observation = runtime.execute_tool_action(
        session.session_id,
        step_id=step.step_id,
        agent_type="writer",
        tool_name="agent_read_tool",
        payload={"query": "memory"},
        side_effect_level="read_only",
        resource_scope_refs=["work:work-1"],
    )

    saved_step = runtime.get_step(step.step_id)
    assert observation.observation_type == AgentObservationType.TOOL_RESULT
    assert observation.status == "success"
    assert observation.decision == "continue"
    assert observation.source_tool_call_id
    assert observation.metadata["tool_name"] == "agent_read_tool"
    assert observation.metadata["result_ref"] == "memory_context:mc_1"
    assert observed_status == AgentStepStatus.WAITING_OBSERVATION
    assert observed_phase == "observation"
    assert observed_waiting_at
    assert saved_step.status == AgentStepStatus.RUNNING
    assert saved_step.step_phase == "perception"
    assert saved_step.waiting_at == ""
    assert len(saved_step.tool_calls) == 1
    assert saved_step.tool_calls[0].tool_call_id == observation.source_tool_call_id
    assert saved_step.tool_calls[0].tool_name == "agent_read_tool"
    assert saved_step.output_refs == ["memory_context:mc_1"]
    assert saved_step.observation_id == observation.observation_id


def test_agent_runtime_service_execute_tool_action_after_retry_uses_retried_request_id(tmp_path) -> None:
    runtime = _build_runtime(tmp_path)
    runtime._tool_facade.register_tool(
        ToolDefinition(
            tool_name="agent_read_tool",
            allowed_callers={"agent"},
            side_effect_level="read_only",
            enabled=True,
        ),
        lambda payload: {"result_ref": "memory_context:mc_retry"},
    )
    session = runtime.create_session(
        work_id="work-1",
        chapter_id="chapter-1",
        agent_workflow_type=AgentWorkflowType.CONTINUATION,
        user_instruction="继续写这一章",
        request_id="req_21b",
        trace_id="trace_21b",
        caller_type="user_action",
    )
    runtime.start_session(session.session_id)
    step = runtime.create_step(session.session_id, agent_type="writer", step_type="read_context", action="call_tool")
    runtime.record_observation(
        step.step_id,
        AgentObservation(
            observation_id="obs_retry_source_21b",
            session_id=session.session_id,
            step_id=step.step_id,
            observation_type=AgentObservationType.ERROR,
            source_type="tool",
            status="failed",
            safe_message="第一次失败",
            decision="fail_step",
            error_code="provider_timeout",
            trace_id=session.trace_id,
            request_id="req_21b_fail",
        ),
    )
    runtime.retry_step(step.step_id, request_id="req_21b_retry")
    runtime.run_next_step(session.session_id)
    runtime.record_observation(
        step.step_id,
        AgentObservation(
            observation_id="obs_retry_to_planning_21b",
            session_id=session.session_id,
            step_id=step.step_id,
            observation_type=AgentObservationType.STATE_CHANGE,
            source_type="system",
            status="success",
            safe_message="进入 planning",
            decision="continue",
            trace_id=session.trace_id,
            request_id="req_21b_plan",
        ),
    )
    runtime.record_observation(
        step.step_id,
        AgentObservation(
            observation_id="obs_retry_to_action_21b",
            session_id=session.session_id,
            step_id=step.step_id,
            observation_type=AgentObservationType.STATE_CHANGE,
            source_type="system",
            status="success",
            safe_message="进入 action",
            decision="continue",
            trace_id=session.trace_id,
            request_id="req_21b_action",
        ),
    )

    observation = runtime.execute_tool_action(
        session.session_id,
        step_id=step.step_id,
        agent_type="writer",
        tool_name="agent_read_tool",
        payload={"query": "memory"},
        side_effect_level="read_only",
        resource_scope_refs=["work:work-1"],
    )

    assert observation.request_id == "req_21b_retry"
    assert observation.trace_id == session.trace_id


def test_agent_runtime_service_execute_tool_action_maps_retryable_error_to_retry_step(tmp_path) -> None:
    runtime = _build_runtime(tmp_path)

    def _retryable_failure(payload):
        raise RuntimeError("temporary_unavailable")

    runtime._tool_facade.register_tool(
        ToolDefinition(
            tool_name="agent_retry_tool",
            allowed_callers={"agent"},
            side_effect_level="read_only",
            enabled=True,
        ),
        _retryable_failure,
    )
    session = runtime.create_session(
        work_id="work-1",
        chapter_id="chapter-1",
        agent_workflow_type=AgentWorkflowType.CONTINUATION,
        user_instruction="继续写这一章",
        request_id="req_22",
        trace_id="trace_22",
        caller_type="user_action",
    )
    runtime.start_session(session.session_id)
    step = runtime.create_step(session.session_id, agent_type="writer", step_type="read_context", action="call_tool")
    runtime.run_next_step(session.session_id)
    runtime.record_observation(
        step.step_id,
        AgentObservation(
            observation_id="obs_retry_to_planning",
            session_id=session.session_id,
            step_id=step.step_id,
            observation_type=AgentObservationType.STATE_CHANGE,
            source_type="system",
            status="success",
            safe_message="进入 planning",
            decision="continue",
            trace_id=session.trace_id,
            request_id="req_22p",
        ),
    )
    runtime.record_observation(
        step.step_id,
        AgentObservation(
            observation_id="obs_retry_to_action",
            session_id=session.session_id,
            step_id=step.step_id,
            observation_type=AgentObservationType.STATE_CHANGE,
            source_type="system",
            status="success",
            safe_message="进入 action",
            decision="continue",
            trace_id=session.trace_id,
            request_id="req_22a",
        ),
    )

    observation = runtime.execute_tool_action(
        session.session_id,
        step_id=step.step_id,
        agent_type="writer",
        tool_name="agent_retry_tool",
        payload={},
        side_effect_level="read_only",
        resource_scope_refs=["work:work-1"],
    )

    refreshed_step = runtime.get_step(step.step_id)
    assert observation.status == "failed"
    assert observation.decision == "retry_step"
    assert observation.error_code == "temporary_unavailable"
    assert refreshed_step.status == AgentStepStatus.PENDING


def test_agent_runtime_service_execute_tool_action_rejects_user_action_only_tool_for_agent(tmp_path) -> None:
    runtime = _build_runtime(tmp_path)
    session = runtime.create_session(
        work_id="work-1",
        chapter_id="chapter-1",
        agent_workflow_type=AgentWorkflowType.CONTINUATION,
        user_instruction="继续写这一章",
        request_id="req_22b",
        trace_id="trace_22b",
        caller_type="user_action",
    )
    runtime.start_session(session.session_id)
    step = runtime.create_step(session.session_id, agent_type="writer", step_type="generate_candidate", action="run_writer")
    runtime.run_next_step(session.session_id)
    runtime.record_observation(
        step.step_id,
        AgentObservation(
            observation_id="obs_22b_to_planning",
            session_id=session.session_id,
            step_id=step.step_id,
            observation_type=AgentObservationType.STATE_CHANGE,
            source_type="system",
            status="success",
            safe_message="进入 planning",
            decision="continue",
            trace_id=session.trace_id,
            request_id="req_22b_plan",
        ),
    )
    runtime.record_observation(
        step.step_id,
        AgentObservation(
            observation_id="obs_22b_to_action",
            session_id=session.session_id,
            step_id=step.step_id,
            observation_type=AgentObservationType.STATE_CHANGE,
            source_type="system",
            status="success",
            safe_message="进入 action",
            decision="continue",
            trace_id=session.trace_id,
            request_id="req_22b_action",
        ),
    )

    observation = runtime.execute_tool_action(
        session.session_id,
        step_id=step.step_id,
        agent_type="writer",
        tool_name="accept_candidate_draft",
        payload={"candidate_draft_id": "cd_1"},
        side_effect_level="draft_write",
        resource_scope_refs=["work:work-1"],
    )

    refreshed_step = runtime.get_step(step.step_id)
    assert observation.status == "failed"
    assert observation.decision == "fail_step"
    assert observation.error_code == "tool_permission_denied"
    assert refreshed_step.status == AgentStepStatus.FAILED
    assert refreshed_step.error_code == "tool_permission_denied"


def test_agent_runtime_service_validation_result_continue_completes_step(tmp_path) -> None:
    runtime = _build_runtime(tmp_path)
    session = runtime.create_session(
        work_id="work-1",
        chapter_id="chapter-1",
        agent_workflow_type=AgentWorkflowType.CONTINUATION,
        user_instruction="继续写这一章",
        request_id="req_23",
        trace_id="trace_23",
        caller_type="user_action",
    )
    runtime.start_session(session.session_id)
    step = runtime.create_step(session.session_id, agent_type="writer", step_type="validate_result", action="validate")
    runtime._step_repository.save_step(
        runtime.get_step(step.step_id).model_copy(
            update={
                "status": AgentStepStatus.WAITING_OBSERVATION,
                "step_phase": PPAOPhase.OBSERVATION,
                "waiting_at": "2026-05-18T00:00:00Z",
            }
        )
    )

    runtime.record_observation(
        step.step_id,
        AgentObservation(
            observation_id="obs_validation_pass",
            session_id=session.session_id,
            step_id=step.step_id,
            observation_type=AgentObservationType.VALIDATION_RESULT,
            source_type="validator",
            status="success",
            safe_message="校验通过",
            decision="continue",
            trace_id=session.trace_id,
            request_id="req_23b",
        ),
    )

    refreshed_step = runtime.get_step(step.step_id)
    assert refreshed_step.status == AgentStepStatus.SUCCEEDED
    assert refreshed_step.observation_id == "obs_validation_pass"
    assert refreshed_step.waiting_at == ""


def test_agent_runtime_service_validation_retry_is_limited_to_two_schema_retries(tmp_path) -> None:
    runtime = _build_runtime(tmp_path)
    session = runtime.create_session(
        work_id="work-1",
        chapter_id="chapter-1",
        agent_workflow_type=AgentWorkflowType.CONTINUATION,
        user_instruction="继续写这一章",
        request_id="req_24",
        trace_id="trace_24",
        caller_type="user_action",
    )
    runtime.start_session(session.session_id)
    step = runtime.create_step(session.session_id, agent_type="writer", step_type="validate_result", action="validate")
    runtime._step_repository.save_step(
        runtime.get_step(step.step_id).model_copy(
            update={
                "status": AgentStepStatus.WAITING_OBSERVATION,
                "step_phase": PPAOPhase.OBSERVATION,
                "attempt_count": 1,
            }
        )
    )

    runtime.record_observation(
        step.step_id,
        AgentObservation(
            observation_id="obs_validation_retry",
            session_id=session.session_id,
            step_id=step.step_id,
            observation_type=AgentObservationType.VALIDATION_RESULT,
            source_type="validator",
            status="failed",
            safe_message="结构校验失败",
            decision="retry_step",
            error_code="validation_error",
            trace_id=session.trace_id,
            request_id="req_24b",
        ),
    )
    retried_step = runtime.get_step(step.step_id)
    assert retried_step.status == AgentStepStatus.PENDING
    assert retried_step.attempt_count == 2

    runtime._step_repository.save_step(
        retried_step.model_copy(update={"status": AgentStepStatus.WAITING_OBSERVATION, "step_phase": PPAOPhase.OBSERVATION})
    )
    runtime.record_observation(
        step.step_id,
        AgentObservation(
            observation_id="obs_validation_fail",
            session_id=session.session_id,
            step_id=step.step_id,
            observation_type=AgentObservationType.VALIDATION_RESULT,
            source_type="validator",
            status="failed",
            safe_message="结构校验失败",
            decision="retry_step",
            error_code="validation_error",
            trace_id=session.trace_id,
            request_id="req_24c",
        ),
    )

    failed_step = runtime.get_step(step.step_id)
    assert failed_step.status == AgentStepStatus.FAILED
    assert failed_step.error_code == "validation_error"


def test_agent_runtime_service_resume_restores_running_without_resetting_phase(tmp_path) -> None:
    runtime = _build_runtime(tmp_path)
    session = runtime.create_session(
        work_id="work-1",
        chapter_id="chapter-1",
        agent_workflow_type=AgentWorkflowType.CONTINUATION,
        user_instruction="继续写这一章",
        request_id="req_25",
        trace_id="trace_25",
        caller_type="user_action",
    )
    runtime.start_session(session.session_id)
    step = runtime.create_step(session.session_id, agent_type="writer", step_type="generate_candidate", action="run_writer")
    runtime.run_next_step(session.session_id)
    runtime.record_observation(
        step.step_id,
        AgentObservation(
            observation_id="obs_resume_to_planning",
            session_id=session.session_id,
            step_id=step.step_id,
            observation_type=AgentObservationType.STATE_CHANGE,
            source_type="system",
            status="success",
            safe_message="进入 planning",
            decision="continue",
            trace_id=session.trace_id,
            request_id="req_25b",
        ),
    )

    paused = runtime.pause_session(session.session_id)
    resumed = runtime.resume_session(session.session_id)

    assert paused.status == AgentSessionStatus.PAUSED
    assert resumed.status == AgentSessionStatus.RUNNING
    assert resumed.resumed_at
    assert resumed.current_phase == "planning"
    assert runtime.get_step(step.step_id).step_phase == "planning"


def test_agent_runtime_service_mark_late_result_ignored_persists_observation(tmp_path) -> None:
    runtime = _build_runtime(tmp_path)
    session = runtime.create_session(
        work_id="work-1",
        chapter_id="chapter-1",
        agent_workflow_type=AgentWorkflowType.CONTINUATION,
        user_instruction="继续写这一章",
        request_id="req_26",
        trace_id="trace_26",
        caller_type="user_action",
    )
    runtime.start_session(session.session_id)
    step = runtime.create_step(session.session_id, agent_type="writer", step_type="generate_candidate", action="run_writer")
    runtime.cancel_session(session.session_id, reason="user_cancelled")

    observation = runtime.mark_late_result_ignored(
        step.step_id,
        safe_message="迟到结果被忽略",
        tool_call_id="tool_call_26",
    )

    refreshed_step = runtime.get_step(step.step_id)
    observations = runtime._observation_repository.list_observations(step.step_id)
    assert observation.observation_type == AgentObservationType.LATE_RESULT_IGNORED
    assert observation.status == "ignored"
    assert observation.metadata["tool_call_id"] == "tool_call_26"
    assert refreshed_step.status == AgentStepStatus.IGNORED_LATE_RESULT
    assert observations[-1].observation_id == observation.observation_id


def test_agent_runtime_service_paused_session_cannot_start_new_action(tmp_path) -> None:
    runtime = _build_runtime(tmp_path)
    runtime._tool_facade.register_tool(
        ToolDefinition(
            tool_name="agent_read_tool",
            allowed_callers={"agent"},
            side_effect_level="read_only",
            enabled=True,
        ),
        lambda payload: {"result_ref": "memory_context:mc_pause"},
    )
    session = runtime.create_session(
        work_id="work-1",
        chapter_id="chapter-1",
        agent_workflow_type=AgentWorkflowType.CONTINUATION,
        user_instruction="继续写这一章",
        request_id="req_27",
        trace_id="trace_27",
        caller_type="user_action",
    )
    runtime.start_session(session.session_id)
    step = runtime.create_step(session.session_id, agent_type="writer", step_type="read_context", action="call_tool")
    runtime.run_next_step(session.session_id)
    runtime.record_observation(
        step.step_id,
        AgentObservation(
            observation_id="obs_pause_to_planning",
            session_id=session.session_id,
            step_id=step.step_id,
            observation_type=AgentObservationType.STATE_CHANGE,
            source_type="system",
            status="success",
            safe_message="进入 planning",
            decision="continue",
            trace_id=session.trace_id,
            request_id="req_27b",
        ),
    )
    runtime.record_observation(
        step.step_id,
        AgentObservation(
            observation_id="obs_pause_to_action",
            session_id=session.session_id,
            step_id=step.step_id,
            observation_type=AgentObservationType.STATE_CHANGE,
            source_type="system",
            status="success",
            safe_message="进入 action",
            decision="continue",
            trace_id=session.trace_id,
            request_id="req_27c",
        ),
    )
    runtime.pause_session(session.session_id)

    with pytest.raises(ValueError, match="session_not_actionable"):
        runtime.execute_tool_action(
            session.session_id,
            step_id=step.step_id,
            agent_type="writer",
            tool_name="agent_read_tool",
            payload={},
            side_effect_level="read_only",
            resource_scope_refs=["work:work-1"],
        )


def test_agent_runtime_service_warning_observation_propagates_warning_codes(tmp_path) -> None:
    runtime = _build_runtime(tmp_path)
    session = runtime.create_session(
        work_id="work-1",
        chapter_id="chapter-1",
        agent_workflow_type=AgentWorkflowType.CONTINUATION,
        user_instruction="继续写这一章",
        request_id="req_28",
        trace_id="trace_28",
        caller_type="user_action",
    )
    runtime.start_session(session.session_id)
    step = runtime.create_step(session.session_id, agent_type="writer", step_type="read_context", action="read")
    runtime.run_next_step(session.session_id)

    runtime.record_observation(
        step.step_id,
        AgentObservation(
            observation_id="obs_warning_28",
            session_id=session.session_id,
            step_id=step.step_id,
            observation_type=AgentObservationType.WARNING,
            source_type="system",
            status="warning",
            safe_message="上下文已降级",
            decision="continue",
            warning_codes=["context_degraded"],
            trace_id=session.trace_id,
            request_id="req_28b",
        ),
    )

    refreshed_session = runtime.get_session(session.session_id)
    refreshed_step = runtime.get_step(step.step_id)
    assert refreshed_session.warning_codes == ["context_degraded"]
    assert refreshed_step.warning_codes == ["context_degraded"]
    assert refreshed_step.step_phase == "planning"


def test_agent_runtime_service_timeout_retry_is_limited_to_one_provider_retry(tmp_path) -> None:
    runtime = _build_runtime(tmp_path)
    session = runtime.create_session(
        work_id="work-1",
        chapter_id="chapter-1",
        agent_workflow_type=AgentWorkflowType.CONTINUATION,
        user_instruction="继续写这一章",
        request_id="req_29",
        trace_id="trace_29",
        caller_type="user_action",
    )
    runtime.start_session(session.session_id)
    step = runtime.create_step(session.session_id, agent_type="writer", step_type="run_writer", action="call_tool")
    runtime._step_repository.save_step(
        runtime.get_step(step.step_id).model_copy(
            update={"status": AgentStepStatus.WAITING_OBSERVATION, "step_phase": PPAOPhase.OBSERVATION}
        )
    )

    runtime.record_observation(
        step.step_id,
        AgentObservation(
            observation_id="obs_timeout_retry_29",
            session_id=session.session_id,
            step_id=step.step_id,
            observation_type=AgentObservationType.TIMEOUT,
            source_type="tool",
            status="failed",
            safe_message="调用超时",
            decision="retry_step",
            error_code="provider_timeout",
            trace_id=session.trace_id,
            request_id="req_29b",
        ),
    )

    retried = runtime.get_step(step.step_id)
    assert retried.status == AgentStepStatus.PENDING
    assert retried.attempt_count == 1

    runtime._step_repository.save_step(
        retried.model_copy(update={"status": AgentStepStatus.WAITING_OBSERVATION, "step_phase": PPAOPhase.OBSERVATION})
    )
    runtime.record_observation(
        step.step_id,
        AgentObservation(
            observation_id="obs_timeout_fail_29",
            session_id=session.session_id,
            step_id=step.step_id,
            observation_type=AgentObservationType.TIMEOUT,
            source_type="tool",
            status="failed",
            safe_message="再次超时",
            decision="retry_step",
            error_code="provider_timeout",
            trace_id=session.trace_id,
            request_id="req_29c",
        ),
    )

    failed = runtime.get_step(step.step_id)
    assert failed.status == AgentStepStatus.FAILED
    assert failed.error_code == "provider_timeout"


def test_agent_runtime_service_can_pause_running_session_for_service_restart(tmp_path) -> None:
    runtime = _build_runtime(tmp_path)
    session = runtime.create_session(
        work_id="work-1",
        chapter_id="chapter-1",
        agent_workflow_type=AgentWorkflowType.CONTINUATION,
        user_instruction="继续写这一章",
        request_id="req_30",
        trace_id="trace_30",
        caller_type="user_action",
    )
    runtime.start_session(session.session_id)

    paused = runtime.pause_session(session.session_id, reason="service_restarted")

    assert paused.status == AgentSessionStatus.PAUSED
    assert paused.status_reason == "service_restarted"


def test_agent_runtime_service_recover_after_restart_pauses_running_sessions(tmp_path) -> None:
    runtime = _build_runtime(tmp_path)
    running_session = runtime.create_session(
        work_id="work-1",
        chapter_id="chapter-1",
        agent_workflow_type=AgentWorkflowType.CONTINUATION,
        user_instruction="继续写这一章",
        request_id="req_31",
        trace_id="trace_31",
        caller_type="user_action",
    )
    paused_session = runtime.create_session(
        work_id="work-1",
        chapter_id="chapter-2",
        agent_workflow_type=AgentWorkflowType.CONTINUATION,
        user_instruction="继续写另一章",
        request_id="req_32",
        trace_id="trace_32",
        caller_type="user_action",
    )
    runtime.start_session(running_session.session_id)
    runtime.start_session(paused_session.session_id)
    step = runtime.create_step(running_session.session_id, agent_type="writer", step_type="generate_candidate", action="run_writer")
    runtime.run_next_step(running_session.session_id)
    runtime.record_observation(
        step.step_id,
        AgentObservation(
            observation_id="obs_restart_to_planning",
            session_id=running_session.session_id,
            step_id=step.step_id,
            observation_type=AgentObservationType.STATE_CHANGE,
            source_type="system",
            status="success",
            safe_message="进入 planning",
            decision="continue",
            trace_id=running_session.trace_id,
            request_id="req_31b",
        ),
    )
    runtime.pause_session(paused_session.session_id, reason="pause_requested")

    recovered_ids = runtime.recover_after_restart()

    refreshed_running = runtime.get_session(running_session.session_id)
    refreshed_paused = runtime.get_session(paused_session.session_id)
    assert running_session.session_id in recovered_ids
    assert paused_session.session_id not in recovered_ids
    assert refreshed_running.status == AgentSessionStatus.PAUSED
    assert refreshed_running.status_reason == "service_restarted"
    assert refreshed_running.current_phase == "planning"
    assert runtime.get_step(step.step_id).step_phase == "planning"
    assert refreshed_paused.status == AgentSessionStatus.PAUSED


def test_agent_observation_type_includes_model_result_and_error_event() -> None:
    assert AgentObservationType.MODEL_RESULT.value == "model_result"
    assert AgentObservationType.ERROR_EVENT.value == "error_event"


def test_agent_runtime_service_model_result_observation_persists_data_ref(tmp_path) -> None:
    runtime = _build_runtime(tmp_path)
    session = runtime.create_session(
        work_id="work-1",
        chapter_id="chapter-1",
        agent_workflow_type=AgentWorkflowType.CONTINUATION,
        user_instruction="继续写这一章",
        request_id="req_33",
        trace_id="trace_33",
        caller_type="user_action",
    )
    runtime.start_session(session.session_id)
    step = runtime.create_step(session.session_id, agent_type="writer", step_type="generate_candidate", action="run_writer")
    runtime._step_repository.save_step(
        runtime.get_step(step.step_id).model_copy(
            update={"status": AgentStepStatus.WAITING_OBSERVATION, "step_phase": PPAOPhase.OBSERVATION}
        )
    )

    runtime.record_observation(
        step.step_id,
        AgentObservation(
            observation_id="obs_model_result_33",
            session_id=session.session_id,
            step_id=step.step_id,
            observation_type=AgentObservationType.MODEL_RESULT,
            source_type="model",
            status="success",
            safe_message="模型输出已生成",
            data_ref="llm_call_log:llm_33",
            decision="continue",
            trace_id=session.trace_id,
            request_id="req_33b",
        ),
    )

    observations = runtime._observation_repository.list_observations(step.step_id)
    refreshed_step = runtime.get_step(step.step_id)
    assert observations[-1].data_ref == "llm_call_log:llm_33"
    assert refreshed_step.observation_id == "obs_model_result_33"


def test_agent_runtime_service_error_event_fails_step(tmp_path) -> None:
    runtime = _build_runtime(tmp_path)
    session = runtime.create_session(
        work_id="work-1",
        chapter_id="chapter-1",
        agent_workflow_type=AgentWorkflowType.CONTINUATION,
        user_instruction="继续写这一章",
        request_id="req_34",
        trace_id="trace_34",
        caller_type="user_action",
    )
    runtime.start_session(session.session_id)
    step = runtime.create_step(session.session_id, agent_type="writer", step_type="generate_candidate", action="run_writer")
    runtime._step_repository.save_step(
        runtime.get_step(step.step_id).model_copy(
            update={"status": AgentStepStatus.WAITING_OBSERVATION, "step_phase": PPAOPhase.OBSERVATION}
        )
    )

    runtime.record_observation(
        step.step_id,
        AgentObservation(
            observation_id="obs_error_event_34",
            session_id=session.session_id,
            step_id=step.step_id,
            observation_type=AgentObservationType.ERROR_EVENT,
            source_type="system",
            status="failed",
            safe_message="不可恢复错误",
            error_code="observation_unresolved",
            decision="fail_step",
            trace_id=session.trace_id,
            request_id="req_34b",
        ),
    )

    refreshed_step = runtime.get_step(step.step_id)
    assert refreshed_step.status == AgentStepStatus.FAILED
    assert refreshed_step.error_code == "observation_unresolved"


def test_agent_runtime_service_complete_session_requires_all_steps_terminal(tmp_path) -> None:
    runtime = _build_runtime(tmp_path)
    session = runtime.create_session(
        work_id="work-1",
        chapter_id="chapter-1",
        agent_workflow_type=AgentWorkflowType.CONTINUATION,
        user_instruction="继续写这一章",
        request_id="req_35",
        trace_id="trace_35",
        caller_type="user_action",
    )
    runtime.start_session(session.session_id)
    runtime.create_step(session.session_id, agent_type="writer", step_type="generate_candidate", action="run_writer")

    with pytest.raises(ValueError, match="session_has_incomplete_steps"):
        runtime.complete_session(session.session_id, result_ref="candidate_draft:cd_35")


def test_agent_runtime_service_paused_session_records_late_observation_without_advancing(tmp_path) -> None:
    runtime = _build_runtime(tmp_path)
    session = runtime.create_session(
        work_id="work-1",
        chapter_id="chapter-1",
        agent_workflow_type=AgentWorkflowType.CONTINUATION,
        user_instruction="继续写这一章",
        request_id="req_36",
        trace_id="trace_36",
        caller_type="user_action",
    )
    runtime.start_session(session.session_id)
    step = runtime.create_step(session.session_id, agent_type="writer", step_type="generate_candidate", action="run_writer")
    runtime._step_repository.save_step(
        runtime.get_step(step.step_id).model_copy(
            update={"status": AgentStepStatus.WAITING_OBSERVATION, "step_phase": PPAOPhase.OBSERVATION}
        )
    )
    runtime.pause_session(session.session_id, reason="pause_requested")

    runtime.record_observation(
        step.step_id,
        AgentObservation(
            observation_id="obs_paused_late_36",
            session_id=session.session_id,
            step_id=step.step_id,
            observation_type=AgentObservationType.TOOL_RESULT,
            source_type="tool",
            status="success",
            safe_message="候选稿已生成",
            decision="continue",
            data_ref="candidate_draft:cd_36",
            trace_id=session.trace_id,
            request_id="req_36b",
        ),
    )

    refreshed_session = runtime.get_session(session.session_id)
    refreshed_step = runtime.get_step(step.step_id)
    observations = runtime._observation_repository.list_observations(step.step_id)
    assert refreshed_session.status == AgentSessionStatus.PAUSED
    assert refreshed_session.current_phase == "observation"
    assert refreshed_step.status == AgentStepStatus.WAITING_OBSERVATION
    assert refreshed_step.observation_id == "obs_paused_late_36"
    assert observations[-1].data_ref == "candidate_draft:cd_36"


def test_agent_runtime_service_resume_rejects_paused_waiting_user_session(tmp_path) -> None:
    runtime = _build_runtime(tmp_path)
    session = runtime.create_session(
        work_id="work-1",
        chapter_id="chapter-1",
        agent_workflow_type=AgentWorkflowType.CONTINUATION,
        user_instruction="继续写这一章",
        request_id="req_37",
        trace_id="trace_37",
        caller_type="user_action",
    )
    runtime.start_session(session.session_id)
    step = runtime.create_step(session.session_id, agent_type="planner", step_type="direction_selection", action="wait_direction")
    runtime.record_observation(
        step.step_id,
        AgentObservation(
            observation_id="obs_wait_37",
            session_id=session.session_id,
            step_id=step.step_id,
            observation_type=AgentObservationType.USER_DECISION,
            source_type="user",
            status="success",
            safe_message="等待用户选择方向",
            decision="wait_for_user",
            trace_id=session.trace_id,
            request_id="req_37b",
        ),
    )
    paused = runtime.pause_session(session.session_id, reason="pause_requested")

    with pytest.raises(ValueError, match="waiting_user_decision_required"):
        runtime.resume_session(session.session_id)

    refreshed_session = runtime.get_session(session.session_id)
    refreshed_step = runtime.get_step(step.step_id)
    assert paused.status == AgentSessionStatus.PAUSED
    assert refreshed_session.status == AgentSessionStatus.PAUSED
    assert refreshed_step.status == AgentStepStatus.WAITING_USER


def test_agent_runtime_service_user_decision_resumes_waiting_session_to_running(tmp_path) -> None:
    runtime = _build_runtime(tmp_path)
    session = runtime.create_session(
        work_id="work-1",
        chapter_id="chapter-1",
        agent_workflow_type=AgentWorkflowType.CONTINUATION,
        user_instruction="继续写这一章",
        request_id="req_38",
        trace_id="trace_38",
        caller_type="user_action",
    )
    runtime.start_session(session.session_id)
    step = runtime.create_step(session.session_id, agent_type="planner", step_type="direction_selection", action="wait_direction")
    runtime.record_observation(
        step.step_id,
        AgentObservation(
            observation_id="obs_wait_38",
            session_id=session.session_id,
            step_id=step.step_id,
            observation_type=AgentObservationType.USER_DECISION,
            source_type="user",
            status="success",
            safe_message="等待用户选择方向",
            decision="wait_for_user",
            trace_id=session.trace_id,
            request_id="req_38a",
        ),
    )
    waiting_step = runtime.get_step(step.step_id)
    assert waiting_step.status == AgentStepStatus.WAITING_USER
    assert waiting_step.waiting_at

    runtime.record_observation(
        step.step_id,
        AgentObservation(
            observation_id="obs_user_continue_38",
            session_id=session.session_id,
            step_id=step.step_id,
            observation_type=AgentObservationType.USER_DECISION,
            source_type="user",
            status="success",
            safe_message="用户已确认继续",
            decision="continue",
            trace_id=session.trace_id,
            request_id="req_38b",
        ),
    )

    refreshed_session = runtime.get_session(session.session_id)
    refreshed_step = runtime.get_step(step.step_id)
    assert refreshed_session.status == AgentSessionStatus.RUNNING
    assert refreshed_session.waiting_at == ""
    assert refreshed_session.status_reason == ""
    assert refreshed_step.status == AgentStepStatus.RUNNING
    assert refreshed_step.step_phase == "perception"
    assert refreshed_step.waiting_at == ""


def test_agent_runtime_service_rejects_non_user_observation_for_waiting_session(tmp_path) -> None:
    runtime = _build_runtime(tmp_path)
    session = runtime.create_session(
        work_id="work-1",
        chapter_id="chapter-1",
        agent_workflow_type=AgentWorkflowType.CONTINUATION,
        user_instruction="继续写这一章",
        request_id="req_39",
        trace_id="trace_39",
        caller_type="user_action",
    )
    runtime.start_session(session.session_id)
    step = runtime.create_step(session.session_id, agent_type="planner", step_type="direction_selection", action="wait_direction")
    runtime.record_observation(
        step.step_id,
        AgentObservation(
            observation_id="obs_wait_39",
            session_id=session.session_id,
            step_id=step.step_id,
            observation_type=AgentObservationType.USER_DECISION,
            source_type="user",
            status="success",
            safe_message="等待用户选择方向",
            decision="wait_for_user",
            trace_id=session.trace_id,
            request_id="req_39a",
        ),
    )

    with pytest.raises(ValueError, match="waiting_user_decision_required"):
        runtime.record_observation(
            step.step_id,
            AgentObservation(
                observation_id="obs_agent_continue_39",
                session_id=session.session_id,
                step_id=step.step_id,
                observation_type=AgentObservationType.STATE_CHANGE,
                source_type="system",
                status="success",
                safe_message="系统试图自动继续",
                decision="continue",
                trace_id=session.trace_id,
                request_id="req_39b",
            ),
        )


def test_agent_runtime_service_record_user_decision_resumes_waiting_session(tmp_path) -> None:
    runtime = _build_runtime(tmp_path)
    session = runtime.create_session(
        work_id="work-1",
        chapter_id="chapter-1",
        agent_workflow_type=AgentWorkflowType.CONTINUATION,
        user_instruction="继续写这一章",
        request_id="req_39c",
        trace_id="trace_39c",
        caller_type="user_action",
    )
    runtime.start_session(session.session_id)
    step = runtime.create_step(session.session_id, agent_type="planner", step_type="direction_selection", action="wait_direction")
    runtime.record_observation(
        step.step_id,
        AgentObservation(
            observation_id="obs_wait_39c",
            session_id=session.session_id,
            step_id=step.step_id,
            observation_type=AgentObservationType.USER_DECISION,
            source_type="user",
            status="success",
            safe_message="等待用户选择方向",
            decision="wait_for_user",
            trace_id=session.trace_id,
            request_id="req_39c_wait",
        ),
    )

    observation = runtime.record_user_decision(
        session.session_id,
        step_id=step.step_id,
        decision="continue",
        safe_message="用户确认继续",
        request_id="req_39c_resume",
    )

    refreshed_session = runtime.get_session(session.session_id)
    refreshed_step = runtime.get_step(step.step_id)
    assert observation.observation_type == AgentObservationType.USER_DECISION
    assert observation.source_type == "user"
    assert observation.request_id == "req_39c_resume"
    assert refreshed_session.status == AgentSessionStatus.RUNNING
    assert refreshed_step.status == AgentStepStatus.RUNNING


def test_agent_runtime_service_rejects_observation_for_succeeded_step(tmp_path) -> None:
    runtime = _build_runtime(tmp_path)
    session = runtime.create_session(
        work_id="work-1",
        chapter_id="chapter-1",
        agent_workflow_type=AgentWorkflowType.CONTINUATION,
        user_instruction="继续写这一章",
        request_id="req_40",
        trace_id="trace_40",
        caller_type="user_action",
    )
    runtime.start_session(session.session_id)
    step = runtime.create_step(session.session_id, agent_type="writer", step_type="generate_candidate", action="run_writer")
    runtime._step_repository.save_step(
        runtime.get_step(step.step_id).model_copy(
            update={"status": AgentStepStatus.SUCCEEDED, "finished_at": "2026-05-15T00:00:00Z"}
        )
    )

    with pytest.raises(ValueError, match="step_not_observable"):
        runtime.record_observation(
            step.step_id,
            AgentObservation(
                observation_id="obs_after_success_40",
                session_id=session.session_id,
                step_id=step.step_id,
                observation_type=AgentObservationType.TOOL_RESULT,
                source_type="tool",
                status="success",
                safe_message="终态后又来了结果",
                decision="continue",
                trace_id=session.trace_id,
                request_id="req_40b",
            ),
        )


def test_agent_runtime_service_accepts_multiple_late_observations_after_cancel(tmp_path) -> None:
    runtime = _build_runtime(tmp_path)
    session = runtime.create_session(
        work_id="work-1",
        chapter_id="chapter-1",
        agent_workflow_type=AgentWorkflowType.CONTINUATION,
        user_instruction="继续写这一章",
        request_id="req_41",
        trace_id="trace_41",
        caller_type="user_action",
    )
    runtime.start_session(session.session_id)
    step = runtime.create_step(session.session_id, agent_type="writer", step_type="generate_candidate", action="run_writer")
    runtime.cancel_session(session.session_id, reason="user_cancelled")

    first = runtime.record_observation(
        step.step_id,
        AgentObservation(
            observation_id="obs_late_first_41",
            session_id=session.session_id,
            step_id=step.step_id,
            observation_type=AgentObservationType.TOOL_RESULT,
            source_type="tool",
            status="success",
            safe_message="第一次迟到结果",
            decision="continue",
            trace_id=session.trace_id,
            request_id="req_41a",
        ),
    )
    second = runtime.record_observation(
        step.step_id,
        AgentObservation(
            observation_id="obs_late_second_41",
            session_id=session.session_id,
            step_id=step.step_id,
            observation_type=AgentObservationType.MODEL_RESULT,
            source_type="model",
            status="success",
            safe_message="第二次迟到结果",
            decision="continue",
            trace_id=session.trace_id,
            request_id="req_41b",
        ),
    )

    refreshed_step = runtime.get_step(step.step_id)
    assert first.observation_id == "obs_late_first_41"
    assert second.observation_id == "obs_late_second_41"
    assert refreshed_step.status == AgentStepStatus.IGNORED_LATE_RESULT
    assert refreshed_step.observation_id == "obs_late_second_41"
    assert refreshed_step.prior_observation_refs == ["obs_late_first_41"]


def test_agent_runtime_service_mark_late_result_ignored_accepts_multiple_calls(tmp_path) -> None:
    runtime = _build_runtime(tmp_path)
    session = runtime.create_session(
        work_id="work-1",
        chapter_id="chapter-1",
        agent_workflow_type=AgentWorkflowType.CONTINUATION,
        user_instruction="继续写这一章",
        request_id="req_42",
        trace_id="trace_42",
        caller_type="user_action",
    )
    runtime.start_session(session.session_id)
    step = runtime.create_step(session.session_id, agent_type="writer", step_type="generate_candidate", action="run_writer")
    runtime.cancel_session(session.session_id, reason="user_cancelled")

    first = runtime.mark_late_result_ignored(
        step.step_id,
        safe_message="第一条迟到结果被忽略",
        tool_call_id="tool_call_42a",
    )
    second = runtime.mark_late_result_ignored(
        step.step_id,
        safe_message="第二条迟到结果被忽略",
        tool_call_id="tool_call_42b",
    )

    refreshed_step = runtime.get_step(step.step_id)
    assert first.observation_id != second.observation_id
    assert refreshed_step.status == AgentStepStatus.IGNORED_LATE_RESULT
    assert refreshed_step.observation_id == second.observation_id
    assert refreshed_step.prior_observation_refs == [first.observation_id]
