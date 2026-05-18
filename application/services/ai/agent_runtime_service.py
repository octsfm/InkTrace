from __future__ import annotations

import uuid
from datetime import UTC, datetime

from application.services.ai.ai_job_service import AIJobService
from application.services.ai.tool_facade import CoreToolFacade, ToolExecutionContext
from domain.entities.ai.models import (
    AgentObservation,
    AgentObservationType,
    PPAOPhase,
    AgentResult,
    AgentRunContext,
    AgentSession,
    AgentSessionStatus,
    AgentStep,
    AgentStepStatus,
    AgentWorkflowType,
    AIJobAttemptStatus,
    ResultRef,
    StepPlan,
    StepSummary,
    StepSummaryItem,
    ToolCallRef,
)
from domain.repositories.ai.agent_observation_repository import AgentObservationRepository
from domain.repositories.ai.agent_session_repository import AgentSessionRepository
from domain.repositories.ai.agent_step_repository import AgentStepRepository


class AgentRuntimeService:
    _NON_RETRYABLE_STEP_TYPES = {"formal_write", "apply_candidate", "memory_formalize"}
    _NON_RETRYABLE_ACTIONS = {"formal_chapter_write", "apply_candidate_to_draft", "memory_formalize"}

    def __init__(
        self,
        *,
        session_repository: AgentSessionRepository,
        step_repository: AgentStepRepository,
        observation_repository: AgentObservationRepository,
        ai_job_service: AIJobService,
        tool_facade: CoreToolFacade | None = None,
    ) -> None:
        self._session_repository = session_repository
        self._step_repository = step_repository
        self._observation_repository = observation_repository
        self._ai_job_service = ai_job_service
        self._tool_facade = tool_facade

    def create_session(
        self,
        *,
        work_id: str,
        chapter_id: str | None,
        agent_workflow_type: AgentWorkflowType,
        user_instruction: str,
        request_id: str = "",
        trace_id: str = "",
        caller_type: str,
        allow_degraded: bool = True,
    ) -> AgentSession:
        now = self._now()
        effective_request_id = request_id or f"req_{uuid.uuid4().hex[:12]}"
        effective_trace_id = trace_id or f"trace_{uuid.uuid4().hex[:12]}"
        job = self._ai_job_service.create_job(
            job_type="agent_session",
            work_id=work_id,
            chapter_id=chapter_id,
            created_by=caller_type,
            payload={"request_id": effective_request_id, "trace_id": effective_trace_id},
        )
        session = AgentSession(
            session_id=f"agent_session_{uuid.uuid4().hex[:12]}",
            job_id=job.job_id,
            work_id=work_id,
            chapter_id=chapter_id,
            agent_workflow_type=agent_workflow_type,
            status=AgentSessionStatus.PENDING,
            allow_degraded=allow_degraded,
            caller_type=caller_type,
            user_instruction=user_instruction,
            request_id=effective_request_id,
            trace_id=effective_trace_id,
            created_at=now,
            updated_at=now,
            metadata={"allow_degraded": allow_degraded},
        )
        return self._session_repository.create_session(session)

    def get_session(self, session_id: str) -> AgentSession:
        return self._session_repository.get_session(session_id)

    def start_session(self, session_id: str) -> AgentSession:
        session = self.get_session(session_id)
        if session.status != AgentSessionStatus.PENDING:
            raise ValueError("session_not_startable")
        self._ai_job_service.start_job(session.job_id)
        now = self._now()
        updated = session.model_copy(
            update={
                "status": AgentSessionStatus.RUNNING,
                "started_at": session.started_at or now,
                "updated_at": now,
                "paused_at": "",
                "waiting_at": "",
                "status_reason": "",
                "current_phase": "",
            }
        )
        return self._session_repository.save_session(updated)

    def pause_session(self, session_id: str, *, reason: str = "pause_requested") -> AgentSession:
        session = self.get_session(session_id)
        if session.status not in {AgentSessionStatus.RUNNING, AgentSessionStatus.WAITING_FOR_USER}:
            raise ValueError("session_not_pausable")
        self._ai_job_service.pause_job(session.job_id, reason=reason)
        now = self._now()
        updated = session.model_copy(
            update={
                "status": AgentSessionStatus.PAUSED,
                "paused_at": now,
                "updated_at": now,
                "status_reason": reason,
            }
        )
        return self._session_repository.save_session(updated)

    def resume_session(self, session_id: str) -> AgentSession:
        session = self.get_session(session_id)
        if session.status != AgentSessionStatus.PAUSED:
            raise ValueError("session_not_resumable")
        steps = self._step_repository.list_steps(session_id)
        if any(step.status == AgentStepStatus.WAITING_USER for step in steps):
            raise ValueError("waiting_user_decision_required")
        self._ai_job_service.start_job(session.job_id)
        now = self._now()
        updated = session.model_copy(
            update={
                "status": AgentSessionStatus.RUNNING,
                "paused_at": "",
                "resumed_at": now,
                "updated_at": now,
                "status_reason": "",
            }
        )
        return self._session_repository.save_session(updated)

    def cancel_session(self, session_id: str, *, reason: str) -> AgentSession:
        session = self.get_session(session_id)
        if session.status not in {
            AgentSessionStatus.PENDING,
            AgentSessionStatus.RUNNING,
            AgentSessionStatus.WAITING_FOR_USER,
            AgentSessionStatus.PAUSED,
        }:
            raise ValueError("session_not_cancellable")
        now = self._now()
        cancelling = session.model_copy(
            update={
                "status": AgentSessionStatus.CANCELLING,
                "cancelling_at": now,
                "updated_at": now,
                "status_reason": reason,
            }
        )
        self._session_repository.save_session(cancelling)
        for step in self._step_repository.list_steps(session_id):
            if step.status in {
                AgentStepStatus.PENDING,
                AgentStepStatus.RUNNING,
                AgentStepStatus.WAITING_OBSERVATION,
                AgentStepStatus.WAITING_USER,
            }:
                if step.job_step_id:
                    self._ai_job_service.mark_step_failed(
                        session.job_id,
                        step.job_step_id,
                        error_code="step_cancelled",
                        error_message=reason,
                    )
                self._step_repository.save_step(
                    step.model_copy(
                        update={
                            "status": AgentStepStatus.CANCELLED,
                            "status_reason": reason,
                            "waiting_at": "",
                            "finished_at": step.finished_at or now,
                            "metadata": self._clear_current_attempt(step.metadata),
                        }
                    )
                )
        self._ai_job_service.cancel_job(session.job_id, reason=reason)
        steps = self._step_repository.list_steps(session_id)
        step_counts = self._build_step_counts(steps)
        updated = cancelling.model_copy(
            update={
                "status": AgentSessionStatus.CANCELLED,
                "cancelled_at": self._now(),
                "updated_at": self._now(),
                "finished_at": session.finished_at or self._now(),
                "result": AgentResult(
                    session_id=session.session_id,
                    status="cancelled",
                    result_refs=[],
                    step_summary=self._build_step_summary(steps),
                    warning_codes=list(session.warning_codes),
                    error_code="",
                    error_message="",
                    total_steps=step_counts["total_steps"],
                    succeeded_steps=step_counts["succeeded_steps"],
                    failed_steps=step_counts["failed_steps"],
                    skipped_steps=step_counts["skipped_steps"],
                    finished_at=now,
                ),
                "current_step_id": "",
                "current_phase": "",
                "current_agent_type": "",
            }
        )
        return self._session_repository.save_session(updated)

    def fail_session(self, session_id: str, *, error_code: str, error_message: str) -> AgentSession:
        session = self.get_session(session_id)
        if session.status not in {
            AgentSessionStatus.RUNNING,
            AgentSessionStatus.WAITING_FOR_USER,
            AgentSessionStatus.PAUSED,
            AgentSessionStatus.CANCELLING,
        }:
            raise ValueError("session_not_failable")
        now = self._now()
        for step in self._step_repository.list_steps(session_id):
            if step.status in {
                AgentStepStatus.PENDING,
                AgentStepStatus.RUNNING,
                AgentStepStatus.WAITING_OBSERVATION,
                AgentStepStatus.WAITING_USER,
            }:
                if step.job_step_id:
                    self._ai_job_service.mark_step_failed(
                        session.job_id,
                        step.job_step_id,
                        error_code=error_code,
                        error_message=error_message,
                    )
                self._step_repository.save_step(
                    step.model_copy(
                        update={
                            "status": AgentStepStatus.FAILED,
                            "status_reason": "session_failed",
                            "error_code": error_code,
                            "error_message": error_message,
                            "waiting_at": "",
                            "finished_at": step.finished_at or now,
                            "metadata": self._clear_current_attempt(step.metadata),
                        }
                    )
                )
        self._ai_job_service.mark_job_failed(session.job_id, error_code=error_code, error_message=error_message)
        steps = self._step_repository.list_steps(session_id)
        step_counts = self._build_step_counts(steps)
        updated = session.model_copy(
            update={
                "status": AgentSessionStatus.FAILED,
                "status_reason": "",
                "error_code": error_code,
                "error_message": error_message,
                "result": AgentResult(
                    session_id=session.session_id,
                    status="failed",
                    result_refs=[],
                    step_summary=self._build_step_summary(steps),
                    warning_codes=list(session.warning_codes),
                    error_code=error_code,
                    error_message=error_message,
                    next_user_action="",
                    total_steps=step_counts["total_steps"],
                    succeeded_steps=step_counts["succeeded_steps"],
                    failed_steps=step_counts["failed_steps"],
                    skipped_steps=step_counts["skipped_steps"],
                    total_elapsed_ms=self._compute_elapsed_ms(session.started_at, now),
                    finished_at=now,
                ),
                "updated_at": now,
                "finished_at": now,
                "current_step_id": "",
                "current_phase": "",
                "current_agent_type": "",
            }
        )
        return self._session_repository.save_session(updated)

    def complete_session(
        self,
        session_id: str,
        *,
        result_ref: str = "",
        warning_codes: list[str] | None = None,
        partial_success: bool = False,
    ) -> AgentSession:
        session = self.get_session(session_id)
        if session.status != AgentSessionStatus.RUNNING:
            raise ValueError("session_not_completable")
        incomplete_steps = [
            step
            for step in self._step_repository.list_steps(session_id)
            if step.status
            not in {
                AgentStepStatus.SUCCEEDED,
                AgentStepStatus.FAILED,
                AgentStepStatus.SKIPPED,
                AgentStepStatus.CANCELLED,
                AgentStepStatus.IGNORED_LATE_RESULT,
            }
        ]
        if incomplete_steps:
            raise ValueError("session_has_incomplete_steps")
        warnings = self._merge_warning_codes(session.warning_codes, list(warning_codes or []))
        steps = self._step_repository.list_steps(session_id)
        step_counts = self._build_step_counts(steps)
        primary_output = self._parse_primary_output(result_ref)
        if partial_success:
            if not result_ref:
                raise ValueError("partial_success_requires_result_ref")
            if steps and all(step.status == AgentStepStatus.SUCCEEDED for step in steps) and not warnings:
                raise ValueError("partial_success_not_applicable")
            self._ai_job_service.mark_job_completed(
                session.job_id,
                result_summary={"completion_mode": "partial_success", "warning_codes": warnings},
                result_ref=result_ref,
            )
            status = AgentSessionStatus.PARTIAL_SUCCESS
        else:
            if steps and any(step.status != AgentStepStatus.SUCCEEDED for step in steps):
                raise ValueError("session_not_completable")
            self._ai_job_service.mark_job_completed(
                session.job_id,
                result_summary={"warning_codes": warnings},
                result_ref=result_ref,
            )
            status = AgentSessionStatus.COMPLETED
        now = self._now()
        updated = session.model_copy(
            update={
                "status": status,
                "status_reason": "",
                "result_ref": result_ref,
                "result": AgentResult(
                    session_id=session.session_id,
                    status="partial_success" if partial_success else "success",
                    result_refs=self._build_result_refs(
                        result_ref,
                        steps=steps,
                        result_status="partial_success" if partial_success else "success",
                    ),
                    primary_output_type=primary_output["primary_output_type"],
                    primary_output_ref=primary_output["primary_output_ref"],
                    step_summary=self._build_step_summary(steps),
                    warning_codes=warnings,
                    error_code="",
                    error_message="",
                    next_user_action="",
                    total_steps=step_counts["total_steps"],
                    succeeded_steps=step_counts["succeeded_steps"],
                    failed_steps=step_counts["failed_steps"],
                    skipped_steps=step_counts["skipped_steps"],
                    total_elapsed_ms=self._compute_elapsed_ms(session.started_at, now),
                    finished_at=now,
                ),
                "warning_codes": warnings,
                "updated_at": now,
                "finished_at": now,
                "error_code": "",
                "error_message": "",
                "current_step_id": "",
                "current_phase": "",
                "current_agent_type": "",
            }
        )
        return self._session_repository.save_session(updated)

    def retry_session(self, session_id: str) -> AgentSession:
        session = self.get_session(session_id)
        if session.status not in {AgentSessionStatus.FAILED, AgentSessionStatus.PARTIAL_SUCCESS}:
            raise ValueError("session_not_retryable")
        metadata = dict(session.metadata)
        metadata["retry_of_session_id"] = session.session_id
        next_request_id = f"req_{uuid.uuid4().hex[:12]}"
        next_trace_id = f"trace_{uuid.uuid4().hex[:12]}"
        retried = self.create_session(
            work_id=session.work_id,
            chapter_id=session.chapter_id,
            agent_workflow_type=session.workflow_type,
            user_instruction=session.user_instruction,
            request_id=next_request_id,
            trace_id=next_trace_id,
            caller_type=session.caller_type,
        )
        updated = retried.model_copy(update={"metadata": metadata, "updated_at": self._now()})
        return self._session_repository.save_session(updated)

    def create_step(self, session_id: str, *, agent_type: str, step_type: str, action: str) -> AgentStep:
        session = self.get_session(session_id)
        order_index = len(self._step_repository.list_steps(session_id)) + 1
        now = self._now()
        step_flags = self._resolve_step_runtime_flags(step_type=step_type, action=action)
        job_step = self._ai_job_service.add_step(
            session.job_id,
            step_type=f"agent_step:{agent_type}:{action}",
            step_name=action,
            metadata={"agent_type": agent_type},
        )
        step = AgentStep(
            step_id=f"agent_step_{uuid.uuid4().hex[:12]}",
            session_id=session_id,
            job_id=session.job_id,
            job_step_id=job_step.step_id,
            agent_type=agent_type,
            step_type=step_type,
            action=action,
            order_index=order_index,
            status=AgentStepStatus.PENDING,
            request_id=session.request_id,
            trace_id=session.trace_id,
            retryable=step_flags["retryable"],
            skippable=step_flags["skippable"],
            requires_user_decision=step_flags["requires_user_decision"],
            created_at=now,
        )
        return self._step_repository.create_step(step)

    def get_step(self, step_id: str) -> AgentStep:
        return self._step_repository.get_step(step_id)

    def build_run_context(
        self,
        session_id: str,
        *,
        step_id: str = "",
        current_agent_type: str,
        context_refs: list[str] | None = None,
        allow_degraded: bool | None = None,
    ) -> AgentRunContext:
        session = self.get_session(session_id)
        step = self.get_step(step_id) if step_id else None
        return AgentRunContext(
            session_id=session.session_id,
            job_id=session.job_id,
            step_id=step_id,
            work_id=session.work_id,
            chapter_id=session.chapter_id,
            agent_workflow_type=session.agent_workflow_type,
            current_agent_type=current_agent_type,
            current_phase=session.current_phase,
            caller_type=session.caller_type,
            user_instruction=session.user_instruction,
            context_refs=list(context_refs or []),
            request_id=step.request_id if step is not None else session.request_id,
            trace_id=session.trace_id,
            allow_degraded=session.allow_degraded if allow_degraded is None else allow_degraded,
            warning_codes=list(session.warning_codes),
            resource_scope_refs=self._build_resource_scope_refs(session.work_id, session.chapter_id),
            prior_observation_refs=list(step.prior_observation_refs) if step is not None else [],
            execution_guard_flags={},
            metadata=dict(session.metadata),
        )

    def build_tool_execution_context(
        self,
        session_id: str,
        *,
        step_id: str,
        agent_type: str,
        side_effect_level: str,
        resource_scope_refs: list[str] | None = None,
    ) -> ToolExecutionContext:
        session = self.get_session(session_id)
        step = self.get_step(step_id)
        scope_refs = list(resource_scope_refs or [f"work:{session.work_id}"])
        if not resource_scope_refs and session.chapter_id:
            scope_refs.append(f"chapter:{session.chapter_id}")
        return ToolExecutionContext(
            caller_type="agent",
            work_id=session.work_id,
            chapter_id=session.chapter_id or "",
            request_id=step.request_id,
            trace_id=session.trace_id,
            agent_session_id=session.session_id,
            agent_step_id=step.step_id,
            agent_type=agent_type,
            session_status=session.status.value,
            step_status=step.status.value,
            resource_scope_refs=scope_refs,
            side_effect_level=side_effect_level,
            idempotency_key=f"{step.step_id}:{step.request_id}",
        )

    def record_user_decision(
        self,
        session_id: str,
        *,
        step_id: str,
        decision: str,
        safe_message: str,
        request_id: str,
        metadata: dict[str, object] | None = None,
    ) -> AgentObservation:
        session = self.get_session(session_id)
        return self.record_observation(
            step_id,
            AgentObservation(
                observation_id=f"obs_user_{uuid.uuid4().hex[:12]}",
                session_id=session_id,
                step_id=step_id,
                observation_type=AgentObservationType.USER_DECISION,
                source_type="user",
                status="success",
                safe_message=safe_message,
                summary=safe_message,
                decision=decision,
                decision_reason=decision,
                trace_id=session.trace_id,
                request_id=request_id,
                metadata=dict(metadata or {}),
            ),
        )

    def run_next_step(self, session_id: str) -> AgentStep:
        session = self.get_session(session_id)
        if session.status != AgentSessionStatus.RUNNING:
            raise ValueError("session_not_runnable")
        pending_step = next((item for item in self._step_repository.list_steps(session_id) if item.status == AgentStepStatus.PENDING), None)
        if pending_step is None:
            raise ValueError("step_not_found")
        now = self._now()
        updated = pending_step.model_copy(
            update={
                "status": AgentStepStatus.RUNNING,
                "status_reason": "step_started",
                "step_phase": PPAOPhase.PERCEPTION,
                "started_at": pending_step.started_at or now,
                "waiting_at": "",
            }
        )
        if pending_step.job_step_id:
            self._ai_job_service.mark_step_running(session.job_id, pending_step.job_step_id)
        saved = self._step_repository.save_step(updated)
        saved = self._start_job_attempt(saved)
        self._session_repository.save_session(
            session.model_copy(
                update={
                    "current_step_id": saved.step_id,
                    "current_agent_type": saved.agent_type,
                    "current_phase": PPAOPhase.PERCEPTION,
                    "updated_at": now,
                }
            )
        )
        return saved

    def execute_tool_action(
        self,
        session_id: str,
        *,
        step_id: str,
        agent_type: str,
        tool_name: str,
        payload: dict[str, object],
        side_effect_level: str,
        resource_scope_refs: list[str] | None = None,
        success_decision: str = "continue",
    ) -> AgentObservation:
        if self._tool_facade is None:
            raise ValueError("tool_facade_not_configured")
        step = self.get_step(step_id)
        session = self.get_session(session_id)
        if session.status != AgentSessionStatus.RUNNING:
            raise ValueError("session_not_actionable")
        if step.step_phase != "action" or step.status != AgentStepStatus.RUNNING:
            raise ValueError("step_not_ready_for_action")
        now = self._now()
        tool_call_id = f"tool_call_{uuid.uuid4().hex[:12]}"
        self._step_repository.save_step(
            step.model_copy(
                update={
                    "status": AgentStepStatus.WAITING_OBSERVATION,
                    "step_phase": PPAOPhase.OBSERVATION,
                    "status_reason": "awaiting_observation",
                    "waiting_at": now,
                    "tool_calls": [*step.tool_calls, ToolCallRef(tool_call_id=tool_call_id, tool_name=tool_name, status="running")],
                }
            )
        )
        self._session_repository.save_session(
            session.model_copy(
                update={
                    "current_step_id": step.step_id,
                    "current_agent_type": step.agent_type,
                    "current_phase": PPAOPhase.OBSERVATION,
                    "updated_at": now,
                }
            )
        )
        tool_context = self.build_tool_execution_context(
            session_id,
            step_id=step_id,
            agent_type=agent_type,
            side_effect_level=side_effect_level,
            resource_scope_refs=resource_scope_refs,
        )
        result = self._tool_facade.call(tool_name, context=tool_context, payload=payload)
        decision = success_decision if result.ok else ("retry_step" if result.error and result.error.retryable else "fail_step")
        observation = AgentObservation(
            observation_id=f"obs_{uuid.uuid4().hex[:12]}",
            session_id=session_id,
            step_id=step_id,
            observation_type=AgentObservationType.TOOL_RESULT,
            source_type="tool",
            status="success" if result.ok else "failed",
            safe_message=result.safe_message or tool_name,
            summary=result.safe_message or tool_name,
            decision=decision,
            decision_reason=decision,
            source_tool_call_id=tool_call_id,
            warning_codes=list(result.warnings),
            error_code=result.error_code,
            error_message=result.safe_message if not result.ok else "",
            request_id=tool_context.request_id,
            trace_id=tool_context.trace_id,
            metadata={
                "tool_name": tool_name,
                "result_ref": str(result.payload.get("result_ref", "")) if isinstance(result.payload, dict) else "",
                "resource_scope_refs": list(tool_context.resource_scope_refs),
            },
        )
        return self.record_observation(step_id, observation)

    def retry_step(self, step_id: str, *, request_id: str) -> AgentStep:
        step = self.get_step(step_id)
        if step.status != AgentStepStatus.FAILED:
            raise ValueError("step_not_retryable")
        if step.step_type in self._NON_RETRYABLE_STEP_TYPES or step.action in self._NON_RETRYABLE_ACTIONS:
            raise ValueError("step_retry_forbidden")
        if step.attempt_count >= step.max_attempts:
            raise ValueError("step_attempt_limit_reached")
        if step.job_step_id:
            self._ai_job_service.retry_step(step.job_id, step.job_step_id)
        prior_refs = [*step.prior_observation_refs]
        if step.observation_id:
            prior_refs.append(step.observation_id)
        updated = step.model_copy(
            update={
                "status": AgentStepStatus.PENDING,
                "attempt_count": step.attempt_count + 1,
                "request_id": request_id,
                "observation_id": "",
                "prior_observation_refs": prior_refs,
                "started_at": "",
                "step_phase": "",
                "error_code": "",
                "error_message": "",
                "status_reason": "retry_requested",
                "waiting_at": "",
                "finished_at": "",
                "metadata": self._clear_current_attempt(step.metadata),
            }
        )
        return self._step_repository.save_step(updated)

    def mark_late_result_ignored(self, step_id: str, *, safe_message: str, tool_call_id: str = "") -> AgentObservation:
        step = self.get_step(step_id)
        session = self.get_session(step.session_id)
        if session.status != AgentSessionStatus.CANCELLED or step.status not in {
            AgentStepStatus.CANCELLED,
            AgentStepStatus.IGNORED_LATE_RESULT,
        }:
            raise ValueError("late_result_not_ignorable")
        now = self._now()
        observation = AgentObservation(
            observation_id=f"obs_{uuid.uuid4().hex[:12]}",
            session_id=session.session_id,
            step_id=step.step_id,
            observation_type=AgentObservationType.LATE_RESULT_IGNORED,
            source_type="system",
            status="ignored",
            safe_message=safe_message,
            request_id=session.request_id,
            trace_id=session.trace_id,
            metadata={"tool_call_id": tool_call_id},
            created_at=now,
        )
        saved = self._observation_repository.create_observation(observation)
        prior_refs = [*step.prior_observation_refs]
        if step.observation_id:
            prior_refs.append(step.observation_id)
        self._step_repository.save_step(
            step.model_copy(
                update={
                    "status": AgentStepStatus.IGNORED_LATE_RESULT,
                    "status_reason": "late_result_ignored",
                    "observation_id": saved.observation_id,
                    "prior_observation_refs": prior_refs,
                    "finished_at": step.finished_at or now,
                }
            )
        )
        return saved

    def recover_after_restart(self) -> list[str]:
        recovered_ids: list[str] = []
        self._ai_job_service.recover_after_restart()
        for session in self._session_repository.list_sessions(status=AgentSessionStatus.RUNNING.value):
            now = self._now()
            paused = session.model_copy(
                update={
                    "status": AgentSessionStatus.PAUSED,
                    "paused_at": now,
                    "updated_at": now,
                    "status_reason": "service_restarted",
                }
            )
            self._session_repository.save_session(paused)
            recovered_ids.append(session.session_id)
        return recovered_ids

    def record_observation(self, step_id: str, observation: AgentObservation) -> AgentObservation:
        step = self.get_step(step_id)
        session = self.get_session(step.session_id)
        now = self._now()
        if (
            session.status == AgentSessionStatus.CANCELLED
            and step.status in {AgentStepStatus.CANCELLED, AgentStepStatus.IGNORED_LATE_RESULT}
        ):
            pass
        elif step.status in {
            AgentStepStatus.SUCCEEDED,
            AgentStepStatus.FAILED,
            AgentStepStatus.SKIPPED,
            AgentStepStatus.IGNORED_LATE_RESULT,
        }:
            raise ValueError("step_not_observable")
        stored_observation = observation.model_copy(update={"created_at": observation.created_at or now})
        saved_observation = self._observation_repository.create_observation(stored_observation)
        prior_refs = [*step.prior_observation_refs]
        if step.observation_id:
            prior_refs.append(step.observation_id)
        merged_step_warnings = self._merge_warning_codes(step.warning_codes, saved_observation.warning_codes)
        merged_session_warnings = self._merge_warning_codes(session.warning_codes, saved_observation.warning_codes)

        if session.status == AgentSessionStatus.CANCELLED:
            self._finish_job_attempt(
                step,
                status=AIJobAttemptStatus.IGNORED,
                error_code="ignored_late_result",
                error_message=saved_observation.safe_message,
            )
            self._step_repository.save_step(
                step.model_copy(
                    update={
                        "status": AgentStepStatus.IGNORED_LATE_RESULT,
                        "status_reason": "ignored_late_result",
                        "observation_id": saved_observation.observation_id,
                        "prior_observation_refs": prior_refs,
                        "warning_codes": merged_step_warnings,
                        "tool_calls": self._finalize_tool_calls(
                            step.tool_calls,
                            source_tool_call_id=saved_observation.source_tool_call_id,
                            status="ignored",
                            result_ref=str(saved_observation.metadata.get("result_ref", "")),
                            error_code=saved_observation.error_code,
                        ),
                        "output_refs": self._merge_output_refs(
                            step.output_refs,
                            str(saved_observation.metadata.get("result_ref", "")),
                        ),
                        "waiting_at": "",
                        "finished_at": now,
                        "metadata": self._clear_current_attempt(step.metadata),
                    }
                )
            )
            return saved_observation
        if session.status == AgentSessionStatus.PAUSED:
            self._step_repository.save_step(
                step.model_copy(
                    update={
                        "observation_id": saved_observation.observation_id,
                        "prior_observation_refs": prior_refs,
                        "warning_codes": merged_step_warnings,
                        "tool_calls": self._finalize_tool_calls(
                            step.tool_calls,
                            source_tool_call_id=saved_observation.source_tool_call_id,
                            status=saved_observation.status,
                            result_ref=str(saved_observation.metadata.get("result_ref", "")),
                            error_code=saved_observation.error_code,
                        ),
                        "output_refs": self._merge_output_refs(
                            step.output_refs,
                            str(saved_observation.metadata.get("result_ref", "")),
                        ),
                    }
                )
            )
            self._session_repository.save_session(
                session.model_copy(
                    update={
                        "current_step_id": step.step_id,
                        "current_agent_type": step.agent_type,
                    "current_phase": PPAOPhase.OBSERVATION,
                        "warning_codes": merged_session_warnings,
                        "updated_at": now,
                    }
                )
            )
            return saved_observation

        if session.status == AgentSessionStatus.WAITING_FOR_USER or step.status == AgentStepStatus.WAITING_USER:
            if (
                saved_observation.observation_type != AgentObservationType.USER_DECISION
                or saved_observation.source_type != "user"
            ):
                raise ValueError("waiting_user_decision_required")
            session = session.model_copy(
                update={
                    "status": AgentSessionStatus.RUNNING,
                    "waiting_at": "",
                    "status_reason": "",
                    "updated_at": now,
                }
            )

        if saved_observation.decision == "wait_for_user":
            updated_step = step.model_copy(
                update={
                    "status": AgentStepStatus.WAITING_USER,
                    "status_reason": "wait_for_user",
                    "step_phase": PPAOPhase.OBSERVATION,
                    "observation_id": saved_observation.observation_id,
                    "prior_observation_refs": prior_refs,
                    "warning_codes": merged_step_warnings,
                    "tool_calls": self._finalize_tool_calls(
                        step.tool_calls,
                        source_tool_call_id=saved_observation.source_tool_call_id,
                        status=saved_observation.status,
                        result_ref=str(saved_observation.metadata.get("result_ref", "")),
                        error_code=saved_observation.error_code,
                    ),
                    "output_refs": self._merge_output_refs(
                        step.output_refs,
                        str(saved_observation.metadata.get("result_ref", "")),
                    ),
                    "waiting_at": now,
                    "finished_at": "",
                }
            )
            updated_session = session.model_copy(
                update={
                    "status": AgentSessionStatus.WAITING_FOR_USER,
                    "waiting_at": now,
                    "updated_at": now,
                    "status_reason": "wait_for_user",
                    "current_step_id": step.step_id,
                    "current_agent_type": step.agent_type,
                    "current_phase": PPAOPhase.OBSERVATION,
                    "warning_codes": merged_session_warnings,
                }
            )
            self._step_repository.save_step(updated_step)
            self._session_repository.save_session(updated_session)
        elif saved_observation.decision == "continue":
            if saved_observation.observation_type == AgentObservationType.VALIDATION_RESULT:
                self._finish_job_attempt(step, status=AIJobAttemptStatus.COMPLETED)
                if step.job_step_id:
                    self._ai_job_service.mark_step_completed(step.job_id, step.job_step_id, summary=saved_observation.safe_message)
                self._step_repository.save_step(
                    step.model_copy(
                        update={
                            "status": AgentStepStatus.SUCCEEDED,
                            "status_reason": "validation_completed",
                            "step_phase": PPAOPhase.OBSERVATION,
                            "observation_id": saved_observation.observation_id,
                            "prior_observation_refs": prior_refs,
                            "warning_codes": merged_step_warnings,
                            "step_plan": self._build_step_plan(step, next_phase="observation"),
                            "tool_calls": self._finalize_tool_calls(
                                step.tool_calls,
                                source_tool_call_id=saved_observation.source_tool_call_id,
                                status=saved_observation.status,
                                result_ref=str(saved_observation.metadata.get("result_ref", "")),
                                error_code=saved_observation.error_code,
                            ),
                            "output_refs": self._merge_output_refs(
                                step.output_refs,
                                str(saved_observation.metadata.get("result_ref", "")),
                            ),
                            "waiting_at": "",
                            "finished_at": now,
                            "error_code": "",
                            "error_message": "",
                            "metadata": self._clear_current_attempt(step.metadata),
                        }
                    )
                )
                self._session_repository.save_session(
                    session.model_copy(
                        update={
                            "current_step_id": step.step_id,
                            "current_agent_type": step.agent_type,
                            "current_phase": PPAOPhase.OBSERVATION,
                            "warning_codes": merged_session_warnings,
                            "updated_at": now,
                        }
                    )
                )
                return saved_observation
            next_phase = self._next_phase_after_continue(step.step_phase)
            self._step_repository.save_step(
                step.model_copy(
                    update={
                        "status": AgentStepStatus.RUNNING,
                        "status_reason": "continue",
                        "step_phase": next_phase,
                        "observation_id": saved_observation.observation_id,
                        "prior_observation_refs": prior_refs,
                        "warning_codes": merged_step_warnings,
                        "step_plan": self._build_step_plan(step, next_phase=next_phase),
                        "tool_calls": self._finalize_tool_calls(
                            step.tool_calls,
                            source_tool_call_id=saved_observation.source_tool_call_id,
                            status=saved_observation.status,
                            result_ref=str(saved_observation.metadata.get("result_ref", "")),
                            error_code=saved_observation.error_code,
                        ),
                        "output_refs": self._merge_output_refs(
                            step.output_refs,
                            str(saved_observation.metadata.get("result_ref", "")),
                        ),
                        "waiting_at": "",
                        "error_code": "",
                        "error_message": "",
                    }
                )
            )
            self._session_repository.save_session(
                session.model_copy(
                    update={
                        "current_step_id": step.step_id,
                        "current_agent_type": step.agent_type,
                        "current_phase": next_phase,
                        "warning_codes": merged_session_warnings,
                        "updated_at": now,
                    }
                )
            )
        elif saved_observation.decision == "retry_step":
            if (
                saved_observation.observation_type == AgentObservationType.TIMEOUT
                and saved_observation.error_code in {"provider_timeout", "provider_rate_limited", "provider_unavailable"}
                and step.attempt_count >= 1
            ):
                self._finish_job_attempt(
                    step,
                    status=AIJobAttemptStatus.FAILED,
                    error_code=saved_observation.error_code,
                    error_message=saved_observation.safe_message,
                    retry_reason="provider_retry_exhausted",
                )
                if step.job_step_id:
                    self._ai_job_service.mark_step_failed(
                        step.job_id,
                        step.job_step_id,
                        error_code=saved_observation.error_code or "provider_timeout",
                        error_message=saved_observation.safe_message,
                    )
                self._step_repository.save_step(
                    step.model_copy(
                        update={
                            "status": AgentStepStatus.FAILED,
                            "status_reason": "provider_retry_exhausted",
                            "step_phase": PPAOPhase.OBSERVATION,
                            "observation_id": saved_observation.observation_id,
                            "prior_observation_refs": prior_refs,
                            "warning_codes": merged_step_warnings,
                            "waiting_at": "",
                            "finished_at": now,
                            "error_code": saved_observation.error_code,
                            "error_message": saved_observation.safe_message,
                            "metadata": self._clear_current_attempt(step.metadata),
                        }
                    )
                )
                self._session_repository.save_session(
                    session.model_copy(
                        update={
                            "current_step_id": step.step_id,
                            "current_phase": PPAOPhase.OBSERVATION,
                            "warning_codes": merged_session_warnings,
                            "updated_at": now,
                        }
                    )
                )
                return saved_observation
            if (
                saved_observation.observation_type == AgentObservationType.VALIDATION_RESULT
                and saved_observation.error_code in {"validation_error", "output_validation_failed"}
                and step.attempt_count >= 2
            ):
                self._finish_job_attempt(
                    step,
                    status=AIJobAttemptStatus.FAILED,
                    error_code=saved_observation.error_code,
                    error_message=saved_observation.safe_message,
                    retry_reason="validation_retry_exhausted",
                )
                if step.job_step_id:
                    self._ai_job_service.mark_step_failed(
                        step.job_id,
                        step.job_step_id,
                        error_code=saved_observation.error_code or "validation_error",
                        error_message=saved_observation.safe_message,
                    )
                self._step_repository.save_step(
                    step.model_copy(
                        update={
                            "status": AgentStepStatus.FAILED,
                            "status_reason": "validation_retry_exhausted",
                            "step_phase": PPAOPhase.OBSERVATION,
                            "observation_id": saved_observation.observation_id,
                            "prior_observation_refs": prior_refs,
                            "warning_codes": merged_step_warnings,
                            "waiting_at": "",
                            "finished_at": now,
                            "error_code": saved_observation.error_code,
                            "error_message": saved_observation.safe_message,
                            "metadata": self._clear_current_attempt(step.metadata),
                        }
                    )
                )
                self._session_repository.save_session(
                    session.model_copy(
                        update={
                            "current_step_id": step.step_id,
                            "current_phase": PPAOPhase.OBSERVATION,
                            "warning_codes": merged_session_warnings,
                            "updated_at": now,
                        }
                    )
                )
                return saved_observation
            if step.job_step_id:
                self._ai_job_service.mark_step_failed(
                    step.job_id,
                    step.job_step_id,
                    error_code=saved_observation.error_code or "retry_step",
                    error_message=saved_observation.safe_message,
                )
            self._finish_job_attempt(
                step,
                status=AIJobAttemptStatus.FAILED,
                error_code=saved_observation.error_code or "retry_step",
                error_message=saved_observation.safe_message,
                retry_reason="retry_step",
            )
            self._step_repository.save_step(
                step.model_copy(
                    update={
                        "status": AgentStepStatus.FAILED,
                        "status_reason": "retry_step",
                        "step_phase": PPAOPhase.OBSERVATION,
                        "observation_id": saved_observation.observation_id,
                        "prior_observation_refs": prior_refs,
                        "warning_codes": merged_step_warnings,
                        "waiting_at": "",
                        "finished_at": now,
                        "error_code": saved_observation.error_code,
                        "error_message": saved_observation.safe_message,
                        "metadata": self._clear_current_attempt(step.metadata),
                    }
                )
            )
            self._session_repository.save_session(
                session.model_copy(
                    update={
                        "current_step_id": step.step_id,
                        "current_phase": PPAOPhase.OBSERVATION,
                        "warning_codes": merged_session_warnings,
                        "updated_at": now,
                    }
                )
            )
            next_request_id = f"req_{uuid.uuid4().hex[:12]}"
            self.retry_step(step.step_id, request_id=next_request_id)
        elif saved_observation.decision == "complete_step":
            self._finish_job_attempt(step, status=AIJobAttemptStatus.COMPLETED)
            if step.job_step_id:
                self._ai_job_service.mark_step_completed(step.job_id, step.job_step_id, summary=saved_observation.safe_message)
            self._step_repository.save_step(
                step.model_copy(
                    update={
                        "status": AgentStepStatus.SUCCEEDED,
                        "status_reason": "complete_step",
                        "step_phase": PPAOPhase.OBSERVATION,
                        "observation_id": saved_observation.observation_id,
                        "prior_observation_refs": prior_refs,
                        "warning_codes": merged_step_warnings,
                        "waiting_at": "",
                        "finished_at": now,
                        "error_code": "",
                        "error_message": "",
                        "metadata": self._clear_current_attempt(step.metadata),
                    }
                )
            )
            self._session_repository.save_session(
                session.model_copy(
                    update={
                        "current_step_id": step.step_id,
                        "current_phase": PPAOPhase.OBSERVATION,
                        "warning_codes": merged_session_warnings,
                        "updated_at": now,
                    }
                )
            )
        elif saved_observation.decision == "fail_step":
            self._finish_job_attempt(
                step,
                status=AIJobAttemptStatus.FAILED,
                error_code=saved_observation.error_code,
                error_message=saved_observation.safe_message,
                retry_reason="fail_step",
            )
            if step.job_step_id:
                self._ai_job_service.mark_step_failed(
                    step.job_id,
                    step.job_step_id,
                    error_code=saved_observation.error_code or "step_failed",
                    error_message=saved_observation.safe_message,
                )
            self._step_repository.save_step(
                step.model_copy(
                    update={
                        "status": AgentStepStatus.FAILED,
                        "status_reason": "fail_step",
                        "step_phase": PPAOPhase.OBSERVATION,
                        "observation_id": saved_observation.observation_id,
                        "prior_observation_refs": prior_refs,
                        "warning_codes": merged_step_warnings,
                        "waiting_at": "",
                        "finished_at": now,
                        "error_code": saved_observation.error_code,
                        "error_message": saved_observation.safe_message,
                        "metadata": self._clear_current_attempt(step.metadata),
                    }
                )
            )
            self._session_repository.save_session(
                session.model_copy(
                    update={
                        "current_step_id": step.step_id,
                        "current_phase": PPAOPhase.OBSERVATION,
                        "warning_codes": merged_session_warnings,
                        "updated_at": now,
                    }
                )
            )
        elif saved_observation.decision == "skip_step":
            skip_reason = str(saved_observation.metadata.get("skip_reason", "")).strip() or "workflow_skipped"
            self._finish_job_attempt(
                step,
                status=AIJobAttemptStatus.IGNORED,
                error_code="workflow_skipped",
                error_message=saved_observation.safe_message,
                retry_reason=skip_reason,
            )
            if step.job_step_id:
                self._ai_job_service.mark_step_skipped(step.job_id, step.job_step_id, reason=skip_reason)
            self._step_repository.save_step(
                step.model_copy(
                    update={
                        "status": AgentStepStatus.SKIPPED,
                        "status_reason": skip_reason,
                        "step_phase": PPAOPhase.OBSERVATION,
                        "observation_id": saved_observation.observation_id,
                        "prior_observation_refs": prior_refs,
                        "warning_codes": merged_step_warnings,
                        "waiting_at": "",
                        "finished_at": now,
                        "error_code": "",
                        "error_message": "",
                        "metadata": self._clear_current_attempt(step.metadata),
                    }
                )
            )
            self._session_repository.save_session(
                session.model_copy(
                    update={
                        "current_step_id": step.step_id,
                        "current_phase": PPAOPhase.OBSERVATION,
                        "warning_codes": merged_session_warnings,
                        "updated_at": now,
                    }
                )
            )
        elif saved_observation.decision == "pause_session":
            self.pause_session(session.session_id)

        return saved_observation

    def _now(self) -> str:
        return datetime.now(UTC).isoformat()

    def _build_resource_scope_refs(self, work_id: str, chapter_id: str | None) -> list[str]:
        refs = [f"work:{work_id}"]
        if chapter_id:
            refs.append(f"chapter:{chapter_id}")
        return refs

    def _resolve_step_runtime_flags(self, *, step_type: str, action: str) -> dict[str, bool]:
        retryable = not (step_type in self._NON_RETRYABLE_STEP_TYPES or action in self._NON_RETRYABLE_ACTIONS)
        requires_user_decision = step_type == "wait_user_decision"
        skippable = False
        return {
            "retryable": retryable,
            "skippable": skippable,
            "requires_user_decision": requires_user_decision,
        }

    def _build_step_plan(self, step: AgentStep, *, next_phase: str) -> StepPlan | None:
        if next_phase != PPAOPhase.PLANNING:
            return step.step_plan
        return StepPlan(
            next_action_type=step.step_type,
            target_tool_name=step.action if step.step_type == "call_tool" else "",
            expected_observation_type="tool_result" if step.step_type == "call_tool" else "",
            retryable=step.retryable,
            requires_user_decision=step.requires_user_decision,
            side_effect_level="",
        )

    def _finalize_tool_calls(
        self,
        tool_calls: list[ToolCallRef],
        *,
        source_tool_call_id: str,
        status: str,
        result_ref: str,
        error_code: str,
    ) -> list[ToolCallRef]:
        if not source_tool_call_id:
            return list(tool_calls)
        finalized: list[ToolCallRef] = []
        for tool_call in tool_calls:
            if tool_call.tool_call_id != source_tool_call_id:
                finalized.append(tool_call)
                continue
            finalized.append(
                tool_call.model_copy(
                    update={
                        "status": status,
                        "result_ref": result_ref,
                        "error_code": error_code,
                    }
                )
            )
        return finalized

    def _merge_output_refs(self, output_refs: list[str], result_ref: str) -> list[str]:
        if not result_ref:
            return list(output_refs)
        merged = list(output_refs)
        if result_ref not in merged:
            merged.append(result_ref)
        return merged

    def _next_phase_after_continue(self, current_phase: str) -> str:
        if current_phase == PPAOPhase.PERCEPTION:
            return PPAOPhase.PLANNING
        if current_phase == PPAOPhase.PLANNING:
            return PPAOPhase.ACTION
        return PPAOPhase.PERCEPTION

    def _parse_primary_output(self, result_ref: str) -> dict[str, str]:
        if not result_ref:
            return {"primary_output_type": "", "primary_output_ref": ""}
        output_type, _, _ = result_ref.partition(":")
        return {
            "primary_output_type": output_type,
            "primary_output_ref": result_ref,
        }

    def _build_result_refs(self, result_ref: str, *, steps: list[AgentStep], result_status: str) -> list[ResultRef]:
        if not result_ref:
            return []
        ref_type, _, _ = result_ref.partition(":")
        source_step = next((step for step in reversed(steps) if step.status == AgentStepStatus.SUCCEEDED), None)
        return [
            ResultRef(
                ref_type=ref_type,
                ref_id=result_ref,
                source_agent_type=source_step.agent_type if source_step else "",
                source_step_id=source_step.step_id if source_step else "",
                status=result_status,
            )
        ]

    def _build_step_summary(self, steps: list[AgentStep]) -> StepSummary:
        summary_steps: list[StepSummaryItem] = []
        for step in sorted(steps, key=lambda item: item.order_index):
            safe_message = ""
            if step.observation_id:
                observation = next(
                    (
                        item
                        for item in self._observation_repository.list_observations(step.step_id)
                        if item.observation_id == step.observation_id
                    ),
                    None,
                )
                safe_message = observation.safe_message if observation is not None else ""
            summary_steps.append(
                StepSummaryItem(
                    step_id=step.step_id,
                    agent_type=step.agent_type,
                    step_type=step.step_type,
                    action=step.action,
                    status=step.status.value,
                    step_phase=step.step_phase,
                    status_reason=step.status_reason,
                    safe_message=safe_message,
                    error_code=step.error_code,
                    error_message=step.error_message,
                    warning_codes=list(step.warning_codes),
                    started_at=step.started_at,
                    waiting_at=step.waiting_at,
                    finished_at=step.finished_at,
                )
            )
        return StepSummary(steps=summary_steps)

    def _compute_elapsed_ms(self, started_at: str, finished_at: str) -> int:
        if not started_at or not finished_at:
            return 0
        try:
            start = datetime.fromisoformat(started_at)
            finish = datetime.fromisoformat(finished_at)
        except ValueError:
            return 0
        return max(int((finish - start).total_seconds() * 1000), 0)

    def _start_job_attempt(self, step: AgentStep) -> AgentStep:
        if not step.job_step_id:
            return step
        attempt = self._ai_job_service.record_attempt(
            job_id=step.job_id,
            step_id=step.job_step_id,
            request_id=step.request_id,
            trace_id=step.trace_id,
            status=AIJobAttemptStatus.RUNNING,
        )
        updated = step.model_copy(update={"metadata": {**step.metadata, "current_job_attempt_id": attempt.attempt_id}})
        return self._step_repository.save_step(updated)

    def _finish_job_attempt(
        self,
        step: AgentStep,
        *,
        status: AIJobAttemptStatus,
        error_code: str = "",
        error_message: str = "",
        retry_reason: str = "",
    ) -> None:
        if not step.job_step_id:
            return
        attempt_id = str(step.metadata.get("current_job_attempt_id", ""))
        if not attempt_id:
            return
        for attempt in self._ai_job_service.list_attempts(step.job_step_id):
            if attempt.attempt_id != attempt_id:
                continue
            updated_attempt = attempt.model_copy(
                update={
                    "status": status,
                    "finished_at": self._now(),
                    "error_code": error_code,
                    "error_message": error_message,
                    "retry_reason": retry_reason,
                }
            )
            self._ai_job_service.save_attempt(updated_attempt)
            return

    def _clear_current_attempt(self, metadata: dict[str, object]) -> dict[str, object]:
        updated = dict(metadata)
        updated.pop("current_job_attempt_id", None)
        return updated

    def _build_step_counts(self, steps: list[AgentStep]) -> dict[str, int]:
        return {
            "total_steps": len(steps),
            "succeeded_steps": sum(1 for step in steps if step.status == AgentStepStatus.SUCCEEDED),
            "failed_steps": sum(1 for step in steps if step.status == AgentStepStatus.FAILED),
            "skipped_steps": sum(1 for step in steps if step.status == AgentStepStatus.SKIPPED),
        }

    def _merge_warning_codes(self, existing: list[str], incoming: list[str]) -> list[str]:
        merged = list(existing)
        for code in incoming:
            if code not in merged:
                merged.append(code)
        return merged
