import asyncio
from datetime import datetime

from application.services.chapter_task_generator import ChapterTaskGenerator
from domain.entities.continuation_context import ContinuationContext


class _WorkflowService:
    class _PromptAIService:
        async def generate_chapter_task(self, *_args, **_kwargs):
            return {"used_fallback": True}

    def __init__(self):
        self.prompt_ai_service = self._PromptAIService()

    def _normalize_foreshadowing_action(self, value: str):
        return value or "advance"

    def _normalize_hook_strength(self, value: str):
        return value or "medium"

    def normalize_text_list(self, items, limit):
        result = []
        for item in items:
            text = str(item or "").strip()
            if text and text not in result:
                result.append(text)
            if len(result) >= limit:
                break
        return result


def test_chapter_task_generator_uses_context_not_only_seed():
    generator = ChapterTaskGenerator(_WorkflowService())
    context = ContinuationContext(
        project_id="p1",
        chapter_id="c9",
        chapter_number=10,
        recent_chapter_memories=[
            {
                "scene_summary": "上一章主角被追击",
                "must_continue_points": ["继续追击线"],
                "immediate_threads": ["现场危机未解"],
                "forbidden_jumps": ["不得突然切场"],
            }
        ],
        last_chapter_tail="主角刚推开门，背后传来脚步声。",
        relevant_characters=[{"name": "主角"}],
        relevant_foreshadowing=["门后异常"],
        global_constraints={"must_keep_threads": ["主线危机"]},
        chapter_outline={"goal": "推进"},
        chapter_task_seed={},
        style_requirements={"preferred_rhythm": "fast"},
        created_at=datetime.now(),
    )
    plan = {
        "id": "plan-1",
        "branch_id": "b1",
        "chapter_number": 10,
        "goal": "继续危机推进",
        "progression": "推进调查",
        "conflict": "追兵逼近",
        "ending_hook": "门后出现异常",
    }
    task = asyncio.run(generator.generate(context, plan))
    assert task["chapter_function"] == "continue_crisis"
    assert "继续追击线" in task["must_continue_points"]
    assert "主线危机" in task["must_continue_points"]
    assert "不得突然切场" in task["forbidden_jumps"]
    assert task["opening_continuation"]
    assert task["chapter_payoff"] == "门后出现异常"
