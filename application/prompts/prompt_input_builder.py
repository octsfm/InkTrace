from __future__ import annotations

from typing import Any, Dict, List

from application.prompts.prompt_constants import (
    PROMPT_DEFAULT_CHARACTER_LIMIT,
    PROMPT_DEFAULT_FORESHADOW_LIMIT,
)


class PromptInputBuilder:
    @staticmethod
    def _normalize_arc_context(chapter_task: Dict[str, Any], chapter_plan: Dict[str, Any], continuation_context=None) -> Dict[str, Any]:
        task = chapter_task or {}
        plan = chapter_plan or {}
        return {
            "target_arc_id": str(task.get("target_arc_id") or plan.get("target_arc_id") or "").strip(),
            "target_arc_stage": str(task.get("arc_stage_before") or plan.get("arc_stage_before") or "").strip(),
            "secondary_arcs": list(task.get("secondary_arc_ids") or plan.get("related_arc_ids") or [])[:4],
            "arc_push_goal": str(task.get("arc_push_goal") or "").strip(),
            "arc_conflict_focus": str(task.get("arc_conflict_focus") or "").strip(),
            "arc_payoff_expectation": str(task.get("arc_payoff_expectation") or "").strip(),
            "active_arcs": list(getattr(continuation_context, "active_arcs", []) or [])[:5] if continuation_context is not None else [],
            "recent_arc_progress": list(getattr(continuation_context, "recent_arc_progress", []) or [])[:6] if continuation_context is not None else [],
            "arc_bindings": list(getattr(continuation_context, "arc_bindings", []) or [])[:6] if continuation_context is not None else [],
        }

    @staticmethod
    def build_continuation_memory_input(chapter_title: str, chapter_content: str, relevant_characters: List[Dict[str, Any]], global_constraints: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "chapter_title": chapter_title or "",
            "chapter_content": chapter_content or "",
            "relevant_characters": list(relevant_characters or [])[:PROMPT_DEFAULT_CHARACTER_LIMIT],
            "global_constraints": global_constraints or {},
        }

    @staticmethod
    def build_global_analysis_input(
        project_name: str,
        outline_context: Dict[str, Any],
        chapters: List[Dict[str, Any]],
        chapter_artifacts: List[Dict[str, Any]] | None = None,
        outline_digest: Dict[str, Any] | None = None,
        batch_digests: List[Dict[str, Any]] | None = None,
    ) -> Dict[str, Any]:
        normalized_chapters = []
        for item in chapters or []:
            if not isinstance(item, dict):
                continue
            normalized_chapters.append(
                {
                    "chapter_id": str(item.get("id") or "").strip(),
                    "chapter_number": int(item.get("index") or item.get("chapter_number") or 0),
                    "title": str(item.get("title") or "").strip(),
                    "content_preview": str(item.get("content_preview") or item.get("content") or "").strip(),
                }
            )
        normalized_artifacts = []
        for item in chapter_artifacts or []:
            if not isinstance(item, dict):
                continue
            normalized_artifacts.append(
                {
                    "chapter_id": str(item.get("chapter_id") or "").strip(),
                    "chapter_number": int(item.get("chapter_number") or 0),
                    "chapter_title": str(item.get("chapter_title") or "").strip(),
                    "analysis_summary": str(item.get("analysis_summary") or "").strip(),
                    "scene_summary": str(item.get("scene_summary") or "").strip(),
                    "goal": str(item.get("goal") or "").strip(),
                    "conflict": str(item.get("conflict") or "").strip(),
                    "ending_hook": str(item.get("ending_hook") or "").strip(),
                    "must_continue_points": [str(x).strip() for x in (item.get("must_continue_points") or []) if str(x).strip()][:6],
                }
            )
        return {
            "project_name": project_name or "",
            "outline_context": outline_context or {},
            "chapters": normalized_chapters,
            "chapter_artifacts": normalized_artifacts,
            "outline_digest": outline_digest or {},
            "batch_digests": [item for item in (batch_digests or []) if isinstance(item, dict)],
            "input_counts": {
                "chapter_count": len(normalized_chapters),
                "artifact_count": len(normalized_artifacts),
                "batch_digest_count": len([item for item in (batch_digests or []) if isinstance(item, dict)]),
            },
        }

    @staticmethod
    def build_plot_arc_extraction_input(
        project_id: str,
        global_analysis: Dict[str, Any],
        chapter_artifacts: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        normalized_artifacts = []
        for item in chapter_artifacts or []:
            if not isinstance(item, dict):
                continue
            normalized_artifacts.append(
                {
                    "chapter_id": str(item.get("chapter_id") or "").strip(),
                    "chapter_number": int(item.get("chapter_number") or 0),
                    "chapter_title": str(item.get("chapter_title") or "").strip(),
                    "analysis_summary": str(item.get("analysis_summary") or "").strip(),
                    "scene_summary": str(item.get("scene_summary") or "").strip(),
                    "goal": str(item.get("goal") or "").strip(),
                    "conflict": str(item.get("conflict") or "").strip(),
                    "ending_hook": str(item.get("ending_hook") or "").strip(),
                    "must_continue_points": [str(x).strip() for x in (item.get("must_continue_points") or []) if str(x).strip()][:6],
                }
            )
        return {
            "project_id": project_id,
            "global_analysis": global_analysis or {},
            "chapter_artifacts": normalized_artifacts[:120],
        }

    @staticmethod
    def build_chapter_task_input(continuation_context, chapter_plan: Dict[str, Any]) -> Dict[str, Any]:
        recent_memories = [item for item in (continuation_context.recent_chapter_memories or []) if isinstance(item, dict)]
        arc_context = PromptInputBuilder._normalize_arc_context({}, chapter_plan or {}, continuation_context)
        return {
            "recent_chapter_memories": recent_memories,
            "last_chapter_tail": continuation_context.last_chapter_tail or "",
            "chapter_plan": chapter_plan or {},
            "global_constraints": continuation_context.global_constraints or {},
            "chapter_outline": continuation_context.chapter_outline or {},
            "relevant_foreshadowing": list(continuation_context.relevant_foreshadowing or [])[:PROMPT_DEFAULT_FORESHADOW_LIMIT],
            "arc_context": arc_context,
        }

    @staticmethod
    def build_structural_draft_input(chapter_task: Dict[str, Any], global_constraints: Dict[str, Any], continuation_context, relevant_characters: List[Dict[str, Any]], relevant_foreshadowing: List[str]) -> Dict[str, Any]:
        arc_context = PromptInputBuilder._normalize_arc_context(chapter_task or {}, {}, continuation_context)
        return {
            "chapter_task": chapter_task or {},
            "global_constraints": global_constraints or {},
            "recent_chapter_memories": continuation_context.recent_chapter_memories or [],
            "last_chapter_tail": continuation_context.last_chapter_tail or "",
            "relevant_characters": list(relevant_characters or [])[:PROMPT_DEFAULT_CHARACTER_LIMIT],
            "relevant_foreshadowing": list(relevant_foreshadowing or [])[:PROMPT_DEFAULT_FORESHADOW_LIMIT],
            "arc_context": arc_context,
        }

    @staticmethod
    def build_detemplate_input(structural_draft: Dict[str, Any], chapter_task: Dict[str, Any], global_constraints: Dict[str, Any], style_requirements: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "chapter_task": chapter_task or {},
            "style_requirements": style_requirements or {},
            "global_constraints": global_constraints or {},
            "structural_draft": structural_draft or {},
            "arc_context": PromptInputBuilder._normalize_arc_context(chapter_task or {}, {}, None),
        }

    @staticmethod
    def build_detemplate_revision_input(
        structural_draft: Dict[str, Any],
        detemplated_draft: Dict[str, Any],
        chapter_task: Dict[str, Any],
        global_constraints: Dict[str, Any],
        style_requirements: Dict[str, Any],
        issue_list: List[Dict[str, Any]],
        revision_suggestion: str,
    ) -> Dict[str, Any]:
        return {
            "chapter_task": chapter_task or {},
            "style_requirements": style_requirements or {},
            "global_constraints": global_constraints or {},
            "structural_draft": structural_draft or {},
            "detemplated_draft": detemplated_draft or {},
            "issue_list": [item for item in (issue_list or []) if isinstance(item, dict)][:12],
            "revision_suggestion": str(revision_suggestion or "").strip(),
            "arc_context": PromptInputBuilder._normalize_arc_context(chapter_task or {}, {}, None),
        }

    @staticmethod
    def build_integrity_check_input(structural_draft: Dict[str, Any], detemplated_draft: Dict[str, Any], chapter_task: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "structural_draft": structural_draft or {},
            "detemplated_draft": detemplated_draft or {},
            "chapter_task": chapter_task or {},
            "arc_context": PromptInputBuilder._normalize_arc_context(chapter_task or {}, {}, None),
        }

    @staticmethod
    def build_title_backfill_input(chapter_task: Dict[str, Any], content: str, recent_context: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "chapter_task": chapter_task or {},
            "content": content or "",
            "recent_context": recent_context or {},
        }
