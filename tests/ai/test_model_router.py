from __future__ import annotations

import pytest

from application.services.ai.model_router import ModelRouter
from application.services.ai.provider_registry import ProviderRegistry
from domain.entities.ai.models import AIProviderConfig, AISettings, ModelSelection
from domain.services.ai.provider import ModelRoleConfigError
from infrastructure.ai.providers.fake_provider import FakeLLMProvider
from infrastructure.database.repositories.ai.file_ai_settings_store import FileAISettingsStore


def test_model_router_resolves_model_role_to_provider_and_model(tmp_path) -> None:
    store = FileAISettingsStore(tmp_path / "ai_settings.json")
    store.save(
        AISettings(
            provider_configs={
                "fake": AIProviderConfig(
                    provider_name="fake",
                    enabled=True,
                    encrypted_api_key="",
                    default_model="fake-chat",
                )
            },
            model_role_mappings={
                "writer": ModelSelection(provider_name="fake", model_name="fake-writer")
            },
        )
    )
    registry = ProviderRegistry()
    registry.register(FakeLLMProvider())

    router = ModelRouter(settings_repository=store, provider_registry=registry)
    selection = router.resolve_model("writer")

    assert selection.provider_name == "fake"
    assert selection.model_name == "fake-writer"


def test_model_router_raises_when_model_role_config_missing(tmp_path) -> None:
    store = FileAISettingsStore(tmp_path / "ai_settings.json")
    store.save(AISettings(provider_configs={}, model_role_mappings={}))
    registry = ProviderRegistry()
    registry.register(FakeLLMProvider())

    router = ModelRouter(settings_repository=store, provider_registry=registry)

    with pytest.raises(ModelRoleConfigError, match="model_role_invalid"):
        router.resolve_model("writer")
