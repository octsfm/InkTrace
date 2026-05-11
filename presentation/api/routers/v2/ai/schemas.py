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
