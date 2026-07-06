from __future__ import annotations

import json

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
        if request.output_schema_key == "candidate_with_citations":
            citations: list[dict[str, object]] = []
            if any(token in user_message for token in ("引用", "前文", "线索")):
                citations.append(
                    {
                        "source_type": "chapter",
                        "source_name": "第一章",
                        "source_id_hint": "",
                        "context_in_draft": "顾迟发现海图的线索",
                        "confidence": 0.88,
                    }
                )
            content = json.dumps(
                {
                    "text": content,
                    "citations": citations,
                },
                ensure_ascii=False,
            )
        elif request.output_schema_key == "selection_rewrite_schema":
            rewritten_text = self._build_selection_rewrite_text(
                prompt_key=str(request.prompt_key or ""),
                source_text=user_message,
            )
            content = json.dumps(
                {
                    "rewritten_text": rewritten_text,
                    "diff_summary": f"{request.prompt_key or request.model_role}_generated",
                    "risk_notes": [],
                },
                ensure_ascii=False,
            )
        return LLMResponse(
            provider_name=self.provider_name,
            model_name=model_name,
            content=content,
            request_id=request.request_id,
            trace_id=request.trace_id,
            token_usage=LLMUsage(input_tokens=10, output_tokens=20, total_tokens=30),
            finish_reason="stop",
        )

    @staticmethod
    def _build_selection_rewrite_text(*, prompt_key: str, source_text: str) -> str:
        base = str(source_text or "").strip() or "测试片段"
        if prompt_key == "selection_expand_v1":
            return f"{base}风更冷些"
        if prompt_key == "selection_abbreviate_v1":
            keep_length = max(1, int(len(base) * 0.5))
            return base[:keep_length]
        if prompt_key == "selection_polish_v1":
            return f"{base}，语气与节奏更克制。"
        if prompt_key == "selection_dialogue_opt_v1":
            return f"{base}，他说得更自然。"
        if prompt_key == "selection_de_ai_v1":
            return f"{base}，表达更贴近日常叙事。"
        return f"{base}，细节更完整。"

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
