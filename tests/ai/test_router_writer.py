from __future__ import annotations

import json

from application.services.ai.model_router import ModelRouter
from application.services.ai.provider_registry import ProviderRegistry
from infrastructure.ai.providers.fake_provider import FakeLLMProvider
from infrastructure.ai.providers.model_router_writer import ModelRouterWriter
from infrastructure.database.repositories.ai.file_ai_settings_store import FileAISettingsStore
from infrastructure.database.repositories.ai.file_llm_call_log_store import FileLLMCallLogStore
from application.services.ai.security import SettingsCipher
from domain.entities.ai.models import AIProviderConfig, AISettings, ContextPackSnapshot, ContextPackStatus, ModelSelection, WritingTask


def test_model_router_writer_uses_model_role_mapping_and_records_llm_log(tmp_path) -> None:
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
                )
            },
            model_role_mappings={
                "writer": ModelSelection(provider_name="fake", model_name="fake-chat")
            },
        )
    )
    registry = ProviderRegistry()
    registry.register(FakeLLMProvider())
    writer = ModelRouterWriter(
        model_router=ModelRouter(
            settings_repository=settings_store,
            provider_registry=registry,
            settings_cipher=cipher,
        ),
        llm_call_log_repository=llm_log_store,
    )

    result = writer.generate_candidate_text(
        context_pack=ContextPackSnapshot(
            context_pack_id="cp_1",
            work_id="work_1",
            chapter_id="chapter_1",
            status=ContextPackStatus.READY,
            summary="灯塔外风暴将至，顾迟准备再次出海。",
            created_at="2026-06-09T00:00:00+00:00",
        ),
        writing_task=WritingTask(
            writing_task_id="wt_1",
            work_id="work_1",
            chapter_id="chapter_1",
            target_chapter_id="chapter_1",
            source_context_pack_id="cp_1",
            status="ready",
            user_instruction="请继续写出顾迟出海前的准备。",
            model_role="writer",
            request_id="req_1",
            trace_id="trace_1",
            created_at="2026-06-09T00:00:00+00:00",
            updated_at="2026-06-09T00:00:00+00:00",
        ),
    )

    assert result["provider_name"] == "fake"
    assert result["model_name"] == "fake-chat"
    assert result["model_role"] == "writer"
    assert "顾迟" in result["content"]

    payload = json.loads((tmp_path / "llm_call_logs.jsonl").read_text(encoding="utf-8").splitlines()[0])
    assert payload["provider_name"] == "fake"
    assert payload["model_name"] == "fake-chat"
    assert payload["model_role"] == "writer"
    assert payload["work_id"] == "work_1"

