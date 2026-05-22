from __future__ import annotations

from fastapi.testclient import TestClient

from application.services.v1.chapter_service import ChapterService
from application.services.v1.work_service import WorkService
from domain.entities.ai.models import CandidateDraftVersion, CandidateDraftVersionStatus, WritingTask, WritingTaskStatus
from infrastructure.database.repositories import ChapterRepo, WorkRepo
from presentation.api import dependencies
from presentation.api.app import app


def _seed_initialized_work() -> tuple[str, str]:
    work_repo = WorkRepo()
    chapter_repo = ChapterRepo()
    work_service = WorkService(work_repo=work_repo, chapter_repo=chapter_repo)
    chapter_service = ChapterService(chapter_repo=chapter_repo, work_repo=work_repo)
    work = work_service.create_work("S5 API 作品", "作者")
    chapter = chapter_service.list_chapters(work.id)[0]
    chapter = chapter_service.update_chapter(
        chapter.id.value,
        title="第一章",
        content="顾迟在海边灯塔醒来，发现整个世界已不同。",
        expected_version=1,
    )
    dependencies.get_initialization_service().start_initialization(work.id, created_by="user_action")
    return work.id, chapter.id.value


def test_continuation_api_creates_candidate_and_candidate_api_controls_content_visibility() -> None:
    work_id, chapter_id = _seed_initialized_work()
    client = TestClient(app)

    start_response = client.post(
        "/api/v2/ai/continuations",
        json={
            "work_id": work_id,
            "chapter_id": chapter_id,
            "user_instruction": "继续写作",
        },
    )
    assert start_response.status_code == 200
    start_payload = start_response.json()
    candidate_draft_id = start_payload["data"]["candidate_draft_id"]
    assert candidate_draft_id.startswith("cd_")
    assert start_payload["data"]["job_id"].startswith("job_")

    list_response = client.get("/api/v2/ai/candidate-drafts", params={"work_id": work_id, "chapter_id": chapter_id})
    assert list_response.status_code == 200
    list_payload = list_response.json()
    assert list_payload["data"]["items"][0]["candidate_draft_id"] == candidate_draft_id
    assert "content" not in list_payload["data"]["items"][0]

    get_response = client.get(f"/api/v2/ai/candidate-drafts/{candidate_draft_id}")
    assert get_response.status_code == 200
    get_payload = get_response.json()
    assert get_payload["data"]["candidate_draft_id"] == candidate_draft_id
    assert get_payload["data"]["content"]


def test_continuation_api_returns_blocked_when_context_pack_is_blocked() -> None:
    work_repo = WorkRepo()
    chapter_repo = ChapterRepo()
    work_service = WorkService(work_repo=work_repo, chapter_repo=chapter_repo)
    chapter_service = ChapterService(chapter_repo=chapter_repo, work_repo=work_repo)
    work = work_service.create_work("S5 blocked API 作品", "作者")
    chapter = chapter_service.list_chapters(work.id)[0]
    chapter = chapter_service.update_chapter(chapter.id.value, title="第一章", content="未初始化正文。", expected_version=1)
    client = TestClient(app)

    response = client.post(
        "/api/v2/ai/continuations",
        json={
            "work_id": work.id,
            "chapter_id": chapter.id.value,
            "user_instruction": "继续写作",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["data"]["status"] == "blocked"
    assert payload["data"]["candidate_draft_id"] == ""
    assert payload["data"]["error_code"] == "context_pack_blocked"


def test_continuation_api_rejects_non_user_action_caller_type() -> None:
    work_id, chapter_id = _seed_initialized_work()
    client = TestClient(app)

    response = client.post(
        "/api/v2/ai/continuations",
        json={
            "work_id": work_id,
            "chapter_id": chapter_id,
            "user_instruction": "继续写作",
            "caller_type": "workflow",
        },
    )

    assert response.status_code == 403
    assert response.json()["error"]["error_code"] == "caller_type_not_allowed"


def test_candidate_draft_api_exposes_versions_and_supports_select_accept_apply_specific_version() -> None:
    work_id, chapter_id = _seed_initialized_work()
    client = TestClient(app)

    start_response = client.post(
        "/api/v2/ai/continuations",
        json={
            "work_id": work_id,
            "chapter_id": chapter_id,
            "user_instruction": "继续写作",
        },
    )
    assert start_response.status_code == 200
    candidate_draft_id = start_response.json()["data"]["candidate_draft_id"]

    candidate_repo = dependencies.get_candidate_draft_repository()
    draft = candidate_repo.get(candidate_draft_id)
    initial_versions = candidate_repo.list_versions(candidate_draft_id)
    assert len(initial_versions) == 1
    candidate_repo.save_version(
        CandidateDraftVersion(
            candidate_version_id="ver_api_2",
            candidate_draft_id=candidate_draft_id,
            work_id=work_id,
            chapter_id=chapter_id,
            agent_session_id="agent_session_rewriter",
            source_candidate_draft_id=candidate_draft_id,
            source_version_id=initial_versions[0].candidate_version_id,
            parent_version_id=initial_versions[0].candidate_version_id,
            version_no=2,
            status=CandidateDraftVersionStatus.GENERATED,
            content="v2 修订稿：顾迟在灯塔夹层里找到父亲留下的海图坐标。",
            content_summary="v2 修订稿摘要",
            word_count=2,
            writing_task_id=draft.writing_task_id,
            direction_plan_snapshot_id=draft.direction_plan_snapshot_id,
            source_context_pack_id=draft.source_context_pack_id,
            created_by="rewriter_agent",
            created_at="2026-05-21T00:10:00+00:00",
            updated_at="2026-05-21T00:10:00+00:00",
        )
    )
    candidate_repo.save(
        draft.model_copy(
            update={
                "latest_version_no": 2,
                "updated_at": "2026-05-21T00:10:00+00:00",
            }
        )
    )

    detail_response = client.get(f"/api/v2/ai/candidate-drafts/{candidate_draft_id}")
    assert detail_response.status_code == 200
    assert detail_response.json()["data"]["selected_version_id"]
    assert detail_response.json()["data"]["accepted_version_id"] == ""
    assert detail_response.json()["data"]["applied_version_id"] == ""

    versions_response = client.get(f"/api/v2/ai/candidate-drafts/{candidate_draft_id}/versions")
    assert versions_response.status_code == 200
    assert [item["candidate_version_id"] for item in versions_response.json()["data"]["items"]] == [
        initial_versions[0].candidate_version_id,
        "ver_api_2",
    ]

    select_response = client.post(
        f"/api/v2/ai/candidate-drafts/{candidate_draft_id}/versions/ver_api_2/select",
        json={
            "caller_type": "user_action",
            "user_action": True,
            "user_id": "ui-user",
        },
    )
    assert select_response.status_code == 200
    assert select_response.json()["data"]["selected_version_id"] == "ver_api_2"

    accept_response = client.post(
        f"/api/v2/ai/candidate-drafts/{candidate_draft_id}/accept",
        json={
            "caller_type": "user_action",
            "user_action": True,
            "user_id": "ui-user",
            "candidate_version_id": "ver_api_2",
        },
    )
    assert accept_response.status_code == 200
    assert accept_response.json()["data"]["accepted_version_id"] == "ver_api_2"
    assert accept_response.json()["data"]["applied_version_id"] == ""

    chapter_version = dependencies.get_chapter_service().list_chapters(work_id)[0].version
    apply_response = client.post(
        f"/api/v2/ai/candidate-drafts/{candidate_draft_id}/apply",
        json={
            "caller_type": "user_action",
            "user_action": True,
            "user_id": "ui-user",
            "candidate_version_id": "ver_api_2",
            "expected_chapter_version": chapter_version,
            "idempotency_key": "candidate-version-apply-1",
        },
    )
    assert apply_response.status_code == 200
    assert apply_response.json()["data"]["status"] == "applied"

    applied_detail = client.get(f"/api/v2/ai/candidate-drafts/{candidate_draft_id}")
    assert applied_detail.status_code == 200
    assert applied_detail.json()["data"]["selected_version_id"] == "ver_api_2"
    assert applied_detail.json()["data"]["accepted_version_id"] == "ver_api_2"
    assert applied_detail.json()["data"]["applied_version_id"] == "ver_api_2"


def test_candidate_draft_api_supports_version_detail_diff_and_rewrite_flow() -> None:
    work_id, chapter_id = _seed_initialized_work()
    client = TestClient(app)

    start_response = client.post(
        "/api/v2/ai/continuations",
        json={
            "work_id": work_id,
            "chapter_id": chapter_id,
            "user_instruction": "继续写作",
        },
    )
    assert start_response.status_code == 200
    candidate_draft_id = start_response.json()["data"]["candidate_draft_id"]

    candidate_repo = dependencies.get_candidate_draft_repository()
    draft = candidate_repo.get(candidate_draft_id)
    ver_1 = candidate_repo.list_versions(candidate_draft_id)[0]

    review_response = client.post(
        f"/api/v2/ai/reviews/candidate-drafts/{candidate_draft_id}",
        json={"user_instruction": ""},
    )
    assert review_response.status_code == 200
    review_id = review_response.json()["data"]["review_id"]

    rewrite_response = client.post(
        f"/api/v2/ai/candidate-drafts/{candidate_draft_id}/rewrites",
        json={
            "caller_type": "user_action",
            "user_action": True,
            "user_id": "ui-user",
            "source_version_id": ver_1.candidate_version_id,
            "trigger_type": "review_based",
            "review_report_id": review_id,
            "user_instruction": "让父亲留下的地图更早出现。",
            "idempotency_key": "rewrite-api-1",
        },
    )
    assert rewrite_response.status_code == 200
    ver_2_id = rewrite_response.json()["data"]["target_version"]["candidate_version_id"]

    version_detail = client.get(f"/api/v2/ai/candidate-drafts/{candidate_draft_id}/versions/{ver_2_id}")
    assert version_detail.status_code == 200
    assert version_detail.json()["data"]["candidate_version_id"] == ver_2_id


def test_candidate_apply_with_direction_plan_warning_still_succeeds_and_records_conflict() -> None:
    work_id, chapter_id = _seed_initialized_work()
    client = TestClient(app)

    start_response = client.post(
        "/api/v2/ai/continuations",
        json={
            "work_id": work_id,
            "chapter_id": chapter_id,
            "user_instruction": "继续写作",
        },
    )
    assert start_response.status_code == 200
    candidate_draft_id = start_response.json()["data"]["candidate_draft_id"]

    candidate_repo = dependencies.get_candidate_draft_repository()
    draft = candidate_repo.get(candidate_draft_id)
    dependencies.get_direction_plan_repository().save_writing_task(
        WritingTask(
            writing_task_id="wt_api_conflict_1",
            work_id=work_id,
            chapter_id=chapter_id,
            target_chapter_id=chapter_id,
            status=WritingTaskStatus.READY,
            writing_goal="继续推进灯塔章节",
            must_include=["钟声"],
            must_not_include=["直接揭晓终局"],
            required_beats=["发现旧标记"],
            created_by="planner_agent",
            created_at="2026-05-21T00:00:00+00:00",
            updated_at="2026-05-21T00:00:00+00:00",
        )
    )
    draft = candidate_repo.save(
        draft.model_copy(update={"writing_task_id": "wt_api_conflict_1"})
    )
    version = candidate_repo.list_versions(candidate_draft_id)[0]
    candidate_repo.save_version(
        version.model_copy(
            update={
                "content": f"{version.content} 不要提前揭示父亲真相，现在直接揭晓终局。",
                "content_summary": "直接揭晓终局",
            }
        )
    )

    chapter_version = dependencies.get_chapter_service().list_chapters(work_id)[0].version
    apply_response = client.post(
        f"/api/v2/ai/candidate-drafts/{candidate_draft_id}/apply",
        json={
            "caller_type": "user_action",
            "user_action": True,
            "user_id": "ui-user",
            "candidate_version_id": version.candidate_version_id,
            "expected_chapter_version": chapter_version,
            "idempotency_key": "candidate-direction-plan-warning-1",
        },
    )
    assert apply_response.status_code == 200
    assert apply_response.json()["data"]["status"] == "applied"

    conflicts_response = client.get("/api/v2/ai/conflicts", params={"candidate_draft_id": candidate_draft_id})
    assert conflicts_response.status_code == 200
    items = conflicts_response.json()["data"]["items"]
    assert any(item["conflict_type"] == "direction_plan_conflict" for item in items)


def test_continuation_start_triggers_async_conflict_detection_record() -> None:
    work_id, chapter_id = _seed_initialized_work()
    client = TestClient(app)

    start_response = client.post(
        "/api/v2/ai/continuations",
        json={
            "work_id": work_id,
            "chapter_id": chapter_id,
            "user_instruction": "继续写作",
        },
    )
    assert start_response.status_code == 200
    candidate_draft_id = start_response.json()["data"]["candidate_draft_id"]

    conflicts_response = client.get("/api/v2/ai/conflicts", params={"candidate_draft_id": candidate_draft_id})
    assert conflicts_response.status_code == 200
    items = conflicts_response.json()["data"]["items"]
    assert any(item["conflict_type"] == "candidate_version_conflict" for item in items)
