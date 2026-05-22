from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from application.services.ai.agent_runtime_service import AgentRuntimeService
from domain.entities.ai.models import (
    ArcQualityLevel,
    ArcStatus,
    AgentObservation,
    AgentObservationType,
    AgentSessionStatus,
    AgentStepStatus,
    AgentWorkflowDefinition,
    AgentWorkflowRun,
    AgentWorkflowType,
    ChapterPlan,
    DirectionPlanStatus,
    DirectionPlanSnapshot,
    DirectionProposal,
    DirectionSelection,
    PlanConfirmation,
    ResultRef,
    SequenceArc,
    SequenceEvent,
    StageRecord,
    WritingTask,
    WritingTaskStatus,
    WorkflowCheckpoint,
    WorkflowDecision,
    WorkflowDecisionSource,
    WorkflowFailureBehavior,
    WorkflowP1Status,
    WorkflowPolicy,
    WorkflowStage,
    WorkflowStageName,
    WorkflowTransition,
    WorkflowTransitionTrigger,
    WorkflowType,
)
from domain.repositories.ai.direction_plan_repository import DirectionPlanRepository
from domain.repositories.ai.chapter_plan_repository import ChapterPlanRepository
from domain.repositories.ai.plot_arc_repository import PlotArcRepository


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _to_runtime_workflow_type(workflow_type: WorkflowType) -> AgentWorkflowType:
    mapping = {
        WorkflowType.CONTINUATION_WORKFLOW: AgentWorkflowType.CONTINUATION,
        WorkflowType.REVISION_WORKFLOW: AgentWorkflowType.REVISION,
        WorkflowType.PLANNING_WORKFLOW: AgentWorkflowType.PLANNING,
        WorkflowType.MEMORY_UPDATE_WORKFLOW: AgentWorkflowType.MEMORY_UPDATE,
        # review_workflow is an optional P1 workflow; reuse the existing runtime projection.
        WorkflowType.REVIEW_WORKFLOW: AgentWorkflowType.REVISION,
        WorkflowType.FULL_WORKFLOW: AgentWorkflowType.FULL_WORKFLOW,
    }
    try:
        return mapping[workflow_type]
    except KeyError as exc:
        raise ValueError("workflow_type_not_mapped") from exc


def _parse_result_ref(result_ref: str, *, source_agent_type: str = "", source_step_id: str = "") -> ResultRef | None:
    if not result_ref:
        return None
    ref_type, _, ref_id = result_ref.partition(":")
    if not ref_type or not ref_id:
        return None
    return ResultRef(
        ref_type=ref_type,
        ref_id=ref_id,
        source_agent_type=source_agent_type,
        source_step_id=source_step_id,
        status="available",
    )


def _reason_code_for_user_decision(stage_name: WorkflowStageName, user_decision: str) -> str:
    stage_specific = {
        (WorkflowStageName.HUMAN_REVIEW_WAITING, "accept"): "user_accepted_candidate",
        (WorkflowStageName.HUMAN_REVIEW_WAITING, "apply"): "user_applied_candidate",
        (WorkflowStageName.HUMAN_REVIEW_WAITING, "reject"): "user_rejected_candidate",
        (WorkflowStageName.MEMORY_REVIEW_WAITING, "confirm_memory_update"): "user_confirmed_memory_update",
        (WorkflowStageName.MEMORY_REVIEW_WAITING, "reject"): "user_rejected_memory_update",
        (WorkflowStageName.CHAPTER_PLAN_CONFIRM_WAITING, "reject"): "user_rejected_chapter_plan",
    }
    if (stage_name, user_decision) in stage_specific:
        return stage_specific[(stage_name, user_decision)]
    generic = {
        "confirm_direction": "user_selected_direction",
        "confirm_chapter_plan": "user_confirmed_chapter_plan",
        "cancel": "user_cancelled_workflow",
    }
    return generic.get(user_decision, user_decision)


def _result_ref_for_user_decision(
    stage_name: WorkflowStageName,
    user_decision: str,
    metadata: dict[str, object],
) -> str:
    if stage_name == WorkflowStageName.DIRECTION_SELECTION_WAITING:
        selected_direction_id = str(metadata.get("selected_direction_id", ""))
        return f"selected_direction:{selected_direction_id}" if selected_direction_id else ""
    if stage_name == WorkflowStageName.CHAPTER_PLAN_CONFIRM_WAITING:
        selected_chapter_plan_id = str(metadata.get("selected_chapter_plan_id", ""))
        return f"selected_chapter_plan:{selected_chapter_plan_id}" if selected_chapter_plan_id else ""
    if stage_name == WorkflowStageName.HUMAN_REVIEW_WAITING and user_decision in {"accept", "reject", "apply"}:
        return f"review_decision:{user_decision}"
    if stage_name == WorkflowStageName.MEMORY_REVIEW_WAITING and user_decision in {"confirm_memory_update", "reject"}:
        return f"memory_review_decision:{user_decision}"
    return ""


def _candidate_result_ref(run: AgentWorkflowRun) -> str:
    current_candidate_version_id = str(run.metadata.get("current_candidate_version_id", ""))
    if current_candidate_version_id:
        return f"candidate:{current_candidate_version_id}"
    current_candidate_draft_id = str(run.metadata.get("current_candidate_draft_id", ""))
    if current_candidate_draft_id:
        return f"candidate:{current_candidate_draft_id}"
    return ""


def _terminal_decision_for_stage(stage_name: WorkflowStageName) -> str:
    mapping = {
        WorkflowStageName.COMPLETED: WorkflowDecision.COMPLETE_WORKFLOW.value,
        WorkflowStageName.PARTIAL_SUCCESS: WorkflowDecision.MARK_PARTIAL_SUCCESS.value,
        WorkflowStageName.FAILED: WorkflowDecision.FAIL_WORKFLOW.value,
        WorkflowStageName.CANCELLED: WorkflowDecision.CANCEL_WORKFLOW.value,
    }
    return mapping[stage_name]


def _reason_code_for_stage_progress(
    stage_name: WorkflowStageName,
    decision: WorkflowDecision,
    *,
    error_code: str = "",
) -> str:
    if decision == WorkflowDecision.CONTINUE:
        return f"{stage_name.value}_success"
    if decision == WorkflowDecision.COMPLETE_WORKFLOW:
        return "workflow_completed"
    if decision == WorkflowDecision.MARK_PARTIAL_SUCCESS:
        return "workflow_partial_success"
    if decision == WorkflowDecision.CANCEL_WORKFLOW:
        return "workflow_cancelled"
    if decision == WorkflowDecision.FAIL_WORKFLOW:
        return error_code or "workflow_failed"
    return f"{stage_name.value}_{decision.value.lower()}"


def _reason_code_for_terminal_stage(stage_name: WorkflowStageName, *, error_code: str = "") -> str:
    if stage_name == WorkflowStageName.COMPLETED:
        return "workflow_completed"
    if stage_name == WorkflowStageName.PARTIAL_SUCCESS:
        return "workflow_partial_success"
    if stage_name == WorkflowStageName.CANCELLED:
        return "workflow_cancelled"
    if stage_name == WorkflowStageName.FAILED:
        return error_code or "workflow_failed"
    raise ValueError("unsupported_terminal_stage")


class AgentWorkflowDefinitionRegistry:
    _DEFINITIONS: dict[WorkflowType, AgentWorkflowDefinition] | None = None

    @classmethod
    def list_definitions(cls) -> dict[WorkflowType, AgentWorkflowDefinition]:
        if cls._DEFINITIONS is None:
            cls._DEFINITIONS = cls._build_definitions()
        return dict(cls._DEFINITIONS)

    @classmethod
    def get_definition(cls, workflow_type: WorkflowType | str) -> AgentWorkflowDefinition:
        normalized = WorkflowType(workflow_type)
        definitions = cls.list_definitions()
        try:
            return definitions[normalized]
        except KeyError as exc:
            raise ValueError("workflow_definition_not_found") from exc

    @classmethod
    def _build_definitions(cls) -> dict[WorkflowType, AgentWorkflowDefinition]:
        return {
            WorkflowType.CONTINUATION_WORKFLOW: cls._build_definition(
                WorkflowType.CONTINUATION_WORKFLOW,
                [
                    WorkflowStageName.SESSION_INIT,
                    WorkflowStageName.MEMORY_CONTEXT_PREPARE,
                    WorkflowStageName.PLANNING_PREPARE,
                    WorkflowStageName.DIRECTION_SELECTION_WAITING,
                    WorkflowStageName.CHAPTER_PLAN_CONFIRM_WAITING,
                    WorkflowStageName.WRITING_PREPARE,
                    WorkflowStageName.DRAFTING,
                    WorkflowStageName.REVIEWING,
                    WorkflowStageName.REWRITING,
                    WorkflowStageName.CANDIDATE_READY,
                    WorkflowStageName.HUMAN_REVIEW_WAITING,
                    WorkflowStageName.MEMORY_SUGGESTION,
                    WorkflowStageName.MEMORY_REVIEW_WAITING,
                    WorkflowStageName.COMPLETED,
                    WorkflowStageName.PARTIAL_SUCCESS,
                    WorkflowStageName.FAILED,
                    WorkflowStageName.CANCELLED,
                ],
                p1_status=WorkflowP1Status.REQUIRED,
            ),
            WorkflowType.REVISION_WORKFLOW: cls._build_definition(
                WorkflowType.REVISION_WORKFLOW,
                [
                    WorkflowStageName.SESSION_INIT,
                    WorkflowStageName.WRITING_PREPARE,
                    WorkflowStageName.REWRITING,
                    WorkflowStageName.REVIEWING,
                    WorkflowStageName.CANDIDATE_READY,
                    WorkflowStageName.HUMAN_REVIEW_WAITING,
                    WorkflowStageName.COMPLETED,
                    WorkflowStageName.PARTIAL_SUCCESS,
                    WorkflowStageName.FAILED,
                    WorkflowStageName.CANCELLED,
                ],
                p1_status=WorkflowP1Status.REQUIRED,
            ),
            WorkflowType.PLANNING_WORKFLOW: cls._build_definition(
                WorkflowType.PLANNING_WORKFLOW,
                [
                    WorkflowStageName.SESSION_INIT,
                    WorkflowStageName.MEMORY_CONTEXT_PREPARE,
                    WorkflowStageName.PLANNING_PREPARE,
                    WorkflowStageName.DIRECTION_SELECTION_WAITING,
                    WorkflowStageName.CHAPTER_PLAN_CONFIRM_WAITING,
                    WorkflowStageName.COMPLETED,
                    WorkflowStageName.FAILED,
                    WorkflowStageName.CANCELLED,
                ],
                p1_status=WorkflowP1Status.REQUIRED,
            ),
            WorkflowType.MEMORY_UPDATE_WORKFLOW: cls._build_definition(
                WorkflowType.MEMORY_UPDATE_WORKFLOW,
                [
                    WorkflowStageName.SESSION_INIT,
                    WorkflowStageName.MEMORY_CONTEXT_PREPARE,
                    WorkflowStageName.MEMORY_SUGGESTION,
                    WorkflowStageName.MEMORY_REVIEW_WAITING,
                    WorkflowStageName.COMPLETED,
                    WorkflowStageName.FAILED,
                    WorkflowStageName.CANCELLED,
                ],
                p1_status=WorkflowP1Status.OPTIONAL,
            ),
            WorkflowType.REVIEW_WORKFLOW: cls._build_definition(
                WorkflowType.REVIEW_WORKFLOW,
                [
                    WorkflowStageName.SESSION_INIT,
                    WorkflowStageName.REVIEWING,
                    WorkflowStageName.COMPLETED,
                    WorkflowStageName.FAILED,
                    WorkflowStageName.CANCELLED,
                ],
                p1_status=WorkflowP1Status.OPTIONAL,
            ),
            WorkflowType.FULL_WORKFLOW: cls._build_definition(
                WorkflowType.FULL_WORKFLOW,
                [
                    WorkflowStageName.SESSION_INIT,
                    WorkflowStageName.MEMORY_CONTEXT_PREPARE,
                    WorkflowStageName.PLANNING_PREPARE,
                    WorkflowStageName.DIRECTION_SELECTION_WAITING,
                    WorkflowStageName.CHAPTER_PLAN_CONFIRM_WAITING,
                    WorkflowStageName.WRITING_PREPARE,
                    WorkflowStageName.DRAFTING,
                    WorkflowStageName.REVIEWING,
                    WorkflowStageName.REWRITING,
                    WorkflowStageName.CANDIDATE_READY,
                    WorkflowStageName.HUMAN_REVIEW_WAITING,
                    WorkflowStageName.MEMORY_SUGGESTION,
                    WorkflowStageName.MEMORY_REVIEW_WAITING,
                    WorkflowStageName.COMPLETED,
                    WorkflowStageName.PARTIAL_SUCCESS,
                    WorkflowStageName.FAILED,
                    WorkflowStageName.CANCELLED,
                ],
                p1_status=WorkflowP1Status.OPTIONAL,
            ),
        }

    @classmethod
    def _build_definition(
        cls,
        workflow_type: WorkflowType,
        stage_names: list[WorkflowStageName],
        *,
        p1_status: WorkflowP1Status,
    ) -> AgentWorkflowDefinition:
        stages = [cls._build_stage(stage_name, index + 1) for index, stage_name in enumerate(stage_names)]
        transitions = [
            WorkflowTransition(
                from_stage=stage_names[index],
                to_stage=stage_names[index + 1],
                trigger=WorkflowTransitionTrigger.AUTO,
                condition="default_stage_flow",
                decision_source=WorkflowDecisionSource.AGENT_ORCHESTRATOR,
                reason_code=f"{stage_names[index].value}_next",
            )
            for index in range(len(stage_names) - 1)
        ]
        return AgentWorkflowDefinition(
            workflow_type=workflow_type,
            stages=stages,
            transitions=transitions,
            default_policy=WorkflowPolicy(),
            p1_status=p1_status,
            enabled=True,
            version="p1-s2",
        )

    @classmethod
    def _build_stage(cls, stage_name: WorkflowStageName, stage_order: int) -> WorkflowStage:
        stage_defaults: dict[WorkflowStageName, dict[str, Any]] = {
            WorkflowStageName.SESSION_INIT: {
                "allow_retry": False,
                "is_terminal": False,
            },
            WorkflowStageName.MEMORY_CONTEXT_PREPARE: {
                "responsible_agent_type": "memory",
                "allow_degraded": False,
                "expected_result_refs": ["memory_context"],
            },
            WorkflowStageName.PLANNING_PREPARE: {
                "responsible_agent_type": "planner",
                "allow_degraded": False,
                "expected_result_refs": ["direction", "chapter_plan"],
            },
            WorkflowStageName.DIRECTION_SELECTION_WAITING: {
                "allow_waiting_user": True,
                "allow_skip": True,
                "allow_retry": False,
                "failure_behavior": WorkflowFailureBehavior.ENTER_WAITING_USER,
            },
            WorkflowStageName.CHAPTER_PLAN_CONFIRM_WAITING: {
                "allow_waiting_user": True,
                "allow_skip": True,
                "allow_retry": False,
                "failure_behavior": WorkflowFailureBehavior.ENTER_WAITING_USER,
            },
            WorkflowStageName.WRITING_PREPARE: {
                "responsible_agent_type": "planner",
                "allow_degraded": True,
                "expected_result_refs": ["writing_task", "writing_context", "context_pack"],
            },
            WorkflowStageName.DRAFTING: {
                "responsible_agent_type": "writer",
                "allow_degraded": True,
                "expected_result_refs": ["candidate_draft"],
            },
            WorkflowStageName.REVIEWING: {
                "responsible_agent_type": "reviewer",
                "allow_degraded": True,
                "allow_skip": True,
                "is_optional": False,
                "failure_behavior": WorkflowFailureBehavior.PARTIAL_SUCCESS_POSSIBLE,
                "expected_result_refs": ["review_report"],
            },
            WorkflowStageName.REWRITING: {
                "responsible_agent_type": "rewriter",
                "allow_degraded": True,
                "allow_skip": True,
                "is_optional": True,
                "failure_behavior": WorkflowFailureBehavior.PARTIAL_SUCCESS_POSSIBLE,
                "expected_result_refs": ["candidate_version"],
            },
            WorkflowStageName.CANDIDATE_READY: {
                "allow_retry": False,
            },
            WorkflowStageName.HUMAN_REVIEW_WAITING: {
                "allow_waiting_user": True,
                "allow_retry": False,
                "failure_behavior": WorkflowFailureBehavior.ENTER_WAITING_USER,
            },
            WorkflowStageName.MEMORY_SUGGESTION: {
                "responsible_agent_type": "memory",
                "allow_skip": True,
                "is_optional": True,
                "expected_result_refs": ["memory_update_suggestion"],
            },
            WorkflowStageName.MEMORY_REVIEW_WAITING: {
                "allow_waiting_user": True,
                "allow_skip": True,
                "allow_retry": False,
                "is_optional": True,
                "failure_behavior": WorkflowFailureBehavior.ENTER_WAITING_USER,
            },
            WorkflowStageName.COMPLETED: {
                "allow_retry": False,
                "is_terminal": True,
            },
            WorkflowStageName.PARTIAL_SUCCESS: {
                "allow_retry": False,
                "is_terminal": True,
            },
            WorkflowStageName.FAILED: {
                "allow_retry": False,
                "is_terminal": True,
            },
            WorkflowStageName.CANCELLED: {
                "allow_retry": False,
                "is_terminal": True,
            },
        }
        payload = {
            "stage_name": stage_name,
            "stage_order": stage_order,
            "responsible_agent_type": "",
            "allow_degraded": False,
            "allow_waiting_user": False,
            "allow_retry": True,
            "allow_skip": False,
            "is_optional": False,
            "is_terminal": False,
            "failure_behavior": WorkflowFailureBehavior.FAIL_WORKFLOW,
            "max_retry_per_stage": 1,
        }
        payload.update(stage_defaults.get(stage_name, {}))
        return WorkflowStage(**payload)


class AgentOrchestrator:
    _WAITING_REASON_BY_STAGE = {
        WorkflowStageName.DIRECTION_SELECTION_WAITING: "direction_selection",
        WorkflowStageName.CHAPTER_PLAN_CONFIRM_WAITING: "chapter_plan_confirmation",
        WorkflowStageName.HUMAN_REVIEW_WAITING: "human_review",
        WorkflowStageName.MEMORY_REVIEW_WAITING: "memory_review",
    }

    def __init__(
        self,
        *,
        runtime_service: AgentRuntimeService,
        plot_arc_repository: PlotArcRepository | None = None,
        chapter_plan_repository: ChapterPlanRepository | None = None,
        direction_plan_repository: DirectionPlanRepository | None = None,
        registry: type[AgentWorkflowDefinitionRegistry] = AgentWorkflowDefinitionRegistry,
    ) -> None:
        self._runtime_service = runtime_service
        self._plot_arc_repository = plot_arc_repository
        self._chapter_plan_repository = chapter_plan_repository
        self._direction_plan_repository = direction_plan_repository
        self._registry = registry

    def start_workflow(
        self,
        *,
        work_id: str,
        chapter_id: str | None,
        workflow_type: WorkflowType | str,
        user_instruction: str,
        caller_type: str,
        policy_overrides: dict[str, object] | None = None,
    ) -> AgentWorkflowRun:
        normalized_workflow_type = WorkflowType(workflow_type)
        definition = self._registry.get_definition(normalized_workflow_type)
        runtime_workflow_type = _to_runtime_workflow_type(normalized_workflow_type)
        session = self._runtime_service.create_session(
            work_id=work_id,
            chapter_id=chapter_id,
            agent_workflow_type=runtime_workflow_type,
            user_instruction=user_instruction,
            caller_type=caller_type,
            allow_degraded=bool(policy_overrides.get("allow_degraded", True)) if policy_overrides else True,
        )
        session = self._runtime_service.start_session(session.session_id)
        run = AgentWorkflowRun(
            run_id=f"workflow_run_{uuid.uuid4().hex[:12]}",
            session_id=session.session_id,
            workflow_type=normalized_workflow_type,
            current_stage=WorkflowStageName.SESSION_INIT,
            policy=self._merge_policy(definition.default_policy, policy_overrides or {}),
            status=session.status,
            request_id=session.request_id,
            trace_id=session.trace_id,
            created_at=_now(),
            metadata={},
        )
        run.stage_history.append(
            StageRecord(
                stage_name=WorkflowStageName.SESSION_INIT,
                status="succeeded",
                decision=WorkflowDecision.CONTINUE.value,
                decision_reason="session_started",
                entered_at=session.created_at,
                exited_at=session.started_at or _now(),
                metadata={"reason_code": "session_started"},
            )
        )
        return self._enter_stage(run, self._next_stage_after_init(run.workflow_type))

    def advance_workflow(
        self,
        session_id: str,
        *,
        decision: WorkflowDecision | str,
        result_ref: str = "",
        safe_message: str = "stage_completed",
        warning_codes: list[str] | None = None,
        error_code: str = "",
        error_message: str = "",
    ) -> AgentWorkflowRun:
        run = self._load_run(session_id)
        current_stage = run.current_stage
        if current_stage in {
            WorkflowStageName.DIRECTION_SELECTION_WAITING,
            WorkflowStageName.CHAPTER_PLAN_CONFIRM_WAITING,
            WorkflowStageName.HUMAN_REVIEW_WAITING,
            WorkflowStageName.MEMORY_REVIEW_WAITING,
        }:
            raise ValueError("waiting_user_decision_required")
        normalized_decision = WorkflowDecision(decision)
        session = self._runtime_service.get_session(session_id)
        source_step_id = session.current_step_id
        if normalized_decision == WorkflowDecision.RETRY_STEP:
            return self._retry_current_step(run, session=session)
        if normalized_decision == WorkflowDecision.RETRY_STAGE:
            return self._retry_current_stage(run, session=session)
        if normalized_decision == WorkflowDecision.SKIP_OPTIONAL_STAGE:
            return self._skip_current_stage(run, session=session, safe_message=safe_message)
        self._validate_expected_result_ref(
            run,
            current_stage=current_stage,
            decision=normalized_decision,
            result_ref=result_ref,
        )
        self._validate_degraded_progression(
            run,
            current_stage=current_stage,
            decision=normalized_decision,
            warning_codes=warning_codes or [],
        )
        if source_step_id:
            self._complete_step(
                session_id,
                step_id=source_step_id,
                safe_message=safe_message,
                result_ref=result_ref,
                warning_codes=warning_codes or [],
                source_type="system",
                observation_type=AgentObservationType.VALIDATION_RESULT,
            )
        run = self._append_result_ref(run, result_ref, source_step_id=source_step_id)
        run.warning_codes = self._merge_warning_codes(run.warning_codes, warning_codes or [])
        reason_code = _reason_code_for_stage_progress(current_stage, normalized_decision, error_code=error_code)
        run.stage_history.append(
            StageRecord(
                stage_name=current_stage,
                status="succeeded",
                decision=normalized_decision.value,
                decision_reason=safe_message,
                result_refs=list(run.result_refs),
                warning_codes=list(warning_codes or []),
                entered_at=run.checkpoints[-1].created_at if run.checkpoints else "",
                exited_at=_now(),
                metadata={"reason_code": reason_code},
            )
        )
        if normalized_decision == WorkflowDecision.FAIL_WORKFLOW:
            run.error_code = error_code or "workflow_failed"
            return self._enter_stage(run, WorkflowStageName.FAILED)
        if normalized_decision == WorkflowDecision.CANCEL_WORKFLOW:
            return self._enter_stage(run, WorkflowStageName.CANCELLED)
        if normalized_decision == WorkflowDecision.MARK_PARTIAL_SUCCESS:
            if not run.policy.allow_partial_success:
                raise ValueError("partial_success_policy_forbidden")
            if not self._deliverable_result_ref(run.result_refs):
                raise ValueError("partial_success_requires_deliverable_result_ref")
            return self._enter_stage(run, WorkflowStageName.PARTIAL_SUCCESS)
        if normalized_decision == WorkflowDecision.COMPLETE_WORKFLOW:
            return self._enter_stage(run, WorkflowStageName.COMPLETED)
        next_stage = self._resolve_next_stage(run, current_stage, normalized_decision)
        return self._enter_stage(run, next_stage)

    def submit_user_decision(
        self,
        session_id: str,
        *,
        user_decision: str,
        safe_message: str,
        request_id: str,
        metadata: dict[str, object] | None = None,
    ) -> AgentWorkflowRun:
        run = self._load_run(session_id)
        if run.current_stage not in self._WAITING_REASON_BY_STAGE:
            raise ValueError("workflow_not_waiting_for_user")
        session = self._runtime_service.get_session(session_id)
        if session.status == AgentSessionStatus.PAUSED and session.status_reason == "service_restarted":
            session = self._runtime_service._session_repository.save_session(
                session.model_copy(
                    update={
                        "status": AgentSessionStatus.WAITING_FOR_USER,
                        "paused_at": "",
                        "updated_at": _now(),
                        "status_reason": "wait_for_user",
                    }
                )
            )
        elif session.status != AgentSessionStatus.WAITING_FOR_USER:
            raise ValueError("session_not_waiting_for_user")
        current_step_id = session.current_step_id
        if not current_step_id:
            raise ValueError("waiting_step_not_found")
        metadata = dict(metadata or {})
        reason_code = _reason_code_for_user_decision(run.current_stage, user_decision)
        decision_result_ref = _result_ref_for_user_decision(run.current_stage, user_decision, metadata)
        self._complete_step(
            session_id,
            step_id=current_step_id,
            safe_message=safe_message,
            result_ref=decision_result_ref,
            warning_codes=[],
            source_type="user",
            observation_type=AgentObservationType.USER_DECISION,
            request_id=request_id,
            metadata={"user_decision": user_decision, "reason_code": reason_code, **metadata},
        )
        run = self._append_result_ref(run, decision_result_ref, source_step_id=current_step_id)
        run.stage_history.append(
            StageRecord(
                stage_name=run.current_stage,
                status="succeeded",
                decision=user_decision,
                decision_reason=safe_message,
                result_refs=list(run.result_refs),
                entered_at=run.checkpoints[-1].created_at if run.checkpoints else "",
                exited_at=_now(),
                metadata={"user_decision": user_decision, "reason_code": reason_code, **metadata},
            )
        )
        if "selected_direction_id" in metadata:
            run.metadata["selected_direction_id"] = str(metadata["selected_direction_id"])
        if "selected_chapter_plan_id" in metadata:
            run.metadata["selected_chapter_plan_id"] = str(metadata["selected_chapter_plan_id"])
        if run.current_stage == WorkflowStageName.DIRECTION_SELECTION_WAITING and user_decision == "confirm_direction":
            self._persist_direction_selection(run, metadata=metadata)
        if run.current_stage == WorkflowStageName.CHAPTER_PLAN_CONFIRM_WAITING and user_decision in {"confirm_chapter_plan", "reject"}:
            self._persist_plan_confirmation_and_writing_task(run, user_decision=user_decision, metadata=metadata)
        if run.current_stage == WorkflowStageName.CHAPTER_PLAN_CONFIRM_WAITING and user_decision == "confirm_chapter_plan":
            self._persist_sequence_arc_for_confirmed_plan(run)
        next_stage = self._resolve_waiting_stage(run, user_decision)
        return self._enter_stage(run, next_stage)

    def pause_workflow(self, session_id: str, *, reason: str = "pause_requested") -> AgentWorkflowRun:
        run = self._load_run(session_id)
        session = self._runtime_service.pause_session(session_id, reason=reason)
        run.stage_history.append(
            StageRecord(
                stage_name=run.current_stage,
                status="paused",
                decision="pause_session",
                decision_reason=reason,
                entered_at=run.checkpoints[-1].created_at if run.checkpoints else "",
                exited_at=_now(),
                metadata={"reason_code": reason},
            )
        )
        return self._persist_with_checkpoint(run, session=session)

    def resume_workflow(self, session_id: str) -> AgentWorkflowRun:
        run = self._load_run(session_id)
        session = self._runtime_service.get_session(session_id)
        if session.status in {AgentSessionStatus.CANCELLED, AgentSessionStatus.FAILED}:
            raise ValueError("workflow_not_resumable")
        if run.metadata.get("stale_result_refs"):
            raise ValueError("checkpoint_result_stale")
        recovery_reason_code = str(run.metadata.get("recovery_reason_code", ""))
        recovery_rerun_stage = str(run.metadata.get("recovery_rerun_stage", ""))
        if recovery_reason_code:
            if recovery_rerun_stage:
                rerun_stage = WorkflowStageName(recovery_rerun_stage)
                self._cancel_current_step_for_rerun(session_id, reason=recovery_reason_code)
                session = self._runtime_service.resume_session(session_id)
                run.stage_history.append(
                    StageRecord(
                        stage_name=run.current_stage,
                        status="resume_rerun_previous_stage",
                        decision=WorkflowDecision.RETRY_STAGE.value,
                        decision_reason=recovery_reason_code,
                        entered_at=run.checkpoints[-1].created_at if run.checkpoints else "",
                        exited_at=_now(),
                        metadata={"rerun_stage": rerun_stage.value, "reason_code": recovery_reason_code},
                    )
                )
                return self._enter_stage(run, rerun_stage)
            raise ValueError(recovery_reason_code)
        session = self._runtime_service.resume_session(session_id)
        if not session.current_step_id and self._is_stage_completed_in_checkpoint(run, run.current_stage):
            next_stage = self._resolve_next_stage(run, run.current_stage, WorkflowDecision.CONTINUE)
            session = session.model_copy(update={"current_step_id": "", "current_agent_type": "", "updated_at": _now()})
            self._runtime_service._session_repository.save_session(session)
            run.stage_history.append(
                StageRecord(
                    stage_name=run.current_stage,
                    status="resume_inferred_transition",
                    decision=WorkflowDecision.CONTINUE.value,
                    decision_reason="checkpoint_stage_completed",
                    entered_at=run.checkpoints[-1].created_at if run.checkpoints else "",
                    exited_at=_now(),
                    metadata={"reason_code": "checkpoint_stage_completed"},
                )
            )
            return self._enter_stage(run, next_stage)
        run.stage_history.append(
            StageRecord(
                stage_name=run.current_stage,
                status="resumed",
                decision="resume_session",
                decision_reason="resume_requested",
                entered_at=run.checkpoints[-1].created_at if run.checkpoints else "",
                exited_at=_now(),
                metadata={"reason_code": "resume_requested"},
            )
        )
        return self._persist_with_checkpoint(run, session=session)

    def recover_after_restart(self) -> list[AgentWorkflowRun]:
        recovered_runs: list[AgentWorkflowRun] = []
        recovered_session_ids = self._runtime_service.recover_after_restart()
        for session_id in recovered_session_ids:
            try:
                run = self._load_run(session_id)
            except ValueError:
                continue
            session = self._runtime_service.get_session(session_id)
            run.stage_history.append(
                StageRecord(
                    stage_name=run.current_stage,
                    status="paused",
                    decision="service_restarted",
                    decision_reason="service_restarted",
                    entered_at=run.checkpoints[-1].created_at if run.checkpoints else "",
                    exited_at=_now(),
                    metadata={"reason_code": "service_restarted"},
                )
            )
            recovered_runs.append(self._persist_with_checkpoint(run, session=session))
        return recovered_runs

    def _load_run(self, session_id: str) -> AgentWorkflowRun:
        session = self._runtime_service.get_session(session_id)
        payload = session.metadata.get("workflow_run")
        if not isinstance(payload, dict):
            raise ValueError("workflow_run_not_found")
        return AgentWorkflowRun.model_validate(payload)

    def _persist_run(self, run: AgentWorkflowRun) -> AgentWorkflowRun:
        self._runtime_service.update_session_metadata(
            run.session_id,
            metadata_updates={
                "workflow_run": run.model_dump(mode="json"),
                "workflow_checkpoints": [item.model_dump(mode="json") for item in run.checkpoints],
            },
        )
        return run

    def _merge_policy(self, base_policy: WorkflowPolicy, overrides: dict[str, object]) -> WorkflowPolicy:
        payload = base_policy.model_dump(mode="python")
        payload.update({key: value for key, value in overrides.items() if key in payload})
        payload["formal_write_allowed"] = False
        payload["auto_apply_allowed"] = False
        return WorkflowPolicy.model_validate(payload)

    def _next_stage_after_init(self, workflow_type: WorkflowType) -> WorkflowStageName:
        if workflow_type == WorkflowType.REVISION_WORKFLOW:
            return WorkflowStageName.WRITING_PREPARE
        if workflow_type == WorkflowType.REVIEW_WORKFLOW:
            return WorkflowStageName.REVIEWING
        return {
            WorkflowType.CONTINUATION_WORKFLOW: WorkflowStageName.MEMORY_CONTEXT_PREPARE,
            WorkflowType.PLANNING_WORKFLOW: WorkflowStageName.MEMORY_CONTEXT_PREPARE,
            WorkflowType.MEMORY_UPDATE_WORKFLOW: WorkflowStageName.MEMORY_CONTEXT_PREPARE,
            WorkflowType.FULL_WORKFLOW: WorkflowStageName.MEMORY_CONTEXT_PREPARE,
        }[workflow_type]

    def _enter_stage(self, run: AgentWorkflowRun, stage_name: WorkflowStageName) -> AgentWorkflowRun:
        run.current_stage = stage_name
        if stage_name == WorkflowStageName.REWRITING:
            run.revision_round += 1
        if stage_name == WorkflowStageName.COMPLETED:
            self._runtime_service.complete_session(
                run.session_id,
                result_ref=self._primary_result_ref(run.result_refs),
                warning_codes=run.warning_codes,
            )
            session = self._runtime_service.get_session(run.session_id)
            run.status = session.status
            run.finished_at = session.finished_at
            run.stage_history.append(
                StageRecord(
                    stage_name=stage_name,
                    status=session.status.value,
                    decision=_terminal_decision_for_stage(stage_name),
                    decision_reason="workflow_completed",
                    result_refs=list(run.result_refs),
                    warning_codes=list(run.warning_codes),
                    entered_at=run.checkpoints[-1].created_at if run.checkpoints else run.created_at,
                    exited_at=session.finished_at or _now(),
                    metadata={"reason_code": _reason_code_for_terminal_stage(stage_name)},
                )
            )
            return self._persist_with_checkpoint(run, session=session)
        if stage_name == WorkflowStageName.PARTIAL_SUCCESS:
            deliverable_result_ref = self._deliverable_result_ref(run.result_refs)
            if not deliverable_result_ref:
                raise ValueError("partial_success_requires_deliverable_result_ref")
            self._runtime_service.complete_session(
                run.session_id,
                result_ref=deliverable_result_ref,
                warning_codes=run.warning_codes,
                partial_success=True,
            )
            session = self._runtime_service.get_session(run.session_id)
            run.status = session.status
            run.finished_at = session.finished_at
            run.stage_history.append(
                StageRecord(
                    stage_name=stage_name,
                    status=session.status.value,
                    decision=_terminal_decision_for_stage(stage_name),
                    decision_reason="workflow_partial_success",
                    result_refs=list(run.result_refs),
                    warning_codes=list(run.warning_codes),
                    entered_at=run.checkpoints[-1].created_at if run.checkpoints else run.created_at,
                    exited_at=session.finished_at or _now(),
                    metadata={"reason_code": _reason_code_for_terminal_stage(stage_name)},
                )
            )
            return self._persist_with_checkpoint(run, session=session)
        if stage_name == WorkflowStageName.FAILED:
            self._runtime_service.fail_session(
                run.session_id,
                error_code=run.error_code or "workflow_failed",
                error_message=run.error_code or "workflow_failed",
            )
            session = self._runtime_service.get_session(run.session_id)
            run.status = session.status
            run.finished_at = session.finished_at
            run.stage_history.append(
                StageRecord(
                    stage_name=stage_name,
                    status=session.status.value,
                    decision=_terminal_decision_for_stage(stage_name),
                    decision_reason=run.error_code or "workflow_failed",
                    result_refs=list(run.result_refs),
                    warning_codes=list(run.warning_codes),
                    entered_at=run.checkpoints[-1].created_at if run.checkpoints else run.created_at,
                    exited_at=session.finished_at or _now(),
                    metadata={
                        "error_code": run.error_code or "workflow_failed",
                        "reason_code": _reason_code_for_terminal_stage(stage_name, error_code=run.error_code or ""),
                    },
                )
            )
            return self._persist_with_checkpoint(run, session=session)
        if stage_name == WorkflowStageName.CANCELLED:
            self._runtime_service.cancel_session(run.session_id, reason="workflow_cancelled")
            session = self._runtime_service.get_session(run.session_id)
            run.status = session.status
            run.finished_at = session.finished_at
            run.stage_history.append(
                StageRecord(
                    stage_name=stage_name,
                    status=session.status.value,
                    decision=_terminal_decision_for_stage(stage_name),
                    decision_reason="workflow_cancelled",
                    result_refs=list(run.result_refs),
                    warning_codes=list(run.warning_codes),
                    entered_at=run.checkpoints[-1].created_at if run.checkpoints else run.created_at,
                    exited_at=session.finished_at or _now(),
                    metadata={"reason_code": _reason_code_for_terminal_stage(stage_name)},
                )
            )
            return self._persist_with_checkpoint(run, session=session)

        stage = self._registry.get_definition(run.workflow_type).stages
        current_stage = next(item for item in stage if item.stage_name == stage_name)
        step_type = "wait_user_decision" if current_stage.allow_waiting_user else "workflow_stage"
        agent_type = current_stage.responsible_agent_type or "workflow"
        step = self._runtime_service.create_step(
            run.session_id,
            agent_type=agent_type,
            step_type=step_type,
            action=stage_name.value,
        )
        self._runtime_service.run_next_step(run.session_id)
        if stage_name == WorkflowStageName.CANDIDATE_READY:
            run = self._append_result_ref(run, _candidate_result_ref(run), source_step_id=step.step_id)
        if current_stage.allow_waiting_user:
            self._runtime_service.record_observation(
                step.step_id,
                AgentObservation(
                    observation_id=f"obs_wait_{uuid.uuid4().hex[:12]}",
                    session_id=run.session_id,
                    step_id=step.step_id,
                    observation_type=AgentObservationType.STATE_CHANGE,
                    source_type="system",
                    status="waiting",
                    safe_message=self._WAITING_REASON_BY_STAGE[stage_name],
                    summary=self._WAITING_REASON_BY_STAGE[stage_name],
                    decision=WorkflowDecision.WAIT_FOR_USER.value,
                    decision_reason=self._WAITING_REASON_BY_STAGE[stage_name],
                    request_id=self._runtime_service.get_session(run.session_id).request_id,
                    trace_id=self._runtime_service.get_session(run.session_id).trace_id,
                    metadata={"waiting_for_user_reason": self._WAITING_REASON_BY_STAGE[stage_name]},
                ),
            )
        session = self._runtime_service.get_session(run.session_id)
        run.status = session.status
        return self._persist_with_checkpoint(run, session=session)

    def _persist_with_checkpoint(self, run: AgentWorkflowRun, *, session) -> AgentWorkflowRun:
        checkpoint = WorkflowCheckpoint(
            checkpoint_id=f"wf_ckpt_{uuid.uuid4().hex[:12]}",
            session_id=run.session_id,
            workflow_type=run.workflow_type,
            current_stage=run.current_stage,
            current_agent_type=session.current_agent_type,
            current_step_id=session.current_step_id,
            revision_round=run.revision_round,
            result_refs=list(run.result_refs),
            warning_codes=list(run.warning_codes),
            error_code=run.error_code,
            waiting_for_user_reason=self._WAITING_REASON_BY_STAGE.get(run.current_stage, ""),
            selected_direction_id=str(run.metadata.get("selected_direction_id", "")),
            selected_chapter_plan_id=str(run.metadata.get("selected_chapter_plan_id", "")),
            current_candidate_draft_id=str(run.metadata.get("current_candidate_draft_id", "")),
            current_candidate_version_id=str(run.metadata.get("current_candidate_version_id", "")),
            created_at=_now(),
        )
        run.checkpoints.append(checkpoint)
        return self._persist_run(run)

    def _retry_current_step(self, run: AgentWorkflowRun, *, session) -> AgentWorkflowRun:
        current_step_id = session.current_step_id
        if not current_step_id:
            raise ValueError("workflow_step_not_found")
        step = self._runtime_service.get_step(current_step_id)
        if step.status != "failed":
            raise ValueError("retry_step_requires_failed_step")
        retried = self._runtime_service.retry_step(step.step_id, request_id=f"req_retry_{uuid.uuid4().hex[:12]}")
        run.stage_history.append(
            StageRecord(
                stage_name=run.current_stage,
                status="retry_requested",
                decision=WorkflowDecision.RETRY_STEP.value,
                decision_reason="retry_current_step",
                entered_at=run.checkpoints[-1].created_at if run.checkpoints else "",
                exited_at=_now(),
                metadata={"reason_code": "retry_current_step"},
            )
        )
        session = self._runtime_service.get_session(run.session_id)
        session = session.model_copy(update={"current_step_id": retried.step_id, "updated_at": _now()})
        self._runtime_service.update_session_metadata(
            run.session_id,
            metadata_updates={"workflow_run": run.model_dump(mode="json")},
        )
        return self._persist_with_checkpoint(run, session=session)

    def _retry_current_stage(self, run: AgentWorkflowRun, *, session) -> AgentWorkflowRun:
        stage = self._stage_definition(run, run.current_stage)
        if not stage.allow_retry:
            raise ValueError("stage_retry_forbidden")
        current_step_id = session.current_step_id
        if not current_step_id:
            raise ValueError("workflow_step_not_found")
        step = self._runtime_service.get_step(current_step_id)
        if step.status != "failed":
            raise ValueError("retry_stage_requires_failed_step")
        retry_counts = dict(run.metadata.get("stage_retry_counts", {}))
        stage_key = run.current_stage.value
        current_retry_count = int(retry_counts.get(stage_key, 0))
        if current_retry_count >= stage.max_retry_per_stage:
            raise ValueError("stage_retry_limit_reached")
        retry_counts[stage_key] = current_retry_count + 1
        run.metadata["stage_retry_counts"] = retry_counts
        run.stage_history.append(
            StageRecord(
                stage_name=run.current_stage,
                status="retry_requested",
                decision=WorkflowDecision.RETRY_STAGE.value,
                decision_reason="retry_current_stage",
                entered_at=run.checkpoints[-1].created_at if run.checkpoints else "",
                exited_at=_now(),
                metadata={
                    "retry_count": retry_counts[stage_key],
                    "reason_code": "retry_current_stage",
                },
            )
        )
        return self._enter_stage(run, run.current_stage)

    def _skip_current_stage(self, run: AgentWorkflowRun, *, session, safe_message: str) -> AgentWorkflowRun:
        stage = self._stage_definition(run, run.current_stage)
        if run.current_stage == WorkflowStageName.REVIEWING and not run.policy.allow_skip_reviewer:
            raise ValueError("stage_skip_policy_forbidden")
        if run.current_stage == WorkflowStageName.REWRITING and not run.policy.allow_skip_rewriter:
            raise ValueError("stage_skip_policy_forbidden")
        reviewer_skip_allowed = run.current_stage == WorkflowStageName.REVIEWING and run.policy.allow_skip_reviewer
        if not stage.is_optional and not reviewer_skip_allowed:
            raise ValueError("stage_not_skippable")
        current_step_id = session.current_step_id
        if current_step_id:
            self._runtime_service.record_observation(
                current_step_id,
                AgentObservation(
                    observation_id=f"obs_skip_{uuid.uuid4().hex[:12]}",
                    session_id=run.session_id,
                    step_id=current_step_id,
                    observation_type=AgentObservationType.STATE_CHANGE,
                    source_type="system",
                    status="skipped",
                    safe_message=safe_message,
                    summary=safe_message,
                    decision="skip_step",
                    decision_reason=safe_message,
                    request_id=session.request_id,
                    trace_id=session.trace_id,
                    metadata={"skip_reason": "workflow_optional_stage_skipped"},
                ),
            )
        run.stage_history.append(
            StageRecord(
                stage_name=run.current_stage,
                status="skipped",
                decision=WorkflowDecision.SKIP_OPTIONAL_STAGE.value,
                decision_reason=safe_message,
                entered_at=run.checkpoints[-1].created_at if run.checkpoints else "",
                exited_at=_now(),
                metadata={
                    "skip_reason": "workflow_optional_stage_skipped",
                    "reason_code": "workflow_optional_stage_skipped",
                },
            )
        )
        next_stage = self._resolve_next_stage(run, run.current_stage, WorkflowDecision.SKIP_OPTIONAL_STAGE)
        return self._enter_stage(run, next_stage)

    def _append_result_ref(self, run: AgentWorkflowRun, result_ref: str, *, source_step_id: str) -> AgentWorkflowRun:
        source_agent_type = ""
        if source_step_id:
            try:
                source_agent_type = self._runtime_service.get_step(source_step_id).agent_type
            except Exception:  # noqa: BLE001
                source_agent_type = ""
        parsed = _parse_result_ref(
            result_ref,
            source_agent_type=source_agent_type,
            source_step_id=source_step_id,
        )
        if parsed is None:
            return run
        singleton_ref_types = {
            "memory_context",
            "direction",
            "chapter_plan",
            "selected_direction",
            "selected_chapter_plan",
            "writing_task",
            "writing_context",
            "context_pack",
            "review_decision",
            "memory_review_decision",
            "review_report",
            "memory_update_suggestion",
            "candidate_draft",
            "candidate_version",
            "candidate",
        }
        if parsed.ref_type in singleton_ref_types:
            run.result_refs = [item for item in run.result_refs if item.ref_type != parsed.ref_type]
        if all(item.ref_type != parsed.ref_type or item.ref_id != parsed.ref_id for item in run.result_refs):
            run.result_refs.append(parsed)
        if parsed.ref_type == "candidate_draft":
            run.metadata["current_candidate_draft_id"] = parsed.ref_id
        if parsed.ref_type == "candidate_version":
            run.metadata["current_candidate_version_id"] = parsed.ref_id
        return run

    def _validate_expected_result_ref(
        self,
        run: AgentWorkflowRun,
        *,
        current_stage: WorkflowStageName,
        decision: WorkflowDecision,
        result_ref: str,
    ) -> None:
        if decision in {
            WorkflowDecision.FAIL_WORKFLOW,
            WorkflowDecision.CANCEL_WORKFLOW,
            WorkflowDecision.MARK_PARTIAL_SUCCESS,
            WorkflowDecision.COMPLETE_WORKFLOW,
        }:
            return
        stage = self._stage_definition(run, current_stage)
        expected_result_refs = list(stage.expected_result_refs)
        if not expected_result_refs:
            return
        parsed = _parse_result_ref(result_ref)
        if parsed is None or parsed.ref_type not in expected_result_refs:
            raise ValueError("expected_result_ref_missing")

    def _complete_step(
        self,
        session_id: str,
        *,
        step_id: str,
        safe_message: str,
        result_ref: str,
        warning_codes: list[str],
        source_type: str,
        observation_type: AgentObservationType,
        request_id: str | None = None,
        metadata: dict[str, object] | None = None,
    ) -> None:
        session = self._runtime_service.get_session(session_id)
        observation_metadata: dict[str, object] = dict(metadata or {})
        if result_ref:
            observation_metadata["result_ref"] = result_ref
        self._runtime_service.record_observation(
            step_id,
            AgentObservation(
                observation_id=f"obs_complete_{uuid.uuid4().hex[:12]}",
                session_id=session_id,
                step_id=step_id,
                observation_type=observation_type,
                source_type=source_type,
                status="success",
                safe_message=safe_message,
                summary=safe_message,
                decision="complete_step",
                decision_reason=safe_message,
                warning_codes=list(warning_codes),
                request_id=request_id or session.request_id,
                trace_id=session.trace_id,
                metadata=observation_metadata,
            ),
        )

    def _resolve_next_stage(
        self,
        run: AgentWorkflowRun,
        current_stage: WorkflowStageName,
        decision: WorkflowDecision,
    ) -> WorkflowStageName:
        if current_stage == WorkflowStageName.MEMORY_CONTEXT_PREPARE:
            if run.workflow_type == WorkflowType.MEMORY_UPDATE_WORKFLOW:
                return WorkflowStageName.MEMORY_SUGGESTION
            return WorkflowStageName.PLANNING_PREPARE
        if current_stage == WorkflowStageName.PLANNING_PREPARE:
            if run.policy.require_direction_confirmation:
                return WorkflowStageName.DIRECTION_SELECTION_WAITING
            if run.policy.require_chapter_plan_confirmation:
                return WorkflowStageName.CHAPTER_PLAN_CONFIRM_WAITING
            return WorkflowStageName.COMPLETED if run.workflow_type == WorkflowType.PLANNING_WORKFLOW else WorkflowStageName.WRITING_PREPARE
        if current_stage == WorkflowStageName.WRITING_PREPARE:
            return WorkflowStageName.REWRITING if run.workflow_type == WorkflowType.REVISION_WORKFLOW else WorkflowStageName.DRAFTING
        if current_stage == WorkflowStageName.DRAFTING:
            return WorkflowStageName.REVIEWING if self._should_require_review(run) else WorkflowStageName.CANDIDATE_READY
        if current_stage == WorkflowStageName.REVIEWING:
            if run.workflow_type == WorkflowType.REVIEW_WORKFLOW:
                return WorkflowStageName.COMPLETED
            if decision == WorkflowDecision.ENTER_REWRITER and run.revision_round < run.policy.max_revision_rounds:
                return WorkflowStageName.REWRITING
            return WorkflowStageName.CANDIDATE_READY
        if current_stage == WorkflowStageName.REWRITING:
            return WorkflowStageName.REVIEWING if self._should_require_review(run) else WorkflowStageName.CANDIDATE_READY
        if current_stage == WorkflowStageName.CANDIDATE_READY:
            return WorkflowStageName.HUMAN_REVIEW_WAITING
        if current_stage == WorkflowStageName.MEMORY_SUGGESTION:
            return WorkflowStageName.MEMORY_REVIEW_WAITING
        return WorkflowStageName.COMPLETED

    def _resolve_waiting_stage(self, run: AgentWorkflowRun, user_decision: str) -> WorkflowStageName:
        if user_decision == WorkflowDecision.CANCEL_WORKFLOW.value:
            return WorkflowStageName.CANCELLED
        if run.current_stage == WorkflowStageName.DIRECTION_SELECTION_WAITING:
            if user_decision != "confirm_direction":
                return WorkflowStageName.CANCELLED if run.workflow_type != WorkflowType.PLANNING_WORKFLOW else WorkflowStageName.COMPLETED
            if run.policy.require_chapter_plan_confirmation:
                return WorkflowStageName.CHAPTER_PLAN_CONFIRM_WAITING
            return WorkflowStageName.COMPLETED if run.workflow_type == WorkflowType.PLANNING_WORKFLOW else WorkflowStageName.WRITING_PREPARE
        if run.current_stage == WorkflowStageName.CHAPTER_PLAN_CONFIRM_WAITING:
            if user_decision == "reject":
                return WorkflowStageName.CHAPTER_PLAN_CONFIRM_WAITING
            if user_decision != "confirm_chapter_plan":
                return WorkflowStageName.CANCELLED if run.workflow_type != WorkflowType.PLANNING_WORKFLOW else WorkflowStageName.COMPLETED
            return WorkflowStageName.COMPLETED if run.workflow_type == WorkflowType.PLANNING_WORKFLOW else WorkflowStageName.WRITING_PREPARE
        if run.current_stage == WorkflowStageName.HUMAN_REVIEW_WAITING:
            if user_decision == "apply" and run.policy.allow_memory_suggestion_after_apply and run.workflow_type in {
                WorkflowType.CONTINUATION_WORKFLOW,
                WorkflowType.FULL_WORKFLOW,
            }:
                return WorkflowStageName.MEMORY_SUGGESTION
            return WorkflowStageName.COMPLETED
        if run.current_stage == WorkflowStageName.MEMORY_REVIEW_WAITING:
            return WorkflowStageName.COMPLETED
        raise ValueError("unsupported_waiting_stage")

    def _stage_definition(self, run: AgentWorkflowRun, stage_name: WorkflowStageName) -> WorkflowStage:
        stages = self._registry.get_definition(run.workflow_type).stages
        return next(item for item in stages if item.stage_name == stage_name)

    def _is_stage_completed_in_checkpoint(self, run: AgentWorkflowRun, stage_name: WorkflowStageName) -> bool:
        for record in reversed(run.stage_history):
            if record.stage_name != stage_name:
                continue
            if record.status in {"succeeded", "skipped"}:
                return True
            if record.status in {"paused", "resumed", "retry_requested"}:
                continue
            return False
        return False

    def _persist_sequence_arc_for_confirmed_plan(self, run: AgentWorkflowRun) -> None:
        if self._plot_arc_repository is None:
            return
        session = self._runtime_service.get_session(run.session_id)
        work_id = session.work_id
        plan_id = str(run.metadata.get("selected_chapter_plan_id", "")).strip()
        if not plan_id:
            return
        plan = self._load_confirmed_chapter_plan(plan_id)
        master_arc = self._plot_arc_repository.get_master_arc(work_id)
        volume_arc = self._plot_arc_repository.get_active_volume_arc(work_id)
        if master_arc is None or volume_arc is None:
            return
        now = _now()
        source_refs = [
            master_arc.master_arc_id,
            volume_arc.volume_arc_id,
            f"chapter_plan:{plan_id}",
            f"selected_chapter_plan:{plan_id}",
        ]
        existing_items = self._plot_arc_repository.list_sequence_arcs(work_id)
        existing = next(
            (
                item
                for item in existing_items
                if f"chapter_plan:{plan_id}" in item.source_refs or item.source_outline_ref == plan_id
            ),
            None,
        )
        seq_no = existing.seq_no if existing is not None else max((item.seq_no for item in existing_items), default=0) + 1
        chapter_range = dict(existing.chapter_range) if existing is not None else dict(volume_arc.chapter_range)
        if not chapter_range:
            chapter_range = {"from_chapter": 1, "to_chapter_estimate": 0}
        sequence_goal = self._sequence_goal_from_plan(plan, existing=existing)
        key_events = self._sequence_events_from_plan(plan, plan_id=plan_id, chapter_range=chapter_range, existing=existing)
        warning_codes = list(existing.warning_codes) if existing is not None else []
        if "arc_placeholder_only" not in warning_codes:
            warning_codes.append("arc_placeholder_only")
        sequence_arc = SequenceArc(
            sequence_arc_id=existing.sequence_arc_id if existing is not None else f"sa_{work_id}_{plan_id}",
            work_id=work_id,
            volume_arc_id=volume_arc.volume_arc_id,
            master_arc_id=master_arc.master_arc_id,
            version=(existing.version + 1) if existing is not None else 1,
            seq_no=seq_no,
            status=ArcStatus.DEGRADED,
            quality_level=ArcQualityLevel.MINIMAL,
            sequence_goal=sequence_goal,
            key_events=key_events,
            turning_points=list(existing.turning_points) if existing is not None else [],
            required_beats=self._required_beats_from_plan(plan, existing=existing),
            forbidden_items=self._forbidden_items_from_plan(plan, volume_arc=volume_arc, existing=existing),
            chapter_range=chapter_range,
            source_initialization_id=(
                existing.source_initialization_id
                if existing is not None and existing.source_initialization_id
                else volume_arc.source_initialization_id or master_arc.source_initialization_id
            ),
            source_outline_ref=plan_id,
            source_refs=list(dict.fromkeys(source_refs)),
            warning_codes=warning_codes,
            stale_status="fresh",
            built_by="planner_agent",
            last_updated_by="planner_agent",
            created_at=existing.created_at if existing is not None and existing.created_at else now,
            updated_at=now,
            request_id=run.request_id,
            trace_id=run.trace_id,
        )
        self._plot_arc_repository.save_sequence_arc(sequence_arc)

    def _load_confirmed_chapter_plan(self, plan_id: str) -> ChapterPlan | None:
        if self._chapter_plan_repository is None:
            return None
        try:
            return self._chapter_plan_repository.get(plan_id)
        except Exception:  # noqa: BLE001
            return None

    def _persist_direction_selection(self, run: AgentWorkflowRun, *, metadata: dict[str, object]) -> None:
        if self._direction_plan_repository is None:
            return
        session = self._runtime_service.get_session(run.session_id)
        selected_direction_id = str(metadata.get("selected_direction_id", "")).strip()
        if not selected_direction_id:
            return
        selected_option_id = str(metadata.get("selected_option_id", "")).strip() or selected_direction_id
        edited_fields = [str(item) for item in list(metadata.get("edited_fields", []) or []) if str(item).strip()]
        edited_values = metadata.get("edited_values", {}) if isinstance(metadata.get("edited_values", {}), dict) else {}
        selection_type = "edited_select" if edited_fields or edited_values else "direct_select"
        selection = DirectionSelection(
            selection_id=f"ds_{run.session_id}_{selected_direction_id}",
            direction_proposal_id=selected_direction_id,
            selected_option_id=selected_option_id,
            work_id=session.work_id,
            chapter_id=session.chapter_id or "",
            agent_session_id=run.session_id,
            selection_type=selection_type,
            edited_fields=edited_fields,
            edited_values=edited_values,
            user_id="user_action",
            confirmed_by="user_action",
            created_at=_now(),
            request_id=run.request_id,
            trace_id=run.trace_id,
        )
        self._direction_plan_repository.save_direction_selection(selection)
        self._apply_direction_selection_to_proposal(
            selected_direction_id=selected_direction_id,
            selected_option_id=selected_option_id,
            selection_type=selection_type,
        )
        if selection_type == "edited_select":
            self._mark_related_chapter_plans_stale(
                work_id=session.work_id,
                chapter_id=session.chapter_id or "",
                direction_proposal_id=selected_direction_id,
                stale_reason="direction_edited",
            )
            self._mark_existing_writing_tasks_stale(
                work_id=session.work_id,
                chapter_id=session.chapter_id or "",
                stale_reason="direction_edited",
                direction_proposal_id=selected_direction_id,
            )

    def _persist_plan_confirmation_and_writing_task(
        self,
        run: AgentWorkflowRun,
        *,
        user_decision: str,
        metadata: dict[str, object],
    ) -> None:
        if self._direction_plan_repository is None:
            return
        session = self._runtime_service.get_session(run.session_id)
        plan_id = str(metadata.get("selected_chapter_plan_id", "")).strip()
        if not plan_id:
            return
        edited_items = [str(item) for item in list(metadata.get("edited_items", []) or []) if str(item).strip()]
        edited_fields = metadata.get("edited_fields", {}) if isinstance(metadata.get("edited_fields", {}), dict) else {}
        confirmation_type = "reject" if user_decision == "reject" else ("edited_confirm" if edited_items or edited_fields else "direct_confirm")
        if confirmation_type != "reject":
            self._apply_plan_confirmation_to_chapter_plan(
                plan_id,
                confirmation_type=confirmation_type,
                edited_items=edited_items,
                edited_fields=edited_fields,
            )
        confirmation = PlanConfirmation(
            confirmation_id=f"pc_{run.session_id}_{plan_id}",
            chapter_plan_id=plan_id,
            direction_proposal_id=str(run.metadata.get("selected_direction_id", "")).strip(),
            work_id=session.work_id,
            chapter_id=session.chapter_id or "",
            agent_session_id=run.session_id,
            confirmation_type=confirmation_type,
            edited_items=edited_items,
            edited_fields=edited_fields,
            user_edit_notes=str(metadata.get("user_edit_notes", "") or ""),
            user_id="user_action",
            confirmed_by="user_action",
            created_at=_now(),
            request_id=run.request_id,
            trace_id=run.trace_id,
        )
        self._direction_plan_repository.save_plan_confirmation(confirmation)
        if confirmation_type == "reject":
            return
        if confirmation_type == "edited_confirm":
            self._mark_existing_writing_tasks_stale(
                work_id=session.work_id,
                chapter_id=session.chapter_id or "",
                stale_reason="chapter_plan_edited",
            )
        task = self._build_writing_task_for_confirmed_plan(run, plan_id=plan_id, chapter_id=session.chapter_id or "")
        if task is not None:
            self._direction_plan_repository.save_writing_task(task)
        snapshot = self._build_direction_plan_snapshot(
            run,
            plan_id=plan_id,
            confirmation=confirmation,
            writing_task=task,
            chapter_id=session.chapter_id or "",
        )
        if snapshot is not None:
            self._direction_plan_repository.save_direction_plan_snapshot(snapshot)

    def _build_writing_task_for_confirmed_plan(
        self,
        run: AgentWorkflowRun,
        *,
        plan_id: str,
        chapter_id: str,
    ) -> WritingTask | None:
        plan = self._load_confirmed_chapter_plan(plan_id)
        if plan is None:
            return None
        current_item = plan.plan_items[0] if plan.plan_items else None
        must_include: list[str] = []
        if current_item is not None:
            must_include.extend(current_item.required_beats)
            must_include.extend(beat.beat_name for beat in current_item.key_events if beat.beat_name)
        must_include = list(dict.fromkeys(item for item in must_include if item))
        must_not_include = list(current_item.forbidden_items) if current_item is not None else []
        direction_summary = str(run.metadata.get("selected_direction_id", "")).strip()
        if direction_summary:
            direction_summary = f"selected_direction:{direction_summary}"
        plan_summary = plan.plan_summary or (current_item.chapter_goal if current_item is not None else "")
        return WritingTask(
            writing_task_id=f"wt_{run.session_id}_{plan_id}",
            work_id=plan.work_id,
            chapter_id=chapter_id,
            target_chapter_id=chapter_id,
            direction_proposal_id=plan.direction_proposal_id,
            selected_option_id=plan.selected_option_id,
            chapter_plan_id=plan.chapter_plan_id,
            plan_item_id=current_item.item_id if current_item is not None else "",
            agent_session_id=run.session_id,
            status=WritingTaskStatus.READY,
            version=1,
            writing_goal=(current_item.chapter_goal if current_item is not None else plan.plan_summary) or "基于已确认章节计划生成写作任务。",
            must_include=must_include,
            must_not_include=must_not_include,
            tone_guidance=current_item.tone_hint if current_item is not None else "",
            target_word_count=current_item.estimated_word_count if current_item is not None else 0,
            target_word_count_max=current_item.estimated_word_count_max if current_item is not None else 0,
            arc_constraints=list(current_item.arc_alignment) if current_item is not None else [],
            foreshadow_requirements=list(current_item.foreshadow_arrangement) if current_item is not None else [],
            required_beats=list(current_item.required_beats) if current_item is not None else [],
            direction_summary=direction_summary,
            plan_summary=plan_summary,
            stale_status="fresh",
            generated_by="planner_agent",
            created_by="planner_agent",
            created_at=_now(),
            updated_at=_now(),
            request_id=run.request_id,
            trace_id=run.trace_id,
        )

    def _build_direction_plan_snapshot(
        self,
        run: AgentWorkflowRun,
        *,
        plan_id: str,
        confirmation: PlanConfirmation,
        writing_task: WritingTask | None,
        chapter_id: str,
    ) -> DirectionPlanSnapshot | None:
        plan = self._load_confirmed_chapter_plan(plan_id)
        if plan is None:
            return None
        current_item = plan.plan_items[0] if plan.plan_items else None
        arc_refs = list(plan.source_arc_refs)
        if current_item is not None:
            for ref in current_item.arc_alignment:
                if not any(item.arc_type == ref.arc_type and item.arc_id == ref.arc_id for item in arc_refs):
                    arc_refs.append(ref)
        direction_summary = str(run.metadata.get("selected_direction_id", "")).strip()
        if direction_summary:
            direction_summary = f"selected_direction:{direction_summary}"
        else:
            direction_summary = f"direction_proposal:{plan.direction_proposal_id}"
        plan_summary = plan.plan_summary or (current_item.chapter_goal if current_item is not None else "")
        return DirectionPlanSnapshot(
            snapshot_id=f"dps_{run.session_id}_{plan_id}",
            work_id=plan.work_id,
            chapter_id=chapter_id,
            agent_session_id=run.session_id,
            direction_proposal_id=plan.direction_proposal_id,
            direction_proposal_version=1,
            selected_option_id=plan.selected_option_id,
            selection_id=plan.selection_id,
            chapter_plan_id=plan.chapter_plan_id,
            chapter_plan_version=plan.version,
            confirmation_id=confirmation.confirmation_id,
            writing_task_id=writing_task.writing_task_id if writing_task is not None else "",
            snapshot_status="ready" if writing_task is not None else "degraded",
            direction_summary=direction_summary[:200],
            plan_summary=plan_summary[:200],
            arc_refs_at_snapshot=arc_refs,
            warning_codes=[],
            created_at=_now(),
        )

    def _apply_plan_confirmation_to_chapter_plan(
        self,
        plan_id: str,
        *,
        confirmation_type: str,
        edited_items: list[str],
        edited_fields: dict[str, object],
    ) -> ChapterPlan | None:
        plan = self._load_confirmed_chapter_plan(plan_id)
        if plan is None or self._chapter_plan_repository is None:
            return plan
        updated_items: list[ChapterPlanItem] = []
        for item in plan.plan_items:
            patch = edited_fields.get(item.item_id, {}) if isinstance(edited_fields, dict) else {}
            if isinstance(patch, dict) and patch:
                updated_item = item.model_copy(update={**patch, "is_user_edited": True})
            else:
                updated_item = item
            updated_items.append(updated_item)
        updated_plan = plan.model_copy(
            update={
                "status": DirectionPlanStatus.EDITED if confirmation_type == "edited_confirm" else DirectionPlanStatus.CONFIRMED,
                "plan_items": updated_items,
                "edited_by": "user_action" if confirmation_type == "edited_confirm" else plan.edited_by,
                "confirmed_by": "user_action",
                "updated_at": _now(),
            }
        )
        self._chapter_plan_repository.save(updated_plan)
        return updated_plan

    def _apply_direction_selection_to_proposal(
        self,
        *,
        selected_direction_id: str,
        selected_option_id: str,
        selection_type: str,
    ) -> DirectionProposal | None:
        if self._direction_plan_repository is None:
            return None
        try:
            proposal = self._direction_plan_repository.get_direction_proposal(selected_direction_id)
        except Exception:  # noqa: BLE001
            return None
        update_fields: dict[str, object] = {
            "status": DirectionPlanStatus.EDITED if selection_type == "edited_select" else DirectionPlanStatus.SELECTED,
            "selected_by": "user_action",
            "selected_option_id": selected_option_id,
            "updated_at": _now(),
        }
        if selection_type == "edited_select":
            update_fields["edited_by"] = "user_action"
        updated_proposal = proposal.model_copy(update=update_fields)
        self._direction_plan_repository.save_direction_proposal(updated_proposal)
        return updated_proposal

    def _mark_related_chapter_plans_stale(
        self,
        *,
        work_id: str,
        chapter_id: str,
        direction_proposal_id: str,
        stale_reason: str,
    ) -> None:
        if self._chapter_plan_repository is None:
            return
        for plan in self._chapter_plan_repository.list_by_work(work_id, chapter_id=chapter_id):
            if plan.direction_proposal_id != direction_proposal_id:
                continue
            stale_plan = plan.model_copy(
                update={
                    "status": DirectionPlanStatus.STALE,
                    "stale_status": "stale",
                    "stale_reason": stale_reason,
                    "updated_at": _now(),
                }
            )
            self._chapter_plan_repository.save(stale_plan)

    def _mark_existing_writing_tasks_stale(
        self,
        *,
        work_id: str,
        chapter_id: str,
        stale_reason: str,
        direction_proposal_id: str = "",
    ) -> None:
        if self._direction_plan_repository is None:
            return
        for task in self._direction_plan_repository.list_writing_tasks(work_id, chapter_id=chapter_id):
            if direction_proposal_id and task.direction_proposal_id != direction_proposal_id:
                continue
            if task.status == WritingTaskStatus.STALE:
                continue
            stale_task = task.model_copy(
                update={
                    "status": WritingTaskStatus.STALE,
                    "stale_status": "stale",
                    "stale_reason": stale_reason,
                    "updated_at": _now(),
                }
            )
            self._direction_plan_repository.save_writing_task(stale_task)

    def _sequence_goal_from_plan(self, plan: ChapterPlan | None, *, existing: SequenceArc | None) -> str:
        if plan is not None:
            if plan.plan_summary:
                return plan.plan_summary
            if plan.plan_items:
                return plan.plan_items[0].chapter_goal
        if existing is not None and existing.sequence_goal:
            return existing.sequence_goal
        return "基于已确认章节计划推进当前序列目标。"

    def _sequence_events_from_plan(
        self,
        plan: ChapterPlan | None,
        *,
        plan_id: str,
        chapter_range: dict[str, int],
        existing: SequenceArc | None,
    ) -> list[SequenceEvent]:
        if plan is not None:
            events: list[SequenceEvent] = []
            for item in sorted(plan.plan_items, key=lambda current: current.plan_order):
                if item.key_events:
                    for beat in item.key_events:
                        events.append(
                            SequenceEvent(
                                event_id=f"seqevt_{plan_id}_{item.plan_order}_{beat.beat_order}",
                                event_order=len(events) + 1,
                                event_name=beat.beat_name,
                                description=beat.beat_description,
                                event_type=beat.beat_type,
                                estimated_chapter=int(chapter_range.get("from_chapter", 1) or 1) + max(item.plan_order - 1, 0),
                                involved_characters=list(beat.involved_characters),
                            )
                        )
                else:
                    events.append(
                        SequenceEvent(
                            event_id=f"seqevt_{plan_id}_{item.plan_order}",
                            event_order=len(events) + 1,
                            event_name=item.chapter_goal[:60] or f"plan_item_{item.plan_order}",
                            description=item.conflict_progression or item.chapter_goal,
                            event_type="development",
                            estimated_chapter=int(chapter_range.get("from_chapter", 1) or 1) + max(item.plan_order - 1, 0),
                        )
                    )
            if events:
                return events
        if existing is not None and existing.key_events:
            return list(existing.key_events)
        return [
            SequenceEvent(
                event_id=f"seqevt_{plan_id}_1",
                event_order=1,
                event_name="按已确认计划推进当前序列",
                description="已确认章节计划已写入轨道仓储，后续由 Planner Agent 继续细化关键事件。",
                event_type="development",
                estimated_chapter=int(chapter_range.get("from_chapter", 1) or 1),
            )
        ]

    def _required_beats_from_plan(self, plan: ChapterPlan | None, *, existing: SequenceArc | None) -> list[str]:
        if plan is not None:
            beats: list[str] = []
            for item in plan.plan_items:
                beats.extend(item.required_beats)
            deduped = list(dict.fromkeys(entry for entry in beats if entry))
            if deduped:
                return deduped
        return list(existing.required_beats) if existing is not None else []

    def _forbidden_items_from_plan(self, plan: ChapterPlan | None, *, volume_arc, existing: SequenceArc | None) -> list[str]:
        items = list(getattr(volume_arc, "forbidden_items", []))
        if plan is not None:
            for plan_item in plan.plan_items:
                items.extend(plan_item.forbidden_items)
        elif existing is not None:
            items.extend(existing.forbidden_items)
        return list(dict.fromkeys(entry for entry in items if entry))

    def _cancel_current_step_for_rerun(self, session_id: str, *, reason: str) -> None:
        session = self._runtime_service.get_session(session_id)
        if not session.current_step_id:
            return
        step = self._runtime_service.get_step(session.current_step_id)
        if step.status in {
            AgentStepStatus.SUCCEEDED,
            AgentStepStatus.FAILED,
            AgentStepStatus.SKIPPED,
            AgentStepStatus.CANCELLED,
            AgentStepStatus.IGNORED_LATE_RESULT,
        }:
            return
        self._runtime_service._step_repository.save_step(
            step.model_copy(
                update={
                    "status": AgentStepStatus.CANCELLED,
                    "status_reason": reason,
                    "finished_at": step.finished_at or _now(),
                }
            )
        )
        self._runtime_service._session_repository.save_session(
            session.model_copy(update={"current_step_id": "", "current_agent_type": "", "updated_at": _now()})
        )

    def _primary_result_ref(self, result_refs: list[ResultRef]) -> str:
        if not result_refs:
            return ""
        primary = result_refs[-1]
        return f"{primary.ref_type}:{primary.ref_id}"

    def _deliverable_result_ref(self, result_refs: list[ResultRef]) -> str:
        for item in reversed(result_refs):
            if item.ref_type in {"candidate_draft", "candidate_version"}:
                return f"{item.ref_type}:{item.ref_id}"
        return ""

    def _merge_warning_codes(self, current: list[str], incoming: list[str]) -> list[str]:
        merged = list(current)
        for warning_code in incoming:
            if warning_code and warning_code not in merged:
                merged.append(warning_code)
        return merged

    def _validate_degraded_progression(
        self,
        run: AgentWorkflowRun,
        *,
        current_stage: WorkflowStageName,
        decision: WorkflowDecision,
        warning_codes: list[str],
    ) -> None:
        if not warning_codes:
            return
        if decision != WorkflowDecision.CONTINUE:
            return
        if not self._contains_degraded_warning(warning_codes):
            return
        stage = self._stage_definition(run, current_stage)
        if not stage.allow_degraded or not run.policy.allow_degraded:
            raise ValueError("degraded_policy_forbidden")

    def _contains_degraded_warning(self, warning_codes: list[str]) -> bool:
        return any(code == "degraded" or code.endswith("_degraded") for code in warning_codes if code)

    def _should_require_review(self, run: AgentWorkflowRun) -> bool:
        return bool(run.policy.require_review_before_candidate_ready)
