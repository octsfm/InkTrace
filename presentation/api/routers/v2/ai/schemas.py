from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class V2AIBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


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


class BuildContextPackRequest(V2AIBaseModel):
    work_id: str
    chapter_id: str = ""
    continuation_mode: str = "continue_chapter"
    user_instruction: str = ""
    max_context_tokens: int = 4000
    model_role: str = "writer"
    allow_degraded: bool = True


class StartContinuationRequest(V2AIBaseModel):
    work_id: str
    chapter_id: str
    user_instruction: str = ""
