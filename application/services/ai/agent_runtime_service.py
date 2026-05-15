from __future__ import annotations

import uuid
from datetime import UTC, datetime

from application.services.ai.ai_job_service import AIJobService
from application.services.ai.tool_facade import CoreToolFacade, ToolExecutionContext
from domain.entities.ai.models import (
    AgentObservation,
    AgentObservationType,
    AgentResult,
    AgentRunContext,
    AgentSession,
    AgentSessionStatus,
    AgentStep,
    AgentStepStatus,
    AgentWorkflowType,
)
from domain.repositories.ai.agent_observation_repository import AgentObservationRepository
from domain.repositories.ai.agent_session_repository import AgentSessionRepository
from domain.repositories.ai.agent_step_repository import AgentStepRepository


class AgentRuntimeService:
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
        request_id: str,
        trace_id: str,
        caller_type: str,
    ) -> AgentSession:
        now = self._now()
        job = self._ai_job_service.create_job(
            job_type=f"agent_runtime_{agent_workflow_type.value}",
            work_id=work_id,
            chapter_id=chapter_id,
            created_by=caller_type,
            payload={"request_id": request_id, "trace_id": trace_id},
        )
        session = AgentSession(
            session_id=f"agent_session_{uuid.uuid4().hex[:12]}",
            job_id=job.job_id,
            work_id=work_id,
            chapter_id=chapter_id,
            workflow_type=agent_workflow_type,
            status=AgentSessionStatus.PENDING,
            caller_type=caller_type,
            user_instruction=user_instruction,
            request_id=request_id,
            trace_id=trace_id,
            created_at=now,
            updated_at=now,
        )
        return self._session_repository.create_session(session)

    def get_session(self, session_id: str) -> AgentSession:
        return self._session_repository.get_session(session_id)

    def start_session(self, session_id: str) -> AgentSession:
        session = self.get_session(session_id)
        if session.status not in {AgentSessionStatus.PENDING, AgentSessionStatus.PAUSED}:
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

    def pause_session(self, session_id: str) -> AgentSession:
        session = self.get_session(session_id)
        if session.status not in {AgentSessionStatus.RUNNING, AgentSessionStatus.WAITING_FOR_USER}:
            raise ValueError("session_not_pausable")
        self._ai_job_service.pause_job(session.job_id, reason="agent_runtime_paused")
        now = self._now()
        updated = session.model_copy(
            update={
                "status": AgentSessionStatus.PAUSED,
                "paused_at": now,
                "updated_at": now,
                "status_reason": "",
            }
        )
        return self._session_repository.save_session(updated)

    def resume_session(self, session_id: str) -> AgentSession:
        session = self.get_session(session_id)
        if session.status != AgentSessionStatus.PAUSED:
            raise ValueError("session_not_resumable")
        self._ai_job_service.start_job(session.job_id)
        updated = session.model_copy(
            update={
                "status": AgentSessionStatus.RUNNING,
                "paused_at": "",
                "updated_at": self._now(),
                "status_reason": "",
            }
        )
        return self._session_repository.save_session(updated)

    def cancel_session(self, session_id: str, *, reason: str) -> AgentSession:
        session = self.get_session(session_id)
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
                            "finished_at": step.finished_at or now,
                        }
                    )
                )
        self._ai_job_service.cancel_job(session.job_id, reason=reason)
        updated = cancelling.model_copy(
            update={
                "status": AgentSessionStatus.CANCELLED,
                "cancelled_at": self._now(),
                "updated_at": self._now(),
                "finished_at": session.finished_at or self._now(),
            }
        )
        return self._session_repository.save_session(updated)

    def fail_session(self, session_id: str, *, error_code: str, error_message: str) -> AgentSession:
        session = self.get_session(session_id)
        self._ai_job_service.mark_job_failed(session.job_id, error_code=error_code, error_message=error_message)
        now = self._now()
        updated = session.model_copy(
            update={
                "status": AgentSessionStatus.FAILED,
                "error_code": error_code,
                "error_message": error_message,
                "result": AgentResult(
                    session_id=session.session_id,
                    status="failed",
                    result_refs=[],
                    warning_codes=[],
                    error_code=error_code,
                ),
                "updated_at": now,
                "finished_at": now,
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
        warnings = list(warning_codes or [])
        if partial_success:
            if not result_ref:
                raise ValueError("partial_success_requires_result_ref")
            self._ai_job_service.mark_job_completed(
                session.job_id,
                result_summary={"completion_mode": "partial_success", "warning_codes": warnings},
                result_ref=result_ref,
            )
            status = AgentSessionStatus.PARTIAL_SUCCESS
        else:
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
                "result_ref": result_ref,
                "result": AgentResult(
                    session_id=session.session_id,
                    status="partial_success" if partial_success else "success",
                    result_refs=[result_ref] if result_ref else [],
                    warning_codes=warnings,
                    error_code="",
                ),
                "warning_codes": warnings,
                "updated_at": now,
                "finished_at": now,
                "error_code": "",
                "error_message": "",
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
        job_step = self._ai_job_service.add_step(
            session.job_id,
            step_type=step_type,
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
        return AgentRunContext(
            session_id=session.session_id,
            step_id=step_id,
            work_id=session.work_id,
            chapter_id=session.chapter_id,
            current_agent_type=current_agent_type,
            user_instruction=session.user_instruction,
            context_refs=list(context_refs or []),
            request_id=session.request_id,
            trace_id=session.trace_id,
            allow_degraded=session.metadata.get("allow_degraded", True) if allow_degraded is None else allow_degraded,
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
        return ToolExecutionContext(
            caller_type="agent",
            work_id=session.work_id,
            chapter_id=session.chapter_id or "",
            request_id=session.request_id,
            trace_id=session.trace_id,
            agent_session_id=session.session_id,
            agent_step_id=step.step_id,
            agent_type=agent_type,
            session_status=session.status.value,
            step_status=step.status.value,
            resource_scope_refs=list(resource_scope_refs or []),
            side_effect_level=side_effect_level,
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
                "step_phase": "perception",
                "started_at": pending_step.started_at or now,
            }
        )
        if pending_step.job_step_id:
            self._ai_job_service.mark_step_running(session.job_id, pending_step.job_step_id)
        saved = self._step_repository.save_step(updated)
        self._session_repository.save_session(
            session.model_copy(
                update={
                    "current_step_id": saved.step_id,
                    "current_phase": "perception",
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
        if step.step_phase != "action" or step.status != AgentStepStatus.RUNNING:
            raise ValueError("step_not_ready_for_action")
        now = self._now()
        self._step_repository.save_step(
            step.model_copy(
                update={
                    "status": AgentStepStatus.WAITING_OBSERVATION,
                    "step_phase": "observation",
                    "status_reason": "awaiting_observation",
                }
            )
        )
        self._session_repository.save_session(
            session.model_copy(
                update={
                    "current_step_id": step.step_id,
                    "current_phase": "observation",
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
            decision=decision,
            warning_codes=list(result.warnings),
            error_code=result.error_code,
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
        if step.attempt_count >= step.max_attempts:
            raise ValueError("step_attempt_limit_reached")
        if step.job_step_id:
            self._ai_job_service.retry_step(step.job_id, step.job_step_id)
        updated = step.model_copy(
            update={
                "status": AgentStepStatus.PENDING,
                "attempt_count": step.attempt_count + 1,
                "request_id": request_id,
                "error_code": "",
                "error_message": "",
                "status_reason": "retry_requested",
                "finished_at": "",
            }
        )
        return self._step_repository.save_step(updated)

    def record_observation(self, step_id: str, observation: AgentObservation) -> AgentObservation:
        step = self.get_step(step_id)
        session = self.get_session(step.session_id)
        now = self._now()
        stored_observation = observation.model_copy(update={"created_at": observation.created_at or now})
        saved_observation = self._observation_repository.create_observation(stored_observation)
        prior_refs = [*step.prior_observation_refs]
        if step.observation_id:
            prior_refs.append(step.observation_id)

        if session.status == AgentSessionStatus.CANCELLED:
            self._step_repository.save_step(
                step.model_copy(
                    update={
                        "status": AgentStepStatus.IGNORED_LATE_RESULT,
                        "status_reason": "ignored_late_result",
                        "observation_id": saved_observation.observation_id,
                        "prior_observation_refs": prior_refs,
                        "finished_at": now,
                    }
                )
            )
            return saved_observation

        if saved_observation.decision == "wait_for_user":
            updated_step = step.model_copy(
                update={
                    "status": AgentStepStatus.WAITING_USER,
                    "status_reason": "wait_for_user",
                    "step_phase": "observation",
                    "observation_id": saved_observation.observation_id,
                    "prior_observation_refs": prior_refs,
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
                    "current_phase": "observation",
                }
            )
            self._step_repository.save_step(updated_step)
            self._session_repository.save_session(updated_session)
        elif saved_observation.decision == "continue":
            if saved_observation.observation_type == AgentObservationType.VALIDATION_RESULT:
                if step.job_step_id:
                    self._ai_job_service.mark_step_completed(step.job_id, step.job_step_id, summary=saved_observation.safe_message)
                self._step_repository.save_step(
                    step.model_copy(
                        update={
                            "status": AgentStepStatus.SUCCEEDED,
                            "status_reason": "validation_completed",
                            "step_phase": "observation",
                            "observation_id": saved_observation.observation_id,
                            "prior_observation_refs": prior_refs,
                            "finished_at": now,
                            "error_code": "",
                            "error_message": "",
                        }
                    )
                )
                self._session_repository.save_session(
                    session.model_copy(
                        update={
                            "current_step_id": step.step_id,
                            "current_phase": "observation",
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
                        "error_code": "",
                        "error_message": "",
                    }
                )
            )
            self._session_repository.save_session(
                session.model_copy(
                    update={
                        "current_step_id": step.step_id,
                        "current_phase": next_phase,
                        "updated_at": now,
                    }
                )
            )
        elif saved_observation.decision == "retry_step":
            if (
                saved_observation.observation_type == AgentObservationType.VALIDATION_RESULT
                and saved_observation.error_code in {"validation_error", "output_validation_failed"}
                and step.attempt_count >= 2
            ):
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
                            "step_phase": "observation",
                            "observation_id": saved_observation.observation_id,
                            "prior_observation_refs": prior_refs,
                            "finished_at": now,
                            "error_code": saved_observation.error_code,
                            "error_message": saved_observation.safe_message,
                        }
                    )
                )
                self._session_repository.save_session(
                    session.model_copy(
                        update={
                            "current_step_id": step.step_id,
                            "current_phase": "observation",
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
            self._step_repository.save_step(
                step.model_copy(
                    update={
                        "status": AgentStepStatus.FAILED,
                        "status_reason": "retry_step",
                        "step_phase": "observation",
                        "observation_id": saved_observation.observation_id,
                        "prior_observation_refs": prior_refs,
                        "finished_at": now,
                        "error_code": saved_observation.error_code,
                        "error_message": saved_observation.safe_message,
                    }
                )
            )
            self._session_repository.save_session(
                session.model_copy(
                    update={
                        "current_step_id": step.step_id,
                        "current_phase": "observation",
                        "updated_at": now,
                    }
                )
            )
            next_request_id = f"req_{uuid.uuid4().hex[:12]}"
            self.retry_step(step.step_id, request_id=next_request_id)
        elif saved_observation.decision == "complete_step":
            if step.job_step_id:
                self._ai_job_service.mark_step_completed(step.job_id, step.job_step_id, summary=saved_observation.safe_message)
            self._step_repository.save_step(
                step.model_copy(
                    update={
                        "status": AgentStepStatus.SUCCEEDED,
                        "status_reason": "complete_step",
                        "step_phase": "observation",
                        "observation_id": saved_observation.observation_id,
                        "prior_observation_refs": prior_refs,
                        "finished_at": now,
                        "error_code": "",
                        "error_message": "",
                    }
                )
            )
            self._session_repository.save_session(
                session.model_copy(
                    update={
                        "current_step_id": step.step_id,
                        "current_phase": "observation",
                        "updated_at": now,
                    }
                )
            )
        elif saved_observation.decision == "fail_step":
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
                        "step_phase": "observation",
                        "observation_id": saved_observation.observation_id,
                        "prior_observation_refs": prior_refs,
                        "finished_at": now,
                        "error_code": saved_observation.error_code,
                        "error_message": saved_observation.safe_message,
                    }
                )
            )
            self._session_repository.save_session(
                session.model_copy(
                    update={
                        "current_step_id": step.step_id,
                        "current_phase": "observation",
                        "updated_at": now,
                    }
                )
            )
        elif saved_observation.decision == "skip_step":
            if step.job_step_id:
                self._ai_job_service.mark_step_skipped(step.job_id, step.job_step_id, reason="skip_step")
            self._step_repository.save_step(
                step.model_copy(
                    update={
                        "status": AgentStepStatus.SKIPPED,
                        "status_reason": "skip_step",
                        "step_phase": "observation",
                        "observation_id": saved_observation.observation_id,
                        "prior_observation_refs": prior_refs,
                        "finished_at": now,
                        "error_code": "",
                        "error_message": "",
                    }
                )
            )
            self._session_repository.save_session(
                session.model_copy(
                    update={
                        "current_step_id": step.step_id,
                        "current_phase": "observation",
                        "updated_at": now,
                    }
                )
            )
        elif saved_observation.decision == "pause_session":
            self.pause_session(session.session_id)

        return saved_observation

    def _now(self) -> str:
        return datetime.now(UTC).isoformat()

    def _next_phase_after_continue(self, current_phase: str) -> str:
        if current_phase == "perception":
            return "planning"
        if current_phase == "planning":
            return "action"
        return "perception"
