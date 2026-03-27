from __future__ import annotations

import asyncio
from types import SimpleNamespace

from fastapi.testclient import TestClient

from domain.types import NovelId
from presentation.api.app import app
from presentation.api.dependencies import (
    get_content_service,
    get_organize_job_repo,
    get_project_service,
    get_v2_workflow_service,
)


class _FakeContentService:
    def import_novel(self, request):
        return SimpleNamespace(model_dump=lambda: {"id": request.novel_id, "title": "示例"})


class _FakeProjectService:
    def ensure_project_for_novel(self, novel_id: NovelId):
        return SimpleNamespace(id=SimpleNamespace(value="proj_v2"), novel_id=novel_id)

    def get_project_by_novel(self, novel_id: NovelId):
        return SimpleNamespace(id=SimpleNamespace(value="proj_v2"), novel_id=novel_id)


class _FakeV2Service:
    async def organize_project(
        self,
        project_id: str,
        mode: str,
        rebuild_memory: bool,
        progress_callback=None,
        resume_from: int = 0,
        checkpoint_memory=None,
    ):
        if callable(progress_callback):
            await progress_callback(
                {
                    "status": "running",
                    "stage": "chapter_analysis",
                    "current": 1,
                    "total": 2,
                    "percent": 50,
                    "message": "正在分析第1/2章：示例",
                    "current_chapter_title": "示例",
                    "resumable": True,
                }
            )
            await progress_callback(
                {
                    "status": "done",
                    "stage": "done",
                    "current": 2,
                    "total": 2,
                    "percent": 100,
                    "message": "整理完成（2/2）",
                    "current_chapter_title": "",
                    "resumable": False,
                }
            )
        await asyncio.sleep(0.05)
        return {"memory_view": {"current_progress": "ok"}}

    def get_memory(self, project_id: str):
        return {"world_facts": {}, "chapter_summaries": []}

    def get_memory_view(self, project_id: str):
        return {"outline_summary": ["大纲摘要"], "current_progress": "推进中"}


class _FakeOrganizeJobRepo:
    def __init__(self):
        self.job = None

    def find_by_novel_id(self, novel_id: NovelId):
        return self.job

    def save(self, job):
        self.job = job


def test_content_import_proxy_to_v2():
    app.dependency_overrides[get_content_service] = lambda: _FakeContentService()
    app.dependency_overrides[get_project_service] = lambda: _FakeProjectService()
    app.dependency_overrides[get_v2_workflow_service] = lambda: _FakeV2Service()
    app.dependency_overrides[get_organize_job_repo] = lambda: _FakeOrganizeJobRepo()
    client = TestClient(app)
    try:
        resp = client.post("/api/content/import", json={"novel_id": "novel_1", "file_path": "d:/a.txt"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["project_id"] == "proj_v2"
        assert data["analysis_status"] == "done"
    finally:
        app.dependency_overrides.clear()


def test_content_organize_proxy_to_v2():
    app.dependency_overrides[get_project_service] = lambda: _FakeProjectService()
    app.dependency_overrides[get_v2_workflow_service] = lambda: _FakeV2Service()
    app.dependency_overrides[get_organize_job_repo] = lambda: _FakeOrganizeJobRepo()
    client = TestClient(app)
    try:
        resp = client.post("/api/content/organize/novel_1?force_rebuild=true")
        assert resp.status_code == 200
        data = resp.json()
        assert data["project_id"] == "proj_v2"
        assert data["status"] == "done"
    finally:
        app.dependency_overrides.clear()


def test_content_memory_compat_returns_v2_payload():
    app.dependency_overrides[get_project_service] = lambda: _FakeProjectService()
    app.dependency_overrides[get_v2_workflow_service] = lambda: _FakeV2Service()
    app.dependency_overrides[get_organize_job_repo] = lambda: _FakeOrganizeJobRepo()
    client = TestClient(app)
    try:
        resp = client.get("/api/content/memory/novel_1")
        assert resp.status_code == 200
        data = resp.json()
        assert data["project_id"] == "proj_v2"
        assert data["compat_mode"] is True
        assert data["route"] == "content_compat_v2"
        assert "memory_view" in data
        assert "?" not in "；".join(data["memory_view"].get("outline_summary") or [])
    finally:
        app.dependency_overrides.clear()


def test_content_organize_start_stop_resume():
    repo = _FakeOrganizeJobRepo()
    app.dependency_overrides[get_project_service] = lambda: _FakeProjectService()
    app.dependency_overrides[get_v2_workflow_service] = lambda: _FakeV2Service()
    app.dependency_overrides[get_organize_job_repo] = lambda: repo
    client = TestClient(app)
    try:
        started = client.post("/api/content/organize/start/novel_1?force_rebuild=true")
        assert started.status_code == 200
        assert started.json()["status"] in {"started", "running"}
        progress = client.get("/api/content/organize/progress/novel_1")
        assert progress.status_code == 200
        payload = progress.json()
        assert payload["current"] >= 0
        assert "stage" in payload
        stopped = client.post("/api/content/organize/stop/novel_1")
        assert stopped.status_code == 200
        assert stopped.json()["status"] == "stopped"
        resumed = client.post("/api/content/organize/resume/novel_1")
        assert resumed.status_code == 200
        assert resumed.json()["status"] in {"resumed", "running"}
    finally:
        app.dependency_overrides.clear()
