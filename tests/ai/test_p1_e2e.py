from __future__ import annotations

from fastapi.testclient import TestClient

from infrastructure.database.session import get_database_path
from presentation.api import dependencies
from presentation.api.app import app


def _clear_p1_singletons() -> None:
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


def _configure_runtime(monkeypatch, tmp_path) -> TestClient:
    monkeypatch.setenv("INKTRACE_DB_PATH", str(tmp_path / "runtime" / "inktrace.db"))
    monkeypatch.setenv("INKTRACE_AI_SETTINGS_SECRET", "test-secret")
    _clear_p1_singletons()
    return TestClient(app)


def _save_ai_settings(client: TestClient) -> None:
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
            "idempotency_key": "p1-s12-settings-save",
        },
    )
    assert response.status_code == 200


def _seed_work() -> tuple[str, str]:
    work_service = dependencies.get_work_service()
    chapter_service = dependencies.get_chapter_service()
    work = work_service.create_work("P1 S12 E2E 作品", "作者")
    chapter = chapter_service.list_chapters(work.id)[0]
    chapter_service.update_chapter(
        chapter.id.value,
        title="第一章 灯塔回响",
        content="顾迟在灯塔底层找到一枚旧铜钥匙，海雾外传来断续钟声。",
        expected_version=1,
    )
    return work.id, chapter.id.value


def test_p1_mainline_e2e_runs_from_direction_to_apply_memory_and_trace(monkeypatch, tmp_path) -> None:
    client = _configure_runtime(monkeypatch, tmp_path)
    _save_ai_settings(client)
    work_id, chapter_id = _seed_work()
    chapter_service = dependencies.get_chapter_service()
    chapter_before = next(item for item in chapter_service.list_chapters(work_id) if item.id.value == chapter_id)
    original_content = chapter_before.content

    init_response = client.post("/api/v2/ai/initializations", json={"work_id": work_id})
    assert init_response.status_code == 200

    direction_response = client.post(
        "/api/v2/ai/directions",
        json={
            "work_id": work_id,
            "chapter_id": chapter_id,
            "user_instruction": "继续推进灯塔与父亲遗留线索。",
            "caller_type": "user_action",
            "idempotency_key": "p1-s12-direction-generate",
        },
    )
    assert direction_response.status_code == 200
    proposal = direction_response.json()["data"]
    proposal_id = proposal["direction_proposal_id"]
    option_id = proposal["options"][0]["option_id"]

    select_response = client.post(
        f"/api/v2/ai/directions/{proposal_id}/select",
        json={
            "caller_type": "user_action",
            "user_action": True,
            "user_id": "ui-user",
            "selected_option_id": option_id,
            "idempotency_key": "p1-s12-direction-select",
        },
    )
    assert select_response.status_code == 200

    plan_response = client.post(
        "/api/v2/ai/chapter-plans",
        json={
            "work_id": work_id,
            "chapter_id": chapter_id,
            "direction_proposal_id": proposal_id,
            "caller_type": "user_action",
            "idempotency_key": "p1-s12-plan-generate",
        },
    )
    assert plan_response.status_code == 200
    plan_id = plan_response.json()["data"]["chapter_plan_id"]

    confirm_response = client.post(
        f"/api/v2/ai/chapter-plans/{plan_id}/confirm",
        json={
            "caller_type": "user_action",
            "user_action": True,
            "user_id": "ui-user",
            "idempotency_key": "p1-s12-plan-confirm",
        },
    )
    assert confirm_response.status_code == 200
    writing_task_id = confirm_response.json()["data"]["writing_task"]["writing_task_id"]

    continuation_response = client.post(
        "/api/v2/ai/continuations",
        json={
            "work_id": work_id,
            "chapter_id": chapter_id,
            "user_instruction": "继续写作，保留悬念，不要直接揭晓答案。",
            "caller_type": "user_action",
            "user_action": True,
            "idempotency_key": "p1-s12-continuation-start",
        },
    )
    assert continuation_response.status_code == 200
    candidate_draft_id = continuation_response.json()["data"]["candidate_draft_id"]

    candidate_detail = client.get(f"/api/v2/ai/candidate-drafts/{candidate_draft_id}")
    assert candidate_detail.status_code == 200
    selected_version_id = candidate_detail.json()["data"]["selected_version_id"]
    assert candidate_detail.json()["data"]["writing_task_id"] == writing_task_id
    assert candidate_detail.json()["data"]["content"]

    chapter_after_candidate = next(item for item in chapter_service.list_chapters(work_id) if item.id.value == chapter_id)
    assert chapter_after_candidate.content == original_content

    review_response = client.post(
        f"/api/v2/ai/reviews/candidate-drafts/{candidate_draft_id}",
        json={
            "user_instruction": "优先检查一致性与风险。",
            "caller_type": "user_action",
            "user_action": True,
            "idempotency_key": "p1-s12-candidate-review",
        },
    )
    assert review_response.status_code == 200
    review_payload = review_response.json()["data"]
    review_id = review_payload["review_id"]
    gate_id = review_payload["memory_gate_id"]
    assert review_payload["generated_suggestion_count"] >= 1

    review_detail = client.get(f"/api/v2/ai/reviews/{review_id}")
    assert review_detail.status_code == 200

    suggestions_response = client.get("/api/v2/ai/suggestions", params={"work_id": work_id, "chapter_id": chapter_id})
    assert suggestions_response.status_code == 200
    suggestions = suggestions_response.json()["data"]["items"]
    assert suggestions
    suggestion_id = suggestions[0]["suggestion_id"]

    accepted_suggestion = client.post(
        f"/api/v2/ai/suggestions/{suggestion_id}/accept",
        json={
            "caller_type": "user_action",
            "user_action": True,
            "user_id": "ui-user",
            "idempotency_key": "p1-s12-suggestion-accept",
        },
    )
    assert accepted_suggestion.status_code == 200

    conflicts_response = client.get("/api/v2/ai/conflicts", params={"candidate_draft_id": candidate_draft_id})
    assert conflicts_response.status_code == 200
    conflict_items = conflicts_response.json()["data"]["items"]
    assert conflict_items
    conflict_id = conflict_items[0]["record_id"]

    resolved_conflict = client.post(
        f"/api/v2/ai/conflicts/{conflict_id}/decide",
        json={
            "caller_type": "user_action",
            "user_action": True,
            "user_id": "ui-user",
            "decision": "resolved",
            "decision_note": "人工确认保留当前方案。",
            "idempotency_key": "p1-s12-conflict-resolve",
        },
    )
    assert resolved_conflict.status_code == 200

    gate_detail = client.get(f"/api/v2/ai/memory-gates/{gate_id}")
    assert gate_detail.status_code == 200
    gate_payload = gate_detail.json()["data"]
    gate_suggestions = gate_payload["suggestions"]
    assert gate_suggestions
    first_memory_suggestion_id = gate_suggestions[0]["id"]

    approve_response = client.post(
        f"/api/v2/ai/memory-gates/{gate_id}/suggestions/{first_memory_suggestion_id}/approve",
        json={
            "caller_type": "user_action",
            "user_action": True,
            "user_id": "ui-user",
            "idempotency_key": "p1-s12-memory-approve-1",
        },
    )
    assert approve_response.status_code == 200

    if len(gate_suggestions) > 1:
        second_memory_suggestion_id = gate_suggestions[1]["id"]
        edit_approve_response = client.post(
            f"/api/v2/ai/memory-gates/{gate_id}/suggestions/{second_memory_suggestion_id}/edit-approve",
            json={
                "caller_type": "user_action",
                "user_action": True,
                "user_id": "ui-user",
                "decision_note": "补充为正式摘要",
                "proposed_value_summary": "顾迟确认铜钥匙与父亲地图存在直接关联，作为后续航道线索保留。",
                "idempotency_key": "p1-s12-memory-edit-approve-1",
            },
        )
        assert edit_approve_response.status_code == 200

    apply_gate_response = client.post(
        f"/api/v2/ai/memory-gates/{gate_id}/apply",
        json={
            "caller_type": "user_action",
            "user_action": True,
            "user_id": "ui-user",
            "idempotency_key": "p1-s12-memory-apply",
        },
    )
    assert apply_gate_response.status_code == 200
    revision_ids = apply_gate_response.json()["data"]["revision_ids"]
    assert revision_ids

    accept_candidate = client.post(
        f"/api/v2/ai/candidate-drafts/{candidate_draft_id}/accept",
        json={
            "caller_type": "user_action",
            "user_action": True,
            "user_id": "ui-user",
            "idempotency_key": "p1-s12-candidate-accept",
        },
    )
    assert accept_candidate.status_code == 200

    apply_candidate = client.post(
        f"/api/v2/ai/candidate-drafts/{candidate_draft_id}/apply",
        json={
            "caller_type": "user_action",
            "user_action": True,
            "user_id": "ui-user",
            "candidate_version_id": selected_version_id,
            "expected_chapter_version": chapter_before.version,
            "idempotency_key": "p1-s12-candidate-apply",
        },
    )
    assert apply_candidate.status_code == 200
    assert apply_candidate.json()["data"]["status"] == "applied"

    chapter_after_apply = next(item for item in chapter_service.list_chapters(work_id) if item.id.value == chapter_id)
    assert chapter_after_apply.content != original_content
    assert chapter_after_apply.version == chapter_before.version + 1

    revision_detail = client.get(f"/api/v2/ai/memory-revisions/{revision_ids[0]}")
    assert revision_detail.status_code == 200
    assert revision_detail.json()["data"]["status"] == "applied"

    traces_response = client.get("/api/v2/ai/traces", params={"work_id": work_id})
    assert traces_response.status_code == 200
    trace_items = traces_response.json()["data"]["items"]
    assert trace_items
    trace_id = trace_items[0]["trace_id"]

    trace_steps = client.get(f"/api/v2/ai/traces/{trace_id}/steps")
    assert trace_steps.status_code == 200

    detail_forbidden = client.get(f"/api/v2/ai/traces/{trace_id}/detail-view", params={"detail": "true"})
    assert detail_forbidden.status_code == 403

    detail_allowed = client.get(
        f"/api/v2/ai/traces/{trace_id}/detail-view",
        params={"detail": "true", "developer_mode": "true"},
    )
    assert detail_allowed.status_code == 200
    tool_calls = detail_allowed.json()["data"]["tool_calls"]
    assert all("api_key" not in str(item) for item in tool_calls)


def test_p1_quick_trial_and_candidate_flow_keep_formal_content_isolated_until_apply(monkeypatch, tmp_path) -> None:
    client = _configure_runtime(monkeypatch, tmp_path)
    _save_ai_settings(client)
    work_id, chapter_id = _seed_work()
    chapter_service = dependencies.get_chapter_service()
    chapter_before = next(item for item in chapter_service.list_chapters(work_id) if item.id.value == chapter_id)
    original_content = chapter_before.content

    init_response = client.post("/api/v2/ai/initializations", json={"work_id": work_id})
    assert init_response.status_code == 200

    jobs_before_trial = client.get("/api/v2/ai/jobs", params={"work_id": work_id}).json()["data"]["items"]
    candidates_before_trial = client.get("/api/v2/ai/candidate-drafts", params={"work_id": work_id}).json()["data"]["items"]

    quick_trial = client.post(
        "/api/v2/ai/quick-trials",
        json={
            "model_role": "quick_trial_writer",
            "input_text": "试写灯塔门口的潮声。",
            "caller_type": "quick_trial",
            "idempotency_key": "p1-s12-quick-trial",
        },
    )
    assert quick_trial.status_code == 200
    assert quick_trial.json()["data"]["status"] == "succeeded"
    assert "job_id" not in quick_trial.json()["data"]
    assert "candidate_draft_id" not in quick_trial.json()["data"]

    jobs_after_trial = client.get("/api/v2/ai/jobs", params={"work_id": work_id}).json()["data"]["items"]
    candidates_after_trial = client.get("/api/v2/ai/candidate-drafts", params={"work_id": work_id}).json()["data"]["items"]
    assert len(jobs_after_trial) == len(jobs_before_trial)
    assert len(candidates_after_trial) == len(candidates_before_trial)

    candidate_response = client.post(
        "/api/v2/ai/continuations",
        json={
            "work_id": work_id,
            "chapter_id": chapter_id,
            "user_instruction": "继续写作",
            "caller_type": "user_action",
            "user_action": True,
            "idempotency_key": "p1-s12-quick-path-continuation",
        },
    )
    assert candidate_response.status_code == 200
    candidate_draft_id = candidate_response.json()["data"]["candidate_draft_id"]
    assert candidate_response.json()["data"]["status"] == "pending_review"

    chapter_after_candidate = next(item for item in chapter_service.list_chapters(work_id) if item.id.value == chapter_id)
    assert chapter_after_candidate.content == original_content
    detail_response = client.get(f"/api/v2/ai/candidate-drafts/{candidate_draft_id}")
    assert detail_response.status_code == 200
    assert detail_response.json()["data"]["content"]
