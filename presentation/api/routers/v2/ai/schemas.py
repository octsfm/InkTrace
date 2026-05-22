from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class V2AIBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class V2AIOperationRequest(V2AIBaseModel):
    caller_type: str = "user_action"
    idempotency_key: str = ""


class ProviderConfigUpdate(V2AIBaseModel):
    provider_name: str
    enabled: bool = True
    api_key: str | None = None
    default_model: str = ""
    timeout: int = 30
    base_url: str | None = None


class ModelRoleMappingUpdate(V2AIBaseModel):
    provider_name: str
    model_name: str


class AISettingsUpdateRequest(V2AIBaseModel):
    provider_configs: list[ProviderConfigUpdate] = Field(default_factory=list)
    model_role_mappings: dict[str, ModelRoleMappingUpdate] = Field(default_factory=dict)


class ProviderConnectionTestRequest(V2AIBaseModel):
    model_name: str = ""


class CancelAIJobRequest(V2AIBaseModel):
    reason: str = "user_cancelled"


class StartInitializationRequest(V2AIBaseModel):
    work_id: str
    created_by: str = "user_action"


class BuildContextPackRequest(V2AIOperationRequest):
    work_id: str
    chapter_id: str = ""
    continuation_mode: str = "continue_chapter"
    user_instruction: str = ""
    max_context_tokens: int = 4000
    model_role: str = "writer"
    allow_degraded: bool = True
    allow_stale_vector: bool = False


class StartContinuationRequest(V2AIOperationRequest):
    work_id: str
    chapter_id: str
    user_instruction: str = ""


class QuickTrialRunRequest(V2AIOperationRequest):
    model_role: str = ""
    provider_name: str = ""
    model_name: str = ""
    input_text: str
    system_prompt: str = ""
    output_schema_key: str = "plain_text"
    max_output_chars: int = 2000
    created_by: str = "user_action"
    metadata: dict[str, object] = Field(default_factory=dict)


class AcceptCandidateDraftRequest(V2AIOperationRequest):
    user_action: bool = False
    user_id: str = ""
    candidate_version_id: str = ""


class RejectCandidateDraftRequest(V2AIOperationRequest):
    user_action: bool = False
    user_id: str = ""
    candidate_version_id: str = ""
    reason: str = ""


class ApplyCandidateDraftRequest(V2AIOperationRequest):
    user_action: bool = False
    user_id: str = ""
    candidate_version_id: str = ""
    expected_chapter_version: int | None = None
    apply_mode: str = "append_to_chapter_end"
    selection_range: list[int] | None = None
    cursor_position: int | None = None


class SelectCandidateDraftVersionRequest(V2AIOperationRequest):
    user_action: bool = False
    user_id: str = ""


class RewriteCandidateDraftRequest(V2AIOperationRequest):
    user_action: bool = False
    user_id: str = ""
    source_version_id: str
    trigger_type: str
    review_report_id: str = ""
    user_instruction: str = ""


class SuggestionDecisionRequest(V2AIOperationRequest):
    user_action: bool = False
    user_id: str = ""
    decision_note: str = ""


class ConflictDecisionRequest(V2AIOperationRequest):
    user_action: bool = False
    user_id: str = ""
    decision: str
    decision_note: str = ""


class ReviewCandidateDraftRequest(V2AIOperationRequest):
    user_instruction: str = ""


class GenerateDirectionProposalRequest(V2AIOperationRequest):
    work_id: str
    chapter_id: str
    user_instruction: str = ""


class SelectDirectionRequest(V2AIOperationRequest):
    user_action: bool = False
    user_id: str = ""
    selected_option_id: str
    edited_fields: list[str] = Field(default_factory=list)
    edited_values: dict[str, object] = Field(default_factory=dict)


class GenerateChapterPlanRequest(V2AIOperationRequest):
    work_id: str
    chapter_id: str
    direction_proposal_id: str


class ConfirmChapterPlanRequest(V2AIOperationRequest):
    user_action: bool = False
    user_id: str = ""
    edited_items: list[str] = Field(default_factory=list)
    edited_fields: dict[str, object] = Field(default_factory=dict)
    user_edit_notes: str = ""


class RejectChapterPlanRequest(V2AIOperationRequest):
    user_action: bool = False
    user_id: str = ""
    user_edit_notes: str = ""


class MemorySuggestionDecisionRequest(V2AIOperationRequest):
    user_action: bool = False
    user_id: str = ""
    decision_note: str = ""


class MemorySuggestionEditApproveRequest(MemorySuggestionDecisionRequest):
    proposed_value_summary: str


class ApplyMemoryGateRequest(V2AIOperationRequest):
    user_action: bool = False
    user_id: str = ""


class RollbackMemoryRevisionRequest(V2AIOperationRequest):
    user_action: bool = False
    user_id: str = ""
    decision_note: str = ""
