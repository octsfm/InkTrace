from __future__ import annotations

from fastapi.testclient import TestClient

from application.services.v1.chapter_service import ChapterService
from application.services.v1.work_service import WorkService
from application.services.v1.service_factory import build_writing_asset_service
from infrastructure.database.repositories import ChapterRepo, WorkRepo
from presentation.api import dependencies
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
    assert state_payload["data"]["current_character_states"] == [
        {
            "character_name": "顾迟",
            "current_location": "海边灯塔",
            "current_status": "出现在本章",
            "recent_actions": [],
            "relationships": [],
            "confidence": 0.9,
        }
    ]
    assert "full_text" not in state_payload["data"]


def test_latest_initialization_returns_not_started_for_work_without_history() -> None:
    work_id = _seed_work_with_chapter()
    client = TestClient(app)

    response = client.get(f"/api/v2/ai/works/{work_id}/initialization/latest")

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload == {
        "work_id": work_id,
        "status": "not_started",
        "analyzed_chapter_count": 0,
        "total_confirmed_chapter_count": 0,
        "empty_chapter_count": 0,
        "failed_chapter_count": 0,
        "stale": False,
    }
    assert "chapter_contents" not in payload
    assert "full_text" not in payload


def test_latest_initialization_returns_work_not_found_for_unknown_work() -> None:
    client = TestClient(app)

    response = client.get("/api/v2/ai/works/missing-work/initialization/latest")

    assert response.status_code == 404
    assert response.json()["error"]["error_code"] == "work_not_found"


def test_initialization_uses_imported_formal_outline_content_text_without_overwriting_it() -> None:
    work_id = _seed_work_with_chapter()
    assets = build_writing_asset_service()
    imported_outline = "第一卷：孔凡圣与宋成从东南亚逃亡，随后进入修仙世界。"
    saved = assets.save_work_outline(
        work_id,
        content_text=imported_outline,
        content_tree_json=[],
        expected_version=1,
    )
    client = TestClient(app)

    response = client.post("/api/v2/ai/initializations", json={"work_id": work_id})

    assert response.status_code == 200
    result = dependencies.get_initialization_service().get_latest_initialization(work_id).outline_analysis
    assert result is not None
    assert result.outline_empty is False
    assert result.important_characters == ["孔凡圣", "宋成"]
    persisted = assets.get_work_outline(work_id)
    assert persisted.content_text == imported_outline
    assert persisted.version == saved.version
