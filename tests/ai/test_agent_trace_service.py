from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from application.services.ai.agent_runtime_service import AgentRuntimeService
from application.services.ai.agent_trace_service import AgentTraceService
from application.services.ai.agent_workflow import AgentOrchestrator
from application.services.ai.ai_job_service import AIJobService
from application.services.ai.llm_call_logger import LLMCallLogger
from application.services.ai.tool_facade import CoreToolFacade
from domain.entities.ai.models import AgentObservation, AgentObservationType, AgentTraceEvent, LLMCallStatus, LLMUsage, WorkflowDecision, WorkflowType
from infrastructure.database.repositories.ai.file_agent_runtime_store import FileAgentRuntimeStore
from infrastructure.database.repositories.ai.file_agent_trace_store import FileAgentTraceStore
from infrastructure.database.repositories.ai.file_ai_job_store import FileAIJobStore
from infrastructure.database.repositories.ai.file_llm_call_log_store import FileLLMCallLogStore


class _FailingTraceStore(FileAgentTraceStore):
    def __init__(self, file_path, *, fail_events: set[str] | None = None):
        super().__init__(file_path)
        self._fail_events = set(fail_events or set())

    def save_event(self, event):
        if event.event_type in self._fail_events:
            raise RuntimeError(f"forced failure: {event.event_type}")
        return super().save_event(event)


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


def _build_bundle(tmp_path):
    runtime_store = FileAgentRuntimeStore(tmp_path / "agent_runtime.json")
    trace_store = FileAgentTraceStore(tmp_path / "agent_trace.json")
    job_store = FileAIJobStore(tmp_path / "ai_jobs.json")
    llm_log_store = FileLLMCallLogStore(tmp_path / "llm_call_logs.jsonl")
    job_service = AIJobService(job_repository=job_store, step_repository=job_store, attempt_repository=job_store)
    trace_service = AgentTraceService(repository=trace_store)
    tool_facade = CoreToolFacade(
        context_pack_service=_StubContextPackService(),
        candidate_draft_repository=_StubCandidateDraftRepository(),
        writer=_StubWriter(),
        job_service=job_service,
        trace_service=trace_service,
    )
    runtime = AgentRuntimeService(
        session_repository=runtime_store,
        step_repository=runtime_store,
        observation_repository=runtime_store,
        ai_job_service=job_service,
        tool_facade=tool_facade,
        trace_service=trace_service,
    )
    workflow = AgentOrchestrator(runtime_service=runtime, trace_service=trace_service)
    llm_logger = LLMCallLogger(repository=llm_log_store, trace_service=trace_service)
    return {
        "trace_service": trace_service,
        "runtime": runtime,
        "workflow": workflow,
        "tool_facade": tool_facade,
        "llm_logger": llm_logger,
    }


def _advance_step_to_action(runtime: AgentRuntimeService, session_id: str, step_id: str) -> None:
    session = runtime.get_session(session_id)
    runtime.record_observation(
        step_id,
        AgentObservation(
            observation_id=f"obs_{step_id}_perception",
            session_id=session_id,
            step_id=step_id,
            observation_type=AgentObservationType.MODEL_RESULT,
            source_type="system",
            status="success",
            safe_message="perception_done",
            summary="perception_done",
            decision="continue",
            decision_reason="perception_done",
            request_id=session.request_id,
            trace_id=session.trace_id,
        ),
    )
    runtime.record_observation(
        step_id,
        AgentObservation(
            observation_id=f"obs_{step_id}_planning",
            session_id=session_id,
            step_id=step_id,
            observation_type=AgentObservationType.MODEL_RESULT,
            source_type="system",
            status="success",
            safe_message="planning_done",
            summary="planning_done",
            decision="continue",
            decision_reason="planning_done",
            request_id=session.request_id,
            trace_id=session.trace_id,
        ),
    )


def test_agent_trace_service_records_runtime_and_workflow_events_with_metrics(tmp_path) -> None:
    bundle = _build_bundle(tmp_path)
    workflow = bundle["workflow"]
    trace_service = bundle["trace_service"]

    run = workflow.start_workflow(
        work_id="work_trace_1",
        chapter_id="chapter_trace_1",
        workflow_type=WorkflowType.CONTINUATION_WORKFLOW,
        user_instruction="继续写作",
        caller_type="user_action",
    )
    session = bundle["runtime"].get_session(run.session_id)
    step = bundle["runtime"].create_step(session.session_id, agent_type="writer", step_type="generate_candidate", action="run_writer")
    bundle["runtime"].run_next_step(session.session_id)
    bundle["runtime"].cancel_session(session.session_id, reason="user_cancelled")
    cancelled_step = bundle["runtime"].get_step(step.step_id)
    assert cancelled_step.status == "cancelled"
    bundle["runtime"].mark_late_result_ignored(step.step_id, safe_message="late result ignored")

    trace = trace_service.get_trace(session.trace_id)
    event_types = [item.event_type for item in trace_service.list_events(trace.trace_id)]
    metric_names = [item.metric_name for item in trace_service.list_metrics(trace.trace_id)]
    alerts = trace_service.list_alerts(trace.trace_id)

    assert trace.status == "cancelled"
    assert "session_created" in event_types
    assert "session_started" in event_types
    assert "stage_entered" in event_types
    assert "checkpoint_saved" in event_types
    assert "step_created" in event_types
    assert "step_started" in event_types
    assert "session_cancelling" in event_types
    assert "session_cancelled" in event_types
    assert "step_ignored_late_result" in event_types
    assert "agent_session_total" in metric_names
    assert "ignored_late_result_total" in metric_names
    assert all(alert.alert_type != "audit_write_failed" for alert in alerts)


def test_agent_trace_service_records_tool_denied_and_llm_projection_in_detail_view(tmp_path) -> None:
    bundle = _build_bundle(tmp_path)
    runtime = bundle["runtime"]
    trace_service = bundle["trace_service"]
    llm_logger = bundle["llm_logger"]

    session = runtime.create_session(
        work_id="work_trace_2",
        chapter_id="chapter_trace_2",
        agent_workflow_type="continuation",
        user_instruction="继续写作",
        request_id="req_trace_2",
        trace_id="trace_trace_2",
        caller_type="user_action",
    )
    runtime.start_session(session.session_id)
    step = runtime.create_step(session.session_id, agent_type="writer", step_type="generate_candidate", action="run_writer")
    runtime.run_next_step(session.session_id)
    _advance_step_to_action(runtime, session.session_id, step.step_id)
    observation = runtime.execute_tool_action(
        session.session_id,
        step_id=step.step_id,
        agent_type="writer",
        tool_name="apply_candidate_to_draft",
        payload={"candidate_draft_id": "cd_denied"},
        side_effect_level="candidate_write",
    )
    started_at = datetime.now(UTC)
    finished_at = started_at + timedelta(milliseconds=120)
    llm_logger.record(
        prompt_key="writer_generation",
        prompt_version="v1",
        model_role="writer",
        provider_name="fake",
        model_name="fake-chat",
        request_id=session.request_id,
        trace_id=session.trace_id,
        status=LLMCallStatus.SUCCEEDED,
        started_at=started_at,
        finished_at=finished_at,
        usage=LLMUsage(input_tokens=10, output_tokens=20, total_tokens=30),
        attempt_no=1,
        context_pack_snapshot_id="cp_1",
        output_schema_key="candidate_draft",
        session_id=session.session_id,
        step_id=step.step_id,
        content_hash="hash_writer_1",
    )

    detail = trace_service.get_detail_view(session.trace_id, developer_mode=True)
    event_types = [item.event_type for item in detail["events"]]
    metric_names = [item.metric_name for item in detail["metrics"]]

    assert observation.error_code == "tool_permission_denied"
    assert "tool_call_started" in event_types
    assert "tool_call_denied" in event_types
    assert detail["tool_calls"][0].permission_result == "deny"
    assert detail["tool_calls"][0].tool_name == "apply_candidate_to_draft"
    assert detail["tool_calls"][0].tool_audit_log_ref == bundle["tool_facade"].audit_logs[0]["audit_log_ref"]
    assert detail["llm_calls"][0].prompt_ref == "writer_generation:v1"
    assert detail["llm_calls"][0].content_hash == "hash_writer_1"
    assert "tool_call_denied_total" in metric_names


def test_agent_trace_service_projects_failed_llm_status_and_error_code(tmp_path) -> None:
    bundle = _build_bundle(tmp_path)
    runtime = bundle["runtime"]
    trace_service = bundle["trace_service"]

    session = runtime.create_session(
        work_id="work_trace_failed_llm",
        chapter_id="chapter_trace_failed_llm",
        agent_workflow_type="planning",
        user_instruction="把这段写顺",
        request_id="req_trace_failed_llm",
        trace_id="trace_failed_llm",
        caller_type="user_action",
    )
    started_at = datetime.now(UTC)
    bundle["llm_logger"].record(
        prompt_key="outline_polish",
        prompt_version="v1",
        model_role="planner",
        provider_name="fake",
        model_name="fake-chat",
        request_id="req_failed_llm_attempt_1",
        trace_id=session.trace_id,
        status=LLMCallStatus.FAILED,
        started_at=started_at,
        finished_at=started_at + timedelta(milliseconds=80),
        error_code="provider_timeout",
        attempt_no=1,
        output_schema_key="outline_polish_v1",
        session_id=session.session_id,
        step_id="step_failed_llm",
    )

    detail = trace_service.get_detail_view(session.trace_id, developer_mode=True)

    assert detail["llm_calls"][0].status == "failed"
    assert detail["llm_calls"][0].error_code == "provider_timeout"


def test_agent_trace_event_rejects_unknown_event_type() -> None:
    with pytest.raises(ValidationError):
        AgentTraceEvent(
            event_id="traceevt_invalid",
            trace_id="trace_invalid",
            session_id="session_invalid",
            event_type="unknown_event_type",
            event_time="2026-05-22T00:00:00+00:00",
            summary="invalid event type should fail",
        )


def test_agent_trace_service_keeps_first_terminal_event_and_records_duplicate_ignored(tmp_path) -> None:
    bundle = _build_bundle(tmp_path)
    runtime = bundle["runtime"]
    trace_service = bundle["trace_service"]

    session = runtime.create_session(
        work_id="work_trace_dup",
        chapter_id="chapter_trace_dup",
        agent_workflow_type="continuation",
        user_instruction="继续写作",
        request_id="req_trace_dup",
        trace_id="trace_trace_dup",
        caller_type="user_action",
    )
    runtime.start_session(session.session_id)
    step = runtime.create_step(session.session_id, agent_type="writer", step_type="generate_candidate", action="run_writer")
    runtime.run_next_step(session.session_id)
    _advance_step_to_action(runtime, session.session_id, step.step_id)

    failed_observation = AgentObservation(
        observation_id=f"obs_{step.step_id}_failed",
        session_id=session.session_id,
        step_id=step.step_id,
            observation_type=AgentObservationType.VALIDATION_RESULT,
        source_type="runtime",
        status="error",
        safe_message="first failed",
        summary="first failed",
        decision="fail_step",
        decision_reason="first_failed",
        error_code="tool_permission_denied",
        request_id=session.request_id,
        trace_id=session.trace_id,
    )
    runtime.record_observation(step.step_id, failed_observation)
    session_after_fail = runtime.get_session(session.session_id)
    step_after_fail = runtime.get_step(step.step_id)
    trace_service.record_step_event(
        session_after_fail,
        step_after_fail,
        event_type="step_failed",
        summary="duplicate failed terminal",
    )

    events = trace_service.list_events(session.trace_id)
    event_types = [item.event_type for item in events]
    failed_events = [item for item in events if item.event_type == "step_failed"]
    duplicate_events = [item for item in events if item.event_type == "duplicate_ignored"]
    step_trace = trace_service.list_step_traces(session.trace_id)[0]

    assert len(failed_events) == 1
    assert len(duplicate_events) == 1
    assert step_trace.status == "failed"
    assert duplicate_events[0].payload_digest["ignored_event_type"] == "step_failed"
    assert "step_failed" in event_types


def test_agent_trace_service_records_stage_exit_checkpoint_restore_and_degraded_blocked_policy_events(tmp_path) -> None:
    bundle = _build_bundle(tmp_path)
    workflow = bundle["workflow"]
    runtime = bundle["runtime"]
    trace_service = bundle["trace_service"]

    degraded_run = workflow.start_workflow(
        work_id="work_trace_degraded",
        chapter_id="chapter_trace_degraded",
        workflow_type=WorkflowType.REVIEW_WORKFLOW,
        user_instruction="继续写作",
        caller_type="user_action",
    )
    workflow.advance_workflow(
        degraded_run.session_id,
        decision=WorkflowDecision.CONTINUE,
        result_ref="review_report:rv_degraded",
        safe_message="memory degraded",
        warning_codes=["context_pack_degraded"],
    )
    restored_run = workflow.start_workflow(
        work_id="work_trace_restore",
        chapter_id="chapter_trace_restore",
        workflow_type=WorkflowType.CONTINUATION_WORKFLOW,
        user_instruction="继续写作",
        caller_type="user_action",
    )
    workflow.pause_workflow(restored_run.session_id, reason="pause_for_restore")
    workflow.resume_workflow(restored_run.session_id)

    blocked_run = workflow.start_workflow(
        work_id="work_trace_blocked",
        chapter_id="chapter_trace_blocked",
        workflow_type=WorkflowType.CONTINUATION_WORKFLOW,
        user_instruction="继续写作",
        caller_type="user_action",
        policy_overrides={"allow_degraded": False},
    )
    with pytest.raises(ValueError):
        workflow.advance_workflow(
            blocked_run.session_id,
            decision=WorkflowDecision.CONTINUE,
            result_ref="memory_context:ctx_blocked",
            safe_message="memory blocked",
            warning_codes=["context_pack_degraded"],
            error_code="memory_blocked",
        )

    degraded_trace_id = runtime.get_session(degraded_run.session_id).trace_id
    restored_trace_id = runtime.get_session(restored_run.session_id).trace_id
    blocked_trace_id = runtime.get_session(blocked_run.session_id).trace_id
    degraded_events = [item.event_type for item in trace_service.list_events(degraded_trace_id)]
    restored_events = [item.event_type for item in trace_service.list_events(restored_trace_id)]
    blocked_events = [item.event_type for item in trace_service.list_events(blocked_trace_id)]

    assert "stage_exited" in restored_events
    assert "degraded_detected" in degraded_events
    assert "checkpoint_restored" in restored_events
    assert "policy_blocked" in blocked_events
    assert "blocked_detected" in blocked_events


def test_agent_trace_service_cleans_old_detail_traces_but_keeps_session_and_audit_data(tmp_path) -> None:
    bundle = _build_bundle(tmp_path)
    runtime = bundle["runtime"]
    trace_service = bundle["trace_service"]
    repo = bundle["trace_service"]._repository

    session = runtime.create_session(
        work_id="work_trace_cleanup",
        chapter_id="chapter_trace_cleanup",
        agent_workflow_type="continuation",
        user_instruction="继续写作",
        request_id="req_trace_cleanup",
        trace_id="trace_trace_cleanup",
        caller_type="user_action",
    )
    runtime.start_session(session.session_id)
    step = runtime.create_step(session.session_id, agent_type="writer", step_type="generate_candidate", action="run_writer")
    runtime.run_next_step(session.session_id)
    _advance_step_to_action(runtime, session.session_id, step.step_id)
    runtime.execute_tool_action(
        session.session_id,
        step_id=step.step_id,
        agent_type="writer",
        tool_name="apply_candidate_to_draft",
        payload={"candidate_draft_id": "cd_cleanup"},
        side_effect_level="candidate_write",
    )
    trace_service.record_user_decision(
        trace_id=session.trace_id,
        session_id=session.session_id,
        step_id=step.step_id,
        decision_type="apply_memory",
        target_entity_type="memory_gate",
        target_entity_id="gate_cleanup",
    )
    old_time = "2025-01-01T00:00:00+00:00"
    repo.save_trace(trace_service.get_trace(session.trace_id).model_copy(update={"ended_at": old_time, "updated_at": old_time}))

    removed = trace_service.cleanup_expired_details(now=datetime(2026, 6, 1, tzinfo=UTC))

    assert removed["tool_calls"] > 0
    assert trace_service.get_trace(session.trace_id).trace_id == session.trace_id
    assert trace_service.list_step_traces(session.trace_id)
    assert trace_service.get_detail_view(session.trace_id, developer_mode=True)["user_decisions"]
    assert not trace_service.get_detail_view(session.trace_id, developer_mode=True)["tool_calls"]


def test_agent_trace_service_supports_filtered_query_and_alert_resolution(tmp_path) -> None:
    bundle = _build_bundle(tmp_path)
    runtime = bundle["runtime"]
    trace_service = bundle["trace_service"]

    session = runtime.create_session(
        work_id="work_trace_query",
        chapter_id="chapter_trace_query",
        agent_workflow_type="continuation",
        user_instruction="继续写作",
        request_id="req_trace_query",
        trace_id="trace_trace_query",
        caller_type="user_action",
    )
    runtime.start_session(session.session_id)
    step = runtime.create_step(session.session_id, agent_type="writer", step_type="generate_candidate", action="run_writer")
    runtime.run_next_step(session.session_id)
    _advance_step_to_action(runtime, session.session_id, step.step_id)
    runtime.execute_tool_action(
        session.session_id,
        step_id=step.step_id,
        agent_type="writer",
        tool_name="apply_candidate_to_draft",
        payload={"candidate_draft_id": "cd_query"},
        side_effect_level="candidate_write",
    )

    tool_events = trace_service.list_events(
        session.trace_id,
        step_id=step.step_id,
        event_type="tool_call_denied",
        time_range_start="2026-01-01T00:00:00+00:00",
    )
    alert = trace_service.list_alerts(session.trace_id)[0]
    resolved = trace_service.resolve_alert(alert.alert_id)
    resolved_events = [item.event_type for item in trace_service.list_events(session.trace_id)]

    assert len(tool_events) == 1
    assert tool_events[0].event_type == "tool_call_denied"
    assert resolved.status == "resolved"
    assert "alert_triggered" in resolved_events
    assert "alert_resolved" in resolved_events


def test_agent_trace_service_degrades_on_normal_write_failure_but_blocks_critical_audit(tmp_path) -> None:
    runtime_store = FileAgentRuntimeStore(tmp_path / "agent_runtime.json")
    trace_store = _FailingTraceStore(tmp_path / "agent_trace.json", fail_events={"session_started", "memory_revision_applied"})
    job_store = FileAIJobStore(tmp_path / "ai_jobs.json")
    job_service = AIJobService(job_repository=job_store, step_repository=job_store, attempt_repository=job_store)
    trace_service = AgentTraceService(repository=trace_store)
    tool_facade = CoreToolFacade(
        context_pack_service=_StubContextPackService(),
        candidate_draft_repository=_StubCandidateDraftRepository(),
        writer=_StubWriter(),
        job_service=job_service,
        trace_service=trace_service,
    )
    runtime = AgentRuntimeService(
        session_repository=runtime_store,
        step_repository=runtime_store,
        observation_repository=runtime_store,
        ai_job_service=job_service,
        tool_facade=tool_facade,
        trace_service=trace_service,
    )

    session = runtime.create_session(
        work_id="work_trace_failsafe",
        chapter_id="chapter_trace_failsafe",
        agent_workflow_type="continuation",
        user_instruction="继续写作",
        request_id="req_trace_failsafe",
        trace_id="trace_trace_failsafe",
        caller_type="user_action",
    )
    started = runtime.start_session(session.session_id)
    degraded_events = [item.event_type for item in trace_service.list_events(session.trace_id)]
    alerts = trace_service.list_alerts(session.trace_id)

    assert started.session_id == session.session_id
    assert "trace_write_failed" in degraded_events
    assert any(item.alert_type == "audit_write_failed" for item in alerts)

    try:
        trace_service.record_audit_event(
            trace_id=session.trace_id,
            session_id=session.session_id,
            step_id="",
            event_type="memory_revision_applied",
            summary="memory applied",
            high_risk_user_action=True,
        )
    except ValueError as exc:
        assert str(exc) == "critical_audit_write_failed"
    else:
        raise AssertionError("critical audit failure should block high risk action")
