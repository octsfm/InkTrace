from __future__ import annotations

from fastapi.testclient import TestClient

from application.services.v1.chapter_service import ChapterService
from application.services.v1.work_service import WorkService
from infrastructure.database.repositories import ChapterRepo, WorkRepo
from presentation.api import dependencies
from presentation.api.app import app
from tests.ai.support import save_fake_ai_settings


def _seed_initialized_candidate() -> tuple[str, str, str]:
    client = TestClient(app)
    save_fake_ai_settings(client)
    work_repo = WorkRepo()
    chapter_repo = ChapterRepo()
    work_service = WorkService(work_repo=work_repo, chapter_repo=chapter_repo)
    chapter_service = ChapterService(chapter_repo=chapter_repo, work_repo=work_repo)
    work = work_service.create_work("P1-S7 API 作品", "作者")
    chapter = chapter_service.list_chapters(work.id)[0]
    chapter_service.update_chapter(
        chapter.id.value,
        title="第一章 灯塔",
        content="顾迟在灯塔中醒来，尚未发现父亲留下的地图。",
        expected_version=1,
    )
    dependencies.get_initialization_service().start_initialization(work.id, created_by="user_action")
    continuation = dependencies.get_continuation_workflow().start_continuation(
        work.id,
        chapter.id.value,
        user_instruction="继续写作",
        created_by="user_action",
    )
    candidate_draft_id = continuation.candidate_draft_id
    review = dependencies.get_ai_review_service().review_candidate_draft(candidate_draft_id, created_by="user_action")
    dependencies.get_ai_suggestion_service().generate_from_review(review.review_id)
    return work.id, chapter.id.value, candidate_draft_id


def test_ai_suggestion_api_lists_details_and_decisions_follow_gate_rules() -> None:
    work_id, chapter_id, candidate_draft_id = _seed_initialized_candidate()
    client = TestClient(app)

    listed = client.get("/api/v2/ai/suggestions", params={"work_id": work_id, "chapter_id": chapter_id})
    assert listed.status_code == 200
    items = listed.json()["data"]["items"]
    assert items
    suggestion_id = items[0]["suggestion_id"]

    detail = client.get(f"/api/v2/ai/suggestions/{suggestion_id}")
    assert detail.status_code == 200
    assert detail.json()["data"]["suggestion_id"] == suggestion_id

    bad_caller = client.post(
        f"/api/v2/ai/suggestions/{suggestion_id}/accept",
        json={"caller_type": "workflow_compat", "user_action": True, "user_id": "ui-user", "idempotency_key": "s7-acc-1"},
    )
    assert bad_caller.status_code == 403

    accepted = client.post(
        f"/api/v2/ai/suggestions/{suggestion_id}/accept",
        json={"caller_type": "user_action", "user_action": True, "user_id": "ui-user", "idempotency_key": "s7-acc-2"},
    )
    assert accepted.status_code == 200
    assert accepted.json()["data"]["status"] == "accepted"

    dismissed = client.post(
        f"/api/v2/ai/suggestions/{suggestion_id}/dismiss",
        json={"caller_type": "user_action", "user_action": True, "user_id": "ui-user", "decision_note": "忽略", "idempotency_key": "s7-dis-1"},
    )
    assert dismissed.status_code in {200, 400}
    assert candidate_draft_id


def test_ai_suggestion_api_converts_rewrite_suggestion_and_blocks_risk_warning() -> None:
    work_id, chapter_id, _ = _seed_initialized_candidate()
    client = TestClient(app)
    items = client.get("/api/v2/ai/suggestions", params={"work_id": work_id, "chapter_id": chapter_id}).json()["data"]["items"]
    rewrite_item = next(item for item in items if item["suggestion_type"] == "rewrite_suggestion")
    risk_item = next(item for item in items if item["suggestion_type"] == "risk_warning")

    converted = client.post(
        f"/api/v2/ai/suggestions/{rewrite_item['suggestion_id']}/convert",
        json={"caller_type": "user_action", "user_action": True, "user_id": "ui-user", "idempotency_key": "s7-convert-ok"},
    )
    assert converted.status_code == 200
    assert converted.json()["data"]["status"] == "converted"
    assert converted.json()["data"]["action"]["action_payload_ref"].startswith("rewrite_request:")

    blocked = client.post(
        f"/api/v2/ai/suggestions/{risk_item['suggestion_id']}/convert",
        json={"caller_type": "user_action", "user_action": True, "user_id": "ui-user", "idempotency_key": "s7-convert-risk"},
    )
    assert blocked.status_code == 400
    assert blocked.json()["error"]["error_code"] == "suggestion_convert_forbidden"
