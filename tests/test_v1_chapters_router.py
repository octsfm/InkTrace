from fastapi.testclient import TestClient

from infrastructure.database.session import get_database_path, initialize_database
from presentation.api.app import app


def _prepare_database(monkeypatch, tmp_path, filename: str) -> None:
    db_path = tmp_path / "runtime" / filename
    monkeypatch.setenv("INKTRACE_DB_PATH", str(db_path))
    get_database_path.cache_clear()
    initialize_database()


def _create_work(client: TestClient) -> str:
    response = client.post("/api/v1/works", json={"title": "章节路由作品", "author": "作者甲"})
    assert response.status_code == 200
    return response.json()["id"]


def test_v1_chapters_router_save_returns_new_version(monkeypatch, tmp_path):
    _prepare_database(monkeypatch, tmp_path, "chapters-router-save.db")
    client = TestClient(app)
    work_id = _create_work(client)
    first = client.get(f"/api/v1/works/{work_id}/chapters").json()["items"][0]

    saved = client.put(
        f"/api/v1/chapters/{first['id']}",
        json={"title": "起点", "content": "正文一", "expected_version": first["version"]},
    )

    assert saved.status_code == 200
    payload = saved.json()
    assert payload["title"] == "起点"
    assert payload["content"] == "正文一"
    assert payload["version"] == first["version"] + 1
    assert payload["word_count"] == 3

    get_database_path.cache_clear()


def test_v1_chapters_router_version_conflict_returns_409_template(monkeypatch, tmp_path):
    _prepare_database(monkeypatch, tmp_path, "chapters-router-conflict.db")
    client = TestClient(app)
    work_id = _create_work(client)
    first = client.get(f"/api/v1/works/{work_id}/chapters").json()["items"][0]

    saved = client.put(
        f"/api/v1/chapters/{first['id']}",
        json={"content": "远端正文", "expected_version": 1},
    )
    assert saved.status_code == 200

    conflicted = client.put(
        f"/api/v1/chapters/{first['id']}",
        json={"content": "本地正文", "expected_version": 1},
    )

    assert conflicted.status_code == 409
    assert conflicted.json() == {
        "detail": "version_conflict",
        "server_version": 2,
        "resource_type": "chapter",
        "resource_id": first["id"],
    }

    get_database_path.cache_clear()


def test_v1_chapters_router_reorder_rejects_invalid_mapping(monkeypatch, tmp_path):
    _prepare_database(monkeypatch, tmp_path, "chapters-router-reorder-invalid.db")
    client = TestClient(app)
    work_id = _create_work(client)
    first = client.get(f"/api/v1/works/{work_id}/chapters").json()["items"][0]
    second = client.post(f"/api/v1/works/{work_id}/chapters", json={"title": "第二章"}).json()

    invalid = client.put(
        f"/api/v1/works/{work_id}/chapters/reorder",
        json={"items": [{"id": first["id"], "order_index": 1}, {"id": second["id"], "order_index": 3}]},
    )

    assert invalid.status_code == 400
    assert invalid.json() == {"detail": "invalid_input"}

    get_database_path.cache_clear()


def test_v1_chapters_router_delete_returns_next_focus(monkeypatch, tmp_path):
    _prepare_database(monkeypatch, tmp_path, "chapters-router-delete.db")
    client = TestClient(app)
    work_id = _create_work(client)
    first = client.get(f"/api/v1/works/{work_id}/chapters").json()["items"][0]
    second = client.post(f"/api/v1/works/{work_id}/chapters", json={"title": "第二章"}).json()

    deleted = client.delete(f"/api/v1/chapters/{first['id']}")

    assert deleted.status_code == 200
    assert deleted.json() == {"ok": True, "id": first["id"], "next_chapter_id": second["id"]}

    chapters = client.get(f"/api/v1/works/{work_id}/chapters").json()["items"]
    assert [item["order_index"] for item in chapters] == [1]
    assert [item["chapter_number"] for item in chapters] == [1]

    get_database_path.cache_clear()
