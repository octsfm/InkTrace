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

    updated = client.put(f"/api/v1/works/{payload['id']}", json={"title": "路由作品-改", "author": "作者甲-改"})
    assert updated.status_code == 200
    assert updated.json()["title"] == "路由作品-改"
    assert updated.json()["author"] == "作者甲-改"


def test_v1_chapters_list_smoke():
    client = TestClient(app)
    response = client.get("/api/v1/works/work-1/chapters")
    assert response.status_code == 404
    assert response.json() == {"detail": "work_not_found"}


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
        json={
            "items": [
                {"id": second_payload["id"], "order_index": 1},
                {"id": first["id"], "order_index": 2},
            ]
        },
    )
    assert reorder.status_code == 200
    reordered_ids = [item["id"] for item in reorder.json()["items"]]
    assert reordered_ids[:2] == [second_payload["id"], first["id"]]

    deleted = client.delete(f"/api/v1/chapters/{first['id']}")
    assert deleted.status_code == 200
    assert deleted.json()["ok"] is True


def test_v1_chapter_delete_cleans_asset_refs_smoke():
    client = TestClient(app)
    created_work = client.post("/api/v1/works", json={"title": "删章清理作品", "author": "作者删"})
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
    second_id = second.json()["id"]

    saved_work_outline = client.put(
        f"/api/v1/works/{work_id}/outline",
        json={
            "content_text": "全书大纲",
            "content_tree_json": [
                {
                    "node_id": "00000000-0000-4000-8000-000000000101",
                    "text": "主线",
                    "chapter_ref": second_id,
                    "children": [],
                }
            ],
            "expected_version": 1,
        },
    )
    assert saved_work_outline.status_code == 200
    saved_chapter_outline = client.put(
        f"/api/v1/chapters/{second_id}/outline",
        json={"content_text": "章节细纲", "content_tree_json": [], "expected_version": 1},
    )
    assert saved_chapter_outline.status_code == 200
    timeline = client.post(
        f"/api/v1/works/{work_id}/timeline-events",
        json={"title": "事件", "description": "描述", "chapter_id": second_id},
    )
    assert timeline.status_code == 200
    foreshadow = client.post(
        f"/api/v1/works/{work_id}/foreshadows",
        json={
            "title": "伏笔",
            "description": "描述",
            "status": "resolved",
            "introduced_chapter_id": second_id,
            "resolved_chapter_id": second_id,
        },
    )
    assert foreshadow.status_code == 200

    deleted = client.delete(f"/api/v1/chapters/{second_id}")
    assert deleted.status_code == 200
    assert deleted.json()["ok"] is True
    assert deleted.json()["next_chapter_id"] == first["id"]

    chapter_outline = client.get(f"/api/v1/chapters/{second_id}/outline")
    assert chapter_outline.status_code == 404
    assert chapter_outline.json() == {"detail": "chapter_not_found"}

    timeline_after = client.get(f"/api/v1/works/{work_id}/timeline-events")
    assert timeline_after.status_code == 200
    assert timeline_after.json()["items"][0]["chapter_id"] is None

    foreshadow_after = client.get(f"/api/v1/works/{work_id}/foreshadows", params={"status": "resolved"})
    assert foreshadow_after.status_code == 200
    assert foreshadow_after.json()["items"][0]["introduced_chapter_id"] is None
    assert foreshadow_after.json()["items"][0]["resolved_chapter_id"] is None

    work_outline_after = client.get(f"/api/v1/works/{work_id}/outline")
    assert work_outline_after.status_code == 200
    assert work_outline_after.json()["content_tree_json"][0]["chapter_ref"] is None

    chapters_after = client.get(f"/api/v1/works/{work_id}/chapters")
    assert chapters_after.status_code == 200
    assert [item["order_index"] for item in chapters_after.json()["items"]] == [1]


def test_v1_work_delete_cleans_workbench_data_smoke():
    client = TestClient(app)
    created_work = client.post("/api/v1/works", json={"title": "删作品路由作品", "author": "作者清"})
    assert created_work.status_code == 200
    work_id = created_work.json()["id"]

    chapters = client.get(f"/api/v1/works/{work_id}/chapters")
    assert chapters.status_code == 200
    first = chapters.json()["items"][0]

    saved_session = client.put(
        f"/api/v1/works/{work_id}/session",
        json={"chapter_id": first["id"], "cursor_position": 3, "scroll_top": 9},
    )
    assert saved_session.status_code == 200
    saved_work_outline = client.put(
        f"/api/v1/works/{work_id}/outline",
        json={"content_text": "大纲", "content_tree_json": [], "expected_version": 1},
    )
    assert saved_work_outline.status_code == 200
    saved_chapter_outline = client.put(
        f"/api/v1/chapters/{first['id']}/outline",
        json={"content_text": "细纲", "content_tree_json": [], "expected_version": 1},
    )
    assert saved_chapter_outline.status_code == 200
    saved_timeline = client.post(
        f"/api/v1/works/{work_id}/timeline-events",
        json={"title": "事件", "description": "描述", "chapter_id": first["id"]},
    )
    assert saved_timeline.status_code == 200
    saved_foreshadow = client.post(
        f"/api/v1/works/{work_id}/foreshadows",
        json={"title": "伏笔", "description": "描述", "status": "open", "introduced_chapter_id": first["id"]},
    )
    assert saved_foreshadow.status_code == 200
    saved_character = client.post(
        f"/api/v1/works/{work_id}/characters",
        json={"name": "角色甲", "description": "描述", "aliases": ["甲"]},
    )
    assert saved_character.status_code == 200

    deleted = client.delete(f"/api/v1/works/{work_id}")
    assert deleted.status_code == 200
    assert deleted.json() == {"ok": True, "id": work_id}

    assert client.get(f"/api/v1/works/{work_id}").status_code == 404
    assert client.get(f"/api/v1/works/{work_id}/chapters").json() == {"detail": "work_not_found"}
    assert client.get(f"/api/v1/works/{work_id}/session").json() == {"detail": "work_not_found"}
    assert client.get(f"/api/v1/works/{work_id}/outline").json() == {"detail": "work_not_found"}
    assert client.get(f"/api/v1/works/{work_id}/timeline-events").json() == {"detail": "work_not_found"}
    assert client.get(f"/api/v1/works/{work_id}/foreshadows").json() == {"detail": "work_not_found"}
    assert client.get(f"/api/v1/works/{work_id}/characters").json() == {"detail": "work_not_found"}
    assert client.get(f"/api/v1/chapters/{first['id']}/outline").json() == {"detail": "chapter_not_found"}
    assert client.put(
        f"/api/v1/works/{work_id}/chapters/reorder",
        json={"items": [{"id": first["id"], "order_index": 1}]},
    ).json() == {"detail": "work_not_found"}


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
    assert conflicted.json() == {
        "detail": "version_conflict",
        "server_version": 2,
        "resource_type": "chapter",
        "resource_id": chapter["id"],
    }

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
    raw_bytes = "第一章 起点\n这里是正文。".encode("utf-8")

    imported = client.post(
        "/api/v1/io/import",
        data={"title": "导入路由作品", "author": "作者丁"},
        files={"file": ("route-import.txt", raw_bytes, "text/plain")},
    )
    assert imported.status_code == 200
    work_id = imported.json()["id"]

    exported = client.get(f"/api/v1/io/export/{work_id}")
    assert exported.status_code == 200
    assert "第1章 起点" in exported.text
    assert "attachment;" in exported.headers["content-disposition"].lower()


def test_v1_io_export_follows_reordered_chapters_smoke(tmp_path):
    client = TestClient(app)
    raw_bytes = "第一章 起点\n正文一。\n第二章 进展\n正文二。".encode("utf-8")

    imported = client.post(
        "/api/v1/io/import",
        data={"title": "导出重排作品", "author": "作者壬"},
        files={"file": ("route-export-reorder.txt", raw_bytes, "text/plain")},
    )
    assert imported.status_code == 200
    work_id = imported.json()["id"]

    chapters = client.get(f"/api/v1/works/{work_id}/chapters")
    assert chapters.status_code == 200
    items = chapters.json()["items"]

    reordered = client.put(
        f"/api/v1/works/{work_id}/chapters/reorder",
        json={
            "items": [
                {"id": items[1]["id"], "order_index": 1},
                {"id": items[0]["id"], "order_index": 2},
            ]
        },
    )
    assert reordered.status_code == 200

    exported = client.get(f"/api/v1/io/export/{work_id}")
    assert exported.status_code == 200
    content = exported.text
    assert content.index("第1章 进展") < content.index("第2章 起点")


def test_v1_io_export_empty_file_when_work_has_no_chapters_smoke(tmp_path):
    client = TestClient(app)

    created_work = client.post("/api/v1/works", json={"title": "空导出路由作品", "author": "作者子"})
    assert created_work.status_code == 200
    work_id = created_work.json()["id"]

    chapters = client.get(f"/api/v1/works/{work_id}/chapters")
    assert chapters.status_code == 200
    first = chapters.json()["items"][0]

    deleted = client.delete(f"/api/v1/chapters/{first['id']}")
    assert deleted.status_code == 200

    exported = client.get(f"/api/v1/io/export/{work_id}")
    assert exported.status_code == 200
    assert exported.content == b""


def test_v1_io_import_fallback_smoke(tmp_path):
    client = TestClient(app)
    raw_bytes = "没有章节名的整本正文。\n第二段内容继续。".encode("utf-8")

    imported = client.post(
        "/api/v1/io/import",
        data={"title": "整本导入作品", "author": "作者己"},
        files={"file": ("route-import-plain.txt", raw_bytes, "text/plain")},
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
    imported = client.post(
        "/api/v1/io/import",
        data={"title": "空文件作品", "author": "作者庚"},
        files={"file": ("route-import-empty.txt", b"", "text/plain")},
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
    raw_bytes = "这是前言。\n第二行前言。\n\n第一章 起点\n正文一。\n\n第三章 转折\n正文三。".encode("utf-8")

    imported = client.post(
        "/api/v1/io/import",
        data={"title": "顺序校正作品", "author": "作者辛"},
        files={"file": ("route-import-intro.txt", raw_bytes, "text/plain")},
    )
    assert imported.status_code == 200
    work_id = imported.json()["id"]

    chapters = client.get(f"/api/v1/works/{work_id}/chapters")
    assert chapters.status_code == 200
    items = chapters.json()["items"]
    assert [item["title"] for item in items] == ["前言", "起点", "转折"]
    assert [item["chapter_number"] for item in items] == [1, 2, 3]
    assert [item["order_index"] for item in items] == [1, 2, 3]


def test_v1_io_import_rejects_too_large_file_smoke(tmp_path):
    client = TestClient(app)
    oversized = b"a" * (20 * 1024 * 1024 + 1)

    imported = client.post(
        "/api/v1/io/import",
        data={"title": "超限作品", "author": "作者壬"},
        files={"file": ("route-import-too-large.txt", oversized, "text/plain")},
    )
    assert imported.status_code == 400
    assert imported.json()["detail"] == "文件过大，请拆分后导入（上限 20MB）。"


def test_v1_io_export_respects_options_smoke():
    client = TestClient(app)
    raw_bytes = "第一章 起点\n正文一。\n第二章 进展\n正文二。".encode("utf-8")

    imported = client.post(
        "/api/v1/io/import",
        data={"title": "选项路由作品", "author": "作者癸"},
        files={"file": ("route-import-options.txt", raw_bytes, "text/plain")},
    )
    assert imported.status_code == 200
    work_id = imported.json()["id"]

    without_titles = client.get(f"/api/v1/io/export/{work_id}", params={"include_titles": False, "gap_lines": 0})
    with_double_gap = client.get(f"/api/v1/io/export/{work_id}", params={"include_titles": True, "gap_lines": 2})

    assert without_titles.status_code == 200
    assert "第1章 起点" not in without_titles.text
    assert "\n\n\n" in with_double_gap.text


def test_v1_validation_error_returns_invalid_input_smoke():
    client = TestClient(app)

    invalid = client.post("/api/v1/works", json={"author": "作者缺标题"})

    assert invalid.status_code == 400
    assert invalid.json() == {"detail": "invalid_input"}
