from __future__ import annotations

from fastapi.testclient import TestClient

from application.services.v1.chapter_service import ChapterService
from application.services.v1.work_service import WorkService
from infrastructure.database.repositories import ChapterRepo, WorkRepo
from presentation.api import dependencies
from presentation.api.app import app


def _seed_initialized_work() -> str:
    work_repo = WorkRepo()
    chapter_repo = ChapterRepo()
    work_service = WorkService(work_repo=work_repo, chapter_repo=chapter_repo)
    chapter_service = ChapterService(chapter_repo=chapter_repo, work_repo=work_repo)
    work = work_service.create_work("S4 上下文作品", "作者")
    chapter = chapter_service.list_chapters(work.id)[0]
    chapter_service.update_chapter(chapter.id.value, title="第一章", content="顾迟在海边灯塔醒来，发现整个世界已不同。", expected_version=1)
    init_service = dependencies.get_initialization_service()
    init_service.start_initialization(work.id, created_by="user_action")
    return work.id


def test_context_pack_api_builds_and_returns_snapshot() -> None:
    work_id = _seed_initialized_work()
    client = TestClient(app)

    build_response = client.post(
        "/api/v2/ai/context-packs",
        json={
            "work_id": work_id,
            "user_instruction": "继续写作",
            "max_context_tokens": 2000,
        },
    )
    assert build_response.status_code == 200
    build_payload = build_response.json()
    cp_id = build_payload["data"]["context_pack_id"]
    assert cp_id.startswith("cp_")
    assert build_payload["data"]["status"] in {"ready", "degraded"}
    assert "full_text" not in build_payload["data"]
    assert "prompt" not in build_payload["data"]

    get_response = client.get(f"/api/v2/ai/context-packs/{cp_id}")
    assert get_response.status_code == 200
    get_payload = get_response.json()
    assert get_payload["data"]["context_pack_id"] == cp_id
    assert get_payload["data"]["estimated_token_count"] > 0

    latest_response = client.get(f"/api/v2/ai/context-packs/works/{work_id}/latest")
    assert latest_response.status_code == 200
    latest_payload = latest_response.json()
    assert latest_payload["data"]["context_pack_id"] == cp_id

    readiness_response = client.get(f"/api/v2/ai/context-packs/works/{work_id}/readiness")
    assert readiness_response.status_code == 200
    readiness_payload = readiness_response.json()
    assert readiness_payload["data"]["status"] in {"ready", "degraded"}
    assert "estimated_token_count" in readiness_payload["data"]


def test_context_pack_api_returns_blocked_when_not_initialized() -> None:
    work_repo = WorkRepo()
    chapter_repo = ChapterRepo()
    work_service = WorkService(work_repo=work_repo, chapter_repo=chapter_repo)
    work = work_service.create_work("未初始化作品 S4", "作者")
    client = TestClient(app)

    readiness_response = client.get(f"/api/v2/ai/context-packs/works/{work.id}/readiness")
    assert readiness_response.status_code == 200
    readiness_payload = readiness_response.json()
    assert readiness_payload["data"]["status"] == "blocked"
    assert "initialization_not_completed" in readiness_payload["data"]["blocked_reason"]


def test_context_pack_api_does_not_expose_full_chapter_text() -> None:
    work_id = _seed_initialized_work()
    client = TestClient(app)

    build_response = client.post(
        "/api/v2/ai/context-packs",
        json={"work_id": work_id, "user_instruction": "续写下一段", "max_context_tokens": 500},
    )
    assert build_response.status_code == 200
    payload = build_response.json()

    for item in payload["data"]["context_items"]:
        text = item.get("content_text", "") or ""
        assert len(text) <= 200, f"content_text too long: {len(text)} chars"
