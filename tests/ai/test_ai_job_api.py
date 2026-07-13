from __future__ import annotations

from fastapi.testclient import TestClient

from presentation.api import dependencies
from presentation.api.app import app


def test_ai_job_api_gets_lists_and_cancels_job() -> None:
    service = dependencies.get_ai_job_service()
    job = service.create_job(
        job_type="continuation",
        work_id="work-api",
        chapter_id="chapter-1",
        steps=[{"step_type": "build_context_pack", "step_name": "Build Context Pack"}],
        payload={"user_instruction": "secret should not leak"},
    )

    client = TestClient(app)

    get_response = client.get(f"/api/v2/ai/jobs/{job.job_id}")
    list_response = client.get("/api/v2/ai/jobs", params={"work_id": "work-api"})
    cancel_response = client.post(f"/api/v2/ai/jobs/{job.job_id}/cancel", json={"reason": "user_cancelled"})
    steps_response = client.get(f"/api/v2/ai/jobs/{job.job_id}/steps")

    assert get_response.status_code == 200
    get_payload = get_response.json()
    assert get_payload["status"] == "ok"
    assert get_payload["data"]["job_id"] == job.job_id
    assert "payload" not in get_payload["data"]

    assert list_response.status_code == 200
    list_payload = list_response.json()
    assert list_payload["data"]["items"][0]["job_id"] == job.job_id
    assert "payload" not in list_payload["data"]["items"][0]

    assert cancel_response.status_code == 200
    cancel_payload = cancel_response.json()
    assert cancel_payload["data"]["status"] == "cancelled"

    assert steps_response.status_code == 200
    steps_payload = steps_response.json()
    assert steps_payload["data"]["steps"][0]["step_name"] == "Build Context Pack"
    assert steps_payload["data"]["steps"][0]["can_skip"] is False


def test_ai_job_api_supports_user_controlled_pause_resume_and_retry() -> None:
    service = dependencies.get_ai_job_service()
    job = service.create_job(
        job_type="initialization",
        work_id="work-job-controls",
        steps=[{"step_type": "analyze", "step_name": "Analyze"}],
    )
    service.start_job(job.job_id)
    client = TestClient(app)
    action = {
        "caller_type": "user_action",
        "user_action": True,
        "user_id": "local-author",
        "idempotency_key": "job-control-1",
        "reason": "user_requested",
    }

    paused = client.post(f"/api/v2/ai/jobs/{job.job_id}/pause", json=action)
    assert paused.status_code == 200
    assert paused.json()["data"]["status"] == "paused"

    resumed = client.post(
        f"/api/v2/ai/jobs/{job.job_id}/resume",
        json={**action, "idempotency_key": "job-control-2"},
    )
    assert resumed.status_code == 200
    assert resumed.json()["data"]["status"] == "running"

    step = service.get_job_steps(job.job_id)[0]
    service.mark_step_running(job.job_id, step.step_id)
    service.mark_step_failed(job.job_id, step.step_id, error_code="provider_failed", error_message="safe")
    service.mark_job_failed(job.job_id, error_code="provider_failed", error_message="safe")

    retried_step = client.post(
        f"/api/v2/ai/jobs/{job.job_id}/steps/{step.step_id}/retry",
        json={**action, "idempotency_key": "job-control-3"},
    )
    assert retried_step.status_code == 200
    assert retried_step.json()["data"]["status"] == "pending"

    retried_job = client.post(
        f"/api/v2/ai/jobs/{job.job_id}/retry",
        json={**action, "idempotency_key": "job-control-4"},
    )
    assert retried_job.status_code == 200
    assert retried_job.json()["data"]["status"] == "queued"


def test_ai_job_control_rejects_non_user_caller() -> None:
    service = dependencies.get_ai_job_service()
    job = service.create_job(job_type="initialization", work_id="work-job-denied", steps=[])
    service.start_job(job.job_id)
    response = TestClient(app).post(
        f"/api/v2/ai/jobs/{job.job_id}/pause",
        json={
            "caller_type": "agent",
            "user_action": False,
            "user_id": "",
            "idempotency_key": "job-control-denied",
            "reason": "agent_requested",
        },
    )
    assert response.status_code == 403
    assert response.json()["error"]["error_code"] == "caller_type_forbidden"
