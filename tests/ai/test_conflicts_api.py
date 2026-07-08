from __future__ import annotations

from fastapi.testclient import TestClient

from presentation.api import dependencies
from presentation.api.app import app
from tests.ai.test_candidate_draft_api import _seed_initialized_work


def test_conflicts_api_lists_detail_and_decide_with_gate_rules() -> None:
    work_id, chapter_id = _seed_initialized_work()
    client = TestClient(app)

    start_response = client.post(
        "/api/v2/ai/continuations",
        json={
            "work_id": work_id,
            "chapter_id": chapter_id,
            "user_instruction": "继续写作",
            "caller_type": "user_action",
            "user_action": True,
            "idempotency_key": "conflicts-api-start-1",
        },
    )
    assert start_response.status_code == 200
    draft_id = start_response.json()["data"]["candidate_draft_id"]
    candidate_repo = dependencies.get_candidate_draft_repository()
    version = candidate_repo.list_versions(draft_id)[0]
    chapter_version = dependencies.get_chapter_service().list_chapters(work_id)[0].version
    result = dependencies.get_conflict_guard_service().precheck_apply_conflicts(
        candidate_draft_id=draft_id,
        candidate_version_id=version.candidate_version_id,
        expected_chapter_version=chapter_version + 1,
        request_id="req_conflict_api",
        trace_id="trace_conflict_api",
    )
    record_id = result.record_refs[0]

    listed = client.get("/api/v2/ai/conflicts", params={"candidate_draft_id": draft_id})
    assert listed.status_code == 200
    assert any(item["record_id"] == record_id for item in listed.json()["data"]["items"])

    detail = client.get(f"/api/v2/ai/conflicts/{record_id}")
    assert detail.status_code == 200
    assert detail.json()["data"]["record_id"] == record_id

    missing_key = client.post(
        f"/api/v2/ai/conflicts/{record_id}/decide",
        json={"caller_type": "user_action", "user_action": True, "user_id": "ui-user", "decision": "resolved", "idempotency_key": ""},
    )
    assert missing_key.status_code == 400
    assert missing_key.json()["error"]["error_code"] == "idempotency_key_required"

    decided = client.post(
        f"/api/v2/ai/conflicts/{record_id}/decide",
        json={
            "caller_type": "user_action",
            "user_action": True,
            "user_id": "ui-user",
            "decision": "resolved",
            "decision_note": "已人工处理。",
            "idempotency_key": "conflict-api-resolve-1",
        },
    )
    assert decided.status_code == 200
    assert decided.json()["data"]["status"] == "resolved"
