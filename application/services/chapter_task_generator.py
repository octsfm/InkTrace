from __future__ import annotations

from application.services.logging_service import build_log_context, get_logger
from domain.constants.story_constants import DEFAULT_FORESHADOWING_ACTION, DEFAULT_HOOK_STRENGTH, DEFAULT_PACE_TARGET
from domain.constants.story_enums import CHAPTER_FUNCTION_ADVANCE_INVESTIGATION, WRITING_STATUS_READY


class ChapterTaskGenerator:
    def __init__(self, workflow_service):
        self.workflow_service = workflow_service
        self.logger = get_logger(__name__)

    async def generate(self, continuation_context, chapter_plan: dict) -> dict:
        seed = chapter_plan.get("chapter_task_seed") if isinstance(chapter_plan.get("chapter_task_seed"), dict) else {}
        prompt_result = await self.workflow_service.prompt_ai_service.generate_chapter_task(continuation_context, chapter_plan)
        recent_memories = [item for item in (continuation_context.recent_chapter_memories or []) if isinstance(item, dict)]
        latest_memory = recent_memories[-1] if recent_memories else {}
        global_constraints = continuation_context.global_constraints or {}
        last_tail = str(continuation_context.last_chapter_tail or "").strip()
        dynamic_must_continue_points = []
        dynamic_must_continue_points.extend([str(x) for x in (latest_memory.get("must_continue_points") or []) if str(x).strip()])
        dynamic_must_continue_points.extend([str(x) for x in (latest_memory.get("immediate_threads") or []) if str(x).strip()])
        dynamic_must_continue_points.extend([str(x) for x in (global_constraints.get("must_keep_threads") or []) if str(x).strip()])
        dynamic_forbidden_jumps = []
        dynamic_forbidden_jumps.extend([str(x) for x in (latest_memory.get("forbidden_jumps") or []) if str(x).strip()])
        if last_tail:
            dynamic_forbidden_jumps.append("不得跳过上一章尾声现场")
        dynamic_forbidden_jumps.extend([f"不得遗失伏笔：{x}" for x in (continuation_context.relevant_foreshadowing or [])[:3]])
        chapter_payoff = (
            str(prompt_result.get("chapter_payoff") or "")
            or
            str(seed.get("chapter_payoff") or "")
            or str(chapter_plan.get("ending_hook") or "")
            or str(chapter_plan.get("progression") or "")
            or str(chapter_plan.get("goal") or "")
        )
        opening_continuation = (
            str(prompt_result.get("opening_continuation") or "")
            or
            str(seed.get("opening_continuation") or "")
            or str(latest_memory.get("scene_summary") or "")
            or last_tail[-80:]
        )
        chapter_function = str(prompt_result.get("chapter_function") or seed.get("chapter_function") or "")
        if not chapter_function:
            goal_text = f"{chapter_plan.get('goal') or ''} {chapter_plan.get('progression') or ''}"
            if "危机" in goal_text or "追击" in goal_text:
                chapter_function = "continue_crisis"
            elif "调查" in goal_text or "线索" in goal_text:
                chapter_function = "advance_investigation"
            elif "异常" in goal_text or "真相" in goal_text:
                chapter_function = "reveal_abnormal"
            else:
                chapter_function = CHAPTER_FUNCTION_ADVANCE_INVESTIGATION
        task = {
            "id": str(chapter_plan.get("id") or ""),
            "chapter_id": str(seed.get("chapter_id") or continuation_context.chapter_id or ""),
            "project_id": continuation_context.project_id,
            "branch_id": str(chapter_plan.get("branch_id") or ""),
            "chapter_number": int(chapter_plan.get("chapter_number") or continuation_context.chapter_number or 0),
            "chapter_function": chapter_function,
            "goals": [str(x) for x in (prompt_result.get("goals") or seed.get("goals") or [str(chapter_plan.get("goal") or ""), str(chapter_plan.get("progression") or "")]) if str(x).strip()],
            "must_continue_points": self.workflow_service.normalize_text_list([*(prompt_result.get("must_continue_points") or []), *(seed.get("must_continue_points") or []), *dynamic_must_continue_points], 8),
            "forbidden_jumps": self.workflow_service.normalize_text_list([*(prompt_result.get("forbidden_jumps") or []), *(seed.get("forbidden_jumps") or []), *dynamic_forbidden_jumps], 8),
            "required_foreshadowing_action": self.workflow_service._normalize_foreshadowing_action(str(prompt_result.get("required_foreshadowing_action") or seed.get("required_foreshadowing_action") or DEFAULT_FORESHADOWING_ACTION)),
            "required_hook_strength": self.workflow_service._normalize_hook_strength(str(prompt_result.get("required_hook_strength") or seed.get("required_hook_strength") or DEFAULT_HOOK_STRENGTH)),
            "pace_target": str(prompt_result.get("pace_target") or seed.get("pace_target") or DEFAULT_PACE_TARGET),
            "opening_continuation": opening_continuation,
            "chapter_payoff": chapter_payoff,
            "style_bias": str(prompt_result.get("style_bias") or seed.get("style_bias") or (continuation_context.style_requirements or {}).get("preferred_rhythm") or ""),
            "status": WRITING_STATUS_READY,
            "used_fallback": bool(prompt_result.get("used_fallback")),
        }
        self.logger.info(
            "章节任务生成完成",
            extra=build_log_context(
                event="chapter_task_generated",
                project_id=continuation_context.project_id,
                chapter_id=task["chapter_id"],
                chapter_number=task["chapter_number"],
                plan_id=str(chapter_plan.get("id") or ""),
                branch_id=task["branch_id"],
                used_structural_fallback=False,
            ),
        )
        return task
