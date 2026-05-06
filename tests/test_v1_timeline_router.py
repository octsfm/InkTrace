from fastapi.testclient import TestClient

from infrastructure.database.session import get_database_path, initialize_database
from presentation.api.app import app


def _prepare_database(monkeypatch, tmp_path, filename: str) -> None:
    db_path = tmp_path / "runtime" / filename
    monkeypatch.setenv("INKTRACE_DB_PATH", str(db_path))
    get_database_path.cache_clear()
    initialize_database()


def _create_work(client: TestClient) -> tuple[str, str]:
    response = client.post("/api/v1/works", json={"title": "Timeline Work", "author": ""})
    assert response.status_code == 200
    work_id = response.json()["id"]
    chapter = client.get(f"/api/v1/works/{work_id}/chapters").json()["items"][0]
    return work_id, chapter["id"]


def test_v1_timeline_router_crud_and_delete(monkeypatch, tmp_path):
    _prepare_database(monkeypatch, tmp_path, "timeline-router-crud.db")
    client = TestClient(app)
    work_id, chapter_id = _create_work(client)

    first = client.post(
        f"/api/v1/works/{work_id}/timeline-events",
        json={"title": "事件一", "description": "描述", "chapter_id": chapter_id},
    )
    second = client.post(f"/api/v1/works/{work_id}/timeline-events", json={"title": "事件二"})
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["order_index"] == 1
    assert second.json()["order_index"] == 2

    listed = client.get(f"/api/v1/works/{work_id}/timeline-events")
    assert [item["id"] for item in listed.json()["items"]] == [first.json()["id"], second.json()["id"]]

    updated = client.put(
        f"/api/v1/timeline-events/{first.json()['id']}",
        json={"title": "事件一更新", "chapter_id": None, "expected_version": 1},
    )
    assert updated.status_code == 200
    assert updated.json()["title"] == "事件一更新"
    assert updated.json()["chapter_id"] is None
    assert updated.json()["version"] == 2

    deleted = client.delete(f"/api/v1/timeline-events/{second.json()['id']}")
    assert deleted.status_code == 200
    assert deleted.json() == {"ok": True, "id": second.json()["id"]}
    assert client.get(f"/api/v1/works/{work_id}/timeline-events").json()["total"] == 1
    get_database_path.cache_clear()


def test_v1_timeline_router_reorder_and_invalid_mapping(monkeypatch, tmp_path):
    _prepare_database(monkeypatch, tmp_path, "timeline-router-reorder.db")
    client = TestClient(app)
    work_id, _ = _create_work(client)
    first = client.post(f"/api/v1/works/{work_id}/timeline-events", json={"title": "事件一"}).json()
    second = client.post(f"/api/v1/works/{work_id}/timeline-events", json={"title": "事件二"}).json()

    reordered = client.put(
        f"/api/v1/works/{work_id}/timeline-events/reorder",
        json={"items": [{"id": second["id"], "order_index": 1}, {"id": first["id"], "order_index": 2}]},
    )
    assert reordered.status_code == 200
    assert [item["id"] for item in reordered.json()["items"]] == [second["id"], first["id"]]

    invalid = client.put(
        f"/api/v1/works/{work_id}/timeline-events/reorder",
        json={"items": [{"id": first["id"], "order_index": 1}]},
    )
    assert invalid.status_code == 400
    assert invalid.json() == {"detail": "invalid_input"}
    get_database_path.cache_clear()


def test_v1_timeline_router_version_conflict_returns_409(monkeypatch, tmp_path):
    _prepare_database(monkeypatch, tmp_path, "timeline-router-conflict.db")
    client = TestClient(app)
    work_id, _ = _create_work(client)
    event = client.post(f"/api/v1/works/{work_id}/timeline-events", json={"title": "事件"}).json()
    assert client.put(
        f"/api/v1/timeline-events/{event['id']}",
        json={"title": "远端", "expected_version": 1},
    ).status_code == 200

    conflicted = client.put(
        f"/api/v1/timeline-events/{event['id']}",
        json={"title": "本地", "expected_version": 1},
    )

    assert conflicted.status_code == 409
    assert conflicted.json() == {
        "detail": "asset_version_conflict",
        "server_version": 2,
        "resource_type": "timeline_event",
        "resource_id": event["id"],
    }
    get_database_path.cache_clear()
