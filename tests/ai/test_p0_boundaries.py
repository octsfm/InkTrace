from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from application.services.ai.context_pack_service import ContextPackService
from application.services.ai.initialization_service import InitializationApplicationService
from application.services.ai.quick_trial_service import QuickTrialApplicationService
from application.services.ai.model_router import ModelRouter
from application.services.ai.provider_registry import ProviderRegistry
from application.services.ai.security import SettingsCipher
from application.services.v1.chapter_service import ChapterService
from application.services.v1.work_service import WorkService
from domain.entities.ai.models import AIProviderConfig, AISettings, ContextPackBuildRequest, ModelSelection, QuickTrialRequest
from infrastructure.ai.providers.fake_provider import FakeLLMProvider
from infrastructure.database.session import get_database_path
from infrastructure.database.repositories import ChapterRepo, WorkRepo
from infrastructure.database.repositories.ai.file_ai_job_store import FileAIJobStore
from infrastructure.database.repositories.ai.file_ai_settings_store import FileAISettingsStore
from infrastructure.database.repositories.ai.file_candidate_draft_store import FileCandidateDraftStore
from infrastructure.database.repositories.ai.file_context_pack_store import FileContextPackStore
from infrastructure.database.repositories.ai.file_initialization_store import FileInitializationStore
from infrastructure.database.repositories.ai.file_llm_call_log_store import FileLLMCallLogStore
from infrastructure.database.repositories.ai.file_story_memory_store import FileStoryMemoryStore
from infrastructure.database.repositories.ai.file_story_state_store import FileStoryStateStore
from presentation.api.app import app
from presentation.api import dependencies


def _clear_p0_singletons() -> None:
    get_database_path.cache_clear()
    dependencies.get_ai_settings_repository.cache_clear()
    dependencies.get_ai_job_store.cache_clear()
    dependencies.get_initialization_repository.cache_clear()
    dependencies.get_story_memory_repository.cache_clear()
    dependencies.get_story_state_repository.cache_clear()
    dependencies.get_context_pack_repository.cache_clear()
    dependencies.get_candidate_draft_repository.cache_clear()
    dependencies.get_ai_review_repository.cache_clear()
    dependencies.get_llm_call_log_repository.cache_clear()
    dependencies.get_settings_cipher.cache_clear()
    dependencies.get_provider_registry.cache_clear()
    dependencies.get_work_service.cache_clear()
    dependencies.get_chapter_service.cache_clear()
    dependencies.get_model_router.cache_clear()
    dependencies.get_ai_settings_service.cache_clear()
    dependencies.get_ai_job_service.cache_clear()
    dependencies.get_initialization_service.cache_clear()
    dependencies.get_context_pack_service.cache_clear()
    dependencies.get_quick_trial_service.cache_clear()
    dependencies.get_continuation_workflow.cache_clear()
    dependencies.get_candidate_review_service.cache_clear()
    dependencies.get_ai_review_service.cache_clear()


def _build_context_services(tmp_path: Path):
    work_repo = WorkRepo()
    chapter_repo = ChapterRepo()
    work_service = WorkService(work_repo=work_repo, chapter_repo=chapter_repo)
    chapter_service = ChapterService(chapter_repo=chapter_repo, work_repo=work_repo)
    job_store = FileAIJobStore(tmp_path / "jobs.json")
    init_store = FileInitializationStore(tmp_path / "initializations.json")
    memory_store = FileStoryMemoryStore(tmp_path / "memory.json")
    state_store = FileStoryStateStore(tmp_path / "state.json")
    context_store = FileContextPackStore(tmp_path / "context_packs.json")
    init_service = InitializationApplicationService(
        work_service=work_service,
        chapter_service=chapter_service,
        job_repository=job_store,
        step_repository=job_store,
        attempt_repository=job_store,
        initialization_repository=init_store,
        story_memory_repository=memory_store,
        story_state_repository=state_store,
    )
    context_service = ContextPackService(
        chapter_service=chapter_service,
        initialization_repository=init_store,
        story_memory_repository=memory_store,
        story_state_repository=state_store,
        context_pack_repository=context_store,
    )
    return work_service, chapter_service, init_service, context_service


def _build_quick_trial_service(tmp_path: Path) -> tuple[QuickTrialApplicationService, Path]:
    settings_path = tmp_path / "ai_settings.json"
    llm_log_path = tmp_path / "llm_call_logs.jsonl"
    settings_store = FileAISettingsStore(settings_path)
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
                )
            },
            model_role_mappings={
                "quick_trial_writer": ModelSelection(provider_name="fake", model_name="fake-chat"),
            },
        )
    )
    registry = ProviderRegistry()
    registry.register(FakeLLMProvider())
    return (
        QuickTrialApplicationService(
            settings_repository=settings_store,
            model_router=ModelRouter(settings_repository=settings_store, provider_registry=registry),
            provider_registry=registry,
            llm_call_log_repository=FileLLMCallLogStore(llm_log_path),
        ),
        llm_log_path,
    )


def test_context_pack_snapshot_does_not_store_full_chapter_text_or_prompt(tmp_path: Path) -> None:
    work_service, chapter_service, init_service, context_service = _build_context_services(tmp_path)
    work = work_service.create_work("P0 Boundary 作品", "作者")
    chapter = chapter_service.list_chapters(work.id)[0]
    chapter_content = "顾迟在灯塔门口停下脚步。"
    user_instruction = "请完整沿用上一段节奏，继续写顾迟推门进入灯塔的一幕。"
    chapter_service.update_chapter(chapter.id.value, title="第一章", content=chapter_content, expected_version=1)
    init_service.start_initialization(work.id, created_by="user_action")

    snapshot = context_service.build_and_save(
        ContextPackBuildRequest(
            work_id=work.id,
            chapter_id=chapter.id.value,
            user_instruction=user_instruction,
        )
    )

    serialized = snapshot.model_dump(mode="json")
    payload = json.dumps(serialized, ensure_ascii=False)

    assert chapter_content not in payload
    assert user_instruction not in payload
    assert snapshot.status.value in {"ready", "degraded"}


def test_quick_trial_logs_do_not_store_prompt_contextpack_or_candidate_content(tmp_path: Path) -> None:
    service, log_path = _build_quick_trial_service(tmp_path)
    prompt_text = "试写一小段有海雾和塔灯的夜景，不要写入正式流程。"

    result = service.run_quick_trial(
        QuickTrialRequest(
            model_role="quick_trial_writer",
            input_text=prompt_text,
            metadata={"candidate_preview": "候选稿完整内容不应出现在日志"},
        )
    )

    assert result.status == "succeeded"
    assert log_path.exists() is True
    line = log_path.read_text(encoding="utf-8").strip()
    assert prompt_text not in line
    assert "candidate_preview" not in line
    assert "api_key" not in line


def test_candidate_draft_list_requires_detail_for_full_content_and_no_streaming_routes(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("INKTRACE_DB_PATH", str(tmp_path / "runtime" / "inktrace.db"))
    monkeypatch.setenv("INKTRACE_AI_SETTINGS_SECRET", "test-secret")
    _clear_p0_singletons()
    client = TestClient(app)

    save_response = client.put(
        "/api/v2/ai/settings",
        json={
            "provider_configs": [
                {
                    "provider_name": "fake",
                    "enabled": True,
                    "api_key": "fake-api-key-123456",
                    "default_model": "fake-chat",
                    "timeout": 30,
                }
            ],
            "model_role_mappings": {
                "writer": {"provider_name": "fake", "model_name": "fake-writer"},
            },
        },
    )
    assert save_response.status_code == 200

    work_service = dependencies.get_work_service()
    chapter_service = dependencies.get_chapter_service()
    work = work_service.create_work("P0 Candidate 边界作品", "作者")
    chapter = chapter_service.list_chapters(work.id)[0]
    chapter_service.update_chapter(
        chapter.id.value,
        title="第一章",
        content="陆川在旧城档案馆里翻到了一张失落已久的海图。",
        expected_version=1,
    )

    dependencies.get_initialization_service().start_initialization(work.id, created_by="user_action")
    start = client.post(
        "/api/v2/ai/continuations",
        json={"work_id": work.id, "chapter_id": chapter.id.value, "user_instruction": "继续写"},
    )
    assert start.status_code == 200
    candidate_id = start.json()["data"]["candidate_draft_id"]

    listed = client.get("/api/v2/ai/candidate-drafts", params={"work_id": work.id, "chapter_id": chapter.id.value})
    assert listed.status_code == 200
    assert "content" not in listed.json()["data"]["items"][0]

    detail = client.get(f"/api/v2/ai/candidate-drafts/{candidate_id}")
    assert detail.status_code == 200
    assert detail.json()["data"]["content"]

    paths = {route.path for route in app.routes}
    assert not any("stream" in path.lower() or "sse" in path.lower() for path in paths)
