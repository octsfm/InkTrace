from fastapi.testclient import TestClient

from infrastructure.database.session import get_database_path, initialize_database
from presentation.api.app import app


def _prepare_database(monkeypatch, tmp_path, filename: str) -> None:
    db_path = tmp_path / "runtime" / filename
    monkeypatch.setenv("INKTRACE_DB_PATH", str(db_path))
    get_database_path.cache_clear()
    initialize_database()


def test_v1_sessions_router_get_defaults_to_first_chapter(monkeypatch, tmp_path):
    _prepare_database(monkeypatch, tmp_path, "sessions-router-default.db")
    client = TestClient(app)
    work = client.post("/api/v1/works", json={"title": "会话作品", "author": "作者甲"}).json()
    first = client.get(f"/api/v1/works/{work['id']}/chapters").json()["items"][0]

    session = client.get(f"/api/v1/works/{work['id']}/session")

    assert session.status_code == 200
    assert session.json()["last_open_chapter_id"] == first["id"]
    assert session.json()["cursor_position"] == 0
    assert session.json()["scroll_top"] == 0

    get_database_path.cache_clear()


def test_v1_sessions_router_put_then_get_restores_position(monkeypatch, tmp_path):
    _prepare_database(monkeypatch, tmp_path, "sessions-router-save.db")
    client = TestClient(app)
    work = client.post("/api/v1/works", json={"title": "会话保存作品", "author": "作者乙"}).json()
    first = client.get(f"/api/v1/works/{work['id']}/chapters").json()["items"][0]

    saved = client.put(
        f"/api/v1/works/{work['id']}/session",
        json={"active_chapter_id": first["id"], "cursor_position": 42, "scroll_top": 96},
    )
    fetched = client.get(f"/api/v1/works/{work['id']}/session")

    assert saved.status_code == 200
    assert fetched.status_code == 200
    assert fetched.json()["last_open_chapter_id"] == first["id"]
    assert fetched.json()["cursor_position"] == 42
    assert fetched.json()["scroll_top"] == 96

    get_database_path.cache_clear()


def test_v1_sessions_router_save_does_not_modify_chapter_content(monkeypatch, tmp_path):
    _prepare_database(monkeypatch, tmp_path, "sessions-router-no-content.db")
    client = TestClient(app)
    work = client.post("/api/v1/works", json={"title": "会话不存正文", "author": "作者丙"}).json()
    first = client.get(f"/api/v1/works/{work['id']}/chapters").json()["items"][0]
    chapter = client.put(
        f"/api/v1/chapters/{first['id']}",
        json={"content": "原正文", "expected_version": first["version"]},
    ).json()

    saved = client.put(
        f"/api/v1/works/{work['id']}/session",
        json={"active_chapter_id": first["id"], "cursor_position": 7, "scroll_top": 9},
    )
    reloaded = client.get(f"/api/v1/works/{work['id']}/chapters").json()["items"][0]

    assert saved.status_code == 200
    assert reloaded["content"] == "原正文"
    assert reloaded["version"] == chapter["version"]

    get_database_path.cache_clear()


def test_v1_sessions_router_rejects_unknown_work_or_chapter(monkeypatch, tmp_path):
    _prepare_database(monkeypatch, tmp_path, "sessions-router-errors.db")
    client = TestClient(app)
    work = client.post("/api/v1/works", json={"title": "会话错误作品", "author": "作者丁"}).json()

    missing_work = client.get("/api/v1/works/missing-work/session")
    missing_chapter = client.put(
        f"/api/v1/works/{work['id']}/session",
        json={"active_chapter_id": "missing-chapter", "cursor_position": 1, "scroll_top": 2},
    )

    assert missing_work.status_code == 404
    assert missing_work.json() == {"detail": "work_not_found"}
    assert missing_chapter.status_code == 404
    assert missing_chapter.json() == {"detail": "chapter_not_found"}

    get_database_path.cache_clear()
