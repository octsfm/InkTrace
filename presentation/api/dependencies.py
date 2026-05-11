from __future__ import annotations

import os
from pathlib import Path


DB_PATH = os.getenv("INKTRACE_DB_PATH", str(Path("data") / "inktrace.db"))
CHROMA_DIR = os.getenv("INKTRACE_CHROMA_DIR", str(Path("data") / "chroma"))


def warmup_singletons_for_startup() -> None:
    return None

from functools import lru_cache

from application.services.ai.ai_settings_service import AISettingsService
from application.services.ai.model_router import ModelRouter
from application.services.ai.provider_registry import ProviderRegistry
from application.services.ai.security import SettingsCipher
from infrastructure.ai.providers.fake_provider import FakeLLMProvider
from infrastructure.database.repositories.ai.file_ai_settings_store import FileAISettingsStore
from infrastructure.database.repositories.ai.file_llm_call_log_store import FileLLMCallLogStore


@lru_cache(maxsize=1)
def get_ai_settings_repository() -> FileAISettingsStore:
    return FileAISettingsStore()


@lru_cache(maxsize=1)
def get_llm_call_log_repository() -> FileLLMCallLogStore:
    return FileLLMCallLogStore()


@lru_cache(maxsize=1)
def get_settings_cipher() -> SettingsCipher:
    return SettingsCipher()


@lru_cache(maxsize=1)
def get_provider_registry() -> ProviderRegistry:
    registry = ProviderRegistry()
    registry.register(FakeLLMProvider())
    return registry


@lru_cache(maxsize=1)
def get_model_router() -> ModelRouter:
    return ModelRouter(
        settings_repository=get_ai_settings_repository(),
        provider_registry=get_provider_registry(),
    )


@lru_cache(maxsize=1)
def get_ai_settings_service() -> AISettingsService:
    return AISettingsService(
        settings_repository=get_ai_settings_repository(),
        model_router=get_model_router(),
        settings_cipher=get_settings_cipher(),
    )
