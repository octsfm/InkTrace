from __future__ import annotations

from domain.entities.ai.models import AIProviderConfig, LLMRequest, LLMResponse, LLMUsage
from domain.services.ai.provider import LLMProvider, ProviderConfigurationError


class FakeLLMProvider(LLMProvider):
    provider_name = "fake"

    def __init__(self) -> None:
        self._supported_models = {"fake-chat", "fake-writer", "fake-review"}

    def supports_model(self, model_name: str) -> bool:
        return model_name in self._supported_models

    def generate(self, request: LLMRequest, provider_config: AIProviderConfig, model_name: str) -> LLMResponse:
        if not provider_config.encrypted_api_key:
            raise ProviderConfigurationError("provider_key_missing")
        if not self.supports_model(model_name):
            raise ProviderConfigurationError("model_not_supported")
        user_message = ""
        for message in request.messages:
            if message.get("role") == "user":
                user_message = message.get("content", "")
        content = user_message.strip() or f"fake provider response for {request.model_role}"
        return LLMResponse(
            provider_name=self.provider_name,
            model_name=model_name,
            content=content,
            request_id=request.request_id,
            trace_id=request.trace_id,
            token_usage=LLMUsage(input_tokens=10, output_tokens=20, total_tokens=30),
            finish_reason="stop",
        )

    def test_connection(self, provider_config: AIProviderConfig, model_name: str) -> dict[str, str]:
        if not provider_config.encrypted_api_key:
            raise ProviderConfigurationError("provider_key_missing")
        if not self.supports_model(model_name):
            raise ProviderConfigurationError("model_not_supported")
        return {
            "provider_name": self.provider_name,
            "model_name": model_name,
            "test_status": "ok",
            "message": "fake provider connection ok",
        }
