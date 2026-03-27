from __future__ import annotations

import tempfile
import time
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from presentation.api.app import app


def _create_temp_novel_file() -> str:
    fd, path = tempfile.mkstemp(suffix=".txt")
    Path(path).write_text("第1章 开始\n主角出场。\n\n第2章 推进\n冲突升级。", encoding="utf-8")
    return path


def test_projects_v2_import_and_query_chain():
    client = TestClient(app)
    novel_path = _create_temp_novel_file()
    try:
        resp = client.post(
            "/api/projects/import",
            json={
                "project_name": "v2测试项目",
                "author": "测试作者",
                "genre": "xuanhuan",
                "novel_file_path": novel_path,
                "outline_file_path": "",
                "auto_organize": False,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["project_id"]
        assert data["novel_id"]

        project_id = data["project_id"]
        novel_id = data["novel_id"]

        by_novel = client.get(f"/api/projects/by-novel/{novel_id}")
        assert by_novel.status_code == 200
        assert by_novel.json()["id"] == project_id

        memory = client.get(f"/api/projects/{project_id}/memory")
        assert memory.status_code == 200
        assert memory.json()["project_id"] == project_id

        view = client.get(f"/api/projects/{project_id}/memory-view")
        assert view.status_code == 200
        assert view.json()["project_id"] == project_id
    finally:
        try:
            Path(novel_path).unlink(missing_ok=True)
        except Exception:
            pass


def test_projects_v2_upload_and_trace_endpoints():
    client = TestClient(app)
    files = {
        "novel_file": ("novel.txt", "第1章 起始\n主角登场。", "text/plain"),
        "outline_file": ("outline.txt", "世界观：上古崩塌后重建秩序。", "text/plain"),
    }
    data = {
        "project_name": "上传链路测试",
        "author": "上传作者",
        "genre": "xuanhuan",
        "auto_organize": "false",
    }
    resp = client.post("/api/projects/import/upload", data=data, files=files)
    assert resp.status_code == 200
    payload = resp.json()
    project_id = payload["project_id"]
    trace = client.get(f"/api/projects/{project_id}/trace")
    assert trace.status_code == 200
    trace_payload = trace.json()
    assert trace_payload["project_id"] == project_id
    jobs = client.get(f"/api/projects/{project_id}/workflow-jobs")
    assert jobs.status_code == 200
    assert "workflow_jobs" in jobs.json()
    sessions = client.get(f"/api/projects/{project_id}/writing-sessions")
    assert sessions.status_code == 200
    assert "writing_sessions" in sessions.json()


def test_projects_v2_final_acceptance_chain():
    client = TestClient(app)
    files = {
        "novel_file": (
            "novel.txt",
            "第1章 初入\n主角进入古城并发现禁制。\n\n第2章 对峙\n主角与守城势力发生冲突并逃离。",
            "text/plain",
        ),
        "outline_file": (
            "outline.txt",
            "故事背景：古城封印松动，三方势力争夺核心遗物。\n世界观：灵纹体系决定力量上限，越级使用会反噬。",
            "text/plain",
        ),
    }
    upload = client.post(
        "/api/projects/import/upload",
        data={"project_name": "最终验收链路", "author": "验收作者", "genre": "xuanhuan", "auto_organize": "true"},
        files=files,
    )
    assert upload.status_code == 200
    imported = upload.json()
    project_id = imported["project_id"]
    novel_id = imported["novel_id"]
    organize = client.post(
        f"/api/projects/{project_id}/organize",
        json={"mode": "chapter_first", "rebuild_memory": True},
    )
    assert organize.status_code == 200
    branches = client.post(
        f"/api/projects/{project_id}/branches",
        json={"direction_hint": "沿大纲推进并放大古城冲突", "branch_count": 3},
    )
    assert branches.status_code == 200
    branch_payload = branches.json()
    assert len(branch_payload["branches"]) >= 3
    branch_id = branch_payload["branches"][0]["id"]
    plan = client.post(
        f"/api/projects/{project_id}/chapter-plan",
        json={"branch_id": branch_id, "chapter_count": 1, "target_words_per_chapter": 1200},
    )
    assert plan.status_code == 200
    plan_payload = plan.json()
    plan_ids = [item["id"] for item in (plan_payload.get("plans") or [])]
    assert plan_ids
    write = client.post(
        f"/api/projects/{project_id}/write",
        json={"plan_ids": plan_ids, "auto_commit": True},
    )
    assert write.status_code == 200
    write_payload = write.json()
    assert write_payload.get("generated_chapter_ids")
    refresh = client.post(
        f"/api/projects/{project_id}/refresh-memory",
        json={"from_chapter_number": 1, "to_chapter_number": 3},
    )
    assert refresh.status_code == 200
    view_resp = client.get(f"/api/projects/{project_id}/memory-view")
    assert view_resp.status_code == 200
    memory_view = view_resp.json().get("memory_view") or {}
    assert memory_view.get("outline_summary")
    assert isinstance(memory_view.get("main_plot_lines"), list)
    by_novel = client.get(f"/api/projects/by-novel/{novel_id}")
    assert by_novel.status_code == 200


def test_delete_chapter_api_updates_novel_stats():
    client = TestClient(app)
    files = {
        "novel_file": (
            "novel.txt",
            "第1章 起始\n主角进城。\n\n第2章 变局\n冲突爆发。",
            "text/plain",
        ),
    }
    upload = client.post(
        "/api/projects/import/upload",
        data={"project_name": "删除章节测试", "author": "删除作者", "genre": "xuanhuan", "auto_organize": "false"},
        files=files,
    )
    assert upload.status_code == 200
    novel_id = upload.json()["novel_id"]
    novel_detail = client.get(f"/api/novels/{novel_id}")
    assert novel_detail.status_code == 200
    chapters = novel_detail.json().get("chapters") or []
    assert len(chapters) == 2
    delete_resp = client.delete(f"/api/novels/{novel_id}/chapters/{chapters[-1]['id']}")
    assert delete_resp.status_code == 200
    delete_payload = delete_resp.json()
    assert delete_payload["chapter_count"] == 1
    latest_detail = client.get(f"/api/novels/{novel_id}")
    assert latest_detail.status_code == 200
    latest = latest_detail.json()
    assert latest["chapter_count"] == 1
    assert latest["chapters"][0]["number"] == 1


def test_projects_v2_import_keeps_author():
    client = TestClient(app)
    novel_path = _create_temp_novel_file()
    try:
        resp = client.post(
            "/api/projects/import",
            json={
                "project_name": "作者贯通测试",
                "author": "孔利群",
                "genre": "xuanhuan",
                "novel_file_path": novel_path,
                "outline_file_path": "",
                "auto_organize": False,
            },
        )
        assert resp.status_code == 200
        novel_id = resp.json()["novel_id"]
        detail = client.get(f"/api/novels/{novel_id}")
        assert detail.status_code == 200
        assert detail.json()["author"] == "孔利群"
    finally:
        try:
            Path(novel_path).unlink(missing_ok=True)
        except Exception:
            pass


def test_content_progress_returns_real_chapter_fields():
    client = TestClient(app)
    files = {
        "novel_file": ("novel.txt", "第1章 起\n甲\n\n第2章 承\n乙", "text/plain"),
    }
    upload = client.post(
        "/api/projects/import/upload",
        data={"project_name": "进度字段测试", "author": "测试作者", "genre": "xuanhuan", "auto_organize": "false"},
        files=files,
    )
    assert upload.status_code == 200
    novel_id = upload.json()["novel_id"]
    started = client.post(f"/api/content/organize/start/{novel_id}?force_rebuild=true")
    assert started.status_code == 200
    observed = []
    for _ in range(12):
        progress = client.get(f"/api/content/organize/progress/{novel_id}")
        assert progress.status_code == 200
        payload = progress.json()
        observed.append(payload)
        if payload.get("status") == "done":
            break
        time.sleep(0.2)
    latest = observed[-1]
    assert "stage" in latest
    assert "current" in latest and "total" in latest
    assert latest["total"] >= 2
    assert latest["current"] <= latest["total"]
    assert latest["percent"] <= 100


def test_create_project_does_not_generate_first_chapter():
    client = TestClient(app)
    created = client.post(
        "/api/projects",
        json={
            "name": "纯创建项目",
            "genre": "xuanhuan",
            "target_words": 300000,
        },
    )
    assert created.status_code == 200
    payload = created.json()
    assert payload["first_chapter"] is None
    novel_id = payload["project"]["novel_id"]
    detail = client.get(f"/api/novels/{novel_id}")
    assert detail.status_code == 200
    assert detail.json()["chapter_count"] == 0


def test_project_flow_import_edit_and_export_modes():
    client = TestClient(app)
    files = {
        "novel_file": ("novel.txt", "第1章 起\n甲\n\n第2章 承\n乙", "text/plain"),
    }
    upload = client.post(
        "/api/projects/import/upload",
        data={"project_name": "主链验收", "author": "主链作者", "genre": "xuanhuan", "auto_organize": "false", "import_mode": "full"},
        files=files,
    )
    assert upload.status_code == 200
    novel_id = upload.json()["novel_id"]
    detail = client.get(f"/api/novels/{novel_id}")
    assert detail.status_code == 200
    assert detail.json()["chapter_count"] >= 1
    chapter_id = detail.json()["chapters"][0]["id"]
    updated = client.put(
        f"/api/chapters/{chapter_id}",
        json={"chapter_id": chapter_id, "content": "章节更新后的正文"},
    )
    assert updated.status_code == 200
    assert "memory_refreshed" in updated.json()
    for scope, fmt, output in [
        ("full", "markdown", "flow_full.md"),
        ("full", "txt", "flow_full.txt"),
        ("by_chapter", "markdown", "flow_dir_md"),
        ("by_chapter", "txt", "flow_dir_txt"),
    ]:
        exported = client.post(
            "/api/export/",
            json={"novel_id": novel_id, "scope": scope, "format": fmt, "output_path": output},
        )
        assert exported.status_code == 200
        payload = exported.json()
        if scope == "full":
            assert payload["mode"] == "file"
            assert payload["file_path"]
        else:
            assert payload["mode"] == "directory"
            assert payload["directory_path"]


def test_v2_write_appends_chapter_number_and_keeps_title():
    client = TestClient(app)
    files = {
        "novel_file": ("novel.txt", "第1章 起\n甲\n\n第2章 承\n乙", "text/plain"),
    }
    upload = client.post(
        "/api/projects/import/upload",
        data={"project_name": "续写编号测试", "author": "测试作者", "genre": "xuanhuan", "auto_organize": "false"},
        files=files,
    )
    assert upload.status_code == 200
    project_id = upload.json()["project_id"]
    novel_id = upload.json()["novel_id"]
    detail_before = client.get(f"/api/novels/{novel_id}").json()
    max_before = max(ch["number"] for ch in detail_before.get("chapters") or [])

    branches = client.post(
        f"/api/projects/{project_id}/branches",
        json={"direction_hint": "推进主线", "branch_count": 4},
    )
    assert branches.status_code == 200
    branch_id = branches.json()["branches"][0]["id"]

    plan = client.post(
        f"/api/projects/{project_id}/chapter-plan",
        json={"branch_id": branch_id, "chapter_count": 1, "target_words_per_chapter": 900},
    )
    assert plan.status_code == 200
    plan_ids = [item["id"] for item in (plan.json().get("plans") or [])]
    assert plan_ids

    class _FakeContinueTool:
        def __init__(self, *_args, **_kwargs):
            pass

        async def execute_async(self, ctx, payload):
            return type(
                "R",
                (),
                {
                    "status": "success",
                    "payload": {
                        "chapter_text": "{\"title\":\"测试标题\",\"content\":\"测试正文\"}",
                        "new_events": [],
                    },
                },
            )()

    with patch("application.services.v2_workflow_service.ContinueWritingTool", _FakeContinueTool):
        write = client.post(
            f"/api/projects/{project_id}/write",
            json={"plan_ids": plan_ids, "auto_commit": True},
        )
    assert write.status_code == 200
    latest_chapter = write.json().get("latest_chapter") or {}
    assert latest_chapter.get("number", 0) >= max_before + 1
    assert str(latest_chapter.get("title") or "").strip() != ""

    detail_after = client.get(f"/api/novels/{novel_id}").json()
    max_after = max(ch["number"] for ch in detail_after.get("chapters") or [])
    assert max_after >= max_before + 1
