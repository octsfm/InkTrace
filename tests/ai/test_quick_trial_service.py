from __future__ import annotations

import json

import pytest

from domain.entities.ai.models import AIProviderConfig, LLMRequest, LLMResponse, LLMUsage
from application.services.ai.model_router import ModelRouter
from application.services.ai.provider_registry import ProviderRegistry
from application.services.ai.quick_trial_service import QuickTrialApplicationService
from application.services.ai.security import SettingsCipher
from domain.entities.ai.models import AISettings, ModelSelection, QuickTrialRequest
from domain.services.ai.provider import LLMProvider
from infrastructure.ai.providers.fake_provider import FakeLLMProvider
from infrastructure.database.repositories.ai.file_ai_settings_store import FileAISettingsStore
from infrastructure.database.repositories.ai.file_llm_call_log_store import FileLLMCallLogStore


class _EmptyOutputProvider(LLMProvider):
    provider_name = "empty"

    def supports_model(self, model_name: str) -> bool:
        return model_name == "empty-chat"

    def generate(self, request: LLMRequest, provider_config: AIProviderConfig, model_name: str) -> LLMResponse:
        return LLMResponse(
            provider_name=self.provider_name,
            model_name=model_name,
            content="",
            request_id=request.request_id,
            trace_id=request.trace_id,
            token_usage=LLMUsage(input_tokens=1, output_tokens=0, total_tokens=1),
            finish_reason="stop",
        )

    def test_connection(self, provider_config: AIProviderConfig, model_name: str) -> dict[str, str]:
        return {
            "provider_name": self.provider_name,
            "model_name": model_name,
            "test_status": "ok",
            "message": "empty provider connection ok",
        }


def _build_service(tmp_path):
    settings_store = FileAISettingsStore(tmp_path / "ai_settings.json")
    llm_log_store = FileLLMCallLogStore(tmp_path / "llm_call_logs.jsonl")
    cipher = SettingsCipher("test-secret")
    settings_store.save(
        AISettings(
            provider_configs={
                "fake": AIProviderConfig(
                    provider_name="fake",
                    enabled=True,
                    encrypted_api_key=cipher.encrypt("fake-api-key"),
                    default_model="fake-chat",
                    timeout=30,
                    base_url=None,
                ),
                "empty": AIProviderConfig(
                    provider_name="empty",
                    enabled=True,
                    encrypted_api_key="not_required",
                    default_model="empty-chat",
                    timeout=30,
                    base_url=None,
                ),
            },
            model_role_mappings={
                "quick_trial_writer": ModelSelection(provider_name="fake", model_name="fake-chat"),
                "writer": ModelSelection(provider_name="fake", model_name="fake-writer"),
                "empty_writer": ModelSelection(provider_name="empty", model_name="empty-chat"),
            },
        )
    )
    registry = ProviderRegistry()
    registry.register(FakeLLMProvider())
    registry.register(_EmptyOutputProvider())
    return (
        QuickTrialApplicationService(
            settings_repository=settings_store,
            model_router=ModelRouter(settings_repository=settings_store, provider_registry=registry),
            provider_registry=registry,
            llm_call_log_repository=llm_log_store,
        ),
        llm_log_store,
    )


def test_quick_trial_runs_with_model_role_and_records_llm_call_log(tmp_path) -> None:
    service, log_store = _build_service(tmp_path)

    result = service.run_quick_trial(
        QuickTrialRequest(
            model_role="quick_trial_writer",
            input_text="请基于这个想法试写一小段海边灯塔场景。",
        )
    )

    assert result.status == "succeeded"
    assert result.output_text
    assert result.provider_name == "fake"
    assert result.model_name == "fake-chat"

    log_lines = (tmp_path / "llm_call_logs.jsonl").read_text(encoding="utf-8").strip().splitlines()
    assert len(log_lines) == 1
    payload = json.loads(log_lines[0])
    assert payload["model_role"] == "quick_trial_writer"
    assert payload["provider_name"] == "fake"


def test_quick_trial_supports_explicit_provider_and_model(tmp_path) -> None:
    service, _ = _build_service(tmp_path)

    result = service.run_quick_trial(
        QuickTrialRequest(
            provider_name="fake",
            model_name="fake-chat",
            input_text="显式 provider/model 试跑。",
        )
    )

    assert result.status == "succeeded"
    assert result.provider_name == "fake"
    assert result.model_name == "fake-chat"


def test_quick_trial_raises_when_model_role_config_missing(tmp_path) -> None:
    service, _ = _build_service(tmp_path)

    with pytest.raises(ValueError, match="model_role_invalid"):
        service.run_quick_trial(QuickTrialRequest(model_role="missing_role", input_text="测试"))


def test_quick_trial_raises_when_provider_missing(tmp_path) -> None:
    service, _ = _build_service(tmp_path)

    with pytest.raises(ValueError, match="provider_not_found"):
        service.run_quick_trial(
            QuickTrialRequest(provider_name="missing", model_name="fake-chat", input_text="测试")
        )


def test_quick_trial_rejects_empty_input(tmp_path) -> None:
    service, _ = _build_service(tmp_path)

    with pytest.raises(ValueError, match="quick_trial_input_empty"):
        service.run_quick_trial(QuickTrialRequest(model_role="quick_trial_writer", input_text=""))


def test_quick_trial_returns_validation_failed_when_output_empty(tmp_path) -> None:
    service, _ = _build_service(tmp_path)

    result = service.run_quick_trial(QuickTrialRequest(model_role="empty_writer", input_text="正常输入但输出为空"))

    assert result.status == "validation_failed"
    assert result.validation_status == "failed"


def test_quick_trial_does_not_create_formal_side_effect_files(tmp_path) -> None:
    service, _ = _build_service(tmp_path)

    service.run_quick_trial(
        QuickTrialRequest(model_role="quick_trial_writer", input_text="只做一次性试跑，不应产生正式副作用。")
    )

    assert not (tmp_path / "ai_jobs.json").exists()
    assert not (tmp_path / "candidate_drafts.json").exists()
    assert not (tmp_path / "story_memory_snapshots.json").exists()
    assert not (tmp_path / "story_state_snapshots.json").exists()
    assert not (tmp_path / "context_packs.json").exists()
