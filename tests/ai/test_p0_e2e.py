from __future__ import annotations

from fastapi.testclient import TestClient

from infrastructure.database.session import get_database_path
from presentation.api import dependencies
from presentation.api.app import app


def _clear_p0_singletons() -> None:
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


def _configure_runtime(monkeypatch, tmp_path) -> TestClient:
    monkeypatch.setenv("INKTRACE_DB_PATH", str(tmp_path / "runtime" / "inktrace.db"))
    monkeypatch.setenv("INKTRACE_AI_SETTINGS_SECRET", "test-secret")
    _clear_p0_singletons()
    return TestClient(app)


def _seed_work_with_two_chapters() -> tuple[str, str]:
    work_service = dependencies.get_work_service()
    chapter_service = dependencies.get_chapter_service()
    work = work_service.create_work("P0 E2E 作品", "作者")
    first = chapter_service.list_chapters(work.id)[0]
    chapter_service.update_chapter(
        first.id.value,
        title="第一章",
        content="顾迟在海边灯塔醒来，发现潮声像旧日誓言，风里还留着昨夜的盐味。",
        expected_version=1,
    )
    chapter_service.create_chapter(work.id, title="第二章")
    return work.id, first.id.value


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
                "writer": {"provider_name": "fake", "model_name": "fake-writer"},
                "quick_trial_writer": {"provider_name": "fake", "model_name": "fake-chat"},
            },
        },
    )
    assert response.status_code == 200


def test_ai_settings_provider_test_reports_success_and_failure(monkeypatch, tmp_path) -> None:
    client = _configure_runtime(monkeypatch, tmp_path)
    _save_ai_settings(client)

    success = client.post("/api/v2/ai/settings/providers/fake/test", json={"model_name": "fake-chat"})
    assert success.status_code == 200
    assert success.json()["data"]["test_status"] == "ok"

    failed = client.post("/api/v2/ai/settings/providers/fake/test", json={"model_name": "missing-model"})
    assert failed.status_code == 400
    assert failed.json()["error"]["error_code"] == "model_not_supported"

    settings = client.get("/api/v2/ai/settings")
    assert settings.status_code == 200
    provider = settings.json()["data"]["provider_configs"][0]
    assert provider["last_test_status"] == "failed"
    assert provider["last_test_error_code"] == "model_not_supported"
    assert "api_key" not in provider


def test_p0_minimal_loop_runs_end_to_end_via_api(monkeypatch, tmp_path) -> None:
    client = _configure_runtime(monkeypatch, tmp_path)
    _save_ai_settings(client)
    work_id, chapter_id = _seed_work_with_two_chapters()
    chapter_service = dependencies.get_chapter_service()
    chapter_before = next(item for item in chapter_service.list_chapters(work_id) if item.id.value == chapter_id)
    original_content = chapter_before.content

    init_response = client.post("/api/v2/ai/initializations", json={"work_id": work_id})
    assert init_response.status_code == 200
    init_payload = init_response.json()["data"]
    job_id = init_payload["job_id"]

    latest_init = client.get(f"/api/v2/ai/works/{work_id}/initialization/latest")
    assert latest_init.status_code == 200
    latest_init_data = latest_init.json()["data"]
    assert latest_init_data["status"] == "completed"
    assert latest_init_data["completion_status"] == "partial_success"
    assert latest_init_data["analyzed_chapter_count"] == 1
    assert latest_init_data["empty_chapter_count"] == 1

    memory_response = client.get(f"/api/v2/ai/works/{work_id}/story-memory/latest")
    state_response = client.get(f"/api/v2/ai/works/{work_id}/story-state/latest")
    assert memory_response.status_code == 200
    assert state_response.status_code == 200
    assert memory_response.json()["data"]["global_summary"]
    assert state_response.json()["data"]["current_position_summary"]

    job_response = client.get(f"/api/v2/ai/jobs/{job_id}")
    assert job_response.status_code == 200
    assert job_response.json()["data"]["status"] == "completed"

    readiness = client.get(
        f"/api/v2/ai/context-packs/works/{work_id}/readiness",
        params={"chapter_id": chapter_id},
    )
    assert readiness.status_code == 200
    assert readiness.json()["data"]["status"] == "degraded"

    build_context = client.post(
        "/api/v2/ai/context-packs",
        json={"work_id": work_id, "chapter_id": chapter_id},
    )
    assert build_context.status_code == 200
    context_pack_id = build_context.json()["data"]["context_pack_id"]
    assert build_context.json()["data"]["status"] == "degraded"

    continuation_1 = client.post(
        "/api/v2/ai/continuations",
        json={"work_id": work_id, "chapter_id": chapter_id, "user_instruction": "继续写下去，推进灯塔谜团。"},
    )
    assert continuation_1.status_code == 200
    continuation_data_1 = continuation_1.json()["data"]
    candidate_1 = continuation_data_1["candidate_draft_id"]
    assert continuation_data_1["status"] == "degraded_completed"

    candidate_list = client.get("/api/v2/ai/candidate-drafts", params={"work_id": work_id, "chapter_id": chapter_id})
    assert candidate_list.status_code == 200
    first_item = candidate_list.json()["data"]["items"][0]
    assert first_item["candidate_draft_id"] == candidate_1
    assert first_item["source_context_pack_id"].startswith("cp_")
    assert context_pack_id.startswith("cp_")
    assert "content" not in first_item

    candidate_detail = client.get(f"/api/v2/ai/candidate-drafts/{candidate_1}")
    assert candidate_detail.status_code == 200
    candidate_content = candidate_detail.json()["data"]["content"]
    assert candidate_content

    review_response = client.post(
        f"/api/v2/ai/reviews/candidate-drafts/{candidate_1}",
        json={"user_instruction": "只看一致性，不要自动应用。"},
    )
    assert review_response.status_code == 200
    review_data = review_response.json()["data"]
    assert review_data["status"] in {"succeeded", "failed"}
    chapter_after_review = next(item for item in chapter_service.list_chapters(work_id) if item.id.value == chapter_id)
    assert chapter_after_review.content == original_content

    accept_response = client.post(
        f"/api/v2/ai/candidate-drafts/{candidate_1}/accept",
        json={"user_action": True, "user_id": "u1"},
    )
    assert accept_response.status_code == 200
    assert accept_response.json()["data"]["status"] == "accepted"
    chapter_after_accept = next(item for item in chapter_service.list_chapters(work_id) if item.id.value == chapter_id)
    assert chapter_after_accept.content == original_content

    continuation_2 = client.post(
        "/api/v2/ai/continuations",
        json={"work_id": work_id, "chapter_id": chapter_id, "user_instruction": "换一个方向继续写。"},
    )
    assert continuation_2.status_code == 200
    candidate_2 = continuation_2.json()["data"]["candidate_draft_id"]

    reject_response = client.post(
        f"/api/v2/ai/candidate-drafts/{candidate_2}/reject",
        json={"user_action": True, "user_id": "u1", "reason": "保留旧方案"},
    )
    assert reject_response.status_code == 200
    assert reject_response.json()["data"]["status"] == "rejected"
    chapter_after_reject = next(item for item in chapter_service.list_chapters(work_id) if item.id.value == chapter_id)
    assert chapter_after_reject.content == original_content

    rejected_apply = client.post(
        f"/api/v2/ai/candidate-drafts/{candidate_2}/apply",
        json={"user_action": True, "user_id": "u1", "expected_chapter_version": chapter_before.version},
    )
    assert rejected_apply.status_code == 400
    assert rejected_apply.json()["error"]["error_code"] == "candidate_already_rejected"

    jobs_before_trial = client.get("/api/v2/ai/jobs", params={"work_id": work_id}).json()["data"]["items"]
    candidates_before_trial = client.get("/api/v2/ai/candidate-drafts", params={"work_id": work_id}).json()["data"]["items"]

    quick_trial = client.post(
        "/api/v2/ai/quick-trials",
        json={"model_role": "quick_trial_writer", "input_text": "试写一小段灯塔门口的风声。"},
    )
    assert quick_trial.status_code == 200
    quick_trial_data = quick_trial.json()["data"]
    assert quick_trial_data["status"] == "succeeded"
    assert quick_trial_data["output_text"]
    assert "job_id" not in quick_trial_data
    assert "candidate_draft_id" not in quick_trial_data

    jobs_after_trial = client.get("/api/v2/ai/jobs", params={"work_id": work_id}).json()["data"]["items"]
    candidates_after_trial = client.get("/api/v2/ai/candidate-drafts", params={"work_id": work_id}).json()["data"]["items"]
    assert len(jobs_after_trial) == len(jobs_before_trial)
    assert len(candidates_after_trial) == len(candidates_before_trial)

    apply_response = client.post(
        f"/api/v2/ai/candidate-drafts/{candidate_1}/apply",
        json={
            "user_action": True,
            "user_id": "u1",
            "expected_chapter_version": chapter_before.version,
        },
    )
    assert apply_response.status_code == 200
    assert apply_response.json()["data"]["status"] == "applied"

    chapter_after_apply = next(item for item in chapter_service.list_chapters(work_id) if item.id.value == chapter_id)
    assert chapter_after_apply.content != original_content
    assert candidate_content in chapter_after_apply.content
    assert chapter_after_apply.version == chapter_before.version + 1

    latest_after_apply = client.get(f"/api/v2/ai/works/{work_id}/initialization/latest")
    assert latest_after_apply.status_code == 200
    assert latest_after_apply.json()["data"]["status"] == "stale"
