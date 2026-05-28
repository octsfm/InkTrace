from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from domain.entities.ai.models import (
    AgentObservation,
    AgentSession,
    AgentStep,
    AgentStepTrace,
    AgentTrace,
    AgentTraceEvent,
    AgentTraceStatus,
    LLMCallLog,
    LLMCallTraceView,
    ObservationTrace,
    ToolCallTrace,
    ToolCallTraceStatus,
    ToolPermissionResult,
    TraceAlertRecord,
    TraceAlertScope,
    TraceAlertStatus,
    TraceAlertType,
    TraceEventStage,
    TraceLevel,
    TraceMetricPoint,
    UserDecisionTrace,
)
from domain.repositories.ai.agent_trace_repository import AgentTraceRepository


def _now() -> str:
    return datetime.now(UTC).isoformat()


class AgentTraceService:
    def __init__(self, *, repository: AgentTraceRepository, detail_retention_days: int = 90) -> None:
        self._repository = repository
        self._detail_retention_days = detail_retention_days

    def ensure_trace_for_session(self, session: AgentSession, *, workflow_run_id: str = "", workflow_type: str = "") -> AgentTrace:
        try:
            existing = self._repository.get_trace(session.trace_id)
        except ValueError:
            existing = AgentTrace(
                trace_id=session.trace_id,
                work_id=session.work_id,
                chapter_id=session.chapter_id or "",
                session_id=session.session_id,
                workflow_run_id=workflow_run_id,
                workflow_type=workflow_type or session.workflow_type.value,
                status=self._trace_status_for_session(session),
                started_at=session.started_at or session.created_at or _now(),
                created_at=session.created_at or _now(),
                updated_at=session.updated_at or _now(),
            )
        updated = existing.model_copy(
            update={
                "workflow_run_id": workflow_run_id or existing.workflow_run_id,
                "workflow_type": workflow_type or existing.workflow_type or session.workflow_type.value,
                "status": self._trace_status_for_session(session),
                "warning_codes": list(session.warning_codes),
                "error_code": session.error_code,
                "started_at": existing.started_at or session.started_at or session.created_at or _now(),
                "ended_at": self._trace_end_time(existing, session),
                "updated_at": session.updated_at or _now(),
                "total_elapsed_ms": self._elapsed_ms(existing.started_at or session.started_at or session.created_at, session.finished_at or session.cancelled_at),
            }
        )
        return self._repository.save_trace(updated)

    def record_session_event(
        self,
        session: AgentSession,
        *,
        event_type: str,
        summary: str,
        level: TraceLevel = TraceLevel.INFO,
        stage: TraceEventStage = TraceEventStage.ORCHESTRATION,
        payload_digest: dict[str, Any] | None = None,
    ) -> AgentTraceEvent:
        trace = self.ensure_trace_for_session(session)
        event = self._save_event_safely(
            AgentTraceEvent(
                event_id=f"traceevt_{uuid.uuid4().hex[:12]}",
                trace_id=trace.trace_id,
                session_id=session.session_id,
                event_type=event_type,
                event_stage=stage,
                event_time=_now(),
                level=level,
                summary=summary,
                safe_refs=[f"session:{session.session_id}"],
                payload_digest=dict(payload_digest or {}),
                request_id=session.request_id,
                correlation_id=session.trace_id,
            )
        )
        self._emit_standard_metrics(trace, event_type=event_type, session=session)
        self._emit_session_audit_mirror(trace, session, event_type=event_type)
        return event

    def record_workflow_event(
        self,
        session: AgentSession,
        *,
        workflow_run_id: str,
        workflow_type: str,
        event_type: str,
        summary: str,
        payload_digest: dict[str, Any] | None = None,
    ) -> AgentTraceEvent:
        self.ensure_trace_for_session(session, workflow_run_id=workflow_run_id, workflow_type=workflow_type)
        return self.record_session_event(
            session,
            event_type=event_type,
            summary=summary,
            stage=TraceEventStage.ORCHESTRATION,
            payload_digest=payload_digest,
        )

    def record_step_trace(self, session: AgentSession, step: AgentStep) -> AgentStepTrace:
        trace = self.ensure_trace_for_session(session)
        try:
            current = self._repository.get_step_trace_by_step(step.step_id)
        except ValueError:
            current = AgentStepTrace(
                step_trace_id=f"steptrace_{uuid.uuid4().hex[:12]}",
                trace_id=trace.trace_id,
                step_id=step.step_id,
                session_id=session.session_id,
                agent_type=step.agent_type,
                action=step.action,
                attempt_no=step.attempt_count,
                status=step.status.value,
                started_at=step.started_at or "",
                ended_at=step.finished_at or "",
                duration_ms=self._elapsed_ms(step.started_at, step.finished_at),
                warning_codes=list(step.warning_codes),
                error_code=step.error_code,
            )
        updated = current.model_copy(
            update={
                "agent_type": step.agent_type,
                "action": step.action,
                "attempt_no": step.attempt_count,
                "status": step.status.value,
                "started_at": step.started_at or current.started_at,
                "ended_at": step.finished_at or current.ended_at,
                "duration_ms": self._elapsed_ms(step.started_at or current.started_at, step.finished_at or current.ended_at),
                "warning_codes": list(step.warning_codes),
                "error_code": step.error_code,
            }
        )
        saved = self._repository.save_step_trace(updated)
        trace = trace.model_copy(
            update={
                "total_steps": max(trace.total_steps, len(self._repository.list_step_traces(trace.trace_id))),
                "agent_sequence": self._append_unique(trace.agent_sequence, step.agent_type),
                "updated_at": _now(),
            }
        )
        self._repository.save_trace(trace)
        return saved

    def record_step_event(
        self,
        session: AgentSession,
        step: AgentStep,
        *,
        event_type: str,
        summary: str,
        level: TraceLevel = TraceLevel.INFO,
    ) -> AgentTraceEvent:
        trace = self.ensure_trace_for_session(session)
        duplicate_event = self._maybe_record_duplicate_terminal(trace.trace_id, session.session_id, step, event_type=event_type)
        if duplicate_event is not None:
            return duplicate_event
        self.record_step_trace(session, step)
        event = self._save_event_safely(
            AgentTraceEvent(
                event_id=f"traceevt_{uuid.uuid4().hex[:12]}",
                trace_id=trace.trace_id,
                session_id=session.session_id,
                step_id=step.step_id,
                event_type=event_type,
                event_stage=self._stage_for_step(step),
                event_time=_now(),
                level=level,
                summary=summary,
                safe_refs=[f"step:{step.step_id}"],
                payload_digest={"agent_type": step.agent_type, "action": step.action, "status": step.status.value, "attempt_no": step.attempt_count},
                request_id=step.request_id,
                correlation_id=session.trace_id,
            )
        )
        self._emit_step_metrics(trace.trace_id, step=step, event_type=event_type)
        return event

    def record_observation(self, session: AgentSession, step: AgentStep, observation: AgentObservation) -> ObservationTrace:
        trace = self.ensure_trace_for_session(session)
        observation_trace = self._repository.save_observation_trace(
            ObservationTrace(
                observation_trace_id=f"obstrace_{uuid.uuid4().hex[:12]}",
                trace_id=trace.trace_id,
                step_id=step.step_id,
                observation_type=observation.observation_type.value,
                decision_hint=observation.decision,
                decision_source=observation.source_type,
                is_blocking=observation.decision in {"wait_for_user", "fail_step", "fail_workflow"},
                warning_codes=list(observation.warning_codes),
                summary=observation.safe_message or observation.summary,
                safe_refs=[f"observation:{observation.observation_id}"] if observation.observation_id else [],
            )
        )
        self._save_event_safely(
            AgentTraceEvent(
                event_id=f"traceevt_{uuid.uuid4().hex[:12]}",
                trace_id=trace.trace_id,
                session_id=session.session_id,
                step_id=step.step_id,
                event_type="observation_recorded",
                event_stage=TraceEventStage.OBSERVATION,
                event_time=_now(),
                level=TraceLevel.WARNING if observation.warning_codes else TraceLevel.INFO,
                summary=observation.safe_message or observation.summary or "observation_recorded",
                safe_refs=observation_trace.safe_refs,
                payload_digest={"decision": observation.decision, "error_code": observation.error_code},
                request_id=observation.request_id,
                correlation_id=session.trace_id,
            )
        )
        if observation.decision == "wait_for_user":
            self.record_session_event(session, event_type="waiting_for_user_entered", summary=observation.safe_message or "waiting_for_user")
        if observation.decision == "continue" and session.status.value == "running":
            self.record_session_event(session, event_type="waiting_for_user_resolved", summary=observation.safe_message or "user_decision_applied")
        if observation.decision == "retry_step":
            self._emit_metric(
                trace.trace_id,
                "retry_attempt_total",
                1,
                labels={"agent_type": step.agent_type, "workflow_type": trace.workflow_type},
            )
        return observation_trace

    def record_tool_call(
        self,
        *,
        trace_id: str,
        step_id: str,
        tool_name: str,
        caller_type: str,
        side_effect_level: str,
        permission_result: str,
        call_status: str,
        request_id: str,
        safe_input_digest: dict[str, Any] | None = None,
        safe_output_digest: dict[str, Any] | None = None,
        error_code: str = "",
        duration_ms: int = 0,
        tool_audit_log_ref: str = "",
    ) -> ToolCallTrace:
        trace = self.get_trace(trace_id)
        self._save_event_safely(
            AgentTraceEvent(
                event_id=f"traceevt_{uuid.uuid4().hex[:12]}",
                trace_id=trace_id,
                session_id=trace.session_id,
                step_id=step_id,
                event_type="tool_call_started",
                event_stage=TraceEventStage.ACTION,
                event_time=_now(),
                level=TraceLevel.INFO,
                summary=tool_name,
                safe_refs=[f"tool:{tool_name}"],
                payload_digest={"caller_type": caller_type, "side_effect_level": side_effect_level},
                request_id=request_id,
                correlation_id=trace_id,
            )
        )
        tool_trace = self._repository.save_tool_call(
            ToolCallTrace(
                tool_trace_id=f"tooltrace_{uuid.uuid4().hex[:12]}",
                trace_id=trace_id,
                step_id=step_id,
                tool_name=tool_name,
                caller_type=caller_type,
                side_effect_level=side_effect_level,
                permission_result=ToolPermissionResult(permission_result),
                call_status=ToolCallTraceStatus(call_status),
                duration_ms=duration_ms,
                error_code=error_code,
                safe_input_digest=dict(safe_input_digest or {}),
                safe_output_digest=dict(safe_output_digest or {}),
                tool_audit_log_ref=tool_audit_log_ref,
            )
        )
        event_type = "tool_call_denied" if permission_result == ToolPermissionResult.DENY.value else (
            "tool_call_failed" if call_status == ToolCallTraceStatus.FAILED.value else "tool_call_succeeded"
        )
        self._save_event_safely(
            AgentTraceEvent(
                event_id=f"traceevt_{uuid.uuid4().hex[:12]}",
                trace_id=trace_id,
                session_id=trace.session_id,
                step_id=step_id,
                event_type=event_type,
                event_stage=TraceEventStage.ACTION,
                event_time=_now(),
                level=TraceLevel.WARNING if permission_result == ToolPermissionResult.DENY.value else TraceLevel.INFO,
                summary=f"{tool_name}:{call_status}",
                safe_refs=[f"tool:{tool_name}"],
                payload_digest={"permission_result": permission_result, "call_status": call_status, "error_code": error_code},
                request_id=request_id,
                correlation_id=trace_id,
            )
        )
        if permission_result == ToolPermissionResult.DENY.value:
            self.record_audit_event(
                trace_id=trace_id,
                session_id=trace.session_id,
                step_id=step_id,
                event_type="tool_call_forbidden",
                summary=f"{tool_name}:forbidden",
                payload_digest={"tool_name": tool_name, "caller_type": caller_type, "error_code": error_code},
            )
            self._emit_metric(trace_id, "tool_call_denied_total", 1, labels={"tool_name": tool_name, "caller_type": caller_type})
        if call_status == ToolCallTraceStatus.FAILED.value:
            self._emit_metric(trace_id, "tool_call_failed_total", 1, labels={"tool_name": tool_name, "error_code": error_code})
        if duration_ms:
            self._emit_metric(trace_id, "tool_call_duration_ms", duration_ms, labels={"tool_name": tool_name})
        return tool_trace

    def record_llm_call(self, entry: LLMCallLog, *, session_id: str = "", step_id: str = "", content_hash: str = "") -> LLMCallTraceView:
        trace_id = entry.trace_id
        trace = self.get_trace(trace_id)
        token_count = int(entry.usage.total_tokens or 0) if entry.usage else 0
        elapsed_ms = int((entry.finished_at - entry.started_at).total_seconds() * 1000)
        view = self._repository.save_llm_call_view(
            LLMCallTraceView(
                llm_call_log_ref=f"{entry.request_id}:{entry.prompt_key}:{entry.attempt_no}",
                trace_id=trace_id,
                step_id=step_id,
                prompt_ref=f"{entry.prompt_key}:{entry.prompt_version}",
                model_role=entry.model_role,
                provider=entry.provider_name,
                model=entry.model_name,
                context_pack_ref=entry.context_pack_snapshot_id,
                output_schema_key=entry.output_schema_key,
                token_count=token_count,
                elapsed_ms=elapsed_ms,
                content_hash=content_hash,
            )
        )
        updated_trace = trace.model_copy(update={"total_tokens": trace.total_tokens + token_count, "updated_at": _now()})
        self._repository.save_trace(updated_trace)
        return view

    def record_user_decision(
        self,
        *,
        trace_id: str,
        session_id: str,
        step_id: str,
        decision_type: str,
        target_entity_type: str,
        target_entity_id: str,
        decision_note: str = "",
    ) -> UserDecisionTrace:
        decision = self._repository.save_user_decision(
            UserDecisionTrace(
                decision_trace_id=f"decisiontrace_{uuid.uuid4().hex[:12]}",
                trace_id=trace_id,
                session_id=session_id,
                step_id=step_id,
                decision_type=decision_type,
                target_entity_type=target_entity_type,
                target_entity_id=target_entity_id,
                decided_by="user_action",
                decision_note=decision_note,
                decided_at=_now(),
            )
        )
        self._save_event_safely(
            AgentTraceEvent(
                event_id=f"traceevt_{uuid.uuid4().hex[:12]}",
                trace_id=trace_id,
                session_id=session_id,
                step_id=step_id,
                event_type="user_decision_recorded",
                event_stage=TraceEventStage.AUDIT,
                event_time=_now(),
                level=TraceLevel.INFO,
                summary=decision_type,
                safe_refs=[f"{target_entity_type}:{target_entity_id}"],
                payload_digest={"decision_type": decision_type},
                correlation_id=trace_id,
            )
        )
        return decision

    def get_trace(self, trace_id: str) -> AgentTrace:
        return self._repository.get_trace(trace_id)

    def list_traces(self, *, work_id: str = "", chapter_id: str = "", session_id: str = "", status: str = "") -> list[AgentTrace]:
        return self._repository.list_traces(work_id=work_id, chapter_id=chapter_id, session_id=session_id, status=status)

    def list_events(
        self,
        trace_id: str,
        *,
        step_id: str = "",
        event_type: str = "",
        time_range_start: str = "",
        time_range_end: str = "",
        event_stage: str = "",
    ) -> list[AgentTraceEvent]:
        return self._repository.list_events(
            trace_id,
            step_id=step_id,
            event_type=event_type,
            time_range_start=time_range_start,
            time_range_end=time_range_end,
            event_stage=event_stage,
        )

    def list_step_traces(self, trace_id: str) -> list[AgentStepTrace]:
        return self._repository.list_step_traces(trace_id)

    def list_metrics(self, trace_id: str) -> list[TraceMetricPoint]:
        return self._repository.list_metrics(trace_id)

    def list_alerts(self, trace_id: str) -> list[TraceAlertRecord]:
        return self._repository.list_alerts(trace_id)

    def record_audit_event(
        self,
        *,
        trace_id: str,
        session_id: str,
        step_id: str,
        event_type: str,
        summary: str,
        payload_digest: dict[str, Any] | None = None,
        high_risk_user_action: bool = False,
    ) -> AgentTraceEvent:
        return self._save_event_safely(
            AgentTraceEvent(
                event_id=f"traceevt_{uuid.uuid4().hex[:12]}",
                trace_id=trace_id,
                session_id=session_id,
                step_id=step_id,
                event_type=event_type,
                event_stage=TraceEventStage.AUDIT,
                event_time=_now(),
                level=TraceLevel.CRITICAL if high_risk_user_action else TraceLevel.INFO,
                summary=summary,
                safe_refs=[f"trace:{trace_id}"],
                payload_digest=dict(payload_digest or {}),
                correlation_id=trace_id,
            ),
            critical=high_risk_user_action,
            high_risk_user_action=high_risk_user_action,
        )

    def resolve_alert(self, alert_id: str) -> TraceAlertRecord:
        alert = self._repository.get_alert(alert_id)
        saved = self._repository.save_alert(alert.model_copy(update={"status": TraceAlertStatus.RESOLVED, "resolved_at": _now()}))
        self._save_event_safely(
            AgentTraceEvent(
                event_id=f"traceevt_{uuid.uuid4().hex[:12]}",
                trace_id=alert.trace_id,
                session_id=self.get_trace(alert.trace_id).session_id if alert.trace_id else "",
                event_type="alert_resolved",
                event_stage=TraceEventStage.ORCHESTRATION,
                event_time=_now(),
                level=TraceLevel.INFO,
                summary=alert.summary,
                safe_refs=[f"alert:{alert.alert_id}"],
                payload_digest={"alert_type": alert.alert_type.value},
                correlation_id=alert.trace_id,
            )
        )
        return saved

    def cleanup_expired_details(self, *, now: datetime | None = None) -> dict[str, int]:
        reference = now or datetime.now(UTC)
        cutoff = reference - timedelta(days=self._detail_retention_days)
        expired_trace_ids = [
            item.trace_id
            for item in self.list_traces()
            if item.ended_at and datetime.fromisoformat(item.ended_at) < cutoff
        ]
        return self._repository.cleanup_expired_details(trace_ids=expired_trace_ids)

    def get_detail_view(self, trace_id: str, *, developer_mode: bool) -> dict[str, Any]:
        if not developer_mode:
            raise ValueError("permission_denied")
        return {
            "trace": self.get_trace(trace_id),
            "events": self.list_events(trace_id),
            "steps": self.list_step_traces(trace_id),
            "tool_calls": self._repository.list_tool_calls(trace_id),
            "observations": self._repository.list_observation_traces(trace_id),
            "llm_calls": self._repository.list_llm_call_views(trace_id),
            "user_decisions": self._repository.list_user_decisions(trace_id),
            "metrics": self.list_metrics(trace_id),
            "alerts": self.list_alerts(trace_id),
        }

    def _emit_standard_metrics(self, trace: AgentTrace, *, event_type: str, session: AgentSession) -> None:
        labels = {"workflow_type": trace.workflow_type or session.workflow_type.value}
        if event_type == "session_created":
            self._emit_metric(trace.trace_id, "agent_session_total", 1, labels=labels)
        if event_type == "session_started":
            self._emit_metric(trace.trace_id, "agent_session_running", 1, labels=labels)
        if event_type == "waiting_for_user_entered":
            self._emit_metric(trace.trace_id, "agent_session_waiting_for_user", 1, labels=labels)
        if event_type == "session_failed":
            self._emit_metric(trace.trace_id, "agent_session_failed_total", 1, labels=labels)
            self._open_alert(trace.trace_id, TraceAlertType.FAILURE_SPIKE, "session failed", scope=TraceAlertScope.SESSION)
        if event_type == "session_partial_success":
            self._emit_metric(trace.trace_id, "agent_session_partial_success_total", 1, labels=labels)
        if event_type == "checkpoint_restored":
            self._emit_metric(trace.trace_id, "checkpoint_restore_total", 1, labels=labels)
        if event_type == "blocked_detected":
            self._emit_metric(trace.trace_id, "workflow_blocked_total", 1, labels=labels)
            self._open_alert(trace.trace_id, TraceAlertType.BLOCKED_SPIKE, "workflow blocked", scope=TraceAlertScope.WORKFLOW)
        if event_type == "degraded_detected":
            self._emit_metric(trace.trace_id, "workflow_degraded_total", 1, labels=labels)
        if event_type == "trace_write_failed":
            self._emit_metric(trace.trace_id, "audit_event_write_failed_total", 1, labels=labels)
            self._open_alert(trace.trace_id, TraceAlertType.AUDIT_WRITE_FAILED, "trace write failed", scope=TraceAlertScope.SYSTEM)

    def _emit_step_metrics(self, trace_id: str, *, step: AgentStep, event_type: str) -> None:
        labels = {"agent_type": step.agent_type}
        if event_type in {"step_succeeded", "step_failed", "step_cancelled", "step_ignored_late_result"}:
            self._emit_metric(trace_id, "agent_step_duration_ms", self._elapsed_ms(step.started_at, step.finished_at), labels=labels)
        if event_type == "step_ignored_late_result":
            self._emit_metric(trace_id, "ignored_late_result_total", 1, labels=labels)
        if event_type == "step_retrying":
            self._emit_metric(trace_id, "retry_attempt_total", 1, labels=labels)
        if event_type == "step_failed":
            self._open_alert(trace_id, TraceAlertType.FAILURE_SPIKE, "step failed", scope=TraceAlertScope.STEP)

    def _emit_metric(self, trace_id: str, metric_name: str, value: float, *, labels: dict[str, str]) -> TraceMetricPoint:
        return self._repository.save_metric(
            TraceMetricPoint(
                metric_id=f"metric_{uuid.uuid4().hex[:12]}",
                trace_id=trace_id,
                metric_name=metric_name,
                metric_value=value,
                labels=dict(labels),
                timestamp=_now(),
            )
        )

    def _open_alert(self, trace_id: str, alert_type: TraceAlertType, summary: str, *, scope: TraceAlertScope) -> TraceAlertRecord:
        alert = self._repository.save_alert(
            TraceAlertRecord(
                alert_id=f"alert_{uuid.uuid4().hex[:12]}",
                trace_id=trace_id,
                scope=scope,
                alert_type=alert_type,
                severity=TraceLevel.WARNING,
                status=TraceAlertStatus.OPEN,
                summary=summary,
                triggered_at=_now(),
            )
        )
        self._emit_metric(trace_id, "trace_alert_open_total", 1, labels={"alert_type": alert_type.value, "scope": scope.value})
        self._save_event_safely(
            AgentTraceEvent(
                event_id=f"traceevt_{uuid.uuid4().hex[:12]}",
                trace_id=trace_id,
                session_id=self.get_trace(trace_id).session_id,
                event_type="alert_triggered",
                event_stage=TraceEventStage.ORCHESTRATION,
                event_time=_now(),
                level=alert.severity,
                summary=summary,
                safe_refs=[f"alert:{alert.alert_id}"],
                payload_digest={"alert_type": alert.alert_type.value, "scope": alert.scope.value},
                correlation_id=trace_id,
            )
        )
        return alert

    def _emit_session_audit_mirror(self, trace: AgentTrace, session: AgentSession, *, event_type: str) -> None:
        mirror = {
            "session_started": "agent_session_started",
            "session_completed": "agent_session_completed",
            "session_failed": "agent_session_failed",
            "session_cancelled": "agent_session_cancelled",
        }.get(event_type)
        if not mirror:
            return
        self.record_audit_event(
            trace_id=trace.trace_id,
            session_id=session.session_id,
            step_id="",
            event_type=mirror,
            summary=event_type,
        )

    def _save_event_safely(
        self,
        event: AgentTraceEvent,
        *,
        critical: bool = False,
        high_risk_user_action: bool = False,
    ) -> AgentTraceEvent:
        try:
            return self._repository.save_event(event)
        except Exception as exc:  # pragma: no cover - exercised by failure injection tests
            self._handle_event_write_failure(event=event, error=exc, critical=critical)
            if critical and high_risk_user_action:
                raise ValueError("critical_audit_write_failed") from exc
            return AgentTraceEvent(
                event_id=f"traceevt_fail_{uuid.uuid4().hex[:8]}",
                trace_id=event.trace_id,
                session_id=event.session_id,
                step_id=event.step_id,
                event_type="trace_write_failed",
                event_stage=TraceEventStage.AUDIT if critical else TraceEventStage.ORCHESTRATION,
                event_time=_now(),
                level=TraceLevel.CRITICAL if critical else TraceLevel.WARNING,
                summary="trace_write_failed",
                safe_refs=event.safe_refs,
                payload_digest={"failed_event_type": event.event_type},
                request_id=event.request_id,
                correlation_id=event.correlation_id,
            )

    def _handle_event_write_failure(self, *, event: AgentTraceEvent, error: Exception, critical: bool) -> None:
        fallback = AgentTraceEvent(
            event_id=f"traceevt_{uuid.uuid4().hex[:12]}",
            trace_id=event.trace_id,
            session_id=event.session_id,
            step_id=event.step_id,
            event_type="trace_write_failed",
            event_stage=TraceEventStage.AUDIT if critical else TraceEventStage.ORCHESTRATION,
            event_time=_now(),
            level=TraceLevel.CRITICAL if critical else TraceLevel.WARNING,
            summary="trace_write_failed",
            safe_refs=event.safe_refs,
            payload_digest={"failed_event_type": event.event_type, "critical": critical, "error": str(error)},
            request_id=event.request_id,
            correlation_id=event.correlation_id,
        )
        try:
            self._repository.save_event(fallback)
        except Exception:
            pass
        if event.trace_id:
            self._emit_metric(
                event.trace_id,
                "audit_event_write_failed_total",
                1,
                labels={"event_type": event.event_type, "critical": str(critical).lower()},
            )
            self._open_alert(
                event.trace_id,
                TraceAlertType.AUDIT_WRITE_FAILED,
                f"trace_write_failed:{event.event_type}",
                scope=TraceAlertScope.SYSTEM,
            )

    def _maybe_record_duplicate_terminal(
        self,
        trace_id: str,
        session_id: str,
        step: AgentStep,
        *,
        event_type: str,
    ) -> AgentTraceEvent | None:
        if event_type not in {"step_succeeded", "step_failed", "step_skipped", "step_cancelled", "step_ignored_late_result"}:
            return None
        existing = self._repository.list_events(trace_id, step_id=step.step_id)
        terminal_existing = [
            item
            for item in existing
            if item.event_type == event_type
            and int(item.payload_digest.get("attempt_no", step.attempt_count) or step.attempt_count) == step.attempt_count
            and item.event_type != "duplicate_ignored"
        ]
        if not terminal_existing:
            return None
        return self._save_event_safely(
            AgentTraceEvent(
                event_id=f"traceevt_{uuid.uuid4().hex[:12]}",
                trace_id=trace_id,
                session_id=session_id,
                step_id=step.step_id,
                event_type="duplicate_ignored",
                event_stage=self._stage_for_step(step),
                event_time=_now(),
                level=TraceLevel.INFO,
                summary="duplicate_ignored",
                safe_refs=[f"step:{step.step_id}"],
                payload_digest={"ignored_event_type": event_type, "attempt_no": step.attempt_count},
                request_id=step.request_id,
                correlation_id=trace_id,
            )
        )

    @staticmethod
    def _append_unique(items: list[str], value: str) -> list[str]:
        if not value or value in items:
            return list(items)
        return [*items, value]

    @staticmethod
    def _trace_end_time(trace: AgentTrace, session: AgentSession) -> str:
        return session.finished_at or session.cancelled_at or trace.ended_at

    @staticmethod
    def _trace_status_for_session(session: AgentSession) -> AgentTraceStatus:
        mapping = {
            "running": AgentTraceStatus.RUNNING,
            "waiting_for_user": AgentTraceStatus.WAITING_FOR_USER,
            "completed": AgentTraceStatus.COMPLETED,
            "partial_success": AgentTraceStatus.PARTIAL_SUCCESS,
            "failed": AgentTraceStatus.FAILED,
            "cancelled": AgentTraceStatus.CANCELLED,
            "cancelling": AgentTraceStatus.RUNNING,
            "paused": AgentTraceStatus.RUNNING,
            "pending": AgentTraceStatus.RUNNING,
        }
        return mapping.get(session.status.value, AgentTraceStatus.RUNNING)

    @staticmethod
    def _stage_for_step(step: AgentStep) -> TraceEventStage:
        phase = str(step.step_phase or "")
        mapping = {
            "perception": TraceEventStage.PERCEPTION,
            "planning": TraceEventStage.PLANNING,
            "action": TraceEventStage.ACTION,
            "observation": TraceEventStage.OBSERVATION,
        }
        return mapping.get(phase, TraceEventStage.ORCHESTRATION)

    @staticmethod
    def _elapsed_ms(started_at: str | datetime | None, ended_at: str | datetime | None) -> int:
        if not started_at or not ended_at:
            return 0
        start_value = datetime.fromisoformat(started_at) if isinstance(started_at, str) else started_at
        end_value = datetime.fromisoformat(ended_at) if isinstance(ended_at, str) else ended_at
        return max(int((end_value - start_value).total_seconds() * 1000), 0)
