from __future__ import annotations

from fastapi.testclient import TestClient

from infrastructure.database.session import get_database_path
from presentation.api import dependencies
from presentation.api.app import app


def _reset_dependencies() -> None:
    get_database_path.cache_clear()
    dependencies.get_feature_preference_repository.cache_clear()
    dependencies.get_feature_capability_service.cache_clear()


def test_feature_capabilities_expose_plain_language_effective_state(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("INKTRACE_DB_PATH", str(tmp_path / "runtime" / "inktrace.db"))
    monkeypatch.setenv("INKTRACE_P2_ENABLE_AUTO_QUEUE", "1")
    _reset_dependencies()

    response = TestClient(app).get("/api/v2/ai/feature-capabilities")

    assert response.status_code == 200
    items = {item["feature_key"]: item for item in response.json()["data"]["capabilities"]}
    auto_queue = items["enable_auto_queue"]
    assert auto_queue["label"] == "接着写"
    assert auto_queue["system_available"] is True
    assert auto_queue["user_enabled"] is True
    assert auto_queue["effective_enabled"] is True
    assert "environment" not in response.text.lower()


def test_feature_capability_preference_requires_real_user_action(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("INKTRACE_DB_PATH", str(tmp_path / "runtime" / "inktrace.db"))
    monkeypatch.setenv("INKTRACE_P2_ENABLE_AUTO_QUEUE", "1")
    _reset_dependencies()
    client = TestClient(app)

    forbidden = client.put(
        "/api/v2/ai/feature-capabilities/enable_auto_queue",
        json={
            "enabled": False,
            "caller_type": "workflow_compat",
            "user_action": True,
            "idempotency_key": "feature-pref-forbidden",
        },
    )
    assert forbidden.status_code == 403

    updated = client.put(
        "/api/v2/ai/feature-capabilities/enable_auto_queue",
        json={
            "enabled": False,
            "caller_type": "user_action",
            "user_action": True,
            "idempotency_key": "feature-pref-disable-auto-queue",
        },
    )
    assert updated.status_code == 200
    assert updated.json()["data"]["capability"]["user_enabled"] is False
    assert updated.json()["data"]["capability"]["effective_enabled"] is False

    fetched = client.get("/api/v2/ai/feature-capabilities")
    items = {item["feature_key"]: item for item in fetched.json()["data"]["capabilities"]}
    assert items["enable_auto_queue"]["user_enabled"] is False


def test_feature_capability_preference_rejects_missing_idempotency_key(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("INKTRACE_DB_PATH", str(tmp_path / "runtime" / "inktrace.db"))
    _reset_dependencies()

    response = TestClient(app).put(
        "/api/v2/ai/feature-capabilities/enable_auto_queue",
        json={
            "enabled": True,
            "caller_type": "user_action",
            "user_action": True,
            "idempotency_key": "",
        },
    )

    assert response.status_code == 400
    assert response.json()["error"]["error_code"] == "idempotency_key_required"
