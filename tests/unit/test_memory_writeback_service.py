import asyncio
from dataclasses import dataclass, field

from application.services.memory_writeback_service import MemoryWritebackService


@dataclass
class _FakeId:
    value: str


@dataclass
class _FakeProject:
    id: _FakeId = field(default_factory=lambda: _FakeId("project-1"))
    novel_id: _FakeId = field(default_factory=lambda: _FakeId("novel-1"))


class _CollectRepo:
    def __init__(self):
        self.items = []

    def save(self, item):
        self.items.append(item)


class _V2Repo:
    def save_project_memory(self, payload):
        self.memory = payload

    def save_memory_view(self, payload):
        self.view = payload


class _Workflow:
    class _PromptAIService:
        async def extract_continuation_memory(self, **_kwargs):
            return {
                "scene_summary": "最终稿内容",
                "scene_state": {"environment": "现场"},
                "protagonist_state": {"current_goal": "推进"},
                "active_characters": [],
                "active_conflicts": ["危机加深"],
                "immediate_threads": ["异常升级"],
                "long_term_threads": ["继续危机"],
                "recent_reveals": ["推进"],
                "must_continue_points": ["继续危机"],
                "forbidden_jumps": ["不得跳场"],
                "tone_and_pacing": {"pace": "fast"},
                "last_hook": "门后异响",
                "used_fallback": False,
            }

    def __init__(self):
        self.chapter_repo = _CollectRepo()
        self.structural_draft_repo = _CollectRepo()
        self.detemplated_draft_repo = _CollectRepo()
        self.draft_integrity_check_repo = _CollectRepo()
        self.chapter_task_repo = _CollectRepo()
        self.chapter_analysis_memory_repo = _CollectRepo()
        self.chapter_continuation_memory_repo = _CollectRepo()
        self.v2_repo = _V2Repo()
        self.prompt_ai_service = self._PromptAIService()

    def _to_project_memory_payload(self, project_id, memory):
        return {"project_id": project_id, "memory": memory}

    def _sync_primary_repositories(self, *_args, **_kwargs):
        return None

    def _to_memory_view_payload(self, project_id, memory):
        return {"project_id": project_id, "current_state": memory.get("current_state") or {}}

    def get_memory_view(self, project_id):
        return {"project_id": project_id}


def test_memory_writeback_service_saves_dual_memory():
    workflow = _Workflow()
    service = MemoryWritebackService(workflow)
    item = {
        "allocation": {"chapter_number": 12, "final_title": "第12章 异常"},
        "chapter_plan": {"id": "plan-1", "branch_id": "b1", "goal": "推进", "progression": "异常升级", "conflict": "危机加深", "ending_hook": "门后异响"},
        "chapter_task": {"id": "task-1", "project_id": "project-1", "branch_id": "b1", "chapter_function": "continue_crisis", "goals": ["推进"], "must_continue_points": ["继续危机"], "forbidden_jumps": ["不得跳场"], "required_foreshadowing_action": "advance", "required_hook_strength": "medium", "pace_target": "fast", "opening_continuation": "承接尾部", "chapter_payoff": "门后异响", "style_bias": "fast"},
        "structural_draft": {"id": "s1", "project_id": "project-1", "content": "结构稿内容", "source_task_id": "task-1", "generation_stage": "structural"},
        "detemplated_draft": {"id": "d1", "project_id": "project-1", "content": "最终稿内容", "based_on_structural_draft_id": "s1", "style_requirements_snapshot": {}, "generation_stage": "detemplated", "display_fallback_to_structural": False},
        "integrity_check": {"id": "i1", "event_integrity_ok": True, "motivation_integrity_ok": True, "foreshadowing_integrity_ok": True, "hook_integrity_ok": True, "continuity_ok": True, "risk_notes": []},
    }
    result = asyncio.run(service.write_batch(_FakeProject(), {"chapter_summaries": [], "current_state": {}}, [item], auto_commit=True))
    assert result["chapter_saved"] is True
    assert result["memory_refreshed"] is True
    assert len(workflow.chapter_analysis_memory_repo.items) == 1
    assert len(workflow.chapter_continuation_memory_repo.items) == 1
