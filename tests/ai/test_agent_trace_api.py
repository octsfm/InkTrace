from __future__ import annotations

from infrastructure.database.session import get_database_path
from presentation.api import dependencies
from presentation.api.app import app
from fastapi.testclient import TestClient
from domain.entities.ai.models import AgentObservation, AgentObservationType


def _clear_singletons() -> None:
    dependencies.get_ai_job_store.cache_clear()
    dependencies.get_agent_runtime_store.cache_clear()
    dependencies.get_llm_call_log_repository.cache_clear()
    dependencies.get_agent_runtime_service.cache_clear()
    dependencies.get_agent_trace_repository.cache_clear()
    dependencies.get_agent_trace_service.cache_clear()
    dependencies.get_core_tool_facade.cache_clear()
    dependencies.get_agent_orchestrator.cache_clear()


def _seed_trace_runtime() -> str:
    runtime = dependencies.get_agent_runtime_service()
    session = runtime.create_session(
        work_id="work_trace_api",
        chapter_id="chapter_trace_api",
        agent_workflow_type="continuation",
        user_instruction="继续写作",
        request_id="req_trace_api",
        trace_id="trace_trace_api",
        caller_type="user_action",
    )
    runtime.start_session(session.session_id)
    step = runtime.create_step(session.session_id, agent_type="writer", step_type="generate_candidate", action="run_writer")
    runtime.run_next_step(session.session_id)
    runtime.record_observation(
        step.step_id,
        AgentObservation(
            observation_id=f"obs_{step.step_id}_perception",
            session_id=session.session_id,
            step_id=step.step_id,
            observation_type=AgentObservationType.MODEL_RESULT,
            source_type="system",
            status="success",
            safe_message="perception_done",
            summary="perception_done",
            decision="continue",
            decision_reason="perception_done",
            request_id=session.request_id,
            trace_id=session.trace_id,
        ),
    )
    runtime.record_observation(
        step.step_id,
        AgentObservation(
            observation_id=f"obs_{step.step_id}_planning",
            session_id=session.session_id,
            step_id=step.step_id,
            observation_type=AgentObservationType.MODEL_RESULT,
            source_type="system",
            status="success",
            safe_message="planning_done",
            summary="planning_done",
            decision="continue",
            decision_reason="planning_done",
            request_id=session.request_id,
            trace_id=session.trace_id,
        ),
    )
    runtime.execute_tool_action(
        session.session_id,
        step_id=step.step_id,
        agent_type="writer",
        tool_name="apply_candidate_to_draft",
        payload={"candidate_draft_id": "cd_denied"},
        side_effect_level="candidate_write",
    )
    return session.trace_id


def test_agent_trace_api_lists_summary_and_protects_detail(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("INKTRACE_DB_PATH", str(tmp_path / "runtime" / "inktrace.db"))
    get_database_path.cache_clear()
    _clear_singletons()
    trace_id = _seed_trace_runtime()
    client = TestClient(app)

    listed = client.get("/api/v2/ai/traces", params={"work_id": "work_trace_api"})
    assert listed.status_code == 200
    items = listed.json()["data"]["items"]
    assert items
    assert items[0]["trace_id"] == trace_id
    assert "events" not in items[0]

    detail = client.get(f"/api/v2/ai/traces/{trace_id}")
    assert detail.status_code == 200
    assert detail.json()["data"]["trace_id"] == trace_id

    steps = client.get(f"/api/v2/ai/traces/{trace_id}/steps")
    assert steps.status_code == 200
    assert steps.json()["data"]["items"]

    forbidden = client.get(f"/api/v2/ai/traces/{trace_id}/detail-view", params={"detail": "true"})
    assert forbidden.status_code == 403
    assert forbidden.json()["error"]["error_code"] == "permission_denied"

    allowed = client.get(
        f"/api/v2/ai/traces/{trace_id}/detail-view",
        params={"detail": "true", "developer_mode": "true"},
    )
    assert allowed.status_code == 200
    assert allowed.json()["data"]["trace"]["trace_id"] == trace_id
    assert allowed.json()["data"]["tool_calls"]
