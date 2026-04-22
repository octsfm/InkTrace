from types import SimpleNamespace

from fastapi.testclient import TestClient

from presentation.api.app import app
from presentation.api.dependencies import (
    get_capacity_planner_service,
    get_content_service,
    get_organize_job_repo,
    get_project_service,
    get_v2_workflow_service,
)


class _FakeContentService:
    def get_novel_text(self, novel_id: str):
        return ("第1章 长篇测试内容\n\n" * 300)

    def get_outline_context(self, novel_id: str):
        return {
            "premise": "主线",
            "story_background": "背景",
            "world_setting": "规则",
            "outline_digest": {"premise": "主线", "summary": "背景", "style_guidance": "规则"},
        }


class _FakeProjectService:
    def ensure_project_for_novel(self, novel_id):
        return SimpleNamespace(id=SimpleNamespace(value="proj_long"), novel_id=novel_id)

    def get_project_by_novel(self, novel_id):
        return SimpleNamespace(id=SimpleNamespace(value="proj_long"), novel_id=novel_id)


class _FakeV2Service:
    async def organize_project(self, *args, **kwargs):
        return {"memory_view": {"current_progress": "ok"}}

    def get_memory(self, project_id: str):
        return {}


class _FakeOrganizeJobRepo:
    def find_by_novel_id(self, novel_id):
        return None

    def save(self, job):
        return None


class _FakeCapacityPlanner:
    def build_plan(self, model_name: str, max_context_tokens: int):
        return {"model_name": "moonshot-v1-8k", "max_context_tokens": 8192}


def test_organize_long_novel_8k_not_directly_failed():
    app.dependency_overrides[get_content_service] = lambda: _FakeContentService()
    app.dependency_overrides[get_project_service] = lambda: _FakeProjectService()
    app.dependency_overrides[get_v2_workflow_service] = lambda: _FakeV2Service()
    app.dependency_overrides[get_organize_job_repo] = lambda: _FakeOrganizeJobRepo()
    app.dependency_overrides[get_capacity_planner_service] = lambda: _FakeCapacityPlanner()
    client = TestClient(app)
    try:
        resp = client.post("/api/content/organize/start/novel_long_8k?force_rebuild=true")
        assert resp.status_code in {200, 202}
        assert resp.json().get("status") in {"started", "running"}
    finally:
        app.dependency_overrides.clear()
