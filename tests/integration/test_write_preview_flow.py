import tempfile
from pathlib import Path

from fastapi.testclient import TestClient

from presentation.api.app import app
from presentation.api.dependencies import get_v2_workflow_service


def _create_temp_novel_file() -> str:
    fd, path = tempfile.mkstemp(suffix=".txt")
    Path(path).write_text("第1章 开始\n主角出场。\n\n第2章 推进\n危机升级。", encoding="utf-8")
    return path


class _FakeTool:
    def __init__(self, *_args, **_kwargs):
        pass

    async def execute_async(self, *_args, **_kwargs):
        return type("Result", (), {"status": "success", "payload": {"chapter_text": "第3章 追击\n主角继续追击，门后传来异响。"}})()


class _FakePromptAIService:
    async def generate_structural_draft(self, *_args, **_kwargs):
        return {
            "title": "门后追击",
            "content": "主角继续追击，门后传来异响。",
            "new_events": [],
            "possible_continuity_flags": [],
            "used_fallback": False,
        }

    async def generate_chapter_task(self, *_args, **_kwargs):
        return {
            "chapter_function": "continue_crisis",
            "goals": ["推进危机"],
            "must_continue_points": ["门后异响"],
            "forbidden_jumps": ["不得突然跳场"],
            "required_foreshadowing_action": "advance",
            "required_hook_strength": "medium",
            "pace_target": "fast",
            "opening_continuation": "紧接门后异响",
            "chapter_payoff": "门后异响升级",
            "style_bias": "fast",
            "used_fallback": False,
        }

    async def rewrite_detemplated_draft(self, structural_draft, *_args, **_kwargs):
        return {
            "content": structural_draft["content"] + "\n去模板改写版",
            "used_fallback": False,
            "integrity_failed": False,
            "display_fallback_to_structural": False,
        }

    async def check_draft_integrity(self, *_args, **_kwargs):
        return {
            "event_integrity_ok": True,
            "motivation_integrity_ok": True,
            "foreshadowing_integrity_ok": True,
            "hook_integrity_ok": True,
            "continuity_ok": True,
            "risk_notes": [],
        }

    async def backfill_title(self, *_args, **_kwargs):
        return "门后追击"


def test_write_preview_flow_returns_dual_drafts():
    original_provider = app.dependency_overrides.get(get_v2_workflow_service)

    def _override_workflow_service():
        service = get_v2_workflow_service()
        service.continue_writing_tool_cls = _FakeTool
        service.prompt_ai_service = _FakePromptAIService()
        return service

    app.dependency_overrides[get_v2_workflow_service] = _override_workflow_service
    client = TestClient(app)
    novel_path = _create_temp_novel_file()
    try:
        resp = client.post(
            "/api/projects/import",
            json={
                "project_name": "预览链项目",
                "author": "测试作者",
                "genre": "xuanhuan",
                "novel_file_path": novel_path,
                "outline_file_path": "",
                "auto_organize": False,
            },
        )
        project_id = resp.json()["project_id"]
        branch = client.post(f"/api/projects/{project_id}/branches", json={"direction_hint": "推进主线", "branch_count": 3}).json()
        branch_id = branch["branches"][0]["id"]
        plans = client.post(f"/api/projects/{project_id}/chapter-plan", json={"branch_id": branch_id, "chapter_count": 1, "target_words_per_chapter": 1600}).json()
        plan_id = plans["plans"][0]["id"]
        preview = client.post(f"/api/projects/{project_id}/write/preview", json={"plan_id": plan_id, "target_word_count": 1600})
        assert preview.status_code == 200
        payload = preview.json()
        assert payload["chapter_task"]
        assert payload["structural_draft"]["content"]
        assert payload["detemplated_draft"]["content"]
        assert "used_structural_fallback" in payload
    finally:
        if original_provider:
            app.dependency_overrides[get_v2_workflow_service] = original_provider
        else:
            app.dependency_overrides.pop(get_v2_workflow_service, None)
