from fastapi.testclient import TestClient

from infrastructure.database.repositories import WorkRepo
from infrastructure.database.session import get_database_path, initialize_database
from presentation.api.app import app


def _prepare_database(monkeypatch, tmp_path, filename: str) -> None:
    db_path = tmp_path / "runtime" / filename
    monkeypatch.setenv("INKTRACE_DB_PATH", str(db_path))
    get_database_path.cache_clear()
    initialize_database()


def test_v1_io_router_import_returns_work_and_chapters(monkeypatch, tmp_path):
    _prepare_database(monkeypatch, tmp_path, "io-router-import.db")
    client = TestClient(app)
    raw_bytes = "第一章 起点\n正文一。\n第二章 进展\n正文二。".encode("utf-8")

    imported = client.post(
        "/api/v1/io/import",
        data={"title": "导入作品", "author": "作者甲"},
        files={"file": ("novel.txt", raw_bytes, "text/plain")},
    )

    assert imported.status_code == 200
    payload = imported.json()
    assert payload["title"] == "导入作品"
    assert payload["author"] == "作者甲"
    assert [item["title"] for item in payload["chapters"]] == ["起点", "进展"]
    assert [item["order_index"] for item in payload["chapters"]] == [1, 2]

    get_database_path.cache_clear()


def test_v1_io_router_import_fallback_and_too_large_error(monkeypatch, tmp_path):
    _prepare_database(monkeypatch, tmp_path, "io-router-import-errors.db")
    client = TestClient(app)

    fallback = client.post(
        "/api/v1/io/import",
        data={"title": "整本导入", "author": "作者乙"},
        files={"file": ("plain.txt", "无章节标记正文。".encode("utf-8"), "text/plain")},
    )
    too_large = client.post(
        "/api/v1/io/import",
        data={"title": "超限作品", "author": "作者丙"},
        files={"file": ("large.txt", b"a" * (20 * 1024 * 1024 + 1), "text/plain")},
    )

    assert fallback.status_code == 200
    assert len(fallback.json()["chapters"]) == 1
    assert fallback.json()["chapters"][0]["title"] == "全本导入"
    assert too_large.status_code == 400
    assert too_large.json() == {"detail": "文件过大，请拆分后导入（上限 20MB）。"}

    get_database_path.cache_clear()


def test_v1_io_router_export_returns_txt_filename_and_does_not_modify_work(monkeypatch, tmp_path):
    _prepare_database(monkeypatch, tmp_path, "io-router-export.db")
    client = TestClient(app)
    raw_bytes = "第一章 起点\n正文一。".encode("utf-8")

    imported = client.post(
        "/api/v1/io/import",
        data={"title": "导出作品", "author": "作者丁"},
        files={"file": ("export.txt", raw_bytes, "text/plain")},
    )
    work_id = imported.json()["id"]
    before = WorkRepo().find_by_id(work_id)

    exported = client.get(f"/api/v1/io/export/{work_id}", params={"include_titles": True, "gap_lines": 1})
    after = WorkRepo().find_by_id(work_id)

    assert exported.status_code == 200
    assert exported.headers["content-type"].startswith("text/plain")
    assert "attachment;" in exported.headers["content-disposition"].lower()
    assert "%E5%AF%BC%E5%87%BA%E4%BD%9C%E5%93%81" in exported.headers["content-disposition"]
    assert "第1章 起点" in exported.text
    assert before is not None
    assert after is not None
    assert after.updated_at == before.updated_at

    get_database_path.cache_clear()


def test_v1_io_router_export_errors_and_options(monkeypatch, tmp_path):
    _prepare_database(monkeypatch, tmp_path, "io-router-export-errors.db")
    client = TestClient(app)

    missing = client.get("/api/v1/io/export/missing-work")
    invalid_gap = client.get("/api/v1/io/export/missing-work", params={"gap_lines": 9})

    assert missing.status_code == 404
    assert missing.json() == {"detail": "work_not_found"}
    assert invalid_gap.status_code == 400
    assert invalid_gap.json() == {"detail": "invalid_input"}

    get_database_path.cache_clear()
