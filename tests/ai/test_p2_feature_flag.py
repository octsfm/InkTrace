from __future__ import annotations

from fastapi.testclient import TestClient

from infrastructure.database.session import get_database_path
from presentation.api import dependencies
from presentation.api.app import app


def _reset_p2_flag_dependencies() -> None:
    get_database_path.cache_clear()
    dependencies.get_ai_settings_repository.cache_clear()
    dependencies.get_ai_job_store.cache_clear()
    dependencies.get_initialization_repository.cache_clear()
    dependencies.get_story_memory_repository.cache_clear()
    dependencies.get_story_state_repository.cache_clear()
    dependencies.get_context_pack_repository.cache_clear()
    dependencies.get_plot_arc_repository.cache_clear()
    dependencies.get_candidate_draft_repository.cache_clear()
    dependencies.get_chapter_plan_repository.cache_clear()
    dependencies.get_direction_plan_repository.cache_clear()
    dependencies.get_ai_review_repository.cache_clear()
    dependencies.get_ai_suggestion_repository.cache_clear()
    dependencies.get_conflict_guard_repository.cache_clear()
    dependencies.get_llm_call_log_repository.cache_clear()
    dependencies.get_memory_review_repository.cache_clear()
    dependencies.get_settings_cipher.cache_clear()
    dependencies.get_provider_registry.cache_clear()
    dependencies.get_work_service.cache_clear()
    dependencies.get_chapter_service.cache_clear()
    dependencies.get_model_router.cache_clear()
    dependencies.get_ai_settings_service.cache_clear()
    dependencies.get_ai_job_service.cache_clear()
    dependencies.get_agent_runtime_store.cache_clear()
    dependencies.get_agent_trace_repository.cache_clear()
    dependencies.get_agent_trace_service.cache_clear()
    dependencies.get_agent_runtime_service.cache_clear()
    dependencies.get_agent_orchestrator.cache_clear()
    dependencies.get_initialization_service.cache_clear()
    dependencies.get_context_pack_service.cache_clear()
    dependencies.get_quick_trial_service.cache_clear()
    dependencies.get_core_tool_facade.cache_clear()
    dependencies.get_continuation_workflow.cache_clear()
    dependencies.get_candidate_review_service.cache_clear()
    dependencies.get_ai_review_service.cache_clear()
    dependencies.get_candidate_rewrite_service.cache_clear()
    dependencies.get_ai_suggestion_service.cache_clear()
    dependencies.get_conflict_guard_service.cache_clear()
    dependencies.get_memory_review_gate_service.cache_clear()
    dependencies.get_planning_api_service.cache_clear()
    dependencies.get_plot_arc_query_service.cache_clear()


def test_p2_feature_flag_blocks_disabled_module_api(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("INKTRACE_DB_PATH", str(tmp_path / "runtime" / "inktrace.db"))
    monkeypatch.setenv("INKTRACE_P2_ENABLE_MULTI_CHAPTER", "0")
    _reset_p2_flag_dependencies()
    client = TestClient(app)

    response = client.post(
        "/api/v2/ai/multi-chapter/start",
        json={"work_id": "work-1", "start_chapter_id": "chapter-1", "target_chapters": 3},
    )

    assert response.status_code == 503
    payload = response.json()
    assert payload["error"]["error_code"] == "P2_FEATURE_DISABLED"


def test_p2_feature_flag_allows_unrelated_api_when_module_disabled(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("INKTRACE_DB_PATH", str(tmp_path / "runtime" / "inktrace.db"))
    monkeypatch.setenv("INKTRACE_P2_ENABLE_MULTI_CHAPTER", "0")
    _reset_p2_flag_dependencies()
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

