from fastapi.testclient import TestClient

from infrastructure.database.repositories import ChapterRepo
from infrastructure.database.session import get_database_path, initialize_database
from presentation.api.app import app


def _prepare_database(monkeypatch, tmp_path, filename: str) -> None:
    db_path = tmp_path / "runtime" / filename
    monkeypatch.setenv("INKTRACE_DB_PATH", str(db_path))
    get_database_path.cache_clear()
    initialize_database()


def test_v1_works_router_create_returns_work_and_creates_first_chapter(monkeypatch, tmp_path):
    _prepare_database(monkeypatch, tmp_path, "works-router-create.db")
    client = TestClient(app)

    created = client.post("/api/v1/works", json={"title": "路由作品", "author": "作者甲"})

    assert created.status_code == 200
    payload = created.json()
    assert payload["id"]
    assert payload["title"] == "路由作品"
    assert payload["author"] == "作者甲"
    assert payload["current_word_count"] == 0

    chapters = ChapterRepo().list_by_work(payload["id"])
    assert len(chapters) == 1
    assert chapters[0].title == ""
    assert chapters[0].content == ""
    assert chapters[0].order_index == 1
    assert chapters[0].version == 1

    get_database_path.cache_clear()


def test_v1_works_router_delete_then_get_returns_work_not_found(monkeypatch, tmp_path):
    _prepare_database(monkeypatch, tmp_path, "works-router-delete.db")
    client = TestClient(app)

    created = client.post("/api/v1/works", json={"title": "待删除作品", "author": "作者乙"})
    assert created.status_code == 200
    work_id = created.json()["id"]

    deleted = client.delete(f"/api/v1/works/{work_id}")
    assert deleted.status_code == 200
    assert deleted.json() == {"ok": True, "id": work_id}

    fetched = client.get(f"/api/v1/works/{work_id}")
    assert fetched.status_code == 404
    assert fetched.json() == {"detail": "work_not_found"}

    get_database_path.cache_clear()


def test_v1_works_router_update_and_list_use_response_schema(monkeypatch, tmp_path):
    _prepare_database(monkeypatch, tmp_path, "works-router-list.db")
    client = TestClient(app)

    created = client.post("/api/v1/works", json={"title": "原作品", "author": "作者丙"})
    assert created.status_code == 200
    work_id = created.json()["id"]

    updated = client.put(f"/api/v1/works/{work_id}", json={"title": "新作品", "author": "作者丁"})
    assert updated.status_code == 200
    assert updated.json()["title"] == "新作品"
    assert updated.json()["author"] == "作者丁"

    listed = client.get("/api/v1/works")
    assert listed.status_code == 200
    payload = listed.json()
    assert payload["total"] == 1
    assert payload["items"][0]["id"] == work_id
    assert set(payload["items"][0].keys()) == {
        "id",
        "title",
        "author",
        "current_word_count",
        "created_at",
        "updated_at",
    }

    get_database_path.cache_clear()
