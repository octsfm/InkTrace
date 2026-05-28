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
    work = work_service.create_work("S11a PlotArc API 作品", "作者")
    chapter = chapter_service.list_chapters(work.id)[0]
    chapter_service.update_chapter(chapter.id.value, title="第一章 海雾", content="顾迟在灯塔与海雾之间寻找父亲线索。", expected_version=1)
    dependencies.get_initialization_service().start_initialization(work.id, created_by="user_action")
    return work.id, chapter.id.value


def test_plot_arcs_api_supports_list_detail_and_status() -> None:
    work_id, chapter_id = _seed_initialized_work()
    client = TestClient(app)

    listed = client.get("/api/v2/ai/plot-arcs", params={"work_id": work_id})
    assert listed.status_code == 200
    items = listed.json()["data"]["items"]
    assert items
    master_arc = next(item for item in items if item["arc_type"] == "master_arc")

    detail = client.get(f"/api/v2/ai/plot-arcs/{master_arc['arc_id']}", params={"work_id": work_id})
    assert detail.status_code == 200
    assert detail.json()["data"]["arc_id"] == master_arc["arc_id"]

    status = client.get("/api/v2/ai/plot-arcs/status", params={"work_id": work_id, "chapter_id": chapter_id})
    assert status.status_code == 200
    payload = status.json()["data"]
    assert "master_arc" in payload
    assert "volume_arc" in payload
    assert "sequence_arc" in payload
