from __future__ import annotations

import uuid

from application.services.logging_service import build_log_context, get_logger
from domain.constants.story_enums import GENERATION_STAGE_DETEMPLATED


class DetemplatingRewriter:
    def __init__(self, workflow_service):
        self.workflow_service = workflow_service
        self.logger = get_logger(__name__)

    async def rewrite(self, structural_draft: dict, chapter_task: dict, global_constraints: dict, style_requirements: dict) -> dict:
        branch_id = str(chapter_task.get("branch_id") or "")
        plan_id = str(chapter_task.get("id") or structural_draft.get("source_task_id") or "")
        try:
            prompt_result = await self.workflow_service.prompt_ai_service.rewrite_detemplated_draft(structural_draft, chapter_task, global_constraints or {}, style_requirements or {})
            content = str(prompt_result.get("content") or "")
            used_fallback = bool(prompt_result.get("used_fallback"))
        except Exception:
            content = structural_draft["content"]
            used_fallback = True
            self.logger.warning(
                "去模板化失败，回退结构稿",
                extra=build_log_context(
                    event="detemplating_rewrite_failed",
                    project_id=str(structural_draft.get("project_id") or ""),
                    chapter_id=str(structural_draft.get("chapter_id") or ""),
                    chapter_number=int(structural_draft.get("chapter_number") or 0),
                    plan_id=plan_id,
                    branch_id=branch_id,
                    used_structural_fallback=True,
                ),
            )
        detemplated_draft = {
            "id": f"{GENERATION_STAGE_DETEMPLATED}_{uuid.uuid4().hex[:10]}",
            "project_id": str(structural_draft.get("project_id") or ""),
            "chapter_id": str(structural_draft.get("chapter_id") or ""),
            "chapter_number": int(structural_draft.get("chapter_number") or 0),
            "title": str(structural_draft.get("title") or ""),
            "content": content,
            "based_on_structural_draft_id": str(structural_draft.get("id") or ""),
            "style_requirements_snapshot": style_requirements or {},
            "model_name": "detemplating-rewrite",
            "used_fallback": used_fallback,
            "integrity_failed": bool((locals().get("prompt_result") or {}).get("integrity_failed")),
            "display_fallback_to_structural": bool((locals().get("prompt_result") or {}).get("display_fallback_to_structural", used_fallback)),
            "generation_stage": GENERATION_STAGE_DETEMPLATED,
            "version": 1,
        }
        self.logger.info(
            "去模板化完成",
            extra=build_log_context(
                event="detemplating_rewrite_finished",
                project_id=str(structural_draft.get("project_id") or ""),
                chapter_id=str(structural_draft.get("chapter_id") or ""),
                chapter_number=int(structural_draft.get("chapter_number") or 0),
                plan_id=plan_id,
                branch_id=branch_id,
                used_structural_fallback=used_fallback,
            ),
        )
        return detemplated_draft
