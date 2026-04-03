from __future__ import annotations

from typing import Any, Dict, List

from application.services.logging_service import build_log_context, get_logger


class ValidationServiceV2:
    def __init__(self, workflow_service):
        self.workflow_service = workflow_service
        self.logger = get_logger(__name__)

    async def validate_and_revise(
        self,
        structural_draft: Dict[str, Any],
        detemplated_draft: Dict[str, Any],
        chapter_task: Dict[str, Any],
        global_constraints: Dict[str, Any],
        style_requirements: Dict[str, Any],
        max_revision_attempts: int = 1,
    ) -> Dict[str, Any]:
        current_draft = dict(detemplated_draft or {})
        integrity_check = await self._run_integrity_check(structural_draft, current_draft, chapter_task)
        revision_attempts: List[Dict[str, Any]] = []

        for revision_index in range(max(0, int(max_revision_attempts or 0))):
            issue_list = list(integrity_check.get("issue_list") or [])
            if self.workflow_service._is_integrity_ok(integrity_check) or not issue_list:
                break

            self.logger.info(
                "revision started",
                extra=build_log_context(
                    event="draft_revision_started",
                    project_id=str(structural_draft.get("project_id") or ""),
                    chapter_id=str(structural_draft.get("chapter_id") or ""),
                    chapter_number=int(structural_draft.get("chapter_number") or 0),
                    attempt=revision_index + 1,
                    issue_count=len(issue_list),
                ),
            )
            revision_result = await self._revise_draft(
                structural_draft=structural_draft,
                detemplated_draft=current_draft,
                chapter_task=chapter_task,
                global_constraints=global_constraints or {},
                style_requirements=style_requirements or {},
                issue_list=issue_list,
                revision_suggestion=str(integrity_check.get("revision_suggestion") or ""),
            )

            revision_attempts.append(
                {
                    "attempt": revision_index + 1,
                    "issue_count": len(issue_list),
                    "used_fallback": bool(revision_result.get("used_fallback")),
                    "revision_applied": bool(revision_result.get("revision_applied")),
                }
            )

            revised_content = str(revision_result.get("content") or "").strip()
            if not revised_content:
                break

            current_draft = {
                **current_draft,
                **revision_result,
                "content": revised_content,
                "title": str(current_draft.get("title") or structural_draft.get("title") or ""),
            }
            integrity_check = await self._run_integrity_check(structural_draft, current_draft, chapter_task)
            integrity_check["revision_attempted"] = True
            integrity_check["revision_succeeded"] = bool(self.workflow_service._is_integrity_ok(integrity_check))

            self.logger.info(
                "revision finished",
                extra=build_log_context(
                    event="draft_revision_finished",
                    project_id=str(structural_draft.get("project_id") or ""),
                    chapter_id=str(structural_draft.get("chapter_id") or ""),
                    chapter_number=int(structural_draft.get("chapter_number") or 0),
                    attempt=revision_index + 1,
                    revision_succeeded=bool(integrity_check.get("revision_succeeded")),
                ),
            )

            if integrity_check.get("revision_succeeded"):
                break

        if not revision_attempts:
            integrity_check["revision_attempted"] = False
            integrity_check["revision_succeeded"] = False

        return {
            "detemplated_draft": current_draft,
            "integrity_check": integrity_check,
            "revision_attempts": revision_attempts,
        }

    async def _run_integrity_check(
        self,
        structural_draft: Dict[str, Any],
        detemplated_draft: Dict[str, Any],
        chapter_task: Dict[str, Any],
    ) -> Dict[str, Any]:
        integrity_check = await self.workflow_service.draft_integrity_checker.check(
            structural_draft,
            detemplated_draft,
            chapter_task,
        )
        issue_list = self._build_issue_list(integrity_check)
        integrity_check["issue_list"] = issue_list
        integrity_check["revision_suggestion"] = self._build_revision_suggestion(issue_list)
        return integrity_check

    async def _revise_draft(
        self,
        structural_draft: Dict[str, Any],
        detemplated_draft: Dict[str, Any],
        chapter_task: Dict[str, Any],
        global_constraints: Dict[str, Any],
        style_requirements: Dict[str, Any],
        issue_list: List[Dict[str, Any]],
        revision_suggestion: str,
    ) -> Dict[str, Any]:
        prompt_ai_service = self.workflow_service.prompt_ai_service
        revise = getattr(prompt_ai_service, "revise_detemplated_draft", None)
        if callable(revise):
            return await revise(
                structural_draft=structural_draft,
                detemplated_draft=detemplated_draft,
                chapter_task=chapter_task,
                global_constraints=global_constraints,
                style_requirements=style_requirements,
                issue_list=issue_list,
                revision_suggestion=revision_suggestion,
            )
        rewrite = getattr(prompt_ai_service, "rewrite_detemplated_draft", None)
        if callable(rewrite):
            return await rewrite(
                structural_draft,
                chapter_task,
                global_constraints,
                style_requirements,
            )
        return {
            "content": str(detemplated_draft.get("content") or structural_draft.get("content") or ""),
            "used_fallback": True,
            "integrity_failed": True,
            "display_fallback_to_structural": bool(detemplated_draft.get("display_fallback_to_structural")),
            "revision_applied": False,
        }

    def _build_issue_list(self, integrity_check: Dict[str, Any]) -> List[Dict[str, Any]]:
        checks = [
            ("event_integrity_ok", "event_integrity", "high", "事件推进不足", "补足本章的关键事件推进与结果落点。"),
            ("motivation_integrity_ok", "motivation_integrity", "high", "人物动机不稳", "补强人物选择的动机链条与代价。"),
            ("foreshadowing_integrity_ok", "foreshadowing_integrity", "medium", "伏笔承接不足", "回收并承接必须继续的伏笔点。"),
            ("hook_integrity_ok", "hook_integrity", "medium", "章节钩子偏弱", "强化章末悬念或下一章压力。"),
            ("continuity_ok", "continuity", "high", "连续性不足", "修正与前文场景、状态、事实不一致的表达。"),
            ("arc_consistency_ok", "arc_consistency", "high", "剧情弧推进不一致", "让正文明确服务当前目标剧情弧与阶段推进。"),
            ("title_alignment_ok", "title_alignment", "low", "标题对齐不足", "让标题更贴合本章功能、结果或钩子。"),
            ("progression_integrity_ok", "progression_integrity", "medium", "推进感被削弱", "保留去模板化后的文采同时恢复推进强度。"),
        ]
        issues: List[Dict[str, Any]] = []
        for key, code, severity, title, suggestion in checks:
            if integrity_check.get(key, True):
                continue
            issues.append(
                {
                    "code": code,
                    "severity": severity,
                    "title": title,
                    "detail": suggestion,
                    "source": key,
                }
            )
        for note in [str(item).strip() for item in (integrity_check.get("risk_notes") or []) if str(item).strip()]:
            issues.append(
                {
                    "code": "risk_note",
                    "severity": "medium",
                    "title": "风险提示",
                    "detail": note,
                    "source": "risk_notes",
                }
            )
        deduped: List[Dict[str, Any]] = []
        seen = set()
        for item in issues:
            key = (item.get("code"), item.get("detail"))
            if key in seen:
                continue
            seen.add(key)
            deduped.append(item)
        return deduped[:12]

    def _build_revision_suggestion(self, issue_list: List[Dict[str, Any]]) -> str:
        if not issue_list:
            return ""
        top = issue_list[:3]
        details = "；".join([str(item.get("detail") or "").strip() for item in top if str(item.get("detail") or "").strip()])
        return details or "根据问题单修订正文，优先修正连续性、推进感与剧情弧一致性。"
