from __future__ import annotations

import pytest

from application.services.ai.agent_runtime_service import AgentRuntimeService
from application.services.ai.tool_facade import CoreToolFacade, ToolDefinition
from domain.entities.ai.models import (
    AgentObservation,
    AgentObservationType,
    AgentSessionStatus,
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
    assert job_steps[0].step_type == "generate_candidate"


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
    assert recorded.decision == "wait_for_user"
    assert refreshed_session.status == AgentSessionStatus.WAITING_FOR_USER
    assert refreshed_step.status == AgentStepStatus.WAITING_USER


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
    assert refreshed_step.status_reason == "skip_step"


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
    assert completed.result.result_refs == ["candidate_draft:cd_19"]
    assert completed.result.warning_codes == ["context_degraded"]


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

    failed = runtime.fail_session(session.session_id, error_code="writer_failed", error_message="writer failed")

    assert failed.result is not None
    assert failed.result.status == "failed"
    assert failed.result.error_code == "writer_failed"
    assert failed.result.result_refs == []


def test_agent_runtime_service_execute_tool_action_records_success_observation(tmp_path) -> None:
    runtime = _build_runtime(tmp_path)
    runtime._tool_facade.register_tool(
        ToolDefinition(
            tool_name="agent_read_tool",
            allowed_callers={"agent"},
            side_effect_level="read_only",
            enabled=True,
        ),
        lambda payload: {"result_ref": "memory_context:mc_1"},
    )
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
    assert observation.metadata["tool_name"] == "agent_read_tool"
    assert observation.metadata["result_ref"] == "memory_context:mc_1"
    assert saved_step.status == AgentStepStatus.RUNNING
    assert saved_step.step_phase == "perception"
    assert saved_step.observation_id == observation.observation_id


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
            update={"status": AgentStepStatus.WAITING_OBSERVATION, "step_phase": "observation"}
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
            update={"status": AgentStepStatus.WAITING_OBSERVATION, "step_phase": "observation", "attempt_count": 1}
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
        retried_step.model_copy(update={"status": AgentStepStatus.WAITING_OBSERVATION, "step_phase": "observation"})
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
