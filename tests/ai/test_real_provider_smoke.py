from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

from infrastructure.database.session import get_database_path
from presentation.api import dependencies
from presentation.api.app import app


def _clear_singletons() -> None:
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


@pytest.mark.skipif(
    not (
        os.getenv("INKTRACE_SMOKE_PROVIDER")
        and os.getenv("INKTRACE_SMOKE_API_KEY")
        and os.getenv("INKTRACE_SMOKE_MODEL")
    ),
    reason="real provider smoke env not configured",
)
def test_real_provider_smoke_via_api(monkeypatch, tmp_path) -> None:
    provider_name = os.environ["INKTRACE_SMOKE_PROVIDER"]
    api_key = os.environ["INKTRACE_SMOKE_API_KEY"]
    model_name = os.environ["INKTRACE_SMOKE_MODEL"]
    base_url = os.getenv("INKTRACE_SMOKE_BASE_URL", "")

    monkeypatch.setenv("INKTRACE_DB_PATH", str(tmp_path / "runtime" / "inktrace.db"))
    monkeypatch.setenv("INKTRACE_AI_SETTINGS_SECRET", "test-secret")
    _clear_singletons()
    client = TestClient(app)

    save_response = client.put(
        "/api/v2/ai/settings",
        json={
            "provider_configs": [
                {
                    "provider_name": provider_name,
                    "enabled": True,
                    "api_key": api_key,
                    "default_model": model_name,
                    "timeout": 30,
                    "base_url": base_url or None,
                }
            ],
            "model_role_mappings": {
                "quick_trial_writer": {
                    "provider_name": provider_name,
                    "model_name": model_name,
                }
            },
        },
    )
    assert save_response.status_code == 200

    test_response = client.post(f"/api/v2/ai/settings/providers/{provider_name}/test", json={"model_name": model_name})
    assert test_response.status_code == 200
    assert test_response.json()["data"]["test_status"] == "ok"

    quick_trial = client.post(
        "/api/v2/ai/quick-trials",
        json={
            "model_role": "quick_trial_writer",
            "input_text": "请只回复一句“smoke-ok”。",
            "max_output_chars": 200,
        },
    )
    assert quick_trial.status_code == 200
    payload = quick_trial.json()["data"]
    assert payload["status"] == "succeeded"
    assert payload["provider_name"] == provider_name
    assert payload["model_name"] == model_name
    assert payload["output_text"]
