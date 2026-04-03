from __future__ import annotations

from types import SimpleNamespace

from fastapi.testclient import TestClient

from domain.types import NovelId
from presentation.api.app import app
from presentation.api.dependencies import (
    get_chapter_repo,
    get_llm_factory,
    get_novel_repo,
    get_project_service,
    get_v2_workflow_service,
)


class _FakeProjectService:
    def get_project_by_novel(self, novel_id: NovelId):
        return SimpleNamespace(id=SimpleNamespace(value="proj_v2"), novel_id=novel_id)

    def ensure_project_for_novel(self, novel_id: NovelId):
        return SimpleNamespace(id=SimpleNamespace(value="proj_v2"), novel_id=novel_id)

    def get_memory_by_novel(self, novel_id: NovelId):
        return {"characters": []}

    def bind_memory_to_novel(self, novel_id: NovelId, memory):
        return None


class _FakeV2Service:
    async def generate_branches(self, project_id: str, direction_hint: str, branch_count: int):
        return {"branches": [{"id": "branch_001", "title": "分支A", "summary": "推进A"}]}

    def get_memory(self, project_id: str):
        return {"chapter_summaries": ["第1章摘要"]}

    def create_chapter_plan(
        self,
        project_id: str,
        branch_id: str,
        chapter_count: int,
        target_words_per_chapter: int,
        planning_mode: str = "light_planning",
        target_arc_id: str = "",
        allow_deep_planning: bool = False,
    ):
        return {"plans": [{"id": "plan_001"}]}

    async def execute_writing(self, project_id: str, plan_ids, auto_commit: bool):
        return {"latest_content": "这是v2生成内容"}

    async def refresh_memory(self, project_id: str, from_chapter_number: int, to_chapter_number: int):
        return {"ok": True}


class _FakeChapterRepo:
    def find_by_novel(self, novel_id: NovelId):
        return [SimpleNamespace(number=2, content="已存在章节")]


class _FakeNovelRepo:
    def find_by_id(self, novel_id: NovelId):
        return None


class _FakeLLMFactory:
    primary_client = SimpleNamespace(api_key="")
    backup_client = SimpleNamespace(api_key="")


def test_writing_branches_proxy_to_v2():
    app.dependency_overrides[get_project_service] = lambda: _FakeProjectService()
    app.dependency_overrides[get_v2_workflow_service] = lambda: _FakeV2Service()
    app.dependency_overrides[get_chapter_repo] = lambda: _FakeChapterRepo()
    app.dependency_overrides[get_llm_factory] = lambda: _FakeLLMFactory()
    client = TestClient(app)
    try:
        resp = client.post(
            "/api/writing/branches",
            json={"novel_id": "novel_x", "branch_count": 4, "direction_hint": "推进主线"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["branches"][0]["id"] == "branch_001"
        assert data["metadata"]["task_role"] == "CHAPTER_PLANNING"
        assert data["metadata"]["routed_model"] == "kimi"
    finally:
        app.dependency_overrides.clear()


def test_writing_continue_proxy_to_v2():
    app.dependency_overrides[get_project_service] = lambda: _FakeProjectService()
    app.dependency_overrides[get_v2_workflow_service] = lambda: _FakeV2Service()
    app.dependency_overrides[get_chapter_repo] = lambda: _FakeChapterRepo()
    app.dependency_overrides[get_novel_repo] = lambda: _FakeNovelRepo()
    app.dependency_overrides[get_llm_factory] = lambda: _FakeLLMFactory()
    client = TestClient(app)
    try:
        resp = client.post(
            "/api/writing/continue",
            json={"novel_id": "novel_x", "goal": "继续推进", "target_word_count": 1200},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["content"] == "这是v2生成内容"
        assert data["metadata"]["route"] == "v2_workflow"
        assert data["metadata"]["task_role"] == "CHAPTER_WRITING"
        assert data["metadata"]["routed_model"] == "deepseek"
    finally:
        app.dependency_overrides.clear()


def test_writing_plan_proxy_to_v2():
    app.dependency_overrides[get_project_service] = lambda: _FakeProjectService()
    app.dependency_overrides[get_v2_workflow_service] = lambda: _FakeV2Service()
    app.dependency_overrides[get_chapter_repo] = lambda: _FakeChapterRepo()
    app.dependency_overrides[get_novel_repo] = lambda: _FakeNovelRepo()
    app.dependency_overrides[get_llm_factory] = lambda: _FakeLLMFactory()
    client = TestClient(app)
    try:
        resp = client.post(
            "/api/writing/plan",
            json={"novel_id": "novel_x", "goal": "推进", "chapter_count": 2},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
    finally:
        app.dependency_overrides.clear()


def test_writing_generate_proxy_to_v2():
    app.dependency_overrides[get_project_service] = lambda: _FakeProjectService()
    app.dependency_overrides[get_v2_workflow_service] = lambda: _FakeV2Service()
    app.dependency_overrides[get_chapter_repo] = lambda: _FakeChapterRepo()
    app.dependency_overrides[get_novel_repo] = lambda: _FakeNovelRepo()
    app.dependency_overrides[get_llm_factory] = lambda: _FakeLLMFactory()
    client = TestClient(app)
    try:
        resp = client.post(
            "/api/writing/generate",
            json={"novel_id": "novel_x", "goal": "推进", "target_word_count": 1200},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["metadata"]["route"] == "v2_preview"
        assert data["metadata"]["task_role"] == "CHAPTER_WRITING"
        assert data["metadata"]["routed_model"] == "deepseek"
    finally:
        app.dependency_overrides.clear()
