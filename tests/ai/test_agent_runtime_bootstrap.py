from __future__ import annotations

from fastapi.testclient import TestClient

from application.services.ai.agent_runtime_service import AgentRuntimeService
from presentation.api import dependencies
from presentation.api.app import create_app


def test_dependencies_build_agent_runtime_service() -> None:
    runtime = dependencies.get_agent_runtime_service()

    assert isinstance(runtime, AgentRuntimeService)


def test_startup_warmup_recovers_runtime_and_ai_jobs(monkeypatch) -> None:
    calls: list[str] = []

    class _StubRuntime:
        def recover_after_restart(self) -> list[str]:
            calls.append("runtime")
            return []

    class _StubAIJobService:
        def recover_after_restart(self) -> list[str]:
            calls.append("ai_job")
            return []

    monkeypatch.setattr(dependencies, "get_agent_runtime_service", lambda: _StubRuntime())
    monkeypatch.setattr(dependencies, "get_ai_job_service", lambda: _StubAIJobService())

    with TestClient(create_app()) as client:
        response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert calls == ["runtime", "ai_job"]
