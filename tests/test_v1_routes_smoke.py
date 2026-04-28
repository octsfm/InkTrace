from fastapi.testclient import TestClient

from presentation.api.app import app


def test_v1_works_list_smoke():
    client = TestClient(app)
    response = client.get("/api/v1/works")
    assert response.status_code == 200
    assert response.json() == {"items": [], "total": 0}


def test_v1_works_create_and_get_smoke():
    client = TestClient(app)
    created = client.post("/api/v1/works", json={"title": "路由作品", "author": "作者甲"})
    assert created.status_code == 200
    payload = created.json()
    assert payload["title"] == "路由作品"

    fetched = client.get(f"/api/v1/works/{payload['id']}")
    assert fetched.status_code == 200
    assert fetched.json()["id"] == payload["id"]


def test_v1_chapters_list_smoke():
    client = TestClient(app)
    response = client.get("/api/v1/works/work-1/chapters")
    assert response.status_code == 200
    assert response.json()["work_id"] == "work-1"


def test_v1_chapters_crud_and_reorder_smoke():
    client = TestClient(app)
    created_work = client.post("/api/v1/works", json={"title": "章节路由作品", "author": "作者乙"})
    assert created_work.status_code == 200
    work_id = created_work.json()["id"]

    chapters = client.get(f"/api/v1/works/{work_id}/chapters")
    assert chapters.status_code == 200
    first = chapters.json()["items"][0]

    second = client.post(
        f"/api/v1/works/{work_id}/chapters",
        json={"title": "第二章", "after_chapter_id": first["id"]},
    )
    assert second.status_code == 200
    second_payload = second.json()
    assert second_payload["chapter_number"] == 2

    updated = client.put(
        f"/api/v1/chapters/{second_payload['id']}",
        json={"content": "新的正文", "expected_version": 1},
    )
    assert updated.status_code == 200
    assert updated.json()["content"] == "新的正文"

    reorder = client.put(
        f"/api/v1/works/{work_id}/chapters/reorder",
        json={"chapter_ids": [second_payload["id"], first["id"]]},
    )
    assert reorder.status_code == 200
    reordered_ids = [item["id"] for item in reorder.json()["items"]]
    assert reordered_ids[:2] == [second_payload["id"], first["id"]]

    deleted = client.delete(f"/api/v1/chapters/{first['id']}")
    assert deleted.status_code == 200
    assert deleted.json()["ok"] is True


def test_v1_chapters_force_override_smoke():
    client = TestClient(app)
    created_work = client.post("/api/v1/works", json={"title": "覆盖路由作品", "author": "作者戊"})
    assert created_work.status_code == 200
    work_id = created_work.json()["id"]
    chapter = client.get(f"/api/v1/works/{work_id}/chapters").json()["items"][0]

    first_saved = client.put(
        f"/api/v1/chapters/{chapter['id']}",
        json={"content": "云端正文", "expected_version": 1},
    )
    assert first_saved.status_code == 200
    assert first_saved.json()["version"] == 2

    conflicted = client.put(
        f"/api/v1/chapters/{chapter['id']}",
        json={"content": "本地正文", "expected_version": 1},
    )
    assert conflicted.status_code == 409

    forced = client.put(
        f"/api/v1/chapters/{chapter['id']}",
        json={"content": "本地正文", "expected_version": 1, "force_override": True},
    )
    assert forced.status_code == 200
    assert forced.json()["content"] == "本地正文"
    assert forced.json()["version"] == 3


def test_v1_sessions_get_and_save_smoke():
    client = TestClient(app)
    created_work = client.post("/api/v1/works", json={"title": "会话路由作品", "author": "作者丙"})
    assert created_work.status_code == 200
    work_id = created_work.json()["id"]
    first = client.get(f"/api/v1/works/{work_id}/chapters").json()["items"][0]

    fetched = client.get(f"/api/v1/works/{work_id}/session")
    assert fetched.status_code == 200
    assert fetched.json()["last_open_chapter_id"] == first["id"]

    saved = client.put(
        f"/api/v1/works/{work_id}/session",
        json={"chapter_id": first["id"], "cursor_position": 42, "scroll_top": 96},
    )
    assert saved.status_code == 200
    assert saved.json()["cursor_position"] == 42
    assert saved.json()["scroll_top"] == 96


def test_v1_io_import_and_export_smoke(tmp_path):
    client = TestClient(app)
    source_path = tmp_path / "route-import.txt"
    export_path = tmp_path / "route-export.txt"
    source_path.write_text("第一章 起点\n这里是正文。", encoding="utf-8")

    imported = client.post(
        "/api/v1/io/import",
        json={"file_path": str(source_path), "title": "导入路由作品", "author": "作者丁"},
    )
    assert imported.status_code == 200
    work_id = imported.json()["id"]

    exported = client.get(f"/api/v1/io/export/{work_id}", params={"output_path": str(export_path)})
    assert exported.status_code == 200
    assert export_path.exists()
    assert "导入路由作品" in export_path.read_text(encoding="utf-8")


def test_v1_io_export_follows_reordered_chapters_smoke(tmp_path):
    client = TestClient(app)
    source_path = tmp_path / "route-export-reorder.txt"
    export_path = tmp_path / "route-export-reordered.txt"
    source_path.write_text("第一章 起点\n正文一。\n第二章 进展\n正文二。", encoding="utf-8")

    imported = client.post(
        "/api/v1/io/import",
        json={"file_path": str(source_path), "title": "导出重排作品", "author": "作者壬"},
    )
    assert imported.status_code == 200
    work_id = imported.json()["id"]

    chapters = client.get(f"/api/v1/works/{work_id}/chapters")
    assert chapters.status_code == 200
    items = chapters.json()["items"]

    reordered = client.put(
        f"/api/v1/works/{work_id}/chapters/reorder",
        json={"chapter_ids": [items[1]["id"], items[0]["id"]]},
    )
    assert reordered.status_code == 200

    exported = client.get(f"/api/v1/io/export/{work_id}", params={"output_path": str(export_path)})
    assert exported.status_code == 200
    content = export_path.read_text(encoding="utf-8")
    assert content.index("第1章 进展") < content.index("第2章 起点")


def test_v1_io_export_empty_file_when_work_has_no_chapters_smoke(tmp_path):
    client = TestClient(app)
    export_path = tmp_path / "route-export-empty.txt"

    created_work = client.post("/api/v1/works", json={"title": "空导出路由作品", "author": "作者子"})
    assert created_work.status_code == 200
    work_id = created_work.json()["id"]

    chapters = client.get(f"/api/v1/works/{work_id}/chapters")
    assert chapters.status_code == 200
    first = chapters.json()["items"][0]

    deleted = client.delete(f"/api/v1/chapters/{first['id']}")
    assert deleted.status_code == 200

    exported = client.get(f"/api/v1/io/export/{work_id}", params={"output_path": str(export_path)})
    assert exported.status_code == 200
    assert export_path.exists()
    assert export_path.read_text(encoding="utf-8") == ""


def test_v1_io_import_fallback_smoke(tmp_path):
    client = TestClient(app)
    source_path = tmp_path / "route-import-plain.txt"
    source_path.write_text("没有章节名的整本正文。\n第二段内容继续。", encoding="utf-8")

    imported = client.post(
        "/api/v1/io/import",
        json={"file_path": str(source_path), "title": "整本导入作品", "author": "作者己"},
    )
    assert imported.status_code == 200
    work_id = imported.json()["id"]

    chapters = client.get(f"/api/v1/works/{work_id}/chapters")
    assert chapters.status_code == 200
    items = chapters.json()["items"]
    assert len(items) == 1
    assert items[0]["title"] == "全本导入"
    assert items[0]["content"] == "没有章节名的整本正文。\n第二段内容继续。"


def test_v1_io_import_empty_file_smoke(tmp_path):
    client = TestClient(app)
    source_path = tmp_path / "route-import-empty.txt"
    source_path.write_text("", encoding="utf-8")

    imported = client.post(
        "/api/v1/io/import",
        json={"file_path": str(source_path), "title": "空文件作品", "author": "作者庚"},
    )
    assert imported.status_code == 200
    work_id = imported.json()["id"]

    chapters = client.get(f"/api/v1/works/{work_id}/chapters")
    assert chapters.status_code == 200
    items = chapters.json()["items"]
    assert len(items) == 1
    assert items[0]["title"] == "全本导入"
    assert items[0]["content"] == ""


def test_v1_io_import_intro_and_order_correction_smoke(tmp_path):
    client = TestClient(app)
    source_path = tmp_path / "route-import-intro.txt"
    source_path.write_text(
        "这是前言。\n第二行前言。\n\n第一章 起点\n正文一。\n\n第三章 转折\n正文三。",
        encoding="utf-8",
    )

    imported = client.post(
        "/api/v1/io/import",
        json={"file_path": str(source_path), "title": "顺序校正作品", "author": "作者辛"},
    )
    assert imported.status_code == 200
    work_id = imported.json()["id"]

    chapters = client.get(f"/api/v1/works/{work_id}/chapters")
    assert chapters.status_code == 200
    items = chapters.json()["items"]
    assert [item["title"] for item in items] == ["前言", "起点", "转折"]
    assert [item["chapter_number"] for item in items] == [1, 2, 3]
    assert [item["order_index"] for item in items] == [1, 2, 3]
