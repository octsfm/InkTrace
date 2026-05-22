from __future__ import annotations

from fastapi.testclient import TestClient

from application.services.v1.chapter_service import ChapterService
from application.services.v1.work_service import WorkService
from infrastructure.database.repositories import ChapterRepo, WorkRepo
from presentation.api.app import app


def _seed_review_generated_memory_gate() -> tuple[str, str, str]:
    from presentation.api import dependencies

    work_repo = WorkRepo()
    chapter_repo = ChapterRepo()
    work_service = WorkService(work_repo=work_repo, chapter_repo=chapter_repo)
    chapter_service = ChapterService(chapter_repo=chapter_repo, work_repo=work_repo)
    work = work_service.create_work("S9 API Work", "Author")
    chapter = chapter_service.list_chapters(work.id)[0]
    chapter = chapter_service.update_chapter(
        chapter.id.value,
        title="第一章 海雾",
        content="顾迟在海雾里重新检查父亲留下的地图碎片。",
        expected_version=1,
    )
    dependencies.get_initialization_service().start_initialization(work.id, created_by="user_action")
    continuation = dependencies.get_continuation_workflow().start_continuation(
        work.id,
        chapter.id.value,
        user_instruction="继续写作",
        created_by="user_action",
    )
    review = dependencies.get_ai_review_service().review_candidate_draft(
        continuation.candidate_draft_id,
        created_by="user_action",
        idempotency_key="s9-api-review-seed",
    )
    dependencies.get_memory_review_gate_service().generate_from_review(review.review_id)
    return work.id, chapter.id.value, continuation.candidate_draft_id


def test_memory_gate_api_lists_decides_applies_and_rolls_back() -> None:
    client = TestClient(app)
    work_id, chapter_id, _ = _seed_review_generated_memory_gate()

    listed = client.get("/api/v2/ai/memory-gates", params={"work_id": work_id, "chapter_id": chapter_id})
    assert listed.status_code == 200
    items = listed.json()["data"]["items"]
    assert items
    gate_id = items[0]["gate_id"]
    suggestion_ids = list(items[0]["suggestion_ids"])
    assert len(suggestion_ids) >= 2

    detail = client.get(f"/api/v2/ai/memory-gates/{gate_id}")
    assert detail.status_code == 200
    assert detail.json()["data"]["gate_id"] == gate_id
    assert detail.json()["data"]["state"] == "waiting_for_user"

    bad_caller = client.post(
        f"/api/v2/ai/memory-gates/{gate_id}/suggestions/{suggestion_ids[0]}/approve",
        json={"caller_type": "workflow_compat", "user_action": True, "user_id": "ui-user", "idempotency_key": "s9-api-bad"},
    )
    assert bad_caller.status_code == 403
    assert bad_caller.json()["error"]["error_code"] == "caller_type_forbidden"

    deferred = client.post(
        f"/api/v2/ai/memory-gates/{gate_id}/suggestions/{suggestion_ids[0]}/defer",
        json={
            "caller_type": "user_action",
            "user_action": True,
            "user_id": "ui-user",
            "decision_note": "晚点再看",
            "idempotency_key": "s9-api-defer-1",
        },
    )
    assert deferred.status_code == 200
    assert deferred.json()["data"]["state"] == "waiting_for_user"

    approved = client.post(
        f"/api/v2/ai/memory-gates/{gate_id}/suggestions/{suggestion_ids[0]}/approve",
        json={"caller_type": "user_action", "user_action": True, "user_id": "ui-user", "idempotency_key": "s9-api-approve-1"},
    )
    assert approved.status_code == 200
    assert approved.json()["data"]["state"] in {"partially_approved", "approved"}

    edit_approved = client.post(
        f"/api/v2/ai/memory-gates/{gate_id}/suggestions/{suggestion_ids[1]}/edit-approve",
        json={
            "caller_type": "user_action",
            "user_action": True,
            "user_id": "ui-user",
            "decision_note": "补充正式记忆摘要",
            "proposed_value_summary": "顾迟已确认地图指向废弃航道，并标记为父亲遗留的重要航线线索。",
            "idempotency_key": "s9-api-edit-approve-1",
        },
    )
    assert edit_approved.status_code == 200
    assert edit_approved.json()["data"]["state"] == "approved"

    apply_missing_key = client.post(
        f"/api/v2/ai/memory-gates/{gate_id}/apply",
        json={"caller_type": "user_action", "user_action": True, "user_id": "ui-user", "idempotency_key": ""},
    )
    assert apply_missing_key.status_code == 400
    assert apply_missing_key.json()["error"]["error_code"] == "idempotency_key_required"

    applied = client.post(
        f"/api/v2/ai/memory-gates/{gate_id}/apply",
        json={"caller_type": "user_action", "user_action": True, "user_id": "ui-user", "idempotency_key": "s9-api-apply-1"},
    )
    assert applied.status_code == 200
    assert applied.json()["data"]["gate"]["state"] == "applied"
    revision_ids = applied.json()["data"]["revision_ids"]
    assert revision_ids

    revision_detail = client.get(f"/api/v2/ai/memory-revisions/{revision_ids[0]}")
    assert revision_detail.status_code == 200
    assert revision_detail.json()["data"]["revision_id"] == revision_ids[0]
    assert revision_detail.json()["data"]["status"] == "applied"

    rollback = client.post(
        f"/api/v2/ai/memory-revisions/{revision_ids[0]}/rollback",
        json={
            "caller_type": "user_action",
            "user_action": True,
            "user_id": "ui-user",
            "decision_note": "回滚到应用前摘要",
            "idempotency_key": "s9-api-rollback-1",
        },
    )
    assert rollback.status_code == 200
    assert rollback.json()["data"]["revision_type"] == "rollback"
    assert rollback.json()["data"]["status"] == "applied"


def test_memory_gate_api_rejects_apply_when_no_approved_suggestions_exist() -> None:
    client = TestClient(app)
    work_id, chapter_id, _ = _seed_review_generated_memory_gate()

    listed = client.get("/api/v2/ai/memory-gates", params={"work_id": work_id, "chapter_id": chapter_id})
    gate = listed.json()["data"]["items"][0]
    gate_id = gate["gate_id"]
    suggestion_id = gate["suggestion_ids"][0]

    rejected = client.post(
        f"/api/v2/ai/memory-gates/{gate_id}/suggestions/{suggestion_id}/reject",
        json={
            "caller_type": "user_action",
            "user_action": True,
            "user_id": "ui-user",
            "decision_note": "这条不成立",
            "idempotency_key": "s9-api-reject-1",
        },
    )
    assert rejected.status_code == 200

    blocked = client.post(
        f"/api/v2/ai/memory-gates/{gate_id}/apply",
        json={"caller_type": "user_action", "user_action": True, "user_id": "ui-user", "idempotency_key": "s9-api-apply-blocked"},
    )
    assert blocked.status_code == 409
    assert blocked.json()["error"]["error_code"] == "memory_revision_apply_blocked"


def test_memory_gate_api_rejecting_one_suggestion_keeps_gate_waiting_for_other_items() -> None:
    client = TestClient(app)
    work_id, chapter_id, _ = _seed_review_generated_memory_gate()

    listed = client.get("/api/v2/ai/memory-gates", params={"work_id": work_id, "chapter_id": chapter_id})
    gate = listed.json()["data"]["items"][0]
    gate_id = gate["gate_id"]
    suggestion_id = gate["suggestion_ids"][0]

    rejected = client.post(
        f"/api/v2/ai/memory-gates/{gate_id}/suggestions/{suggestion_id}/reject",
        json={
            "caller_type": "user_action",
            "user_action": True,
            "user_id": "ui-user",
            "decision_note": "先拒绝一条",
            "idempotency_key": "s9-api-reject-partial-1",
        },
    )
    assert rejected.status_code == 200
    assert rejected.json()["data"]["state"] == "waiting_for_user"


def test_memory_gate_api_rejects_reused_idempotency_key() -> None:
    client = TestClient(app)
    work_id, chapter_id, _ = _seed_review_generated_memory_gate()

    listed = client.get("/api/v2/ai/memory-gates", params={"work_id": work_id, "chapter_id": chapter_id})
    gate = listed.json()["data"]["items"][0]
    gate_id = gate["gate_id"]
    suggestion_id = gate["suggestion_ids"][0]
    payload = {
        "caller_type": "user_action",
        "user_action": True,
        "user_id": "ui-user",
        "idempotency_key": "s9-api-approve-idempotent-1",
    }

    first = client.post(
        f"/api/v2/ai/memory-gates/{gate_id}/suggestions/{suggestion_id}/approve",
        json=payload,
    )
    assert first.status_code == 200

    duplicated = client.post(
        f"/api/v2/ai/memory-gates/{gate_id}/suggestions/{suggestion_id}/approve",
        json=payload,
    )
    assert duplicated.status_code == 409
    assert duplicated.json()["error"]["error_code"] == "idempotency_key_conflict"
