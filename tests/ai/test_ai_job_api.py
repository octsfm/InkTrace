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
