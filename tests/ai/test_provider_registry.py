from __future__ import annotations

import pytest

from application.services.ai.provider_registry import ProviderRegistry
from domain.services.ai.provider import ProviderNotFoundError
from infrastructure.ai.providers.fake_provider import FakeLLMProvider


def test_provider_registry_registers_and_returns_provider() -> None:
    registry = ProviderRegistry()
    provider = FakeLLMProvider()

    registry.register(provider)

    assert registry.get("fake") is provider
    assert registry.list_provider_names() == ["fake"]


def test_provider_registry_raises_when_provider_missing() -> None:
    registry = ProviderRegistry()

    with pytest.raises(ProviderNotFoundError, match="provider_not_found"):
        registry.get("missing")
