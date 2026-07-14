from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator, model_validator


class AIBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ModelRole(StrEnum):
    OUTLINE_ANALYZER = "outline_analyzer"
    MANUSCRIPT_ANALYZER = "manuscript_analyzer"
    MEMORY_EXTRACTOR = "memory_extractor"
    STYLE_EXTRACTOR = "style_extractor"
    PLANNER = "planner"
    WRITING_TASK_BUILDER = "writing_task_builder"
    REVIEWER = "reviewer"
    WRITER = "writer"
    REWRITER = "rewriter"
    POLISHER = "polisher"
    DIALOGUE_WRITER = "dialogue_writer"
    SCENE_GENERATOR = "scene_generator"
    QUICK_TRIAL_WRITER = "quick_trial_writer"
    OPENING_STRATEGY_PLANNER = "opening_strategy_planner"
    OPENING_WRITER = "opening_writer"
    OPENING_RISK_CHECKER = "opening_risk_checker"


class AIProviderTestStatus(StrEnum):
    NOT_TESTED = "not_tested"
    OK = "ok"
    FAILED = "failed"


class ModelSelection(AIBaseModel):
    provider_name: str
    model_name: str


class AIProviderConfig(AIBaseModel):
    provider_name: str
    enabled: bool = True
    encrypted_api_key: str = ""
    default_model: str = ""
    timeout: int = 30
    base_url: str | None = None
    last_test_status: AIProviderTestStatus = AIProviderTestStatus.NOT_TESTED
    last_test_at: str = ""
    last_test_error_code: str = ""
    last_test_error_message: str = ""

    @property
    def key_configured(self) -> bool:
        return bool(self.encrypted_api_key)


class AISettings(AIBaseModel):
    provider_configs: dict[str, AIProviderConfig] = Field(default_factory=dict)
    model_role_mappings: dict[str, ModelSelection] = Field(default_factory=dict)


class AIJobStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    PAUSED = "paused"
    FAILED = "failed"
    CANCELLED = "cancelled"
    COMPLETED = "completed"


class AIJobStepStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    FAILED = "failed"
    SKIPPED = "skipped"
    COMPLETED = "completed"


class AIJobAttemptStatus(StrEnum):
    RUNNING = "running"
    FAILED = "failed"
    COMPLETED = "completed"
    IGNORED = "ignored"


class AIJobProgress(AIBaseModel):
    total_steps: int = 0
    completed_steps: int = 0
    current_step: str = ""
    current_step_label: str = ""
    percent: int = 0
    status: str = AIJobStatus.QUEUED.value
    error_code: str = ""
    error_message: str = ""
    warning_count: int = 0
    failed_step_count: int = 0
    skipped_step_count: int = 0
    updated_at: str = ""


class AIJob(AIBaseModel):
    job_id: str
    work_id: str
    chapter_id: str | None = None
    job_type: str
    status: AIJobStatus
    progress: AIJobProgress
    created_by: str = "user_action"
    idempotency_key: str = ""
    payload: dict[str, Any] = Field(default_factory=dict)
    input_snapshot: dict[str, Any] = Field(default_factory=dict)
    params: dict[str, Any] = Field(default_factory=dict)
    result_summary: dict[str, Any] = Field(default_factory=dict)
    result_ref: str = ""
    error_code: str = ""
    error_message: str = ""
    status_reason: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: str = ""
    updated_at: str = ""
    started_at: str = ""
    finished_at: str = ""
    paused_at: str = ""
    cancelled_at: str = ""


class AIJobStep(AIBaseModel):
    step_id: str
    job_id: str
    step_type: str
    step_name: str
    status: AIJobStepStatus
    order_index: int
    progress: int = 0
    label: str = ""
    started_at: str = ""
    finished_at: str = ""
    error_code: str = ""
    error_message: str = ""
    status_reason: str = ""
    warning_count: int = 0
    attempt_count: int = 0
    max_attempts: int = 3
    can_retry: bool = False
    can_skip: bool = False
    summary: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class AIJobAttempt(AIBaseModel):
    attempt_id: str
    job_id: str
    step_id: str
    attempt_no: int
    request_id: str
    trace_id: str
    provider_name: str
    model_name: str
    model_role: str
    prompt_key: str
    prompt_version: str
    output_schema_key: str
    status: AIJobAttemptStatus
    started_at: str = ""
    finished_at: str = ""
    elapsed_ms: int = 0
    error_code: str = ""
    error_message: str = ""
    llm_call_log_id: str = ""
    retry_reason: str = ""


def _normalize_agent_workflow_type(value: object) -> object:
    if value == "memory_refresh":
        return "memory_update"
    if value == "review":
        return "revision"
    return value


class AgentWorkflowType(StrEnum):
    CONTINUATION = "continuation"
    REVISION = "revision"
    PLANNING = "planning"
    MEMORY_UPDATE = "memory_update"
    FULL_WORKFLOW = "full_workflow"


class AgentSessionStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    WAITING_FOR_USER = "waiting_for_user"
    PAUSED = "paused"
    CANCELLING = "cancelling"
    CANCELLED = "cancelled"
    FAILED = "failed"
    COMPLETED = "completed"
    PARTIAL_SUCCESS = "partial_success"


class AgentStepStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    WAITING_OBSERVATION = "waiting_observation"
    WAITING_USER = "waiting_user"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"
    IGNORED_LATE_RESULT = "ignored_late_result"


class AgentObservationType(StrEnum):
    TOOL_RESULT = "tool_result"
    MODEL_RESULT = "model_result"
    USER_DECISION = "user_decision"
    VALIDATION_RESULT = "validation_result"
    STATE_CHANGE = "state_change"
    SYSTEM_EVENT = "system_event"
    ERROR_EVENT = "error_event"
    WARNING = "warning"
    TIMEOUT = "timeout"
    LATE_RESULT_IGNORED = "late_result_ignored"
    ERROR = "error"


class PPAOPhase(StrEnum):
    PERCEPTION = "perception"
    PLANNING = "planning"
    ACTION = "action"
    OBSERVATION = "observation"


class AgentSession(AIBaseModel):
    session_id: str
    job_id: str
    work_id: str
    chapter_id: str | None = None
    agent_workflow_type: AgentWorkflowType
    status: AgentSessionStatus
    current_agent_type: str = ""
    allow_degraded: bool = True
    caller_type: str = "user_action"
    user_instruction: str = ""
    request_id: str = ""
    trace_id: str = ""
    current_step_id: str = ""
    current_phase: PPAOPhase | Literal[""] = ""
    result_ref: str = ""
    result: AgentResult | None = None
    warning_codes: list[str] = Field(default_factory=list)
    error_code: str = ""
    error_message: str = ""
    status_reason: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: str = ""
    updated_at: str = ""
    started_at: str = ""
    waiting_at: str = ""
    paused_at: str = ""
    resumed_at: str = ""
    cancelling_at: str = ""
    cancelled_at: str = ""
    finished_at: str = ""

    @model_validator(mode="before")
    @classmethod
    def _normalize_legacy_keys(cls, data: object) -> object:
        if not isinstance(data, dict):
            return data
        payload = dict(data)
        if "workflow_type" in payload and "agent_workflow_type" not in payload:
            payload["agent_workflow_type"] = payload.pop("workflow_type")
        if "agent_workflow_type" in payload:
            payload["agent_workflow_type"] = _normalize_agent_workflow_type(payload["agent_workflow_type"])
        if "allow_degraded" not in payload:
            metadata = payload.get("metadata")
            if isinstance(metadata, dict) and "allow_degraded" in metadata:
                payload["allow_degraded"] = bool(metadata.get("allow_degraded", True))
        return payload

    @property
    def workflow_type(self) -> AgentWorkflowType:
        return self.agent_workflow_type


class ToolCallRef(AIBaseModel):
    tool_call_id: str
    tool_name: str
    status: str = ""
    result_ref: str = ""
    error_code: str = ""


class StepPlan(AIBaseModel):
    next_action_type: str = ""
    target_tool_name: str = ""
    expected_observation_type: str = ""
    retryable: bool = True
    requires_user_decision: bool = False
    side_effect_level: str = ""


class AgentStep(AIBaseModel):
    step_id: str
    session_id: str
    job_id: str
    job_step_id: str = ""
    agent_type: str
    step_type: str
    action: str
    order_index: int
    status: AgentStepStatus
    step_phase: PPAOPhase | Literal[""] = ""
    request_id: str = ""
    trace_id: str = ""
    tool_calls: list[ToolCallRef] = Field(default_factory=list)
    step_plan: StepPlan | None = None
    input_ref: str = ""
    output_refs: list[str] = Field(default_factory=list)
    attempt_count: int = 0
    max_attempts: int = 3
    retryable: bool = True
    skippable: bool = False
    requires_user_decision: bool = False
    skip_reason: str = ""
    warning_codes: list[str] = Field(default_factory=list)
    error_code: str = ""
    error_message: str = ""
    status_reason: str = ""
    observation_id: str = ""
    prior_observation_refs: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: str = ""
    started_at: str = ""
    waiting_at: str = ""
    finished_at: str = ""

    @model_validator(mode="before")
    @classmethod
    def _normalize_legacy_keys(cls, data: object) -> object:
        if not isinstance(data, dict):
            return data
        payload = dict(data)
        if "step_order" in payload and "order_index" not in payload:
            payload["order_index"] = payload.pop("step_order")
        return payload

    @property
    def step_order(self) -> int:
        return self.order_index


class AgentObservation(AIBaseModel):
    observation_id: str
    session_id: str
    step_id: str
    observation_type: AgentObservationType
    source_type: str
    source_ref: str = ""
    status: str
    data_ref: str = ""
    safe_message: str = ""
    summary: str = ""
    decision: str = ""
    decision_reason: str = ""
    source_tool_call_id: str = ""
    source_attempt_no: int = 0
    warning_codes: list[str] = Field(default_factory=list)
    error_code: str = ""
    error_message: str = ""
    next_action_hint: str = ""
    request_id: str = ""
    trace_id: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: str = ""


class AgentRunContext(AIBaseModel):
    session_id: str
    job_id: str = ""
    step_id: str = ""
    work_id: str
    chapter_id: str | None = None
    agent_workflow_type: AgentWorkflowType = AgentWorkflowType.CONTINUATION
    current_agent_type: str
    current_phase: PPAOPhase | Literal[""] = ""
    caller_type: str = "user_action"
    user_instruction: str = ""
    context_refs: list[str] = Field(default_factory=list)
    selected_direction_id: str = ""
    selected_chapter_plan_id: str = ""
    request_id: str = ""
    trace_id: str = ""
    allow_degraded: bool = True
    warning_codes: list[str] = Field(default_factory=list)
    resource_scope_refs: list[str] = Field(default_factory=list)
    prior_observation_refs: list[str] = Field(default_factory=list)
    execution_guard_flags: dict[str, bool] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def _normalize_workflow_type(cls, data: object) -> object:
        if not isinstance(data, dict):
            return data
        payload = dict(data)
        if "workflow_type" in payload and "agent_workflow_type" not in payload:
            payload["agent_workflow_type"] = payload.pop("workflow_type")
        if "agent_workflow_type" in payload:
            payload["agent_workflow_type"] = _normalize_agent_workflow_type(payload["agent_workflow_type"])
        return payload


class TraceLevel(StrEnum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class TraceEventStage(StrEnum):
    PERCEPTION = "perception"
    PLANNING = "planning"
    ACTION = "action"
    OBSERVATION = "observation"
    ORCHESTRATION = "orchestration"
    AUDIT = "audit"


class TraceEventType(StrEnum):
    SESSION_CREATED = "session_created"
    SESSION_STARTED = "session_started"
    SESSION_PAUSED = "session_paused"
    SESSION_RESUMED = "session_resumed"
    SESSION_CANCELLING = "session_cancelling"
    SESSION_CANCELLED = "session_cancelled"
    SESSION_FAILED = "session_failed"
    SESSION_COMPLETED = "session_completed"
    SESSION_PARTIAL_SUCCESS = "session_partial_success"
    STAGE_ENTERED = "stage_entered"
    STAGE_EXITED = "stage_exited"
    STEP_CREATED = "step_created"
    STEP_STARTED = "step_started"
    STEP_RETRYING = "step_retrying"
    STEP_SUCCEEDED = "step_succeeded"
    STEP_FAILED = "step_failed"
    STEP_SKIPPED = "step_skipped"
    STEP_CANCELLED = "step_cancelled"
    STEP_IGNORED_LATE_RESULT = "step_ignored_late_result"
    TOOL_CALL_STARTED = "tool_call_started"
    TOOL_CALL_SUCCEEDED = "tool_call_succeeded"
    TOOL_CALL_FAILED = "tool_call_failed"
    TOOL_CALL_DENIED = "tool_call_denied"
    OBSERVATION_RECORDED = "observation_recorded"
    WAITING_FOR_USER_ENTERED = "waiting_for_user_entered"
    WAITING_FOR_USER_RESOLVED = "waiting_for_user_resolved"
    POLICY_BLOCKED = "policy_blocked"
    DEGRADED_DETECTED = "degraded_detected"
    BLOCKED_DETECTED = "blocked_detected"
    CHECKPOINT_SAVED = "checkpoint_saved"
    CHECKPOINT_RESTORED = "checkpoint_restored"
    ALERT_TRIGGERED = "alert_triggered"
    ALERT_RESOLVED = "alert_resolved"
    TRACE_WRITE_FAILED = "trace_write_failed"
    AGENT_SESSION_STARTED = "agent_session_started"
    AGENT_SESSION_COMPLETED = "agent_session_completed"
    AGENT_SESSION_FAILED = "agent_session_failed"
    AGENT_SESSION_CANCELLED = "agent_session_cancelled"
    TOOL_CALL_FORBIDDEN = "tool_call_forbidden"
    USER_DECISION_RECORDED = "user_decision_recorded"
    SUGGESTION_ACCEPTED = "suggestion_accepted"
    SUGGESTION_DISMISSED = "suggestion_dismissed"
    CONFLICT_RESOLVED = "conflict_resolved"
    CONFLICT_OVERRIDDEN = "conflict_overridden"
    MEMORY_REVISION_CREATED = "memory_revision_created"
    MEMORY_REVISION_APPLIED = "memory_revision_applied"
    MEMORY_REVISION_ROLLED_BACK = "memory_revision_rolled_back"
    DUPLICATE_IGNORED = "duplicate_ignored"


class AgentTraceStatus(StrEnum):
    RUNNING = "running"
    WAITING_FOR_USER = "waiting_for_user"
    COMPLETED = "completed"
    PARTIAL_SUCCESS = "partial_success"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ToolPermissionResult(StrEnum):
    ALLOW = "allow"
    DENY = "deny"
    CONDITIONAL_ALLOW = "conditional_allow"


class ToolCallTraceStatus(StrEnum):
    STARTED = "started"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"
    IGNORED_LATE_RESULT = "ignored_late_result"


class TraceAlertScope(StrEnum):
    STEP = "step"
    SESSION = "session"
    WORKFLOW = "workflow"
    SYSTEM = "system"


class TraceAlertType(StrEnum):
    TIMEOUT_SPIKE = "timeout_spike"
    FAILURE_SPIKE = "failure_spike"
    BLOCKED_SPIKE = "blocked_spike"
    RETRY_EXHAUSTED = "retry_exhausted"
    QUEUE_BACKLOG = "queue_backlog"
    AUDIT_WRITE_FAILED = "audit_write_failed"


class TraceAlertStatus(StrEnum):
    OPEN = "open"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    MUTED = "muted"


class AgentTrace(AIBaseModel):
    trace_id: str
    work_id: str
    chapter_id: str = ""
    session_id: str
    workflow_run_id: str = ""
    workflow_type: str = ""
    status: AgentTraceStatus = AgentTraceStatus.RUNNING
    agent_sequence: list[str] = Field(default_factory=list)
    total_steps: int = 0
    result_summary: str = ""
    result_ref_ids: list[str] = Field(default_factory=list)
    total_elapsed_ms: int = 0
    total_tokens: int = 0
    warning_codes: list[str] = Field(default_factory=list)
    error_code: str = ""
    started_at: str = ""
    ended_at: str = ""
    created_at: str = ""
    updated_at: str = ""


class AgentTraceEvent(AIBaseModel):
    event_id: str
    trace_id: str
    session_id: str
    step_id: str = ""
    event_type: TraceEventType
    event_stage: TraceEventStage = TraceEventStage.ORCHESTRATION
    event_time: str
    level: TraceLevel = TraceLevel.INFO
    summary: str
    safe_refs: list[str] = Field(default_factory=list)
    payload_digest: dict[str, Any] = Field(default_factory=dict)
    request_id: str = ""
    correlation_id: str = ""


class AgentStepTrace(AIBaseModel):
    step_trace_id: str
    trace_id: str
    step_id: str
    session_id: str
    agent_type: str
    action: str
    attempt_no: int = 0
    status: str
    started_at: str = ""
    ended_at: str = ""
    duration_ms: int = 0
    warning_codes: list[str] = Field(default_factory=list)
    error_code: str = ""


class ToolCallTrace(AIBaseModel):
    tool_trace_id: str
    trace_id: str
    step_id: str
    tool_name: str
    caller_type: str
    side_effect_level: str
    permission_result: ToolPermissionResult = ToolPermissionResult.ALLOW
    call_status: ToolCallTraceStatus = ToolCallTraceStatus.STARTED
    duration_ms: int = 0
    error_code: str = ""
    safe_input_digest: dict[str, Any] = Field(default_factory=dict)
    safe_output_digest: dict[str, Any] = Field(default_factory=dict)
    tool_audit_log_ref: str = ""


class ObservationTrace(AIBaseModel):
    observation_trace_id: str
    trace_id: str
    step_id: str
    observation_type: str
    decision_hint: str = ""
    decision_source: str = ""
    is_blocking: bool = False
    warning_codes: list[str] = Field(default_factory=list)
    summary: str
    safe_refs: list[str] = Field(default_factory=list)


class LLMCallTraceView(AIBaseModel):
    llm_call_log_ref: str
    trace_id: str
    step_id: str = ""
    prompt_ref: str
    model_role: str
    provider: str
    model: str
    context_pack_ref: str = ""
    output_schema_key: str = ""
    token_count: int = 0
    elapsed_ms: int = 0
    status: str = ""
    error_code: str = ""
    content_hash: str = ""


class UserDecisionTrace(AIBaseModel):
    decision_trace_id: str
    trace_id: str
    session_id: str
    step_id: str = ""
    decision_type: str
    target_entity_type: str
    target_entity_id: str
    decided_by: str
    decision_note: str = ""
    decided_at: str


class TraceMetricPoint(AIBaseModel):
    metric_id: str
    trace_id: str
    metric_name: str
    metric_value: float
    labels: dict[str, str] = Field(default_factory=dict)
    timestamp: str


class TraceAlertRecord(AIBaseModel):
    alert_id: str
    trace_id: str = ""
    scope: TraceAlertScope
    alert_type: TraceAlertType
    severity: TraceLevel
    status: TraceAlertStatus = TraceAlertStatus.OPEN
    summary: str
    triggered_at: str
    resolved_at: str = ""


class ResultRef(AIBaseModel):
    ref_type: str
    ref_id: str
    source_agent_type: str = ""
    source_step_id: str = ""
    status: str = ""


class AgentType(StrEnum):
    MEMORY = "memory"
    PLANNER = "planner"
    WRITER = "writer"
    REVIEWER = "reviewer"
    REWRITER = "rewriter"


class AgentCapability(StrEnum):
    STORY_CONTEXT_READ = "story_context_read"
    MEMORY_GAP_DETECTION = "memory_gap_detection"
    MEMORY_UPDATE_SUGGESTION = "memory_update_suggestion"
    DIRECTION_PROPOSAL = "direction_proposal"
    CHAPTER_PLANNING = "chapter_planning"
    WRITING_TASK_PREPARATION = "writing_task_preparation"
    CANDIDATE_GENERATION = "candidate_generation"
    CANDIDATE_VALIDATION = "candidate_validation"
    CONSISTENCY_REVIEW = "consistency_review"
    STYLE_REVIEW = "style_review"
    PLOT_REVIEW = "plot_review"
    ISSUE_REPORTING = "issue_reporting"
    CANDIDATE_REVISION = "candidate_revision"
    REVISION_VALIDATION = "revision_validation"


class AgentToolPermissionMode(StrEnum):
    ALLOW = "allow"
    DENY = "deny"
    CONDITIONAL = "conditional"


class AgentResultRef(ResultRef):
    ref_scope: Literal["work", "chapter", "session"] = "session"
    checksum: str = ""
    summary: str = ""
    created_at: str = ""


class AgentExecutionProfile(AIBaseModel):
    agent_type: AgentType
    capabilities: list[str] = Field(default_factory=list)
    model_role: str
    default_timeout: int = 300
    max_retry: int = 1
    allow_degraded: bool = True
    allowed_tool_names: list[str] = Field(default_factory=list)
    denied_tool_names: list[str] = Field(default_factory=list)
    max_output_chars: int = 8000
    output_schema_key: str = "plain_text"
    trace_level: Literal["minimal", "standard", "verbose"] = "standard"
    metadata: dict[str, Any] = Field(default_factory=dict)


class AgentToolPermission(AIBaseModel):
    tool_name: str
    agent_type: AgentType
    permission: AgentToolPermissionMode
    side_effect_level: str
    requires_user_action: bool = False
    allow_degraded: bool = False
    retryable: bool = False
    notes: str = ""


class AgentInput(AIBaseModel):
    session_id: str
    workflow_type: AgentWorkflowType
    stage: str
    agent_type: AgentType
    work_id: str
    chapter_id: str | None = None
    user_instruction: str = ""
    context_refs: list[str] = Field(default_factory=list)
    selected_direction_id: str = ""
    selected_chapter_plan_id: str = ""
    current_candidate_draft_id: str = ""
    current_candidate_version_id: str = ""
    review_id: str = ""
    allow_degraded: bool = True
    warning_codes: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class AgentOutput(AIBaseModel):
    agent_type: AgentType
    step_id: str
    status: str
    result_refs: list[AgentResultRef] = Field(default_factory=list)
    warning_codes: list[str] = Field(default_factory=list)
    error_code: str = ""
    decision_hint: str = ""
    suggested_next_stage: str = ""
    requires_user_action: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


class StepSummaryItem(AIBaseModel):
    step_id: str
    agent_type: str
    step_type: str
    action: str
    status: str
    step_phase: PPAOPhase | Literal[""] = ""
    status_reason: str = ""
    safe_message: str = ""
    error_code: str = ""
    error_message: str = ""
    warning_codes: list[str] = Field(default_factory=list)
    started_at: str = ""
    waiting_at: str = ""
    finished_at: str = ""


class StepSummary(AIBaseModel):
    steps: list[StepSummaryItem] = Field(default_factory=list)


class AgentResult(AIBaseModel):
    session_id: str
    status: str
    result_refs: list[ResultRef] = Field(default_factory=list)
    primary_output_type: str = ""
    primary_output_ref: str = ""
    step_summary: StepSummary | None = None
    warning_codes: list[str] = Field(default_factory=list)
    error_code: str = ""
    error_message: str = ""
    next_user_action: str = ""
    total_steps: int = 0
    succeeded_steps: int = 0
    failed_steps: int = 0
    skipped_steps: int = 0
    total_elapsed_ms: int = 0
    finished_at: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class WorkflowType(StrEnum):
    CONTINUATION_WORKFLOW = "continuation_workflow"
    REVISION_WORKFLOW = "revision_workflow"
    PLANNING_WORKFLOW = "planning_workflow"
    MEMORY_UPDATE_WORKFLOW = "memory_update_workflow"
    REVIEW_WORKFLOW = "review_workflow"
    FULL_WORKFLOW = "full_workflow"


class WorkflowP1Status(StrEnum):
    REQUIRED = "required"
    OPTIONAL = "optional"
    RESERVED = "reserved"


class WorkflowStageName(StrEnum):
    SESSION_INIT = "session_init"
    MEMORY_CONTEXT_PREPARE = "memory_context_prepare"
    PLANNING_PREPARE = "planning_prepare"
    DIRECTION_SELECTION_WAITING = "direction_selection_waiting"
    CHAPTER_PLAN_CONFIRM_WAITING = "chapter_plan_confirm_waiting"
    WRITING_PREPARE = "writing_prepare"
    DRAFTING = "drafting"
    REVIEWING = "reviewing"
    REWRITING = "rewriting"
    CANDIDATE_READY = "candidate_ready"
    HUMAN_REVIEW_WAITING = "human_review_waiting"
    MEMORY_SUGGESTION = "memory_suggestion"
    MEMORY_REVIEW_WAITING = "memory_review_waiting"
    COMPLETED = "completed"
    PARTIAL_SUCCESS = "partial_success"
    FAILED = "failed"
    CANCELLED = "cancelled"


class WorkflowTransitionTrigger(StrEnum):
    AUTO = "auto"
    USER_ACTION = "user_action"
    OBSERVATION_DECISION = "observation_decision"
    POLICY_RULE = "policy_rule"


class WorkflowDecisionSource(StrEnum):
    AGENT_ORCHESTRATOR = "agent_orchestrator"
    USER_ACTION = "user_action"
    RUNTIME_OBSERVATION = "runtime_observation"
    TOOL_RESULT = "tool_result"
    POLICY = "policy"


class WorkflowDecision(StrEnum):
    CONTINUE = "continue"
    WAIT_FOR_USER = "wait_for_user"
    RETRY_STEP = "retry_step"
    RETRY_STAGE = "retry_stage"
    SKIP_OPTIONAL_STAGE = "skip_optional_stage"
    ENTER_REWRITER = "enter_rewriter"
    RETURN_TO_REVIEWER = "return_to_reviewer"
    MARK_PARTIAL_SUCCESS = "mark_partial_success"
    FAIL_WORKFLOW = "fail_workflow"
    COMPLETE_WORKFLOW = "complete_workflow"
    CANCEL_WORKFLOW = "cancel_workflow"


class WorkflowFailureBehavior(StrEnum):
    FAIL_WORKFLOW = "fail_workflow"
    PARTIAL_SUCCESS_POSSIBLE = "partial_success_possible"
    ENTER_WAITING_USER = "enter_waiting_user"


class ConflictBlockingStrategy(StrEnum):
    BLOCK_WORKFLOW = "block_workflow"
    WARN_BUT_CONTINUE = "warn_but_continue"


class StageCondition(AIBaseModel):
    condition_type: str
    expression: str = ""
    required: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)


class StageRecord(AIBaseModel):
    stage_name: WorkflowStageName
    status: str
    decision: str = ""
    decision_reason: str = ""
    result_refs: list[ResultRef] = Field(default_factory=list)
    warning_codes: list[str] = Field(default_factory=list)
    entered_at: str = ""
    exited_at: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class WorkflowPolicy(AIBaseModel):
    max_revision_rounds: int = 1
    max_retry_per_stage: int = 1
    allow_degraded: bool = True
    require_direction_confirmation: bool = True
    require_chapter_plan_confirmation: bool = True
    require_review_before_candidate_ready: bool = True
    allow_partial_success: bool = True
    allow_skip_reviewer: bool = False
    allow_skip_rewriter: bool = True
    allow_memory_suggestion_after_apply: bool = True
    conflict_blocking_strategy: ConflictBlockingStrategy = ConflictBlockingStrategy.BLOCK_WORKFLOW
    timeout_policy: dict[str, Any] = Field(default_factory=dict)
    formal_write_allowed: bool = False
    auto_apply_allowed: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("max_revision_rounds", "max_retry_per_stage")
    @classmethod
    def _validate_non_negative(cls, value: int) -> int:
        if value < 0:
            raise ValueError("workflow_policy_negative_value")
        return value

    @model_validator(mode="after")
    def _enforce_hard_safety_flags(self) -> "WorkflowPolicy":
        object.__setattr__(self, "formal_write_allowed", False)
        object.__setattr__(self, "auto_apply_allowed", False)
        return self


class WorkflowStage(AIBaseModel):
    stage_name: WorkflowStageName
    stage_order: int
    responsible_agent_type: str = ""
    entry_conditions: list[StageCondition] = Field(default_factory=list)
    exit_conditions: list[StageCondition] = Field(default_factory=list)
    expected_result_refs: list[str] = Field(default_factory=list)
    allow_degraded: bool = False
    allow_waiting_user: bool = False
    allow_retry: bool = True
    allow_skip: bool = False
    is_optional: bool = False
    is_terminal: bool = False
    failure_behavior: WorkflowFailureBehavior = WorkflowFailureBehavior.FAIL_WORKFLOW
    max_retry_per_stage: int = 1


class WorkflowTransition(AIBaseModel):
    from_stage: WorkflowStageName
    to_stage: WorkflowStageName
    trigger: WorkflowTransitionTrigger
    condition: str = ""
    decision_source: WorkflowDecisionSource = WorkflowDecisionSource.AGENT_ORCHESTRATOR
    reason_code: str = ""
    created_at: str = ""


class WorkflowCheckpoint(AIBaseModel):
    checkpoint_id: str
    session_id: str
    workflow_type: WorkflowType
    current_stage: WorkflowStageName
    current_agent_type: str = ""
    current_step_id: str = ""
    revision_round: int = 0
    result_refs: list[ResultRef] = Field(default_factory=list)
    warning_codes: list[str] = Field(default_factory=list)
    error_code: str = ""
    waiting_for_user_reason: str = ""
    selected_direction_id: str = ""
    selected_chapter_plan_id: str = ""
    current_candidate_draft_id: str = ""
    current_candidate_version_id: str = ""
    created_at: str = ""


class AgentWorkflowDefinition(AIBaseModel):
    workflow_type: WorkflowType
    stages: list[WorkflowStage] = Field(default_factory=list)
    transitions: list[WorkflowTransition] = Field(default_factory=list)
    default_policy: WorkflowPolicy = Field(default_factory=WorkflowPolicy)
    p1_status: WorkflowP1Status = WorkflowP1Status.REQUIRED
    enabled: bool = True
    version: str = "v1"


class AgentWorkflowRun(AIBaseModel):
    run_id: str
    session_id: str
    workflow_type: WorkflowType
    current_stage: WorkflowStageName
    stage_history: list[StageRecord] = Field(default_factory=list)
    policy: WorkflowPolicy = Field(default_factory=WorkflowPolicy)
    checkpoints: list[WorkflowCheckpoint] = Field(default_factory=list)
    revision_round: int = 0
    status: AgentSessionStatus = AgentSessionStatus.PENDING
    result: AgentResult | None = None
    result_refs: list[ResultRef] = Field(default_factory=list)
    warning_codes: list[str] = Field(default_factory=list)
    error_code: str = ""
    request_id: str = ""
    trace_id: str = ""
    created_at: str = ""
    finished_at: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class InitializationStatus(StrEnum):
    NOT_STARTED = "not_started"
    OUTLINE_ANALYZING = "outline_analyzing"
    MANUSCRIPT_ANALYZING = "manuscript_analyzing"
    MEMORY_BUILDING = "memory_building"
    STATE_BUILDING = "state_building"
    VECTOR_INDEXING = "vector_indexing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    STALE = "stale"


class InitializationCompletionStatus(StrEnum):
    SUCCEEDED = "succeeded"
    PARTIAL_SUCCESS = "partial_success"
    FAILED = "failed"
    IGNORED = "ignored"


class ChapterAnalysisStatus(StrEnum):
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    EMPTY = "empty"


class OutlineAnalysisResult(AIBaseModel):
    work_id: str
    title: str = ""
    chapter_order: list[str] = Field(default_factory=list)
    chapter_titles: list[str] = Field(default_factory=list)
    global_summary: str = ""
    genre: str = ""
    tone: str = ""
    issues: list[str] = Field(default_factory=list)
    outline_empty: bool = True
    story_phase_map: list[str] = Field(default_factory=list)
    main_conflict: str = ""
    important_characters: list[str] = Field(default_factory=list)
    setting_facts: list[str] = Field(default_factory=list)
    foreshadow_map: list[str] = Field(default_factory=list)
    expected_story_direction: str = ""
    analysis_confidence: float = 0.0


class ChapterSceneDetail(AIBaseModel):
    chapter_id: str
    chapter_title: str = ""
    chapter_version: int = 1
    scene_order: int = 1
    location: str
    time_of_day: str = ""
    atmosphere: str = ""
    characters_present: list[str] = Field(default_factory=list)
    emotional_tone: str = ""
    pov_hint: str = ""
    reveal_points: list[str] = Field(default_factory=list)


class ChapterAnalysisResult(AIBaseModel):
    chapter_id: str
    chapter_title: str = ""
    chapter_version: int = 1
    status: ChapterAnalysisStatus
    summary: str = ""
    characters: list[str] = Field(default_factory=list)
    locations: list[str] = Field(default_factory=list)
    plot_points: list[str] = Field(default_factory=list)
    unresolved_threads: list[str] = Field(default_factory=list)
    scene_details: list[ChapterSceneDetail] = Field(default_factory=list)
    chapter_position: str = ""
    plot_progress: str = ""
    character_state_delta: list[dict[str, Any]] = Field(default_factory=list)
    setting_fact_delta: list[dict[str, Any]] = Field(default_factory=list)
    foreshadow_candidate_delta: list[dict[str, Any]] = Field(default_factory=list)
    deviations_from_outline: list[str] = Field(default_factory=list)
    timeline_info: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    analysis_confidence: float = 0.0
    error_code: str = ""
    error_message: str = ""
    is_empty: bool = False
    analyzed_at: str = ""


class HierarchicalStorySummary(AIBaseModel):
    stage_summaries: list[dict[str, Any]] = Field(default_factory=list)
    volume_summaries: list[dict[str, Any]] = Field(default_factory=list)
    global_summary: str
    current_story_phase: str = ""
    main_plot_threads: list[str] = Field(default_factory=list)
    unresolved_questions: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    analysis_confidence: float = 0.0


class StoryMemorySnapshot(AIBaseModel):
    snapshot_id: str
    work_id: str
    source_initialization_id: str
    source_job_id: str
    source_chapter_ids: list[str] = Field(default_factory=list)
    source_chapter_versions: dict[str, int] = Field(default_factory=dict)
    global_summary: str = ""
    chapter_summaries: list[dict[str, str]] = Field(default_factory=list)
    stage_summaries: list[dict[str, Any]] = Field(default_factory=list)
    volume_summaries: list[dict[str, Any]] = Field(default_factory=list)
    characters: list[str] = Field(default_factory=list)
    locations: list[str] = Field(default_factory=list)
    plot_threads: list[str] = Field(default_factory=list)
    scene_details: list[ChapterSceneDetail] = Field(default_factory=list)
    source: str = "initialization_analysis"
    source_analysis_version: str = ""
    outline_analysis_id: str = ""
    story_blueprint_id: str = ""
    chapter_analysis_ids: list[str] = Field(default_factory=list)
    current_story_summary: dict[str, Any] = Field(default_factory=dict)
    character_states: list[dict[str, Any]] = Field(default_factory=list)
    setting_facts: list[dict[str, Any]] = Field(default_factory=list)
    foreshadow_candidates: list[dict[str, Any]] = Field(default_factory=list)
    unresolved_questions: list[str] = Field(default_factory=list)
    timeline_facts: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    confidence: float = 0.0
    stale_status: str = "fresh"
    stale_reason: str = ""
    created_at: str = ""
    updated_at: str = ""


class StoryStateSnapshot(AIBaseModel):
    story_state_id: str
    work_id: str
    source_initialization_id: str
    source_job_id: str
    latest_chapter_id: str = ""
    latest_chapter_version: int = 0
    current_position_summary: str = ""
    active_characters: list[str] = Field(default_factory=list)
    active_locations: list[str] = Field(default_factory=list)
    unresolved_threads: list[str] = Field(default_factory=list)
    continuity_notes: list[str] = Field(default_factory=list)
    source_snapshot_id: str = ""
    baseline_type: str = "analysis_baseline"
    source: str = "confirmed_chapter_analysis"
    source_chapter_analysis_ids: list[str] = Field(default_factory=list)
    current_chapter_id: str = ""
    current_chapter_order: int = 0
    current_story_phase: str = ""
    current_time_position: str = ""
    current_character_states: list[dict[str, Any]] = Field(default_factory=list)
    active_conflicts: list[str] = Field(default_factory=list)
    active_foreshadows: list[dict[str, Any]] = Field(default_factory=list)
    resolved_foreshadows: list[dict[str, Any]] = Field(default_factory=list)
    important_setting_facts: list[dict[str, Any]] = Field(default_factory=list)
    current_location_scope: list[str] = Field(default_factory=list)
    recent_key_events: list[str] = Field(default_factory=list)
    unresolved_questions: list[str] = Field(default_factory=list)
    analysis_confidence: float = 0.0
    stale_status: str = "fresh"
    stale_reason: str = ""
    created_at: str = ""
    updated_at: str = ""


class MemoryTargetType(StrEnum):
    STORY_MEMORY = "story_memory"
    STORY_STATE = "story_state"
    BOTH = "both"


class MemoryUpdateType(StrEnum):
    CHARACTER_UPDATE = "character_update"
    SETTING_UPDATE = "setting_update"
    TIMELINE_EVENT_ADD = "timeline_event_add"
    TIMELINE_EVENT_UPDATE = "timeline_event_update"
    FORESHADOW_ADD = "foreshadow_add"
    FORESHADOW_UPDATE = "foreshadow_update"
    FORESHADOW_RESOLVE = "foreshadow_resolve"
    PLOT_THREAD_UPDATE = "plot_thread_update"
    STORY_STATE_UPDATE = "story_state_update"
    ARC_NOTE_UPDATE = "arc_note_update"
    CONTINUITY_NOTE_ADD = "continuity_note_add"
    UNKNOWN_MEMORY_UPDATE = "unknown_memory_update"


class MemorySuggestionSeverity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class MemorySuggestionStatus(StrEnum):
    PENDING = "pending"
    GENERATED = "generated"
    SHOWN = "shown"
    ACCEPTED = "accepted"
    EDITED = "edited"
    REJECTED = "rejected"
    CONVERTED = "converted"
    STALE = "stale"
    SUPERSEDED = "superseded"
    FAILED = "failed"


class MemorySuggestionDecisionType(StrEnum):
    NONE = ""
    APPROVED = "approved"
    EDITED_APPROVED = "edited_approved"
    REJECTED = "rejected"
    DEFERRED = "deferred"


class MemoryCandidateChangeType(StrEnum):
    ADD = "add"
    UPDATE = "update"
    DELETE = "delete"
    NOTE_ONLY = "note_only"


class MemoryCandidateStatus(StrEnum):
    PENDING = "pending"
    SELECTED = "selected"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"


class MemoryGateState(StrEnum):
    OPEN = "open"
    WAITING_FOR_USER = "waiting_for_user"
    PARTIALLY_APPROVED = "partially_approved"
    APPROVED = "approved"
    REJECTED = "rejected"
    APPLIED = "applied"
    CANCELLED = "cancelled"
    FAILED = "failed"


class MemoryRevisionRecordType(StrEnum):
    NORMAL = "normal"
    ROLLBACK = "rollback"


class MemoryRevisionStatus(StrEnum):
    PENDING = "pending"
    WAITING_FOR_REVIEW = "waiting_for_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    APPLIED = "applied"
    STALE = "stale"
    SUPERSEDED = "superseded"
    FAILED = "failed"


class MemoryReviewDecisionType(StrEnum):
    APPROVED = "approved"
    REJECTED = "rejected"
    DEFERRED = "deferred"


class MemoryApplyStatus(StrEnum):
    SUCCESS = "success"
    PARTIAL_SUCCESS = "partial_success"
    FAILED = "failed"


class MemoryRevisionSource(AIBaseModel):
    source_id: str = ""
    source_type: str
    entity_type: str = ""
    entity_ref_id: str = ""
    source_ref_id: str = ""
    source_session_id: str = ""
    source_version_id: str = ""
    excerpt: str = ""
    relevance: str = ""


class MemoryUpdateCandidate(AIBaseModel):
    candidate_id: str
    suggestion_id: str
    candidate_no: int
    field_path: str
    field_label: str
    current_value: str
    proposed_value: str
    change_type: MemoryCandidateChangeType = MemoryCandidateChangeType.UPDATE
    rationale: str
    confidence: float = 0.0
    status: MemoryCandidateStatus = MemoryCandidateStatus.PENDING
    suggestion_ids: list[str] = Field(default_factory=list)
    selected_suggestion_id: str = ""
    created_at: str = ""


class MemoryUpdateSuggestion(AIBaseModel):
    id: str
    work_id: str
    chapter_id: str = ""
    candidate_draft_id: str = ""
    candidate_version_id: str = ""
    review_report_id: str = ""
    ai_suggestion_id: str = ""
    conflict_guard_record_id: str = ""
    agent_session_id: str
    source_type: str
    source_ref_id: str = ""
    target_memory_type: MemoryTargetType
    target_memory_ref_id: str = ""
    revision_type: MemoryUpdateType
    proposed_value_summary: str
    current_value_summary: str
    evidence_refs: list[MemoryRevisionSource] = Field(default_factory=list)
    candidates: list[MemoryUpdateCandidate] = Field(default_factory=list)
    confidence: float = 0.0
    severity: MemorySuggestionSeverity = MemorySuggestionSeverity.WARNING
    status: MemorySuggestionStatus = MemorySuggestionStatus.GENERATED
    decision: MemorySuggestionDecisionType = MemorySuggestionDecisionType.NONE
    decided_by: str = ""
    decided_at: str = ""
    warning_codes: list[str] = Field(default_factory=list)
    created_by: str = "memory_agent"
    created_at: str = ""
    updated_at: str = ""
    request_id: str = ""
    trace_id: str = ""


class MemoryReviewGate(AIBaseModel):
    gate_id: str
    work_id: str
    chapter_id: str = ""
    suggestion_ids: list[str] = Field(default_factory=list)
    state: MemoryGateState = MemoryGateState.OPEN
    warning_codes: list[str] = Field(default_factory=list)
    open_at: str = ""
    closed_at: str = ""
    operator_id: str = ""


class StoryMemoryRevisionItem(AIBaseModel):
    id: str
    revision_id: str
    target_memory_type: str
    target_memory_ref_id: str
    revision_type: MemoryUpdateType
    before_value_summary: str = ""
    after_value_summary: str
    evidence_refs: list[MemoryRevisionSource] = Field(default_factory=list)
    status: MemoryRevisionStatus = MemoryRevisionStatus.PENDING


class StoryMemoryRevision(AIBaseModel):
    id: str
    work_id: str
    chapter_id: str = ""
    source_suggestion_id: str
    revision_items: list[StoryMemoryRevisionItem] = Field(default_factory=list)
    revision_type: MemoryRevisionRecordType = MemoryRevisionRecordType.NORMAL
    status: MemoryRevisionStatus = MemoryRevisionStatus.PENDING
    approved_by: str = ""
    approved_at: str = ""
    applied_by: str = ""
    applied_at: str = ""
    apply_result_ref: str = ""
    before_summary: str
    after_summary: str = ""
    request_id: str = ""
    trace_id: str = ""
    created_at: str = ""
    updated_at: str = ""


class StoryStateRevision(AIBaseModel):
    id: str
    work_id: str
    chapter_id: str = ""
    source_suggestion_id: str
    state_items: list[dict[str, str]] = Field(default_factory=list)
    target_state_ref: str = ""
    version_guard: str = ""
    revision_type: MemoryRevisionRecordType = MemoryRevisionRecordType.NORMAL
    status: MemoryRevisionStatus = MemoryRevisionStatus.PENDING
    approved_by: str = ""
    approved_at: str = ""
    applied_by: str = ""
    applied_at: str = ""
    apply_result_ref: str = ""
    before_summary: str
    after_summary: str = ""
    request_id: str = ""
    trace_id: str = ""
    created_at: str = ""
    updated_at: str = ""


class MemoryRevisionDecision(AIBaseModel):
    id: str
    revision_id: str
    decision: MemoryReviewDecisionType
    decided_by: str
    decided_at: str
    decision_note: str = ""


class MemoryRevisionApplyResult(AIBaseModel):
    id: str
    revision_id: str
    apply_status: MemoryApplyStatus
    applied_memory_refs: list[str] = Field(default_factory=list)
    failed_item_refs: list[str] = Field(default_factory=list)
    error_codes: list[str] = Field(default_factory=list)
    before_after_snapshot_ref: str = ""
    applied_at: str = ""


class InitializationRecord(AIBaseModel):
    initialization_id: str
    work_id: str
    job_id: str
    status: InitializationStatus
    completion_status: InitializationCompletionStatus = InitializationCompletionStatus.FAILED
    analyzed_chapter_count: int = 0
    total_confirmed_chapter_count: int = 0
    skipped_chapter_count: int = 0
    empty_chapter_count: int = 0
    failed_chapter_count: int = 0
    partial_success_reason: str = ""
    story_memory_snapshot_id: str = ""
    story_state_snapshot_id: str = ""
    error_code: str = ""
    error_message: str = ""
    stale: bool = False
    stale_reason: str = ""
    source_chapter_versions: dict[str, int] = Field(default_factory=dict)
    outline_analysis: OutlineAnalysisResult | None = None
    chapter_results: list[ChapterAnalysisResult] = Field(default_factory=list)
    hierarchical_story_summary: HierarchicalStorySummary | None = None
    created_at: str = ""
    updated_at: str = ""
    finalized_at: str = ""


class LLMUsage(AIBaseModel):
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None
    estimated_cost: float | None = None
    price_snapshot_json: dict[str, Any] = Field(default_factory=dict)


class LLMCallStatus(StrEnum):
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class LLMRequest(AIBaseModel):
    model_role: str
    work_id: str = ""
    job_id: str = ""
    session_id: str = ""
    run_id: str = ""
    operation_type: str = ""
    external_logging: bool = False
    prompt_key: str = ""
    prompt_version: str = ""
    messages: list[dict[str, str]] = Field(default_factory=list)
    output_schema_key: str = "plain_text"
    request_id: str = ""
    trace_id: str = ""
    temperature: float | None = None
    max_tokens: int | None = None


class LLMResponse(AIBaseModel):
    provider_name: str
    model_name: str
    content: str = ""
    request_id: str = ""
    trace_id: str = ""
    token_usage: LLMUsage | None = None
    finish_reason: str = ""
    error_code: str = ""
    error_message: str = ""
    further_provider_calls_allowed: bool = True
    budget_status: str = ""


class PromptTemplate(AIBaseModel):
    prompt_key: str
    prompt_version: str
    model_role: str
    output_schema_key: str = "plain_text"
    template_text: str
    enabled: bool = True


class OutputValidationResult(AIBaseModel):
    success: bool
    error_code: str = ""
    message: str = ""
    parsed_output: Any = None


class LLMCallLog(AIBaseModel):
    prompt_key: str = ""
    prompt_version: str = ""
    work_id: str = ""
    model_role: str
    provider_name: str
    model_name: str
    request_id: str
    trace_id: str
    session_id: str = ""
    step_id: str = ""
    job_id: str = ""
    run_id: str = ""
    status: LLMCallStatus
    error_code: str = ""
    error_message: str = ""
    attempt_no: int = 1
    started_at: datetime
    finished_at: datetime
    usage: LLMUsage | None = None
    estimated_cost: float = 0.0
    price_snapshot_json: dict[str, Any] = Field(default_factory=dict)
    context_pack_snapshot_id: str = ""
    output_schema_key: str = ""


class ContextPackStatus(StrEnum):
    READY = "ready"
    DEGRADED = "degraded"
    BLOCKED = "blocked"


class ArcStatus(StrEnum):
    PENDING = "pending"
    READY = "ready"
    DEGRADED = "degraded"
    STALE = "stale"
    FAILED = "failed"
    EMPTY = "empty"


class ArcQualityLevel(StrEnum):
    PLACEHOLDER = "placeholder"
    MINIMAL = "minimal"
    COMPLETE = "complete"


class SequenceEvent(AIBaseModel):
    event_id: str
    event_order: int
    event_name: str
    description: str = ""
    event_type: str = "development"
    estimated_chapter: int = 0
    involved_characters: list[str] = Field(default_factory=list)
    foreshadow_triggers: list[str] = Field(default_factory=list)
    arc_impact: str = ""


class MasterArc(AIBaseModel):
    master_arc_id: str
    work_id: str
    arc_title: str
    version: int = 1
    arc_logline: str = ""
    status: ArcStatus
    quality_level: ArcQualityLevel = ArcQualityLevel.MINIMAL
    ultimate_goal: str = ""
    protagonist_motivation: str = ""
    current_stage: str = ""
    stage_position: str = ""
    core_theme: str = ""
    final_conflict: str = ""
    main_antagonist: str = ""
    hard_constraints: list[str] = Field(default_factory=list)
    forbidden_outcomes: list[str] = Field(default_factory=list)
    key_milestones: list[str] = Field(default_factory=list)
    endgame_foreshadows: list[str] = Field(default_factory=list)
    source_initialization_id: str = ""
    source_outline_ref: str = ""
    source_refs: list[str] = Field(default_factory=list)
    warning_codes: list[str] = Field(default_factory=list)
    stale_status: str = "fresh"
    stale_reason: str = ""
    built_from_text_inference: bool = False
    built_by: str = ""
    last_updated_by: str = ""
    created_at: str = ""
    updated_at: str = ""
    request_id: str = ""
    trace_id: str = ""


class VolumeArc(AIBaseModel):
    volume_arc_id: str
    work_id: str
    master_arc_id: str = ""
    version: int = 1
    volume_no: int = 1
    status: ArcStatus
    quality_level: ArcQualityLevel = ArcQualityLevel.PLACEHOLDER
    stage_goal: str = ""
    core_conflict: str = ""
    climax_description: str = ""
    resolution_condition: str = ""
    stage_open_loops: list[str] = Field(default_factory=list)
    key_characters: list[str] = Field(default_factory=list)
    foreshadow_planted: list[str] = Field(default_factory=list)
    foreshadow_resolved: list[str] = Field(default_factory=list)
    forbidden_items: list[str] = Field(default_factory=list)
    chapter_range: dict[str, int] = Field(default_factory=dict)
    source_initialization_id: str = ""
    source_outline_ref: str = ""
    source_refs: list[str] = Field(default_factory=list)
    warning_codes: list[str] = Field(default_factory=list)
    stale_status: str = "fresh"
    stale_reason: str = ""
    built_by: str = ""
    last_updated_by: str = ""
    created_at: str = ""
    updated_at: str = ""
    request_id: str = ""
    trace_id: str = ""


class SequenceArc(AIBaseModel):
    sequence_arc_id: str
    work_id: str
    volume_arc_id: str = ""
    master_arc_id: str = ""
    version: int = 1
    seq_no: int = 1
    status: ArcStatus
    quality_level: ArcQualityLevel = ArcQualityLevel.PLACEHOLDER
    sequence_goal: str = ""
    key_events: list[SequenceEvent] = Field(default_factory=list)
    turning_points: list[str] = Field(default_factory=list)
    required_beats: list[str] = Field(default_factory=list)
    forbidden_items: list[str] = Field(default_factory=list)
    chapter_range: dict[str, int] = Field(default_factory=dict)
    source_initialization_id: str = ""
    source_outline_ref: str = ""
    source_refs: list[str] = Field(default_factory=list)
    warning_codes: list[str] = Field(default_factory=list)
    stale_status: str = "fresh"
    stale_reason: str = ""
    built_by: str = ""
    last_updated_by: str = ""
    created_at: str = ""
    updated_at: str = ""
    request_id: str = ""
    trace_id: str = ""


class ChapterContextItem(AIBaseModel):
    chapter_id: str
    chapter_no: int = 0
    title: str = ""
    summary: str = ""
    key_event: str = ""


class CurrentChapterContext(AIBaseModel):
    chapter_id: str
    chapter_no: int = 0
    title: str = ""
    content_summary: str = ""
    writing_position: str = ""
    unresolved_in_chapter: list[str] = Field(default_factory=list)


class CharacterMoment(AIBaseModel):
    character_name: str
    current_status: str
    emotional_state: str = ""
    location: str = ""
    last_action: str = ""


class SceneMoment(AIBaseModel):
    location: str
    time_of_day: str = ""
    atmosphere: str = ""
    characters_present: list[str] = Field(default_factory=list)
    emotional_tone: str = ""
    pov_hint: str = ""
    reveal_points: list[str] = Field(default_factory=list)


class ImmediateWindow(AIBaseModel):
    window_id: str
    work_id: str
    context_pack_id: str
    status: ArcStatus
    quality_level: ArcQualityLevel = ArcQualityLevel.MINIMAL
    recent_chapters_summary: list[ChapterContextItem] = Field(default_factory=list)
    recent_3_chapters_detail: list[ChapterContextItem] = Field(default_factory=list)
    current_chapter_context: CurrentChapterContext | None = None
    previous_chapter_hook: str = ""
    character_current_states: list[CharacterMoment] = Field(default_factory=list)
    active_plot_threads: list[str] = Field(default_factory=list)
    scene_details: list[SceneMoment] = Field(default_factory=list)
    warning_codes: list[str] = Field(default_factory=list)
    stale_status: str = "fresh"
    assembled_at: str = ""


class ContextItem(AIBaseModel):
    item_id: str
    source_type: str
    source_id: str = ""
    priority: int = 10
    content_text: str = ""
    summary: str = ""
    token_estimate: int = 0
    required: bool = False
    included: bool = True
    trim_reason: str = ""
    filter_reason: str = ""
    stale_status: str = "fresh"
    warning: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class ContextPackSnapshot(AIBaseModel):
    context_pack_id: str
    work_id: str
    chapter_id: str = ""
    source_initialization_id: str = ""
    source_story_memory_snapshot_id: str = ""
    source_story_state_id: str = ""
    status: ContextPackStatus
    blocked_reason: str = ""
    degraded_reason: str = ""
    warnings: list[str] = Field(default_factory=list)
    vector_recall_status: str = "skipped"
    context_items: list[ContextItem] = Field(default_factory=list)
    token_budget: int = 0
    estimated_token_count: int = 0
    trimmed_items: list[ContextItem] = Field(default_factory=list)
    stale: bool = False
    stale_reason: str = ""
    source_chapter_versions: dict[str, int] = Field(default_factory=dict)
    plot_arc_statuses: dict[str, dict[str, Any]] = Field(default_factory=dict)
    plot_arc_summary: dict[str, dict[str, Any]] = Field(default_factory=dict)
    summary: str = ""
    created_at: str = ""


class ContextPackBuildRequest(AIBaseModel):
    work_id: str
    chapter_id: str = ""
    continuation_mode: str = "continue_chapter"
    user_instruction: str = ""
    max_context_tokens: int = 4000
    model_role: str = "writer"
    request_id: str = ""
    trace_id: str = ""
    allow_degraded: bool = True
    allow_stale_vector: bool = False


class EmptyVectorRecallResult(AIBaseModel):
    status: str = "unavailable"
    items: list[ContextItem] = Field(default_factory=list)
    error_reason: str = "vector_recall_disabled"


class VectorIndexBuildResult(AIBaseModel):
    index_status: str = "missing"
    indexed_chapter_count: int = 0
    indexed_chunk_count: int = 0
    failed_chunk_count: int = 0
    warning_count: int = 0
    degraded_reason: str = ""
    warnings: list[str] = Field(default_factory=list)


class CandidateDraftStatus(StrEnum):
    GENERATED = "generated"
    PENDING_REVIEW = "pending_review"
    UNDER_REVIEW = "under_review"
    REVISION_REQUESTED = "revision_requested"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    APPLIED = "applied"
    STALE = "stale"
    SUPERSEDED = "superseded"
    FAILED = "failed"


class CandidateDraftValidationStatus(StrEnum):
    PASSED = "passed"
    FAILED = "failed"


class CandidateDraftVersionStatus(StrEnum):
    GENERATED = "generated"
    REVIEWING = "reviewing"
    REVIEW_COMPLETED = "review_completed"
    REVISION_REQUESTED = "revision_requested"
    SELECTED = "selected"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    APPLIED = "applied"
    SUPERSEDED = "superseded"
    STALE = "stale"
    FAILED = "failed"


class RewriteTriggerType(StrEnum):
    REVIEW_BASED = "review_based"
    USER_INSTRUCTION = "user_instruction"
    REJECT_REGENERATE = "reject_regenerate"


class RewriteRequestStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class RevisionRoundStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class DirectionPlanStatus(StrEnum):
    PENDING = "pending"
    GENERATED = "generated"
    WAITING_FOR_SELECTION = "waiting_for_selection"
    WAITING_FOR_CONFIRMATION = "waiting_for_confirmation"
    SELECTED = "selected"
    CONFIRMED = "confirmed"
    EDITED = "edited"
    STALE = "stale"
    SUPERSEDED = "superseded"
    FAILED = "failed"


class WritingTaskStatus(StrEnum):
    PENDING = "pending"
    READY = "ready"
    STALE = "stale"
    CONSUMED = "consumed"
    FAILED = "failed"


class ArcRef(AIBaseModel):
    arc_type: str
    arc_id: str
    arc_summary: str
    arc_status_at_generation: str


class DirectionScore(AIBaseModel):
    total_score: int
    consistency_score: int
    conflict_density_score: int
    satisfaction_rhythm_score: int
    foreshadow_progress_score: int
    risk_controllability_score: int
    score_rationale: str = ""


class ConflictItem(AIBaseModel):
    conflict_name: str
    conflict_description: str
    conflict_type: str
    intensity: str = ""


class ForeshadowUsageItem(AIBaseModel):
    foreshadow_id: str = ""
    foreshadow_description: str
    usage_plan: str
    is_new: bool = False


class RiskItem(AIBaseModel):
    risk_description: str
    risk_severity: str
    mitigation: str = ""


class ForeshadowArrangementItem(AIBaseModel):
    foreshadow_id: str = ""
    foreshadow_description: str
    arrangement: str
    arrangement_detail: str = ""


class DirectionOption(AIBaseModel):
    option_id: str
    direction_proposal_id: str
    label: str
    title: str = ""
    plot_summary: str
    narrative_premise: str
    narrative_benefits: list[str] = Field(default_factory=list)
    main_conflicts: list[ConflictItem] = Field(default_factory=list)
    foreshadow_usage: list[ForeshadowUsageItem] = Field(default_factory=list)
    risk_points: list[RiskItem] = Field(default_factory=list)
    estimated_chapters: int
    chapter_preview: list[str] = Field(default_factory=list)
    base_arc_refs: list[ArcRef] = Field(default_factory=list)
    base_memory_refs: list[str] = Field(default_factory=list)
    score: DirectionScore
    confidence: float = 0.0
    tone_direction: str = ""
    key_characters_involved: list[str] = Field(default_factory=list)
    edited_summary: str = ""
    is_user_edited: bool = False
    editable: bool = True
    created_at: str = ""


class DirectionProposal(AIBaseModel):
    direction_proposal_id: str
    work_id: str
    chapter_id: str
    chapter_order: int = 0
    agent_session_id: str
    source_context_pack_id: str
    source_arc_refs: list[ArcRef] = Field(default_factory=list)
    source_memory_refs: list[str] = Field(default_factory=list)
    status: DirectionPlanStatus
    version: int = 1
    options: list[DirectionOption] = Field(default_factory=list)
    generation_metadata: dict[str, Any] = Field(default_factory=dict)
    created_by: str = "planner_agent"
    selected_by: str = ""
    selected_option_id: str = ""
    edited_by: str = ""
    stale_status: str = "fresh"
    stale_reason: str = ""
    warning_codes: list[str] = Field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""
    request_id: str = ""
    trace_id: str = ""


class DirectionSelection(AIBaseModel):
    selection_id: str
    direction_proposal_id: str
    selected_option_id: str
    work_id: str
    chapter_id: str
    agent_session_id: str
    selection_type: str
    edited_fields: list[str] = Field(default_factory=list)
    edited_values: dict[str, Any] = Field(default_factory=dict)
    user_id: str
    confirmed_by: str = "user_action"
    warning_codes: list[str] = Field(default_factory=list)
    created_at: str = ""
    request_id: str = ""
    trace_id: str = ""


class ChapterBeat(AIBaseModel):
    beat_order: int
    beat_name: str
    beat_description: str
    beat_type: str
    emotional_tone: str = ""
    involved_characters: list[str] = Field(default_factory=list)


class ChapterPlanItem(AIBaseModel):
    item_id: str
    chapter_plan_id: str
    plan_order: int
    chapter_goal: str
    key_events: list[ChapterBeat] = Field(default_factory=list)
    conflict_progression: str
    foreshadow_arrangement: list[ForeshadowArrangementItem] = Field(default_factory=list)
    forbidden_items: list[str] = Field(default_factory=list)
    required_beats: list[str] = Field(default_factory=list)
    estimated_word_count: int = 0
    estimated_word_count_max: int = 0
    tone_hint: str = ""
    pov_hint: str = ""
    arc_alignment: list[ArcRef] = Field(default_factory=list)
    source_sequence_event_refs: list[str] = Field(default_factory=list)
    writing_task_id: str = ""
    is_user_edited: bool = False
    created_at: str = ""


class ChapterPlan(AIBaseModel):
    chapter_plan_id: str
    work_id: str
    chapter_id: str
    direction_proposal_id: str
    selected_option_id: str
    selection_id: str
    agent_session_id: str
    source_context_pack_id: str
    source_arc_refs: list[ArcRef] = Field(default_factory=list)
    source_memory_refs: list[str] = Field(default_factory=list)
    status: DirectionPlanStatus
    version: int = 1
    plan_items: list[ChapterPlanItem] = Field(default_factory=list)
    plan_summary: str = ""
    constraints: list[str] = Field(default_factory=list)
    total_estimated_chapters: int = 0
    total_estimated_words: int = 0
    generation_metadata: dict[str, Any] = Field(default_factory=dict)
    created_by: str = "planner_agent"
    confirmed_by: str = ""
    edited_by: str = ""
    stale_status: str = "fresh"
    stale_reason: str = ""
    warning_codes: list[str] = Field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""
    request_id: str = ""
    trace_id: str = ""


class PlanConfirmation(AIBaseModel):
    confirmation_id: str
    chapter_plan_id: str
    direction_proposal_id: str
    work_id: str
    chapter_id: str
    agent_session_id: str
    confirmation_type: str
    edited_items: list[str] = Field(default_factory=list)
    edited_fields: dict[str, Any] = Field(default_factory=dict)
    user_edit_notes: str = ""
    user_id: str
    confirmed_by: str = "user_action"
    warning_codes: list[str] = Field(default_factory=list)
    created_at: str = ""
    request_id: str = ""
    trace_id: str = ""


class DirectionPlanRef(AIBaseModel):
    ref_type: str
    ref_id: str
    ref_scope: str
    ref_summary: str
    checksum: str = ""
    created_at: str = ""


class DirectionPlanSnapshot(AIBaseModel):
    snapshot_id: str
    work_id: str
    chapter_id: str
    agent_session_id: str
    direction_proposal_id: str
    direction_proposal_version: int = 1
    selected_option_id: str
    selection_id: str
    chapter_plan_id: str
    chapter_plan_version: int = 1
    confirmation_id: str
    writing_task_id: str = ""
    snapshot_status: str = "ready"
    direction_summary: str
    plan_summary: str
    arc_refs_at_snapshot: list[ArcRef] = Field(default_factory=list)
    warning_codes: list[str] = Field(default_factory=list)
    created_at: str = ""


class WritingTask(AIBaseModel):
    writing_task_id: str
    work_id: str
    chapter_id: str = ""
    target_chapter_id: str = ""
    chapter_order: int = 0
    direction_proposal_id: str = ""
    selected_option_id: str = ""
    chapter_plan_id: str = ""
    plan_item_id: str = ""
    agent_session_id: str = ""
    source_context_pack_id: str = ""
    source_arc_refs: list[str] = Field(default_factory=list)
    source_memory_refs: list[str] = Field(default_factory=list)
    status: WritingTaskStatus = WritingTaskStatus.PENDING
    version: int = 1
    writing_goal: str = ""
    must_include: list[str] = Field(default_factory=list)
    must_not_include: list[str] = Field(default_factory=list)
    task_constraints: list[str] = Field(default_factory=list)
    tone_guidance: str = ""
    target_word_count: int = 0
    target_word_count_max: int = 0
    expected_output_shape: str = ""
    arc_constraints: list[ArcRef] = Field(default_factory=list)
    foreshadow_requirements: list[ForeshadowArrangementItem] = Field(default_factory=list)
    required_beats: list[str] = Field(default_factory=list)
    direction_summary: str = ""
    plan_summary: str = ""
    stale_status: str = "fresh"
    stale_reason: str = ""
    warning_codes: list[str] = Field(default_factory=list)
    generated_by: str = "planner_agent"
    consumed_by: str = ""
    continuation_mode: str = "continue_chapter"
    user_instruction: str = ""
    model_role: str = ModelRole.WRITER.value
    created_by: str = "user_action"
    created_at: str = ""
    updated_at: str = ""
    request_id: str = ""
    trace_id: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def _normalize_task_chapter_ids(cls, value: Any) -> Any:
        if not isinstance(value, dict):
            return value
        data = dict(value)
        chapter_id = str(data.get("chapter_id", "") or "")
        target_chapter_id = str(data.get("target_chapter_id", "") or "")
        if not chapter_id and target_chapter_id:
            data["chapter_id"] = target_chapter_id
        if not target_chapter_id and chapter_id:
            data["target_chapter_id"] = chapter_id
        if not data.get("generated_by") and data.get("created_by"):
            data["generated_by"] = str(data["created_by"])
        return data


class CandidateDraft(AIBaseModel):
    candidate_draft_id: str
    work_id: str
    chapter_id: str
    agent_session_id: str = ""
    writing_task_id: str = ""
    direction_plan_snapshot_id: str = ""
    source_context_pack_id: str
    source_job_id: str
    status: CandidateDraftStatus
    selected_version_id: str = ""
    accepted_version_id: str = ""
    applied_version_id: str = ""
    latest_version_no: int = 0
    revision_round: int = 0
    revision_count: int = 0
    max_revision_rounds: int = 1
    warning_codes: list[str] = Field(default_factory=list)
    stale_status: str = "fresh"
    content: str = ""
    content_preview: str = ""
    word_count: int = 0
    char_count: int = 0
    validation_status: CandidateDraftValidationStatus = CandidateDraftValidationStatus.PASSED
    validation_errors: list[str] = Field(default_factory=list)
    writer_model_role: str = ModelRole.WRITER.value
    provider_name: str = ""
    model_name: str = ""
    created_by: str = "user_action"
    created_at: str = ""
    updated_at: str = ""
    applied_at: str = ""
    request_id: str = ""
    trace_id: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("status", mode="before")
    @classmethod
    def _normalize_legacy_status(cls, value: object) -> object:
        if value == "generated":
            return CandidateDraftStatus.PENDING_REVIEW
        if value in {"apply_failed", "validation_failed", "save_failed"}:
            return CandidateDraftStatus.STALE
        return value


class CandidateDraftVersion(AIBaseModel):
    candidate_version_id: str
    candidate_draft_id: str
    work_id: str
    chapter_id: str
    agent_session_id: str = ""
    source_candidate_draft_id: str = ""
    source_version_id: str = ""
    parent_version_id: str = ""
    version_no: int
    status: CandidateDraftVersionStatus
    content_ref: str = ""
    text_ref: str = ""
    content: str = ""
    content_summary: str = ""
    word_count: int = 0
    writing_task_id: str = ""
    direction_plan_snapshot_id: str = ""
    source_context_pack_id: str = ""
    review_report_id: str = ""
    warning_codes: list[str] = Field(default_factory=list)
    stale_status: str = "fresh"
    created_by: str = "user_action"
    created_at: str = ""
    updated_at: str = ""
    request_id: str = ""
    trace_id: str = ""


class RewriteRequest(AIBaseModel):
    rewrite_request_id: str
    candidate_draft_id: str
    source_version_id: str
    work_id: str
    chapter_id: str
    agent_session_id: str = ""
    trigger_type: RewriteTriggerType
    review_report_id: str = ""
    status: RewriteRequestStatus = RewriteRequestStatus.PENDING
    created_by: str = "user_action"
    created_at: str = ""
    updated_at: str = ""
    request_id: str = ""
    trace_id: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class RewriteInstruction(AIBaseModel):
    rewrite_instruction_id: str
    rewrite_request_id: str
    instruction_source: str
    instruction_ref: str = ""
    instruction_summary: str = ""
    constraint_refs: list[str] = Field(default_factory=list)
    created_at: str = ""


class RevisionRound(AIBaseModel):
    revision_round_id: str
    candidate_draft_id: str
    round_no: int
    source_version_id: str
    target_version_id: str = ""
    rewrite_request_id: str
    status: RevisionRoundStatus = RevisionRoundStatus.PENDING
    created_at: str = ""
    updated_at: str = ""


class CandidateDraftVersionDiff(AIBaseModel):
    diff_id: str
    candidate_draft_id: str
    from_version_id: str
    to_version_id: str
    diff_preview: list[str] = Field(default_factory=list)
    summary: str = ""


class ContinuationResult(AIBaseModel):
    workflow_id: str
    job_id: str
    writing_task_id: str
    candidate_draft_id: str = ""
    status: str
    warnings: list[str] = Field(default_factory=list)
    error_code: str = ""
    error_message: str = ""


class MultiChapterStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    WAITING_USER_DECISION = "waiting_user_decision"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    PARTIAL_SUCCESS = "partial_success"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ChapterAdvanceDecision(StrEnum):
    APPLIED = "applied"
    SKIPPED = "skipped"
    CONTINUE_WITHOUT_APPLY = "continue_without_apply"
    REGENERATE = "regenerate"


class PerChapterStatus(StrEnum):
    PENDING = "pending"
    GENERATING = "generating"
    REVIEWING = "reviewing"
    READY = "ready"
    BLOCKED = "blocked"
    SKIPPED = "skipped"
    FAILED = "failed"
    APPLIED = "applied"


class ChapterStatusEntry(AIBaseModel):
    chapter_index: int
    chapter_id: str = ""
    agent_session_id: str = ""
    candidate_draft_id: str = ""
    status: PerChapterStatus = PerChapterStatus.PENDING
    error_code: str = ""
    started_at: str = ""
    finished_at: str = ""


class ChapterProgressEntry(AIBaseModel):
    chapter_index: int
    status: PerChapterStatus = PerChapterStatus.PENDING
    candidate_draft_id: str = ""
    candidate_draft_status: str = ""
    word_count: int = 0
    review_summary: str = ""


class CitationSourceType(StrEnum):
    CHAPTER = "chapter"
    CHARACTER = "character"
    FORESHADOW = "foreshadow"
    SETTING = "setting"
    EVENT = "event"
    LOCATION = "location"


class CitationVerificationStatus(StrEnum):
    VERIFIED = "verified"
    UNKNOWN_SOURCE = "unknown_source"
    LOW_CONFIDENCE = "low_confidence"
    VERIFICATION_FAILED = "verification_failed"


class CitationLink(AIBaseModel):
    citation_id: str
    candidate_version_id: str
    candidate_draft_id: str
    work_id: str = ""
    source_type: CitationSourceType
    source_id: str = ""
    source_hash: str = ""
    source_name_snapshot: str = ""
    source_span: str = ""
    source_excerpt: str = ""
    context_in_draft: str = ""
    verification_status: CitationVerificationStatus = CitationVerificationStatus.UNKNOWN_SOURCE
    verification_detail: str = ""
    confidence: float = 0.0
    verified_at: str = ""
    created_at: str = ""


class CitationBatch(AIBaseModel):
    batch_id: str
    candidate_version_id: str
    candidate_draft_id: str = ""
    total_count: int = 0
    verified_count: int = 0
    unknown_count: int = 0
    citations: list[CitationLink] = Field(default_factory=list)


class MentionEntityType(StrEnum):
    CHARACTER = "character"
    EVENT = "event"
    FORESHADOW = "foreshadow"
    LOCATION = "location"


class MentionSource(StrEnum):
    USER_INPUT = "user_input"
    AI_SUGGESTION = "ai_suggestion"


class MentionStatus(StrEnum):
    ACTIVE = "active"
    BROKEN = "broken"
    STALE = "stale"
    INACTIVE_ENTITY = "inactive_entity"


class ChapterMention(AIBaseModel):
    mention_id: str
    chapter_id: str
    work_id: str
    entity_type: MentionEntityType
    entity_id: str = ""
    entity_name_snapshot: str = ""
    start_pos: int = 0
    end_pos: int = 0
    source: MentionSource = MentionSource.USER_INPUT
    ai_suggestion_id: str = ""
    status: MentionStatus = MentionStatus.ACTIVE
    is_active: bool = True
    validation_detail: str = ""
    created_at: str = ""
    updated_at: str = ""


class MentionSuggestion(AIBaseModel):
    entity_type: MentionEntityType
    entity_id: str
    entity_name: str
    match_type: str = "prefix"
    last_used_at: str = ""
    summary_preview: str = ""


class MentionSummary(AIBaseModel):
    mention_id: str
    entity_type: MentionEntityType
    entity_id: str = ""
    entity_name_snapshot: str = ""
    entity_current_name: str = ""
    summary_text: str = ""
    status: MentionStatus = MentionStatus.ACTIVE
    is_active: bool = True
    last_updated: str = ""


class StyleProfileSourceType(StrEnum):
    USER_UPLOAD = "user_upload"
    CHAPTER_REFERENCE = "chapter_reference"
    MANUAL = "manual"


class StyleProfileStatus(StrEnum):
    PENDING_CONFIRM = "pending_confirm"
    ACTIVE = "active"
    DISABLED = "disabled"
    ARCHIVED = "archived"
    DRAFT = "draft"


class StyleProfile(AIBaseModel):
    profile_id: str
    work_id: str
    source_type: StyleProfileSourceType
    source_ref: str = ""
    source_text_hash: str = ""
    source_text_length: int = 0
    confidence: float = 0.0
    low_confidence_reason: str = ""
    avg_sentence_length: float = 0.0
    sentence_length_variance: float = 0.0
    short_sentence_ratio: float = 0.0
    long_sentence_ratio: float = 0.0
    compound_sentence_ratio: float = 0.0
    avg_paragraph_length: float = 0.0
    paragraph_length_variance: float = 0.0
    dialogue_ratio: float = 0.0
    psychological_ratio: float = 0.0
    action_ratio: float = 0.0
    description_ratio: float = 0.0
    narrative_perspective: str = ""
    tense_preference: str = ""
    style_summary: str = ""
    style_tags: list[str] = Field(default_factory=list)
    version: int = 1
    status: StyleProfileStatus = StyleProfileStatus.PENDING_CONFIRM
    created_at: str = ""
    updated_at: str = ""
    confirmed_at: str = ""

    def to_context_summary(self) -> str:
        parts = [f"风格特征：{self.style_summary}".strip()]
        if self.style_tags:
            parts.append(f"风格标签：{', '.join(self.style_tags)}")
        parts.append(f"对白占比约 {self.dialogue_ratio:.0%}")
        parts.append(f"平均句长 {self.avg_sentence_length:.0f} 字")
        if self.narrative_perspective:
            parts.append(f"叙述视角：{self.narrative_perspective}")
        if self.confidence < 0.5:
            parts.append("[注意：风格画像置信度较低，仅供参考]")
        return "\n".join(item for item in parts if item and item != "风格特征：")


class StyleDNAExtractionRequest(AIBaseModel):
    work_id: str
    source_type: StyleProfileSourceType
    source_text: str
    source_ref: str = ""


class StyleDNAExtractionResult(AIBaseModel):
    profile: StyleProfile
    confidence: float = 0.0
    warnings: list[str] = Field(default_factory=list)


class AutoQueueStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPING = "stopping"
    STOPPED = "stopped"
    WAITING_USER_DECISION = "waiting_user_decision"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class StopCondition(StrEnum):
    TARGET_CHAPTERS_REACHED = "target_chapters_reached"
    TARGET_WORDS_REACHED = "target_words_reached"
    SEQUENCE_ARC_ENDED = "sequence_arc_ended"
    BLOCKING_REVIEW_CONSECUTIVE = "blocking_review_consecutive"
    FORESHADOW_PREMATURE_REVEAL = "foreshadow_premature_reveal"
    CONSECUTIVE_REVISION_FAILURE = "consecutive_revision_failure"
    BUDGET_EXCEEDED = "budget_exceeded"
    PROVIDER_UNRECOVERABLE = "provider_unrecoverable"
    USER_MANUAL_STOP = "user_manual_stop"


class StopSeverity(StrEnum):
    NORMAL = "normal"
    ABNORMAL = "abnormal"
    BUDGET = "budget"
    PROVIDER = "provider"
    USER = "user"


class AutoQueueConfig(AIBaseModel):
    config_id: str
    work_id: str
    target_chapters: int = 0
    target_word_count: int = 0
    stop_at_sequence_end: bool = True
    stop_on_blocking_review: bool = True
    max_consecutive_blocking: int = 2
    stop_on_budget_exceeded: bool = True
    max_consecutive_revision_failures: int = 3
    stop_on_foreshadow_premature: bool = True
    budget_limit_tokens: int = 0
    revision: int = 1
    enabled: bool = True
    created_at: str = ""
    updated_at: str = ""


class AutoQueueStopRecord(AIBaseModel):
    stop_record_id: str = ""
    stop_reason: StopCondition
    stop_severity: StopSeverity
    stop_context: dict[str, Any] = Field(default_factory=dict)
    stopped_at: str = ""
    user_action_required: bool = False
    suggested_action: str = ""


class StopEvaluationResult(AIBaseModel):
    should_stop: bool = False
    should_pause: bool = False
    condition: StopCondition | None = None
    severity: StopSeverity | None = None
    reason: str = ""
    user_action_required: bool = False
    suggested_action: str = ""


class AutoQueueRun(AIBaseModel):
    run_id: str
    job_id: str = ""
    config_id: str
    work_id: str
    multi_chapter_session_id: str
    status: AutoQueueStatus = AutoQueueStatus.PENDING
    generated_count: int = 0
    total_word_count: int = 0
    consumed_tokens: int = 0
    current_stop_evaluation: dict[str, Any] = Field(default_factory=dict)
    stop_record: AutoQueueStopRecord | None = None
    stop_record_history: list[AutoQueueStopRecord] = Field(default_factory=list)
    resume_allowed: bool = True
    current_candidate_story_state: dict[str, Any] = Field(default_factory=dict)
    queue_state_snapshots: list[dict[str, Any]] = Field(default_factory=list)
    consecutive_blocking_count: int = 0
    consecutive_revision_failure_count: int = 0
    error_code: str = ""
    error_message: str = ""
    request_id: str = ""
    trace_id: str = ""
    created_at: str = ""
    updated_at: str = ""
    started_at: str = ""
    stopped_at: str = ""
    finished_at: str = ""


class ChapterChunk(AIBaseModel):
    chunk_id: str
    work_id: str
    chapter_id: str
    chapter_order: int
    chunk_index: int
    text_excerpt: str
    content_hash: str
    token_count: int = 0
    start_offset: int = 0
    end_offset: int = 0
    source: str = "confirmed_chapter"
    index_status: str = "active"
    stale_status: str = "fresh"
    created_at: str = ""
    updated_at: str = ""


class ChunkEmbedding(AIBaseModel):
    embedding_id: str
    chunk_id: str
    work_id: str
    chapter_id: str
    embedding_model: str
    embedding_provider: str
    embedding_version: str
    vector_id: str
    content_hash: str
    status: str = "active"
    created_at: str = ""
    updated_at: str = ""


class MultiChapterSession(AIBaseModel):
    session_id: str
    work_id: str
    start_chapter_id: str
    target_chapters: int
    current_index: int = 0
    status: MultiChapterStatus = MultiChapterStatus.PENDING
    per_chapter_status: list[ChapterStatusEntry] = Field(default_factory=list)
    agent_session_ids: list[str] = Field(default_factory=list)
    candidate_draft_ids: list[str] = Field(default_factory=list)
    candidate_story_state: dict[str, Any] = Field(default_factory=dict)
    queue_state_snapshots: list[dict[str, Any]] = Field(default_factory=list)
    warning_codes: list[str] = Field(default_factory=list)
    error_code: str = ""
    error_message: str = ""
    paused_reason: str = ""
    blocked_source: str = ""
    blocked_reason_code: str = ""
    request_id: str = ""
    trace_id: str = ""
    created_by: str = "user_action"
    created_at: str = ""
    updated_at: str = ""
    started_at: str = ""
    finished_at: str = ""
    auto_mode: str = "safe"
    pending_pause: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


class MultiChapterProgress(AIBaseModel):
    session_id: str
    status: MultiChapterStatus
    current_index: int = 0
    target_chapters: int = 0
    completed_count: int = 0
    blocked_count: int = 0
    per_chapter: list[ChapterProgressEntry] = Field(default_factory=list)


class QuickTrialRequest(AIBaseModel):
    trial_id: str = ""
    work_id: str = ""
    job_id: str = ""
    model_role: str = ""
    provider_name: str = ""
    model_name: str = ""
    input_text: str = ""
    system_prompt: str = ""
    output_schema_key: str = "plain_text"
    max_output_chars: int = 2000
    created_by: str = "user_action"
    metadata: dict[str, Any] = Field(default_factory=dict)


class QuickTrialResult(AIBaseModel):
    trial_id: str
    status: str
    output_text: str = ""
    output_preview: str = ""
    validation_status: str
    validation_errors: list[str] = Field(default_factory=list)
    provider_name: str = ""
    model_name: str = ""
    model_role: str = ""
    request_id: str = ""
    created_at: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class AIReviewTargetType(StrEnum):
    CANDIDATE_DRAFT = "candidate_draft"
    CHAPTER_DRAFT = "chapter_draft"


class AIReviewStatus(StrEnum):
    COMPLETED = "completed"
    COMPLETED_WITH_WARNINGS = "completed_with_warnings"
    FAILED = "failed"
    SKIPPED = "skipped"
    BLOCKED = "blocked"


class AIReviewRiskLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ReviewIssue(AIBaseModel):
    issue_id: str
    severity: str = "medium"
    category: str = "consistency"
    message: str
    suggestion: str = ""
    source_ref: str = ""


class AIReviewRequest(AIBaseModel):
    review_id: str = ""
    work_id: str
    chapter_id: str
    candidate_draft_id: str = ""
    review_target_type: AIReviewTargetType
    review_target_ref: str
    review_mode: str = "candidate_draft_review"
    review_scope: str = "basic_quality+apply_risk"
    allow_degraded: bool = True
    idempotency_key: str = ""
    created_by: str = "user_action"
    user_instruction: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class AIReviewResult(AIBaseModel):
    review_id: str
    work_id: str
    chapter_id: str
    candidate_draft_id: str = ""
    status: AIReviewStatus
    summary: str = ""
    warnings: list[str] = Field(default_factory=list)
    issues: list[ReviewIssue] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)
    risk_level: AIReviewRiskLevel = AIReviewRiskLevel.LOW
    consistency_notes: list[str] = Field(default_factory=list)
    style_notes: list[str] = Field(default_factory=list)
    logic_notes: list[str] = Field(default_factory=list)
    reviewer_model_role: str = ModelRole.REVIEWER.value
    provider_name: str = ""
    model_name: str = ""
    created_at: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class AISuggestionType(StrEnum):
    REWRITE_SUGGESTION = "rewrite_suggestion"
    STYLE_SUGGESTION = "style_suggestion"
    PLOT_SUGGESTION = "plot_suggestion"
    CHARACTER_SUGGESTION = "character_suggestion"
    FORESHADOW_SUGGESTION = "foreshadow_suggestion"
    MENTION_SUGGESTION = "mention_suggestion"
    MEMORY_UPDATE_SUGGESTION_REF = "memory_update_suggestion_ref"
    CONFLICT_RESOLUTION_SUGGESTION = "conflict_resolution_suggestion"
    DIRECTION_PLAN_SUGGESTION = "direction_plan_suggestion"
    CONTINUITY_SUGGESTION = "continuity_suggestion"
    RISK_WARNING = "risk_warning"
    OUTLINE_POLISH = "outline_polish"
    OUTLINE_EXPAND = "outline_expand"
    CHAPTER_OUTLINE_DETAIL = "chapter_outline_detail"
    WRITING_TASK_SUGGESTION = "writing_task_suggestion"


class AISuggestionSeverity(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class AISuggestionPriority(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class AISuggestionStatus(StrEnum):
    PENDING = "pending"
    GENERATED = "generated"
    SHOWN = "shown"
    ACCEPTED = "accepted"
    DISMISSED = "dismissed"
    CONVERTED = "converted"
    SUPERSEDED = "superseded"
    STALE = "stale"
    FAILED = "failed"


class AISuggestionDecisionType(StrEnum):
    NONE = ""
    ACCEPTED = "accepted"
    DISMISSED = "dismissed"
    CONVERTED = "converted"


class AISuggestionActionType(StrEnum):
    CONVERT_TO_REWRITE_INSTRUCTION = "convert_to_rewrite_instruction"
    OPEN_CONFLICT_RESOLUTION = "open_conflict_resolution"
    CREATE_MEMORY_UPDATE_REF = "create_memory_update_ref"
    ADJUST_DIRECTION_OR_PLAN = "adjust_direction_or_plan"
    MANUAL_EDIT_HINT = "manual_edit_hint"
    DISMISS_ONLY = "dismiss_only"
    APPLY_OUTLINE = "apply_outline"
    CREATE_WRITING_TASK = "create_writing_task"


class AISuggestionSource(AIBaseModel):
    source_type: str
    source_ref_id: str
    source_agent_type: str = ""
    source_agent_session_id: str = ""
    source_version_id: str = ""


class AISuggestionTarget(AIBaseModel):
    target_type: str
    target_ref_id: str
    target_scope: str = "chapter"
    target_snapshot_ref: str = ""


class AISuggestionAction(AIBaseModel):
    action_type: AISuggestionActionType
    action_payload_ref: str = ""
    requires_user_action: bool = True
    action_status: str = "pending"


class AISuggestionDecision(AIBaseModel):
    suggestion_id: str
    decision: AISuggestionDecisionType = AISuggestionDecisionType.NONE
    decided_by: str = ""
    decision_note: str = ""
    decided_at: str = ""
    request_id: str = ""
    trace_id: str = ""


class AISuggestionBatch(AIBaseModel):
    batch_id: str
    work_id: str
    chapter_id: str
    agent_session_id: str = ""
    source_report_id: str = ""
    suggestion_ids: list[str] = Field(default_factory=list)
    generated_count: int = 0
    stale_count: int = 0
    created_at: str = ""


class AISuggestionRef(AIBaseModel):
    ref_type: str
    ref_id: str
    ref_scope: str = ""
    summary: str = ""
    checksum: str = ""
    created_at: str = ""


class AISuggestion(AIBaseModel):
    suggestion_id: str
    work_id: str
    chapter_id: str
    agent_session_id: str = ""
    source: AISuggestionSource
    target: AISuggestionTarget
    suggestion_type: AISuggestionType
    severity: AISuggestionSeverity = AISuggestionSeverity.MEDIUM
    priority: AISuggestionPriority = AISuggestionPriority.MEDIUM
    title: str
    summary: str = ""
    rationale: str = ""
    proposed_action: str = ""
    status: AISuggestionStatus = AISuggestionStatus.GENERATED
    decision: AISuggestionDecisionType = AISuggestionDecisionType.NONE
    decided_by: str = ""
    warning_codes: list[str] = Field(default_factory=list)
    created_by: str = "reviewer_agent"
    created_at: str = ""
    updated_at: str = ""
    request_id: str = ""
    trace_id: str = ""
    expires_at: str = ""
    action: AISuggestionAction = Field(
        default_factory=lambda: AISuggestionAction(action_type=AISuggestionActionType.DISMISS_ONLY)
    )
    decision_log: AISuggestionDecision | None = None
    batch_id: str = ""
    payload: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @computed_field
    @property
    def is_expired(self) -> bool:
        if not self.expires_at:
            return False
        try:
            return datetime.fromisoformat(self.expires_at) <= datetime.now(UTC)
        except ValueError:
            return False


class SelectionRewriteMode(StrEnum):
    EXPAND = "expand"
    REWRITE = "rewrite"
    ABBREVIATE = "abbreviate"
    POLISH = "polish"
    DIALOGUE_OPT = "dialogue_opt"
    DE_AI = "de_ai"


class SelectionRewriteStatus(StrEnum):
    GENERATING = "generating"
    PENDING = "pending"
    APPLIED = "applied"
    REJECTED = "rejected"
    FAILED = "failed"
    CONFLICTED = "conflicted"
    EXPIRED = "expired"


class SelectionRewriteCandidate(AIBaseModel):
    rewrite_id: str
    chapter_id: str
    work_id: str
    rewrite_mode: SelectionRewriteMode
    source_text: str
    source_hash: str = ""
    source_start_pos: int = 0
    source_end_pos: int = 0
    rewritten_text: str = ""
    applied_text: str = ""
    word_count_before: int = 0
    word_count_after: int = 0
    diff_summary: str = ""
    status: SelectionRewriteStatus = SelectionRewriteStatus.GENERATING
    model_role: str = ""
    chapter_revision: int = 0
    draft_revision: int = 0
    draft_text_hash: str = ""
    draft_length: int = 0
    edited_before_apply: bool = False
    context_before: str = ""
    context_after: str = ""
    error_code: str = ""
    error_message: str = ""
    request_id: str = ""
    trace_id: str = ""
    created_at: str = ""
    applied_at: str = ""


class ConflictType(StrEnum):
    CHARACTER_CONFLICT = "character_conflict"
    SETTING_CONFLICT = "setting_conflict"
    TIMELINE_CONFLICT = "timeline_conflict"
    ARC_CONFLICT = "arc_conflict"
    DIRECTION_PLAN_CONFLICT = "direction_plan_conflict"
    MEMORY_CONFLICT = "memory_conflict"
    FORESHADOW_CONFLICT = "foreshadow_conflict"
    CANDIDATE_VERSION_CONFLICT = "candidate_version_conflict"
    USER_DRAFT_CONFLICT = "user_draft_conflict"
    APPLY_VERSION_CONFLICT = "apply_version_conflict"
    UNKNOWN_CONFLICT = "unknown_conflict"


class ConflictSeverity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    BLOCKING = "blocking"


class ConflictRecordStatus(StrEnum):
    PENDING = "pending"
    DETECTED = "detected"
    SHOWN = "shown"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    OVERRIDDEN = "overridden"
    DISMISSED = "dismissed"
    STALE = "stale"
    SUPERSEDED = "superseded"
    FAILED = "failed"


class ConflictDecisionType(StrEnum):
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    DISMISSED = "dismissed"
    OVERRIDDEN = "overridden"


class ConflictDetectionStatus(StrEnum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"


class ConflictGuardRecord(AIBaseModel):
    record_id: str
    work_id: str
    chapter_id: str
    candidate_draft_id: str
    candidate_version_id: str
    agent_session_id: str = ""
    source_type: str
    source_ref_id: str
    target_type: str
    target_ref_id: str
    conflict_type: ConflictType
    severity: ConflictSeverity
    status: ConflictRecordStatus = ConflictRecordStatus.DETECTED
    title: str
    summary: str = ""
    evidence_refs: list[str] = Field(default_factory=list)
    suggested_action_refs: list[str] = Field(default_factory=list)
    resolution_status: str = "unresolved"
    resolved_by: str = ""
    resolved_at: str = ""
    warning_codes: list[str] = Field(default_factory=list)
    created_by: str = "conflict_guard"
    created_at: str = ""
    updated_at: str = ""
    request_id: str = ""
    trace_id: str = ""


class ConflictDetectionResult(AIBaseModel):
    result_id: str
    work_id: str
    chapter_id: str
    candidate_version_id: str
    total_conflicts: int = 0
    blocking_count: int = 0
    warning_count: int = 0
    info_count: int = 0
    record_refs: list[str] = Field(default_factory=list)
    detection_status: ConflictDetectionStatus = ConflictDetectionStatus.COMPLETED
    detection_started_at: str = ""
    detection_finished_at: str = ""


class ConflictGuardDecision(AIBaseModel):
    decision_id: str
    record_id: str
    decision: ConflictDecisionType
    decided_by: str = ""
    decided_at: str = ""
    decision_note: str = ""
    request_id: str = ""
    trace_id: str = ""


def build_default_model_role_mappings() -> dict[str, ModelSelection]:
    return {
        ModelRole.OUTLINE_ANALYZER.value: ModelSelection(provider_name="kimi", model_name="kimi-analysis"),
        ModelRole.MANUSCRIPT_ANALYZER.value: ModelSelection(provider_name="kimi", model_name="kimi-analysis"),
        ModelRole.MEMORY_EXTRACTOR.value: ModelSelection(provider_name="kimi", model_name="kimi-analysis"),
        ModelRole.STYLE_EXTRACTOR.value: ModelSelection(provider_name="kimi", model_name="kimi-analysis"),
        ModelRole.PLANNER.value: ModelSelection(provider_name="kimi", model_name="kimi-planner"),
        ModelRole.WRITING_TASK_BUILDER.value: ModelSelection(provider_name="kimi", model_name="kimi-planner"),
        ModelRole.REVIEWER.value: ModelSelection(provider_name="kimi", model_name="kimi-review"),
        ModelRole.WRITER.value: ModelSelection(provider_name="deepseek", model_name="deepseek-writer"),
        ModelRole.REWRITER.value: ModelSelection(provider_name="deepseek", model_name="deepseek-rewriter"),
        ModelRole.POLISHER.value: ModelSelection(provider_name="deepseek", model_name="deepseek-polisher"),
        ModelRole.DIALOGUE_WRITER.value: ModelSelection(provider_name="deepseek", model_name="deepseek-dialogue"),
        ModelRole.SCENE_GENERATOR.value: ModelSelection(provider_name="deepseek", model_name="deepseek-scene"),
        ModelRole.QUICK_TRIAL_WRITER.value: ModelSelection(provider_name="deepseek", model_name="deepseek-quick-trial"),
    }
