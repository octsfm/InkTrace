from __future__ import annotations

import re
import uuid

from application.services.logging_service import build_log_context, get_logger
from domain.constants.story_enums import GENERATION_STAGE_STRUCTURAL


class ContinuationWriter:
    def __init__(self, workflow_service):
        self.workflow_service = workflow_service
        self.logger = get_logger(__name__)

    async def write(
        self,
        project,
        chapter_plan: dict,
        chapter_task: dict,
        continuation_context,
        memory: dict,
        chapters: list,
    ) -> dict:
        result = await self.workflow_service.prompt_ai_service.generate_structural_draft(
            chapter_task=chapter_task,
            continuation_context=continuation_context,
            global_constraints=memory.get("global_constraints") or {},
            target_word_count=int(chapter_plan["target_words"]),
        )
        if not result or not str(result.get("content") or "").strip():
            self.logger.error(
                "结构稿生成失败",
                extra=build_log_context(
                    event="structural_draft_failed",
                    project_id=continuation_context.project_id,
                    chapter_id=chapter_task.get("chapter_id") or "",
                    chapter_number=chapter_task.get("chapter_number") or 0,
                    plan_id=str(chapter_plan.get("id") or ""),
                    branch_id=str(chapter_plan.get("branch_id") or ""),
                    used_structural_fallback=False,
                ),
            )
            raise ValueError("结构稿生成失败")
        normalized = self.workflow_service._normalize_generated_chapter_output(
            chapter_text=str(result.get("content") or result.get("chapter_text") or ""),
            plan_title=str(chapter_plan.get("title") or ""),
            chapter_number=int(chapter_plan.get("chapter_number") or 0),
        )
        title = str(result.get("title") or normalized["title"] or "").strip()
        if not title or re.fullmatch(r"第?\d+章?", title):
            title = await self.workflow_service.prompt_ai_service.backfill_title(
                chapter_task=chapter_task,
                content=str(result.get("content") or normalized["content"] or ""),
                recent_context={
                    "project_id": continuation_context.project_id,
                    "last_chapter_tail": continuation_context.last_chapter_tail,
                    "recent_chapter_memories": continuation_context.recent_chapter_memories,
                },
            )
        structural_draft = {
            "id": f"{GENERATION_STAGE_STRUCTURAL}_{uuid.uuid4().hex[:10]}",
            "project_id": continuation_context.project_id,
            "chapter_id": str(chapter_task.get("chapter_id") or ""),
            "chapter_number": int(normalized["chapter_number"] or 0),
            "title": self.workflow_service._ensure_chapter_title(title, int(normalized["chapter_number"] or 0)),
            "content": str(result.get("content") or normalized["content"] or ""),
            "source_task_id": str(chapter_task.get("id") or chapter_plan.get("id") or ""),
            "model_name": "continue-writing",
            "used_fallback": False,
            "generation_stage": GENERATION_STAGE_STRUCTURAL,
            "version": 1,
        }
        self.logger.info(
            "结构稿生成完成",
            extra=build_log_context(
                event="structural_draft_generated",
                project_id=continuation_context.project_id,
                chapter_id=structural_draft["chapter_id"],
                chapter_number=structural_draft["chapter_number"],
                plan_id=str(chapter_plan.get("id") or ""),
                branch_id=str(chapter_plan.get("branch_id") or ""),
                used_structural_fallback=False,
            ),
        )
        return {"result": result, "structural_draft": structural_draft}
