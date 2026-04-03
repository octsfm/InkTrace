from __future__ import annotations

import uuid

from application.services.logging_service import build_log_context, get_logger


class DraftIntegrityChecker:
    def __init__(self, workflow_service):
        self.workflow_service = workflow_service
        self.logger = get_logger(__name__)

    async def check(self, structural_draft: dict, detemplated_draft: dict, chapter_task: dict) -> dict:
        heuristic_check = self.workflow_service._check_draft_integrity(structural_draft, detemplated_draft, chapter_task)
        prompt_check = await self.workflow_service.prompt_ai_service.check_draft_integrity(structural_draft, detemplated_draft, chapter_task)
        if prompt_check:
            integrity_check = {
                "event_integrity_ok": bool(prompt_check.get("event_integrity_ok")) and bool(heuristic_check.get("event_integrity_ok")),
                "motivation_integrity_ok": bool(prompt_check.get("motivation_integrity_ok")) and bool(heuristic_check.get("motivation_integrity_ok")),
                "foreshadowing_integrity_ok": bool(prompt_check.get("foreshadowing_integrity_ok")) and bool(heuristic_check.get("foreshadowing_integrity_ok")),
                "hook_integrity_ok": bool(prompt_check.get("hook_integrity_ok")) and bool(heuristic_check.get("hook_integrity_ok")),
                "continuity_ok": bool(prompt_check.get("continuity_ok")) and bool(heuristic_check.get("continuity_ok")),
                "arc_consistency_ok": bool(prompt_check.get("arc_consistency_ok", True)) and bool(heuristic_check.get("arc_consistency_ok", True)),
                "title_alignment_ok": bool(prompt_check.get("title_alignment_ok", True)),
                "progression_integrity_ok": bool(prompt_check.get("progression_integrity_ok", True)),
                "risk_notes": [*list(heuristic_check.get("risk_notes") or []), *list(prompt_check.get("risk_notes") or [])],
            }
        else:
            integrity_check = heuristic_check
        if integrity_check.get("title_alignment_ok") is False:
            integrity_check["risk_notes"] = [*list(integrity_check.get("risk_notes") or []), "标题与章节功能或钩子不一致"]
        if integrity_check.get("progression_integrity_ok") is False:
            integrity_check["risk_notes"] = [*list(integrity_check.get("risk_notes") or []), "去模板化后章节推进感被削弱"]
        if integrity_check.get("arc_consistency_ok") is False:
            integrity_check["risk_notes"] = [*list(integrity_check.get("risk_notes") or []), "剧情弧推进一致性不足"]
        integrity_check["id"] = str(integrity_check.get("id") or f"check_{uuid.uuid4().hex[:10]}")
        self.logger.info(
            "一致性校验完成",
            extra=build_log_context(
                event="integrity_check_finished",
                project_id=str(structural_draft.get("project_id") or ""),
                chapter_id=str(structural_draft.get("chapter_id") or ""),
                chapter_number=int(structural_draft.get("chapter_number") or 0),
                plan_id=str(chapter_task.get("id") or structural_draft.get("source_task_id") or ""),
                branch_id=str(chapter_task.get("branch_id") or ""),
                used_structural_fallback=bool(detemplated_draft.get("used_fallback") or detemplated_draft.get("display_fallback_to_structural")),
            ),
        )
        if not self.workflow_service._is_integrity_ok(integrity_check):
            self.logger.warning(
                "一致性校验失败",
                extra=build_log_context(
                    event="integrity_check_failed",
                    project_id=str(structural_draft.get("project_id") or ""),
                    chapter_id=str(structural_draft.get("chapter_id") or ""),
                    chapter_number=int(structural_draft.get("chapter_number") or 0),
                    plan_id=str(chapter_task.get("id") or structural_draft.get("source_task_id") or ""),
                    branch_id=str(chapter_task.get("branch_id") or ""),
                    used_structural_fallback=bool(detemplated_draft.get("used_fallback") or detemplated_draft.get("display_fallback_to_structural")),
                ),
            )
        return integrity_check
