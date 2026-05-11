from __future__ import annotations

from fastapi.testclient import TestClient

from application.services.v1.chapter_service import ChapterService
from application.services.v1.work_service import WorkService
from infrastructure.database.repositories import ChapterRepo, WorkRepo
from presentation.api.app import app


def _seed_work_with_chapter() -> str:
    work_repo = WorkRepo()
    chapter_repo = ChapterRepo()
    work_service = WorkService(work_repo=work_repo, chapter_repo=chapter_repo)
    chapter_service = ChapterService(chapter_repo=chapter_repo, work_repo=work_repo)
    work = work_service.create_work("API 初始化作品", "作者")
    chapter = chapter_service.list_chapters(work.id)[0]
    chapter_service.update_chapter(chapter.id.value, title="第一章", content="顾迟在海边灯塔醒来。", expected_version=1)
    return work.id


def test_initialization_api_returns_job_id_and_latest_snapshots() -> None:
    work_id = _seed_work_with_chapter()
    client = TestClient(app)

    start_response = client.post("/api/v2/ai/initializations", json={"work_id": work_id})
    assert start_response.status_code == 200
    start_payload = start_response.json()
    initialization_id = start_payload["data"]["initialization_id"]
    job_id = start_payload["data"]["job_id"]

    get_response = client.get(f"/api/v2/ai/initializations/{initialization_id}")
    latest_response = client.get(f"/api/v2/ai/works/{work_id}/initialization/latest")
    memory_response = client.get(f"/api/v2/ai/works/{work_id}/story-memory/latest")
    state_response = client.get(f"/api/v2/ai/works/{work_id}/story-state/latest")

    assert job_id.startswith("job_")
    assert get_response.status_code == 200
    get_payload = get_response.json()
    assert get_payload["data"]["initialization_id"] == initialization_id
    assert "payload" not in get_payload["data"]

    assert latest_response.status_code == 200
    latest_payload = latest_response.json()
    assert latest_payload["data"]["job_id"] == job_id

    assert memory_response.status_code == 200
    memory_payload = memory_response.json()
    assert memory_payload["data"]["work_id"] == work_id
    assert "chapter_contents" not in memory_payload["data"]

    assert state_response.status_code == 200
    state_payload = state_response.json()
    assert state_payload["data"]["work_id"] == work_id
    assert "full_text" not in state_payload["data"]
