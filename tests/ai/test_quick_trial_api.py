from __future__ import annotations

from fastapi.testclient import TestClient

from infrastructure.database.session import get_database_path
from presentation.api import dependencies
from presentation.api.app import app


def _clear_ai_singletons() -> None:
    dependencies.get_ai_settings_repository.cache_clear()
    dependencies.get_provider_registry.cache_clear()
    dependencies.get_model_router.cache_clear()
    dependencies.get_llm_call_log_repository.cache_clear()
    dependencies.get_quick_trial_service.cache_clear()


def test_quick_trial_api_runs_and_hides_provider_secret(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("INKTRACE_DB_PATH", str(tmp_path / "runtime" / "inktrace.db"))
    get_database_path.cache_clear()
    _clear_ai_singletons()
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
                "quick_trial_writer": {
                    "provider_name": "fake",
                    "model_name": "fake-chat",
                }
            },
        },
    )
    assert save_response.status_code == 200

    response = client.post(
        "/api/v2/ai/quick-trials",
        json={
            "model_role": "quick_trial_writer",
            "input_text": "试写一小段灯塔夜景。",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["data"]["trial_id"].startswith("trial_")
    assert payload["data"]["status"] == "succeeded"
    assert payload["data"]["output_text"]
    assert "api_key" not in str(payload)
    assert "candidate_draft_id" not in payload["data"]
    assert "job_id" not in payload["data"]


def test_quick_trial_api_returns_error_for_empty_input(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("INKTRACE_DB_PATH", str(tmp_path / "runtime" / "inktrace.db"))
    get_database_path.cache_clear()
    _clear_ai_singletons()
    client = TestClient(app)

    response = client.post(
        "/api/v2/ai/quick-trials",
        json={
            "provider_name": "fake",
            "model_name": "fake-chat",
            "input_text": "",
        },
    )

    assert response.status_code == 400
    payload = response.json()
    assert payload["error"]["error_code"] == "quick_trial_input_empty"
