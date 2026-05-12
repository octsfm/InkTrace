from __future__ import annotations

import httpx

from application.services.ai.model_router import ModelRouter
from application.services.ai.provider_registry import ProviderRegistry
from application.services.ai.security import SettingsCipher
from domain.entities.ai.models import AIProviderConfig, AISettings, LLMRequest, ModelSelection
from domain.services.ai.provider import LLMProvider
from infrastructure.database.repositories.ai.file_ai_settings_store import FileAISettingsStore
from infrastructure.ai.providers.openai_compatible_provider import OpenAICompatibleProvider


class _SpyProvider(LLMProvider):
    provider_name = "kimi"

    def __init__(self) -> None:
        self.last_api_key = ""

    def supports_model(self, model_name: str) -> bool:
        return bool(model_name)

    def generate(self, request: LLMRequest, provider_config: AIProviderConfig, model_name: str):
        self.last_api_key = provider_config.encrypted_api_key
        raise NotImplementedError

    def test_connection(self, provider_config: AIProviderConfig, model_name: str) -> dict[str, str]:
        self.last_api_key = provider_config.encrypted_api_key
        return {
            "provider_name": self.provider_name,
            "model_name": model_name,
            "test_status": "ok",
            "message": "ok",
        }


def test_openai_compatible_provider_generates_text_and_normalizes_usage() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["authorization"] = request.headers.get("Authorization", "")
        captured["payload"] = request.content.decode("utf-8")
        return httpx.Response(
            200,
            json={
                "id": "chatcmpl-test",
                "choices": [{"message": {"content": "真实 provider 已响应"}}],
                "usage": {"prompt_tokens": 11, "completion_tokens": 7, "total_tokens": 18},
            },
        )

    transport = httpx.MockTransport(handler)
    provider = OpenAICompatibleProvider(
        provider_name="kimi",
        default_base_url="https://api.moonshot.cn/v1",
        client_factory=lambda timeout: httpx.Client(transport=transport, timeout=timeout),
    )
    request = LLMRequest(
        model_role="reviewer",
        prompt_key="smoke",
        prompt_version="p0",
        request_id="req_1",
        trace_id="trace_1",
        messages=[{"role": "user", "content": "ping"}],
    )
    config = AIProviderConfig(
        provider_name="kimi",
        enabled=True,
        encrypted_api_key="plain-api-key",
        default_model="moonshot-v1-8k",
        timeout=9,
    )

    response = provider.generate(request=request, provider_config=config, model_name="moonshot-v1-8k")

    assert response.provider_name == "kimi"
    assert response.model_name == "moonshot-v1-8k"
    assert response.content == "真实 provider 已响应"
    assert response.token_usage is not None
    assert response.token_usage.total_tokens == 18
    assert captured["url"] == "https://api.moonshot.cn/v1/chat/completions"
    assert captured["authorization"] == "Bearer plain-api-key"
    assert '"model":"moonshot-v1-8k"' in str(captured["payload"])


def test_model_router_decrypts_provider_key_before_real_provider_test(tmp_path) -> None:
    cipher = SettingsCipher("test-secret")
    store = FileAISettingsStore(tmp_path / "ai_settings.json")
    store.save(
        AISettings(
            provider_configs={
                "kimi": AIProviderConfig(
                    provider_name="kimi",
                    enabled=True,
                    encrypted_api_key=cipher.encrypt("real-provider-key"),
                    default_model="moonshot-v1-8k",
                    timeout=15,
                )
            },
            model_role_mappings={
                "reviewer": ModelSelection(provider_name="kimi", model_name="moonshot-v1-8k"),
            },
        )
    )
    registry = ProviderRegistry()
    spy = _SpyProvider()
    registry.register(spy)
    router = ModelRouter(settings_repository=store, provider_registry=registry, settings_cipher=cipher)

    payload = router.test_connection(provider_name="kimi", model_name="moonshot-v1-8k")

    assert payload["test_status"] == "ok"
    assert spy.last_api_key == "real-provider-key"
