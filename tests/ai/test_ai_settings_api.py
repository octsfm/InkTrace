from __future__ import annotations

from fastapi.testclient import TestClient

from presentation.api.app import app


def test_ai_settings_api_updates_and_hides_api_key(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("INKTRACE_DB_PATH", str(tmp_path / "runtime" / "inktrace.db"))
    monkeypatch.setenv("INKTRACE_AI_SETTINGS_SECRET", "test-secret")
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
            "model_role_mappings": {
                "writer": {
                    "provider_name": "fake",
                    "model_name": "fake-writer",
                }
            },
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["data"]["provider_configs"][0]["provider_name"] == "fake"
    assert payload["data"]["provider_configs"][0]["key_configured"] is True
    assert "api_key" not in payload["data"]["provider_configs"][0]
    assert payload["data"]["model_role_mappings"]["writer"]["provider_name"] == "fake"

    fetched = client.get("/api/v2/ai/settings")
    assert fetched.status_code == 200
    fetched_payload = fetched.json()
    assert fetched_payload["data"]["provider_configs"][0]["api_key_masked"].startswith("fak")
    assert fetched_payload["data"]["provider_configs"][0]["api_key_masked"] != "fake-api-key-1234567890"


def test_ai_settings_api_tests_provider_connection(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("INKTRACE_DB_PATH", str(tmp_path / "runtime" / "inktrace.db"))
    monkeypatch.setenv("INKTRACE_AI_SETTINGS_SECRET", "test-secret")
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
            "model_role_mappings": {},
        },
    )
    assert save_response.status_code == 200

    response = client.post("/api/v2/ai/settings/providers/fake/test", json={"model_name": "fake-chat"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["data"]["provider_name"] == "fake"
    assert payload["data"]["test_status"] == "ok"


def test_ai_settings_api_redacts_provider_test_error_message(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("INKTRACE_DB_PATH", str(tmp_path / "runtime" / "inktrace.db"))
    monkeypatch.setenv("INKTRACE_AI_SETTINGS_SECRET", "test-secret")
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
            "model_role_mappings": {},
        },
    )
    assert save_response.status_code == 200

    response = client.post("/api/v2/ai/settings/providers/fake/test", json={"model_name": "bad-model"})
    assert response.status_code == 400
    assert response.json()["error"]["error_code"] == "model_not_supported"

    fetched = client.get("/api/v2/ai/settings")
    assert fetched.status_code == 200
    provider = fetched.json()["data"]["provider_configs"][0]
    assert provider["last_test_error_code"] == "model_not_supported"
    assert provider["last_test_error_message"] == "model_not_supported"
