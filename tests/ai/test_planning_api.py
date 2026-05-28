from __future__ import annotations

from fastapi.testclient import TestClient

from application.services.v1.chapter_service import ChapterService
from application.services.v1.work_service import WorkService
from infrastructure.database.repositories import ChapterRepo, WorkRepo
from presentation.api import dependencies
from presentation.api.app import app


def _seed_initialized_work() -> tuple[str, str]:
    work_repo = WorkRepo()
    chapter_repo = ChapterRepo()
    work_service = WorkService(work_repo=work_repo, chapter_repo=chapter_repo)
    chapter_service = ChapterService(chapter_repo=chapter_repo, work_repo=work_repo)
    work = work_service.create_work("P1-S5 API 作品", "作者")
    chapter = chapter_service.list_chapters(work.id)[0]
    chapter = chapter_service.update_chapter(
        chapter.id.value,
        title="第一章 灯塔雾夜",
        content="顾迟在灯塔听见钟声，旧航海图边角沾着海盐。他怀疑父亲留下的线索指向海雾深处。",
        expected_version=1,
    )
    dependencies.get_initialization_service().start_initialization(work.id, created_by="user_action")
    return work.id, chapter.id.value


def test_planning_api_generates_direction_and_plan_then_confirms_to_writing_task() -> None:
    work_id, chapter_id = _seed_initialized_work()
    client = TestClient(app)

    proposal_response = client.post(
        "/api/v2/ai/directions",
        json={
            "work_id": work_id,
            "chapter_id": chapter_id,
            "user_instruction": "继续推进灯塔谜团。",
            "caller_type": "user_action",
            "idempotency_key": "idem-direction-generate-1",
        },
    )
    assert proposal_response.status_code == 200
    proposal_payload = proposal_response.json()["data"]
    proposal_id = proposal_payload["direction_proposal_id"]
    option_id = proposal_payload["options"][0]["option_id"]
    assert proposal_payload["status"] == "waiting_for_selection"
    assert len(proposal_payload["options"]) >= 3

    listed_proposals = client.get("/api/v2/ai/directions", params={"work_id": work_id, "chapter_id": chapter_id})
    assert listed_proposals.status_code == 200
    assert listed_proposals.json()["data"]["items"][0]["direction_proposal_id"] == proposal_id

    proposal_detail = client.get(f"/api/v2/ai/directions/{proposal_id}")
    assert proposal_detail.status_code == 200
    assert proposal_detail.json()["data"]["direction_proposal_id"] == proposal_id

    selection_response = client.post(
        f"/api/v2/ai/directions/{proposal_id}/select",
        json={
            "caller_type": "user_action",
            "user_action": True,
            "user_id": "ui-user",
            "selected_option_id": option_id,
            "idempotency_key": "idem-direction-select-1",
        },
    )
    assert selection_response.status_code == 200
    selection_payload = selection_response.json()["data"]
    assert selection_payload["selection"]["selection_type"] == "direct_select"
    assert selection_payload["proposal"]["status"] == "selected"

    plan_response = client.post(
        "/api/v2/ai/chapter-plans",
        json={
            "work_id": work_id,
            "chapter_id": chapter_id,
            "direction_proposal_id": proposal_id,
            "caller_type": "user_action",
            "idempotency_key": "idem-plan-generate-1",
        },
    )
    assert plan_response.status_code == 200
    plan_payload = plan_response.json()["data"]
    plan_id = plan_payload["chapter_plan_id"]
    assert plan_payload["status"] == "waiting_for_confirmation"
    assert len(plan_payload["plan_items"]) >= 3

    listed_plans = client.get("/api/v2/ai/chapter-plans", params={"work_id": work_id, "chapter_id": chapter_id})
    assert listed_plans.status_code == 200
    assert listed_plans.json()["data"]["items"][0]["chapter_plan_id"] == plan_id

    plan_detail = client.get(f"/api/v2/ai/chapter-plans/{plan_id}")
    assert plan_detail.status_code == 200
    assert plan_detail.json()["data"]["chapter_plan_id"] == plan_id

    confirm_response = client.post(
        f"/api/v2/ai/chapter-plans/{plan_id}/confirm",
        json={
            "caller_type": "user_action",
            "user_action": True,
            "user_id": "ui-user",
            "idempotency_key": "idem-plan-confirm-1",
        },
    )
    assert confirm_response.status_code == 200
    confirm_payload = confirm_response.json()["data"]
    writing_task_id = confirm_payload["writing_task"]["writing_task_id"]
    assert confirm_payload["confirmation"]["confirmation_type"] == "direct_confirm"
    assert confirm_payload["plan"]["status"] == "confirmed"
    assert confirm_payload["writing_task"]["status"] == "ready"

    listed_tasks = client.get("/api/v2/ai/writing-tasks", params={"work_id": work_id, "chapter_id": chapter_id})
    assert listed_tasks.status_code == 200
    assert listed_tasks.json()["data"]["items"][0]["writing_task_id"] == writing_task_id

    task_detail = client.get(f"/api/v2/ai/writing-tasks/{writing_task_id}")
    assert task_detail.status_code == 200
    assert task_detail.json()["data"]["writing_task_id"] == writing_task_id


def test_planning_gate_api_requires_user_action_and_idempotency_key() -> None:
    work_id, chapter_id = _seed_initialized_work()
    client = TestClient(app)

    proposal_response = client.post(
        "/api/v2/ai/directions",
        json={
            "work_id": work_id,
            "chapter_id": chapter_id,
            "caller_type": "user_action",
            "idempotency_key": "idem-direction-generate-2",
        },
    )
    assert proposal_response.status_code == 200
    proposal_id = proposal_response.json()["data"]["direction_proposal_id"]
    option_id = proposal_response.json()["data"]["options"][0]["option_id"]

    no_idempotency = client.post(
        f"/api/v2/ai/directions/{proposal_id}/select",
        json={
            "caller_type": "user_action",
            "user_action": True,
            "user_id": "ui-user",
            "selected_option_id": option_id,
            "idempotency_key": "",
        },
    )
    assert no_idempotency.status_code == 400
    assert no_idempotency.json()["error"]["error_code"] == "idempotency_key_required"

    wrong_caller = client.post(
        f"/api/v2/ai/directions/{proposal_id}/select",
        json={
            "caller_type": "workflow_compat",
            "user_action": True,
            "user_id": "ui-user",
            "selected_option_id": option_id,
            "idempotency_key": "idem-direction-select-2",
        },
    )
    assert wrong_caller.status_code == 403
    assert wrong_caller.json()["error"]["error_code"] == "caller_type_forbidden"

    no_user_action = client.post(
        f"/api/v2/ai/directions/{proposal_id}/select",
        json={
            "caller_type": "user_action",
            "user_action": False,
            "user_id": "ui-user",
            "selected_option_id": option_id,
            "idempotency_key": "idem-direction-select-3",
        },
    )
    assert no_user_action.status_code == 403
    assert no_user_action.json()["error"]["error_code"] == "action_not_allowed"


def test_planning_api_rejects_chapter_plan_and_returns_confirmation_payload() -> None:
    work_id, chapter_id = _seed_initialized_work()
    client = TestClient(app)

    proposal = client.post(
        "/api/v2/ai/directions",
        json={
            "work_id": work_id,
            "chapter_id": chapter_id,
            "user_instruction": "继续推进灯塔谜团。",
            "caller_type": "user_action",
            "idempotency_key": "idem-direction-generate-reject-1",
        },
    ).json()["data"]
    proposal_id = proposal["direction_proposal_id"]
    option_id = proposal["options"][0]["option_id"]

    selected = client.post(
        f"/api/v2/ai/directions/{proposal_id}/select",
        json={
            "caller_type": "user_action",
            "user_action": True,
            "user_id": "ui-user",
            "selected_option_id": option_id,
            "idempotency_key": "idem-direction-select-reject-1",
        },
    )
    assert selected.status_code == 200

    plan = client.post(
        "/api/v2/ai/chapter-plans",
        json={
            "work_id": work_id,
            "chapter_id": chapter_id,
            "direction_proposal_id": proposal_id,
            "caller_type": "user_action",
            "idempotency_key": "idem-plan-generate-reject-1",
        },
    ).json()["data"]
    plan_id = plan["chapter_plan_id"]

    rejected = client.post(
        f"/api/v2/ai/chapter-plans/{plan_id}/reject",
        json={
            "caller_type": "user_action",
            "user_action": True,
            "user_id": "ui-user",
            "user_edit_notes": "这版节奏太快，退回重做",
            "idempotency_key": "idem-plan-reject-1",
        },
    )
    assert rejected.status_code == 200
    payload = rejected.json()["data"]
    assert payload["confirmation"]["confirmation_type"] == "reject"
    assert payload["plan"]["chapter_plan_id"] == plan_id
