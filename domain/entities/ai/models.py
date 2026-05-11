from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class AIBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ModelRole(StrEnum):
    OUTLINE_ANALYZER = "outline_analyzer"
    MANUSCRIPT_ANALYZER = "manuscript_analyzer"
    MEMORY_EXTRACTOR = "memory_extractor"
    PLANNER = "planner"
    WRITING_TASK_BUILDER = "writing_task_builder"
    REVIEWER = "reviewer"
    WRITER = "writer"
    REWRITER = "rewriter"
    POLISHER = "polisher"
    DIALOGUE_WRITER = "dialogue_writer"
    SCENE_GENERATOR = "scene_generator"
    QUICK_TRIAL_WRITER = "quick_trial_writer"


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


class LLMUsage(AIBaseModel):
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None


class LLMCallStatus(StrEnum):
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class LLMRequest(AIBaseModel):
    model_role: str
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
    model_role: str
    provider_name: str
    model_name: str
    request_id: str
    trace_id: str
    status: LLMCallStatus
    error_code: str = ""
    error_message: str = ""
    attempt_no: int = 1
    started_at: datetime
    finished_at: datetime
    usage: LLMUsage | None = None
    context_pack_snapshot_id: str = ""
    output_schema_key: str = ""


def build_default_model_role_mappings() -> dict[str, ModelSelection]:
    return {
        ModelRole.OUTLINE_ANALYZER.value: ModelSelection(provider_name="kimi", model_name="kimi-analysis"),
        ModelRole.MANUSCRIPT_ANALYZER.value: ModelSelection(provider_name="kimi", model_name="kimi-analysis"),
        ModelRole.MEMORY_EXTRACTOR.value: ModelSelection(provider_name="kimi", model_name="kimi-analysis"),
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
