from uuid import uuid4

from fastapi.testclient import TestClient

from infrastructure.database.session import get_database_path, initialize_database
from presentation.api.app import app


def _prepare_database(monkeypatch, tmp_path, filename: str) -> None:
    db_path = tmp_path / "runtime" / filename
    monkeypatch.setenv("INKTRACE_DB_PATH", str(db_path))
    get_database_path.cache_clear()
    initialize_database()


def _create_work(client: TestClient) -> tuple[str, str]:
    response = client.post("/api/v1/works", json={"title": "Outline Work", "author": ""})
    assert response.status_code == 200
    work_id = response.json()["id"]
    chapter = client.get(f"/api/v1/works/{work_id}/chapters").json()["items"][0]
    return work_id, chapter["id"]


def _node(**overrides):
    payload = {
        "node_id": str(uuid4()),
        "text": "节点",
        "children": [],
        "chapter_ref": None,
    }
    payload.update(overrides)
    return payload


def test_v1_outlines_router_work_outline_roundtrip(monkeypatch, tmp_path):
    _prepare_database(monkeypatch, tmp_path, "outlines-work.db")
    client = TestClient(app)
    work_id, chapter_id = _create_work(client)

    initial = client.get(f"/api/v1/works/{work_id}/outline")
    assert initial.status_code == 200
    assert initial.json()["version"] == 1
    assert initial.json()["content_text"] == ""

    saved = client.put(
        f"/api/v1/works/{work_id}/outline",
        json={
            "content_text": "全书大纲",
            "content_tree_json": [_node(chapter_ref=chapter_id)],
            "expected_version": 1,
        },
    )
    assert saved.status_code == 200
    payload = saved.json()
    assert payload["work_id"] == work_id
    assert payload["content_text"] == "全书大纲"
    assert payload["content_tree_json"][0]["chapter_ref"] == chapter_id
    assert payload["version"] == 1

    updated = client.put(
        f"/api/v1/works/{work_id}/outline",
        json={"content_text": "更新", "content_tree_json": [], "expected_version": 1},
    )
    assert updated.status_code == 200
    assert updated.json()["version"] == 2

    get_database_path.cache_clear()


def test_v1_outlines_router_chapter_outline_roundtrip(monkeypatch, tmp_path):
    _prepare_database(monkeypatch, tmp_path, "outlines-chapter.db")
    client = TestClient(app)
    _, chapter_id = _create_work(client)

    initial = client.get(f"/api/v1/chapters/{chapter_id}/outline")
    assert initial.status_code == 200
    assert initial.json()["chapter_id"] == chapter_id

    saved = client.put(
        f"/api/v1/chapters/{chapter_id}/outline",
        json={"content_text": "章节细纲", "content_tree_json": [_node()], "expected_version": 1},
    )
    assert saved.status_code == 200
    assert saved.json()["content_text"] == "章节细纲"
    assert saved.json()["version"] == 1

    get_database_path.cache_clear()


def test_v1_outlines_router_version_conflict_returns_409(monkeypatch, tmp_path):
    _prepare_database(monkeypatch, tmp_path, "outlines-conflict.db")
    client = TestClient(app)
    work_id, _ = _create_work(client)
    assert client.put(
        f"/api/v1/works/{work_id}/outline",
        json={"content_text": "初版", "content_tree_json": [], "expected_version": 1},
    ).status_code == 200

    conflicted = client.put(
        f"/api/v1/works/{work_id}/outline",
        json={"content_text": "冲突", "content_tree_json": [], "expected_version": 0},
    )

    assert conflicted.status_code == 409
    assert conflicted.json() == {
        "detail": "asset_version_conflict",
        "server_version": 1,
        "resource_type": "work_outline",
        "resource_id": work_id,
    }
    get_database_path.cache_clear()


def test_v1_outlines_router_invalid_tree_schema_returns_invalid_input(monkeypatch, tmp_path):
    _prepare_database(monkeypatch, tmp_path, "outlines-invalid.db")
    client = TestClient(app)
    _, chapter_id = _create_work(client)

    invalid = client.put(
        f"/api/v1/chapters/{chapter_id}/outline",
        json={"content_text": "非法", "content_tree_json": [_node(ai_summary="禁止")], "expected_version": 1},
    )

    assert invalid.status_code == 400
    assert invalid.json() == {"detail": "invalid_input"}
    get_database_path.cache_clear()
