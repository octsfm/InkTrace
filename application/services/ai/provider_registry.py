from __future__ import annotations

from domain.services.ai.provider import LLMProvider, ProviderNotFoundError


class ProviderRegistry:
    def __init__(self) -> None:
        self._providers: dict[str, LLMProvider] = {}

    def register(self, provider: LLMProvider) -> None:
        self._providers[provider.provider_name] = provider

    def get(self, provider_name: str) -> LLMProvider:
        provider = self._providers.get(provider_name)
        if provider is None:
            raise ProviderNotFoundError(provider_name)
        return provider

    def list_provider_names(self) -> list[str]:
        return sorted(self._providers.keys())
