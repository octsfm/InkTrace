from __future__ import annotations

from fastapi.testclient import TestClient

from application.services.v1.chapter_service import ChapterService
from application.services.v1.work_service import WorkService
from infrastructure.database.repositories import ChapterRepo, WorkRepo
from presentation.api.app import app


def _seed_work() -> tuple[str, str]:
    work_repo = WorkRepo()
    chapter_repo = ChapterRepo()
    work_service = WorkService(work_repo=work_repo, chapter_repo=chapter_repo)
    chapter_service = ChapterService(chapter_repo=chapter_repo, work_repo=work_repo)
    work = work_service.create_work("S11a Session API 作品", "作者")
    chapter = chapter_service.list_chapters(work.id)[0]
    return work.id, chapter.id.value


def test_agent_sessions_api_supports_create_list_detail_pause_resume_cancel() -> None:
    work_id, chapter_id = _seed_work()
    client = TestClient(app)

    created = client.post(
        "/api/v2/ai/sessions",
        json={
            "work_id": work_id,
            "chapter_id": chapter_id,
            "workflow_type": "continuation",
            "user_instruction": "启动会话",
            "caller_type": "user_action",
            "user_action": True,
            "idempotency_key": "session-create-1",
        },
    )
    assert created.status_code == 200
    session_id = created.json()["data"]["session_id"]
    assert created.json()["data"]["status"] == "running"

    listed = client.get("/api/v2/ai/sessions", params={"work_id": work_id})
    assert listed.status_code == 200
    assert any(item["session_id"] == session_id for item in listed.json()["data"]["items"])

    detail = client.get(f"/api/v2/ai/sessions/{session_id}")
    assert detail.status_code == 200
    assert detail.json()["data"]["session_id"] == session_id

    paused = client.post(
        f"/api/v2/ai/sessions/{session_id}/pause",
        json={"caller_type": "user_action", "user_action": True, "idempotency_key": "session-pause-1", "reason": "manual_pause"},
    )
    assert paused.status_code == 200
    assert paused.json()["data"]["status"] == "paused"

    resumed = client.post(
        f"/api/v2/ai/sessions/{session_id}/resume",
        json={"caller_type": "user_action", "user_action": True, "idempotency_key": "session-resume-1"},
    )
    assert resumed.status_code == 200
    assert resumed.json()["data"]["status"] == "running"

    cancelled = client.post(
        f"/api/v2/ai/sessions/{session_id}/cancel",
        json={"caller_type": "user_action", "user_action": True, "idempotency_key": "session-cancel-1", "reason": "manual_cancel"},
    )
    assert cancelled.status_code == 200
    assert cancelled.json()["data"]["status"] == "cancelled"


def test_agent_sessions_api_requires_gate_fields() -> None:
    work_id, chapter_id = _seed_work()
    client = TestClient(app)

    wrong_caller = client.post(
        "/api/v2/ai/sessions",
        json={
            "work_id": work_id,
            "chapter_id": chapter_id,
            "workflow_type": "continuation",
            "user_instruction": "启动会话",
            "caller_type": "workflow_compat",
            "user_action": True,
            "idempotency_key": "session-create-bad",
        },
    )
    assert wrong_caller.status_code == 403
    assert wrong_caller.json()["error"]["error_code"] == "caller_type_forbidden"

    missing_key = client.post(
        "/api/v2/ai/sessions",
        json={
            "work_id": work_id,
            "chapter_id": chapter_id,
            "workflow_type": "continuation",
            "user_instruction": "启动会话",
            "caller_type": "user_action",
            "user_action": True,
            "idempotency_key": "",
        },
    )
    assert missing_key.status_code == 400
    assert missing_key.json()["error"]["error_code"] == "idempotency_key_required"
