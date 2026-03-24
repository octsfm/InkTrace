from __future__ import annotations

import tempfile
from pathlib import Path

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
        data={"project_name": "最终验收链路", "genre": "xuanhuan", "auto_organize": "true"},
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
