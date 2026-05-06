from fastapi.testclient import TestClient

from infrastructure.database.session import get_database_path, initialize_database
from presentation.api.app import app


def _prepare_database(monkeypatch, tmp_path, filename: str) -> None:
    db_path = tmp_path / "runtime" / filename
    monkeypatch.setenv("INKTRACE_DB_PATH", str(db_path))
    get_database_path.cache_clear()
    initialize_database()


def _create_work(client: TestClient) -> tuple[str, str]:
    response = client.post("/api/v1/works", json={"title": "Foreshadow Work", "author": ""})
    assert response.status_code == 200
    work_id = response.json()["id"]
    chapter = client.get(f"/api/v1/works/{work_id}/chapters").json()["items"][0]
    return work_id, chapter["id"]


def test_v1_foreshadows_router_crud_and_status_filter(monkeypatch, tmp_path):
    _prepare_database(monkeypatch, tmp_path, "foreshadows-router-crud.db")
    client = TestClient(app)
    work_id, chapter_id = _create_work(client)

    open_item = client.post(
        f"/api/v1/works/{work_id}/foreshadows",
        json={
            "title": "未回收伏笔",
            "description": "描述",
            "introduced_chapter_id": chapter_id,
        },
    )
    resolved_item = client.post(
        f"/api/v1/works/{work_id}/foreshadows",
        json={
            "title": "已回收伏笔",
            "status": "resolved",
            "introduced_chapter_id": chapter_id,
            "resolved_chapter_id": chapter_id,
        },
    )
    assert open_item.status_code == 200
    assert resolved_item.status_code == 200
    assert open_item.json()["status"] == "open"
    assert resolved_item.json()["status"] == "resolved"

    open_list = client.get(f"/api/v1/works/{work_id}/foreshadows")
    assert open_list.status_code == 200
    assert [item["id"] for item in open_list.json()["items"]] == [open_item.json()["id"]]

    resolved_list = client.get(f"/api/v1/works/{work_id}/foreshadows?status=resolved")
    assert resolved_list.status_code == 200
    assert [item["id"] for item in resolved_list.json()["items"]] == [resolved_item.json()["id"]]

    updated = client.put(
        f"/api/v1/foreshadows/{open_item.json()['id']}",
        json={"status": "resolved", "resolved_chapter_id": chapter_id, "expected_version": 1},
    )
    assert updated.status_code == 200
    assert updated.json()["status"] == "resolved"
    assert updated.json()["resolved_chapter_id"] == chapter_id
    assert updated.json()["version"] == 2

    deleted = client.delete(f"/api/v1/foreshadows/{resolved_item.json()['id']}")
    assert deleted.status_code == 200
    assert deleted.json() == {"ok": True, "id": resolved_item.json()["id"]}
    get_database_path.cache_clear()


def test_v1_foreshadows_router_invalid_status(monkeypatch, tmp_path):
    _prepare_database(monkeypatch, tmp_path, "foreshadows-router-invalid.db")
    client = TestClient(app)
    work_id, _ = _create_work(client)

    created = client.post(
        f"/api/v1/works/{work_id}/foreshadows",
        json={"title": "非法状态", "status": "closed"},
    )
    assert created.status_code == 400
    assert created.json() == {"detail": "invalid_input"}

    listed = client.get(f"/api/v1/works/{work_id}/foreshadows?status=closed")
    assert listed.status_code == 400
    assert listed.json() == {"detail": "invalid_input"}
    get_database_path.cache_clear()


def test_v1_foreshadows_router_version_conflict_returns_409(monkeypatch, tmp_path):
    _prepare_database(monkeypatch, tmp_path, "foreshadows-router-conflict.db")
    client = TestClient(app)
    work_id, _ = _create_work(client)
    item = client.post(f"/api/v1/works/{work_id}/foreshadows", json={"title": "伏笔"}).json()
    assert client.put(
        f"/api/v1/foreshadows/{item['id']}",
        json={"title": "远端", "expected_version": 1},
    ).status_code == 200

    conflicted = client.put(
        f"/api/v1/foreshadows/{item['id']}",
        json={"title": "本地", "expected_version": 1},
    )

    assert conflicted.status_code == 409
    assert conflicted.json() == {
        "detail": "asset_version_conflict",
        "server_version": 2,
        "resource_type": "foreshadow",
        "resource_id": item["id"],
    }
    get_database_path.cache_clear()
