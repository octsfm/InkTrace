from __future__ import annotations

from fastapi.testclient import TestClient

from infrastructure.database.session import get_database_path
from presentation.api import dependencies
from presentation.api.app import app


def _reset_ai_settings_dependencies() -> None:
    get_database_path.cache_clear()
    dependencies.get_ai_settings_repository.cache_clear()
    dependencies.get_settings_cipher.cache_clear()
    dependencies.get_provider_registry.cache_clear()
    dependencies.get_model_router.cache_clear()
    dependencies.get_ai_settings_service.cache_clear()


def _critical_role_mappings() -> dict[str, dict[str, str]]:
    return {
        "analysis": {"provider_name": "fake", "model_name": "fake-chat"},
        "writer": {"provider_name": "fake", "model_name": "fake-writer"},
    }


def test_ai_settings_api_updates_and_hides_api_key(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("INKTRACE_DB_PATH", str(tmp_path / "runtime" / "inktrace.db"))
    monkeypatch.setenv("INKTRACE_AI_SETTINGS_SECRET", "test-secret")
    _reset_ai_settings_dependencies()
    client = TestClient(app)

    response = client.put(
        "/api/v2/ai/settings",
        json={
            "provider_configs": [
                {
                    "provider_name": "fake",
                    "enabled": True,
                    "api_key": "fake-api-key-1234567890",
                    "default_model": "fake-chat",
                    "timeout": 30,
                }
            ],
            "model_role_mappings": _critical_role_mappings(),
            "caller_type": "user_action",
            "user_action": True,
            "idempotency_key": "settings-update-1",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    provider_map = {item["provider_name"]: item for item in payload["data"]["provider_configs"]}
    assert provider_map["fake"]["key_configured"] is True
    assert "api_key" not in provider_map["fake"]
    assert payload["data"]["model_role_mappings"]["writer"]["provider_name"] == "fake"

    fetched = client.get("/api/v2/ai/settings")
    assert fetched.status_code == 200
    fetched_payload = fetched.json()
    fetched_provider_map = {item["provider_name"]: item for item in fetched_payload["data"]["provider_configs"]}
    assert fetched_provider_map["fake"]["api_key_masked"].startswith("fak")
    assert fetched_provider_map["fake"]["api_key_masked"] != "fake-api-key-1234567890"


def test_ai_settings_api_tests_provider_connection(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("INKTRACE_DB_PATH", str(tmp_path / "runtime" / "inktrace.db"))
    monkeypatch.setenv("INKTRACE_AI_SETTINGS_SECRET", "test-secret")
    _reset_ai_settings_dependencies()
    client = TestClient(app)

    save_response = client.put(
        "/api/v2/ai/settings",
        json={
            "provider_configs": [
                {
                    "provider_name": "fake",
                    "enabled": True,
                    "api_key": "fake-api-key-1234567890",
                    "default_model": "fake-chat",
                    "timeout": 30,
                }
            ],
            "model_role_mappings": _critical_role_mappings(),
            "caller_type": "user_action",
            "user_action": True,
            "idempotency_key": "settings-save-1",
        },
    )
    assert save_response.status_code == 200

    response = client.post(
        "/api/v2/ai/settings/providers/fake/test",
        json={
            "model_name": "fake-chat",
            "caller_type": "user_action",
            "user_action": True,
            "idempotency_key": "provider-test-1",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["data"]["provider_name"] == "fake"
    assert payload["data"]["test_status"] == "ok"


def test_ai_settings_api_redacts_provider_test_error_message(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("INKTRACE_DB_PATH", str(tmp_path / "runtime" / "inktrace.db"))
    monkeypatch.setenv("INKTRACE_AI_SETTINGS_SECRET", "test-secret")
    _reset_ai_settings_dependencies()
    client = TestClient(app)

    save_response = client.put(
        "/api/v2/ai/settings",
        json={
            "provider_configs": [
                {
                    "provider_name": "fake",
                    "enabled": True,
                    "api_key": "fake-api-key-1234567890",
                    "default_model": "fake-chat",
                    "timeout": 30,
                }
            ],
            "model_role_mappings": _critical_role_mappings(),
            "caller_type": "user_action",
            "user_action": True,
            "idempotency_key": "settings-save-2",
        },
    )
    assert save_response.status_code == 200

    response = client.post(
        "/api/v2/ai/settings/providers/fake/test",
        json={
            "model_name": "bad-model",
            "caller_type": "user_action",
            "user_action": True,
            "idempotency_key": "provider-test-2",
        },
    )
    assert response.status_code == 400
    assert response.json()["error"]["error_code"] == "model_not_supported"

    fetched = client.get("/api/v2/ai/settings")
    assert fetched.status_code == 200
    provider_map = {item["provider_name"]: item for item in fetched.json()["data"]["provider_configs"]}
    provider = provider_map["fake"]
    assert provider["last_test_error_code"] == "model_not_supported"
    assert provider["last_test_error_message"] == "model_not_supported"


def test_ai_settings_api_requires_gate_payload_for_save_and_test(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("INKTRACE_DB_PATH", str(tmp_path / "runtime" / "inktrace.db"))
    monkeypatch.setenv("INKTRACE_AI_SETTINGS_SECRET", "test-secret")
    _reset_ai_settings_dependencies()
    client = TestClient(app)

    update_missing_key = client.put(
        "/api/v2/ai/settings",
        json={
            "provider_configs": [
                {
                    "provider_name": "fake",
                    "enabled": True,
                    "api_key": "fake-api-key-1234567890",
                    "default_model": "fake-chat",
                }
            ],
            "model_role_mappings": _critical_role_mappings(),
            "caller_type": "user_action",
            "user_action": True,
            "idempotency_key": "",
        },
    )
    assert update_missing_key.status_code == 400
    assert update_missing_key.json()["error"]["error_code"] == "idempotency_key_required"

    update_forbidden = client.put(
        "/api/v2/ai/settings",
        json={
            "provider_configs": [],
            "model_role_mappings": _critical_role_mappings(),
            "caller_type": "workflow_compat",
            "user_action": True,
            "idempotency_key": "settings-update-forbidden",
        },
    )
    assert update_forbidden.status_code == 403
    assert update_forbidden.json()["error"]["error_code"] == "caller_type_forbidden"

    save_response = client.put(
        "/api/v2/ai/settings",
        json={
            "provider_configs": [
                {
                    "provider_name": "fake",
                    "enabled": True,
                    "api_key": "fake-api-key-1234567890",
                    "default_model": "fake-chat",
                }
            ],
            "model_role_mappings": _critical_role_mappings(),
            "caller_type": "user_action",
            "user_action": True,
            "idempotency_key": "settings-save-3",
        },
    )
    assert save_response.status_code == 200

    test_missing_action = client.post(
        "/api/v2/ai/settings/providers/fake/test",
        json={
            "model_name": "fake-chat",
            "caller_type": "user_action",
            "user_action": False,
            "idempotency_key": "provider-test-missing-action",
        },
    )
    assert test_missing_action.status_code == 403
    assert test_missing_action.json()["error"]["error_code"] == "action_not_allowed"


def test_ai_settings_api_rejects_invalid_critical_role_mapping(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("INKTRACE_DB_PATH", str(tmp_path / "runtime" / "inktrace.db"))
    monkeypatch.setenv("INKTRACE_AI_SETTINGS_SECRET", "test-secret")
    _reset_ai_settings_dependencies()
    client = TestClient(app)

    response = client.put(
        "/api/v2/ai/settings",
        json={
            "provider_configs": [
                {
                    "provider_name": "fake",
                    "enabled": True,
                    "api_key": "",
                    "default_model": "fake-chat",
                }
            ],
            "model_role_mappings": {
                "analysis": {
                    "provider_name": "fake",
                    "model_name": "fake-chat",
                },
                "writer": {
                    "provider_name": "fake",
                    "model_name": "fake-chat",
                },
            },
            "caller_type": "user_action",
            "user_action": True,
            "idempotency_key": "settings-invalid-role-1",
        },
    )

    assert response.status_code == 400
    assert response.json()["error"]["error_code"] == "provider_key_missing"


def test_ai_settings_api_returns_registered_providers_when_not_configured(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("INKTRACE_DB_PATH", str(tmp_path / "runtime" / "inktrace.db"))
    monkeypatch.setenv("INKTRACE_AI_SETTINGS_SECRET", "test-secret")
    _reset_ai_settings_dependencies()
    client = TestClient(app)

    response = client.get("/api/v2/ai/settings")
    assert response.status_code == 200
    providers = {item["provider_name"]: item for item in response.json()["data"]["provider_configs"]}
    assert "deepseek" in providers
    assert "kimi" in providers
    assert providers["deepseek"]["key_configured"] is False
    assert providers["kimi"]["key_configured"] is False


def test_ai_settings_api_requires_analysis_and_writer_mapping(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("INKTRACE_DB_PATH", str(tmp_path / "runtime" / "inktrace.db"))
    monkeypatch.setenv("INKTRACE_AI_SETTINGS_SECRET", "test-secret")
    _reset_ai_settings_dependencies()
    client = TestClient(app)

    response = client.put(
        "/api/v2/ai/settings",
        json={
            "provider_configs": [
                {
                    "provider_name": "fake",
                    "enabled": True,
                    "api_key": "fake-api-key-1234567890",
                    "default_model": "fake-chat",
                }
            ],
            "model_role_mappings": {
                "planning": {"provider_name": "fake", "model_name": "fake-chat"},
            },
            "caller_type": "user_action",
            "user_action": True,
            "idempotency_key": "settings-missing-critical-1",
        },
    )
    assert response.status_code == 400
    assert response.json()["error"]["error_code"] == "critical_role_mapping_missing"
