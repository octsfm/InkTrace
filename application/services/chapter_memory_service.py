from __future__ import annotations

from typing import Dict, List, Optional

from application.services.chapter_ai_service import ChapterAIService


class ChapterMemoryService:
    def __init__(self, chapter_ai_service: ChapterAIService):
        self.chapter_ai_service = chapter_ai_service

    async def build_memories(
        self,
        chapter_title: str,
        chapter_content: str,
        constraints: Dict[str, object],
        global_memory_summary: str = "",
        global_outline_summary: str = "",
        recent_chapter_summaries: Optional[List[str]] = None,
    ) -> Dict[str, object]:
        analyze_to_outline = getattr(self.chapter_ai_service, "analyze_to_outline", None)
        if callable(analyze_to_outline):
            outline_result = await analyze_to_outline(
                chapter_title=chapter_title,
                chapter_content=chapter_content,
                global_memory_summary=global_memory_summary,
                global_outline_summary=global_outline_summary,
                recent_chapter_summaries=recent_chapter_summaries or [],
            )
        else:
            outline_result = {"outline_draft": {}, "used_fallback": True}

        extract_continuation_memory = getattr(self.chapter_ai_service, "extract_continuation_memory", None)
        if callable(extract_continuation_memory):
            continuation = await extract_continuation_memory(
                chapter_title=chapter_title,
                chapter_content=chapter_content,
                relevant_characters=[],
                global_constraints=constraints or {},
            )
        else:
            text = str(chapter_content or "").strip()
            continuation = {
                "scene_summary": text[:180],
                "scene_state": {},
                "protagonist_state": {},
                "active_characters": [],
                "active_conflicts": [],
                "immediate_threads": [],
                "long_term_threads": [],
                "recent_reveals": [],
                "must_continue_points": [],
                "forbidden_jumps": [],
                "tone_and_pacing": {},
                "last_hook": "",
                "used_fallback": True,
            }
        outline_draft = outline_result.get("outline_draft") if isinstance(outline_result, dict) else {}
        outline_draft = outline_draft if isinstance(outline_draft, dict) else {}
        analysis_summary = {
            "summary": str(continuation.get("scene_summary") or chapter_content[:180]).strip(),
            "events": [str(x).strip() for x in (outline_draft.get("events") or []) if str(x).strip()][:8],
            "plot_role": str(outline_draft.get("goal") or "").strip(),
            "conflict": str(outline_draft.get("conflict") or "").strip(),
            "foreshadowing": [str(x).strip() for x in (continuation.get("must_continue_points") or []) if str(x).strip()][:6],
            "hook": str(outline_draft.get("ending_hook") or continuation.get("last_hook") or "").strip(),
            "problems": [],
        }
        return {
            "analysis_summary": analysis_summary,
            "continuation_memory": continuation,
            "outline_draft": outline_draft,
            "used_fallback": bool((outline_result or {}).get("used_fallback") or continuation.get("used_fallback")),
        }
