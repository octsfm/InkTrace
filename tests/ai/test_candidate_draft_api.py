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
