from fastapi.testclient import TestClient

from presentation.api.app import app
from presentation.api.dependencies import (
    get_chapter_repo,
    get_llm_factory,
    get_novel_repo,
    get_project_service,
    get_v2_workflow_service,
)
from tests.integration.test_writing_v2_proxy import _FakeLLMFactory, _FakeChapterRepo, _FakeNovelRepo, _FakeProjectService


class _V2ServiceRoles:
    async def generate_branches(self, project_id: str, direction_hint: str, branch_count: int):
        return {"branches": [{"id": "branch_001", "title": "分支A"}]}

    def get_memory(self, project_id: str):
        return {"chapter_summaries": ["第1章摘要"]}

    async def create_chapter_plan(self, project_id: str, branch_id: str, chapter_count: int, target_words_per_chapter: int, planning_mode: str = "light_planning", target_arc_id: str = "", allow_deep_planning: bool = False):
        return {"plans": [{"id": "plan_001"}]}

    async def execute_writing(self, project_id: str, plan_ids, auto_commit: bool):
        return {"latest_content": "v2内容"}

    async def refresh_memory(self, project_id: str, from_chapter_number: int, to_chapter_number: int):
        return {"ok": True}


def _make_client():
    app.dependency_overrides[get_project_service] = lambda: _FakeProjectService()
    app.dependency_overrides[get_v2_workflow_service] = lambda: _V2ServiceRoles()
    app.dependency_overrides[get_chapter_repo] = lambda: _FakeChapterRepo()
    app.dependency_overrides[get_novel_repo] = lambda: _FakeNovelRepo()
    app.dependency_overrides[get_llm_factory] = lambda: _FakeLLMFactory()
    return TestClient(app)


def test_branches_reports_kimi_role():
    client = _make_client()
    try:
        resp = client.post("/api/writing/branches", json={"novel_id": "n1", "branch_count": 3, "direction_hint": "推进"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["metadata"]["task_role"] == "CHAPTER_PLANNING"
        assert data["metadata"]["routed_model"] == "kimi"
    finally:
        app.dependency_overrides.clear()


def test_generate_and_continue_report_deepseek_role():
    client = _make_client()
    try:
        resp = client.post("/api/writing/generate", json={"novel_id": "n1", "goal": "推进", "target_word_count": 1200})
        assert resp.status_code == 200
        data = resp.json()
        assert data["metadata"]["task_role"] == "CHAPTER_WRITING"
        assert data["metadata"]["routed_model"] == "deepseek"

        resp2 = client.post("/api/writing/continue", json={"novel_id": "n1", "goal": "推进", "target_word_count": 1200})
        assert resp2.status_code == 200
        data2 = resp2.json()
        assert data2["metadata"]["task_role"] == "CHAPTER_WRITING"
        assert data2["metadata"]["routed_model"] == "deepseek"
    finally:
        app.dependency_overrides.clear()
