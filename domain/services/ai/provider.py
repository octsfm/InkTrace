from __future__ import annotations

from abc import ABC, abstractmethod

from domain.entities.ai.models import AIProviderConfig, LLMRequest, LLMResponse


class AIInfraError(RuntimeError):
    def __init__(self, error_code: str, message: str | None = None) -> None:
        self.error_code = error_code
        super().__init__(message or error_code)


class ProviderNotFoundError(AIInfraError):
    def __init__(self, provider_name: str) -> None:
        super().__init__("provider_not_found", f"provider_not_found:{provider_name}")


class ModelRoleConfigError(AIInfraError):
    def __init__(self, model_role: str) -> None:
        super().__init__("model_role_invalid", f"model_role_invalid:{model_role}")


class ProviderConfigurationError(AIInfraError):
    pass


class LLMProvider(ABC):
    provider_name: str

    @abstractmethod
    def supports_model(self, model_name: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    def generate(self, request: LLMRequest, provider_config: AIProviderConfig, model_name: str) -> LLMResponse:
        raise NotImplementedError

    @abstractmethod
    def test_connection(self, provider_config: AIProviderConfig, model_name: str) -> dict[str, str]:
        raise NotImplementedError
