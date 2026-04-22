from __future__ import annotations

import asyncio
import time
from types import SimpleNamespace

from fastapi.testclient import TestClient

from domain.entities.organize_job import OrganizeJob
from domain.exceptions import APIKeyError, RateLimitError
from domain.types import NovelId
from domain.types import OrganizeJobStatus
from presentation.api.app import app
from presentation.api.dependencies import (
    get_capacity_planner_service,
    get_content_service,
    get_organize_job_repo,
    get_project_service,
    get_v2_workflow_service,
)


class _FakeContentService:
    def import_novel(self, request):
        return SimpleNamespace(model_dump=lambda: {"id": request.novel_id, "title": "示例"})


class _FakeContentQueryService(_FakeContentService):
    def get_novel_text(self, novel_id: str):
        return ("第1章 测试内容\n\n" * 200)

    def get_outline_context(self, novel_id: str):
        return {
            "premise": "主线测试",
            "story_background": "背景测试",
            "world_setting": "世界规则测试",
            "outline_digest": {"premise": "主线测试", "summary": "背景测试", "style_guidance": "世界规则测试"},
        }


class _FakeProjectService:
    def ensure_project_for_novel(self, novel_id: NovelId):
        return SimpleNamespace(id=SimpleNamespace(value="proj_v2"), novel_id=novel_id)

    def get_project_by_novel(self, novel_id: NovelId):
        return SimpleNamespace(id=SimpleNamespace(value="proj_v2"), novel_id=novel_id)


class _FakeV2Service:
    def __init__(self):
        self.calls = []

    async def organize_project(
        self,
        project_id: str,
        mode: str,
        rebuild_memory: bool,
        progress_callback=None,
        resume_from: int = 0,
        checkpoint_memory=None,
        capacity_plan=None,
    ):
        self.calls.append(
            {
                "project_id": project_id,
                "mode": mode,
                "rebuild_memory": rebuild_memory,
                "capacity_plan": capacity_plan or {},
            }
        )
        if callable(progress_callback):
            await progress_callback({"status": "running", "stage": "chapter_analysis", "current": 1, "total": 2, "percent": 50, "message": "正在分析第1/2章：示例", "current_chapter_title": "示例", "resumable": True})
            await asyncio.sleep(0.08)
            await progress_callback({"status": "running", "stage": "chapter_analysis", "current": 2, "total": 2, "percent": 100, "message": "正在分析第2/2章：第二章", "current_chapter_title": "第二章", "resumable": True})
            await asyncio.sleep(0.08)
            await progress_callback({"status": "done", "stage": "done", "current": 2, "total": 2, "percent": 100, "message": "整理完成（2/2）", "current_chapter_title": "", "resumable": False})
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


class _FailingV2Service:
    async def organize_project(
        self,
        project_id: str,
        mode: str,
        rebuild_memory: bool,
        progress_callback=None,
        resume_from: int = 0,
        checkpoint_memory=None,
        capacity_plan=None,
    ):
        raise APIKeyError("Kimi", "API密钥无效")

    def get_memory(self, project_id: str):
        return {}


class _RateLimitedV2Service:
    async def organize_project(
        self,
        project_id: str,
        mode: str,
        rebuild_memory: bool,
        progress_callback=None,
        resume_from: int = 0,
        checkpoint_memory=None,
        capacity_plan=None,
    ):
        raise RateLimitError("Kimi", retry_after=7)

    def get_memory(self, project_id: str):
        return {}


class _NoBaselineV2Service(_FakeV2Service):
    def can_rebuild_global(self, project_id: str) -> bool:
        return False


class _FakeCapacityPlannerService:
    def build_plan(self, model_name: str, max_context_tokens: int):
        return {
            "model_name": model_name,
            "max_context_tokens": max_context_tokens,
            "chapter_soft_limit_chars": 12000,
            "chunk_size_chars": 4000,
            "batch_size_chapters": 8,
            "need_outline_digest": True,
            "enable_chunking": True,
            "strategy": "chunked_chapter_first",
        }


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
    app.dependency_overrides[get_content_service] = lambda: _FakeContentQueryService()
    app.dependency_overrides[get_project_service] = lambda: _FakeProjectService()
    app.dependency_overrides[get_capacity_planner_service] = lambda: _FakeCapacityPlannerService()
    service = _FakeV2Service()
    app.dependency_overrides[get_v2_workflow_service] = lambda: service
    app.dependency_overrides[get_organize_job_repo] = lambda: _FakeOrganizeJobRepo()
    client = TestClient(app)
    try:
        resp = client.post("/api/content/organize/novel_1?force_rebuild=true")
        assert resp.status_code == 200
        data = resp.json()
        assert data["project_id"] == "proj_v2"
        assert data["status"] == "done"
        assert service.calls[-1]["mode"] == "full_reanalyze"
        assert service.calls[-1]["capacity_plan"].get("strategy") == "chunked_chapter_first"
    finally:
        app.dependency_overrides.clear()


def test_content_retry_defaults_to_full_reanalyze():
    repo = _FakeOrganizeJobRepo()
    service = _FakeV2Service()
    app.dependency_overrides[get_content_service] = lambda: _FakeContentQueryService()
    app.dependency_overrides[get_project_service] = lambda: _FakeProjectService()
    app.dependency_overrides[get_capacity_planner_service] = lambda: _FakeCapacityPlannerService()
    app.dependency_overrides[get_v2_workflow_service] = lambda: service
    app.dependency_overrides[get_organize_job_repo] = lambda: repo
    client = TestClient(app)
    try:
        started = client.post("/api/content/organize/retry/novel_retry")
        assert started.status_code == 200
        assert started.json()["status"] in {"started", "running"}
        time.sleep(0.25)
        assert service.calls[-1]["mode"] == "full_reanalyze"
        assert service.calls[-1]["rebuild_memory"] is True
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
    app.dependency_overrides[get_content_service] = lambda: _FakeContentQueryService()
    app.dependency_overrides[get_project_service] = lambda: _FakeProjectService()
    app.dependency_overrides[get_capacity_planner_service] = lambda: _FakeCapacityPlannerService()
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
        assert "strategy" in payload
        stopped = client.post("/api/content/organize/stop/novel_1")
        assert stopped.status_code == 200
        assert stopped.json()["status"] == "stopped"
        resumed = client.post("/api/content/organize/resume/novel_1")
        assert resumed.status_code == 200
        assert resumed.json()["status"] in {"resumed", "running"}
    finally:
        app.dependency_overrides.clear()


def test_content_organize_pause_resume_done():
    repo = _FakeOrganizeJobRepo()
    app.dependency_overrides[get_content_service] = lambda: _FakeContentQueryService()
    app.dependency_overrides[get_project_service] = lambda: _FakeProjectService()
    app.dependency_overrides[get_capacity_planner_service] = lambda: _FakeCapacityPlannerService()
    app.dependency_overrides[get_v2_workflow_service] = lambda: _FakeV2Service()
    app.dependency_overrides[get_organize_job_repo] = lambda: repo
    client = TestClient(app)
    try:
        started = client.post("/api/content/organize/start/novel_pause?force_rebuild=true")
        assert started.status_code == 200
        paused = client.post("/api/content/organize/pause/novel_pause")
        assert paused.status_code == 200
        assert paused.json()["status"] in {"pause_requested", "paused"}
        for _ in range(10):
            progress = client.get("/api/content/organize/progress/novel_pause").json()
            if progress["status"] == "paused":
                break
            time.sleep(0.05)
        assert progress["status"] in {"paused", "done"}
        resumed = client.post("/api/content/organize/resume/novel_pause")
        assert resumed.status_code == 200
        for _ in range(12):
            progress = client.get("/api/content/organize/progress/novel_pause").json()
            if progress["status"] == "done":
                break
            time.sleep(0.05)
        assert progress["status"] in {"running", "done", "paused"}
    finally:
        app.dependency_overrides.clear()


def test_content_organize_cancelled():
    repo = _FakeOrganizeJobRepo()
    app.dependency_overrides[get_content_service] = lambda: _FakeContentQueryService()
    app.dependency_overrides[get_project_service] = lambda: _FakeProjectService()
    app.dependency_overrides[get_capacity_planner_service] = lambda: _FakeCapacityPlannerService()
    app.dependency_overrides[get_v2_workflow_service] = lambda: _FakeV2Service()
    app.dependency_overrides[get_organize_job_repo] = lambda: repo
    client = TestClient(app)
    try:
        started = client.post("/api/content/organize/start/novel_cancel?force_rebuild=true")
        assert started.status_code == 200
        cancelled = client.post("/api/content/organize/cancel/novel_cancel")
        assert cancelled.status_code == 200
        assert cancelled.json()["status"] in {"cancelling", "cancelled"}
        for _ in range(10):
            progress = client.get("/api/content/organize/progress/novel_cancel").json()
            if progress["status"] == "cancelled":
                break
            time.sleep(0.05)
        assert progress["status"] in {"cancelled", "done"}
    finally:
        app.dependency_overrides.clear()


def test_content_organize_progress_recovers_stale_running_job():
    repo = _FakeOrganizeJobRepo()
    repo.job = OrganizeJob(
        novel_id=NovelId("novel_stale"),
        total_chapters=12,
        completed_chapters=5,
        status=OrganizeJobStatus.RUNNING,
        stage="chapter_analysis",
        message="正在分析第5章",
        current_chapter_title="第5章",
    )
    app.dependency_overrides[get_project_service] = lambda: _FakeProjectService()
    app.dependency_overrides[get_v2_workflow_service] = lambda: _FakeV2Service()
    app.dependency_overrides[get_organize_job_repo] = lambda: repo
    client = TestClient(app)
    try:
        progress = client.get("/api/content/organize/progress/novel_stale")
        assert progress.status_code == 200
        payload = progress.json()
        assert payload["status"] == "paused"
        assert payload["resumable"] is True
        assert "继续整理" in payload["message"]
        assert payload.get("can_rebuild_global") is False
    finally:
        app.dependency_overrides.clear()


def test_content_organize_progress_surfaces_kimi_api_key_error():
    repo = _FakeOrganizeJobRepo()
    app.dependency_overrides[get_content_service] = lambda: _FakeContentQueryService()
    app.dependency_overrides[get_project_service] = lambda: _FakeProjectService()
    app.dependency_overrides[get_v2_workflow_service] = lambda: _FailingV2Service()
    app.dependency_overrides[get_organize_job_repo] = lambda: repo
    client = TestClient(app)
    try:
        started = client.post("/api/content/organize/start/novel_bad_key?force_rebuild=true")
        assert started.status_code == 200
        for _ in range(20):
            progress = client.get("/api/content/organize/progress/novel_bad_key").json()
            if progress["status"] == "error":
                break
            time.sleep(0.05)
        assert progress["status"] == "error"
        assert "Kimi API Key" in progress["message"]
        assert "更新后重新整理" in progress["message"]
    finally:
        app.dependency_overrides.clear()


def test_content_organize_progress_surfaces_rate_limit_with_actionable_hint():
    repo = _FakeOrganizeJobRepo()
    app.dependency_overrides[get_content_service] = lambda: _FakeContentQueryService()
    app.dependency_overrides[get_project_service] = lambda: _FakeProjectService()
    app.dependency_overrides[get_v2_workflow_service] = lambda: _RateLimitedV2Service()
    app.dependency_overrides[get_organize_job_repo] = lambda: repo
    client = TestClient(app)
    try:
        started = client.post("/api/content/organize/start/novel_rate_limited?force_rebuild=true")
        assert started.status_code == 200
        for _ in range(20):
            progress = client.get("/api/content/organize/progress/novel_rate_limited").json()
            if progress["status"] == "error":
                break
            time.sleep(0.05)
        assert progress["status"] == "error"
        assert "自动退避重试" in progress["message"]
        assert "7秒后" in progress["message"]
    finally:
        app.dependency_overrides.clear()


def test_content_organize_rebuild_global_requires_baseline():
    app.dependency_overrides[get_content_service] = lambda: _FakeContentQueryService()
    app.dependency_overrides[get_project_service] = lambda: _FakeProjectService()
    app.dependency_overrides[get_v2_workflow_service] = lambda: _NoBaselineV2Service()
    app.dependency_overrides[get_organize_job_repo] = lambda: _FakeOrganizeJobRepo()
    client = TestClient(app)
    try:
        resp = client.post("/api/content/organize/novel_no_baseline?mode=rebuild_global")
        assert resp.status_code == 409
        detail = resp.json().get("detail") or {}
        assert detail.get("code") == "REBUILD_BASELINE_MISSING"
    finally:
        app.dependency_overrides.clear()
