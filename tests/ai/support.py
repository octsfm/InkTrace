from __future__ import annotations

import uuid

from fastapi.testclient import TestClient


def save_fake_ai_settings(client: TestClient, *, idempotency_key: str | None = None) -> None:
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
                "analysis": {"provider_name": "fake", "model_name": "fake-chat"},
                "planning": {"provider_name": "fake", "model_name": "fake-chat"},
                "writer": {"provider_name": "fake", "model_name": "fake-writer"},
                "reviewer": {"provider_name": "fake", "model_name": "fake-review"},
                "rewriter": {"provider_name": "fake", "model_name": "fake-writer"},
                "quick_trial_writer": {"provider_name": "fake", "model_name": "fake-chat"},
            },
            "caller_type": "user_action",
            "user_action": True,
            "idempotency_key": idempotency_key or f"test-settings-{uuid.uuid4().hex[:12]}",
        },
    )
    assert response.status_code == 200, response.text
