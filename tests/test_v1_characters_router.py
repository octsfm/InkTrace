from fastapi.testclient import TestClient

from infrastructure.database.session import get_database_path, initialize_database
from presentation.api.app import app


def _prepare_database(monkeypatch, tmp_path, filename: str) -> None:
    db_path = tmp_path / "runtime" / filename
    monkeypatch.setenv("INKTRACE_DB_PATH", str(db_path))
    get_database_path.cache_clear()
    initialize_database()


def _create_work(client: TestClient) -> str:
    response = client.post("/api/v1/works", json={"title": "Character Work", "author": ""})
    assert response.status_code == 200
    return response.json()["id"]


def test_v1_characters_router_crud_aliases_and_search(monkeypatch, tmp_path):
    _prepare_database(monkeypatch, tmp_path, "characters-router-crud.db")
    client = TestClient(app)
    work_id = _create_work(client)

    created = client.post(
        f"/api/v1/works/{work_id}/characters",
        json={
            "name": "林舟",
            "description": "主角",
            "aliases": [" 舟 ", "", "lin", "LIN"],
        },
    )
    assert created.status_code == 200
    assert created.json()["name"] == "林舟"
    assert created.json()["aliases"] == ["舟", "lin"]

    listed = client.get(f"/api/v1/works/{work_id}/characters")
    assert listed.status_code == 200
    assert listed.json()["total"] == 1
    assert listed.json()["items"][0]["id"] == created.json()["id"]

    searched_by_alias = client.get(f"/api/v1/works/{work_id}/characters?keyword=LIN")
    assert searched_by_alias.status_code == 200
    assert [item["id"] for item in searched_by_alias.json()["items"]] == [created.json()["id"]]

    updated = client.put(
        f"/api/v1/characters/{created.json()['id']}",
        json={"name": "林舟改", "aliases": [], "expected_version": 1},
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "林舟改"
    assert updated.json()["aliases"] == []
    assert updated.json()["version"] == 2

    deleted = client.delete(f"/api/v1/characters/{created.json()['id']}")
    assert deleted.status_code == 200
    assert deleted.json() == {"ok": True, "id": created.json()["id"]}
    assert client.get(f"/api/v1/works/{work_id}/characters").json()["total"] == 0
    get_database_path.cache_clear()


def test_v1_characters_router_invalid_empty_name(monkeypatch, tmp_path):
    _prepare_database(monkeypatch, tmp_path, "characters-router-invalid.db")
    client = TestClient(app)
    work_id = _create_work(client)

    created = client.post(f"/api/v1/works/{work_id}/characters", json={"name": "   "})
    assert created.status_code == 400
    assert created.json() == {"detail": "invalid_input"}
    get_database_path.cache_clear()


def test_v1_characters_router_version_conflict_returns_409(monkeypatch, tmp_path):
    _prepare_database(monkeypatch, tmp_path, "characters-router-conflict.db")
    client = TestClient(app)
    work_id = _create_work(client)
    character = client.post(f"/api/v1/works/{work_id}/characters", json={"name": "角色"}).json()
    assert client.put(
        f"/api/v1/characters/{character['id']}",
        json={"description": "远端", "expected_version": 1},
    ).status_code == 200

    conflicted = client.put(
        f"/api/v1/characters/{character['id']}",
        json={"description": "本地", "expected_version": 1},
    )

    assert conflicted.status_code == 409
    assert conflicted.json() == {
        "detail": "asset_version_conflict",
        "server_version": 2,
        "resource_type": "character",
        "resource_id": character["id"],
    }
    get_database_path.cache_clear()
