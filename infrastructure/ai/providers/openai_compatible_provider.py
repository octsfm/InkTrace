from __future__ import annotations

from typing import Callable

import httpx

from domain.entities.ai.models import AIProviderConfig, LLMRequest, LLMResponse, LLMUsage
from domain.services.ai.provider import LLMProvider, ProviderConfigurationError


class OpenAICompatibleProvider(LLMProvider):
    def __init__(
        self,
        *,
        provider_name: str,
        default_base_url: str,
        client_factory: Callable[[float], httpx.Client] | None = None,
    ) -> None:
        self.provider_name = provider_name
        self._default_base_url = default_base_url.rstrip("/")
        self._client_factory = client_factory or (lambda timeout: httpx.Client(timeout=timeout))

    def supports_model(self, model_name: str) -> bool:
        return bool(str(model_name or "").strip())

    def generate(self, request: LLMRequest, provider_config: AIProviderConfig, model_name: str) -> LLMResponse:
        api_key = str(provider_config.encrypted_api_key or "").strip()
        if not api_key:
            raise ProviderConfigurationError("provider_key_missing")
        if not self.supports_model(model_name):
            raise ProviderConfigurationError("model_not_supported")
        base_url = str(provider_config.base_url or self._default_base_url).rstrip("/")
        if not base_url:
            raise ProviderConfigurationError("provider_base_url_missing")

        payload = {
            "model": model_name,
            "messages": request.messages,
        }
        if request.temperature is not None:
            payload["temperature"] = request.temperature
        if request.max_tokens is not None:
            payload["max_tokens"] = request.max_tokens

        timeout = float(provider_config.timeout or 30)
        try:
            with self._client_factory(timeout) as client:
                response = client.post(
                    f"{base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )
                response.raise_for_status()
        except httpx.TimeoutException as exc:
            raise ProviderConfigurationError("provider_timeout") from exc
        except httpx.HTTPStatusError as exc:
            raise self._map_http_error(exc) from exc
        except httpx.HTTPError as exc:
            raise ProviderConfigurationError("provider_request_failed") from exc

        data = response.json()
        usage_payload = data.get("usage", {}) if isinstance(data, dict) else {}
        content = self._extract_content(data)
        return LLMResponse(
            provider_name=self.provider_name,
            model_name=model_name,
            content=content,
            request_id=request.request_id,
            trace_id=request.trace_id,
            token_usage=LLMUsage(
                input_tokens=usage_payload.get("prompt_tokens"),
                output_tokens=usage_payload.get("completion_tokens"),
                total_tokens=usage_payload.get("total_tokens"),
            ),
            finish_reason=self._extract_finish_reason(data),
        )

    def test_connection(self, provider_config: AIProviderConfig, model_name: str) -> dict[str, str]:
        request = LLMRequest(
            model_role="provider_smoke",
            prompt_key="provider_test",
            prompt_version="p0",
            output_schema_key="plain_text",
            request_id="provider_test",
            trace_id="provider_test",
            messages=[{"role": "user", "content": "ping"}],
            max_tokens=8,
        )
        self.generate(request=request, provider_config=provider_config, model_name=model_name)
        return {
            "provider_name": self.provider_name,
            "model_name": model_name,
            "test_status": "ok",
            "message": "provider connection ok",
        }

    def _extract_content(self, payload: object) -> str:
        if not isinstance(payload, dict):
            return ""
        choices = payload.get("choices", [])
        if not isinstance(choices, list) or not choices:
            return ""
        first = choices[0] if isinstance(choices[0], dict) else {}
        message = first.get("message", {}) if isinstance(first, dict) else {}
        if isinstance(message, dict):
            return str(message.get("content", "") or "")
        return ""

    def _extract_finish_reason(self, payload: object) -> str:
        if not isinstance(payload, dict):
            return ""
        choices = payload.get("choices", [])
        if not isinstance(choices, list) or not choices:
            return ""
        first = choices[0] if isinstance(choices[0], dict) else {}
        return str(first.get("finish_reason", "") or "")

    def _map_http_error(self, exc: httpx.HTTPStatusError) -> ProviderConfigurationError:
        status_code = exc.response.status_code
        if status_code in {401, 403}:
            return ProviderConfigurationError("provider_auth_failed")
        if status_code == 429:
            return ProviderConfigurationError("provider_rate_limited")
        if status_code >= 500:
            return ProviderConfigurationError("provider_unavailable")
        return ProviderConfigurationError("provider_request_failed")
