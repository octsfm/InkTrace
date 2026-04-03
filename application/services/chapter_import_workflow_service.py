from __future__ import annotations

from datetime import datetime

from application.services.logging_service import build_log_context, get_logger
from domain.entities.chapter_outline import ChapterOutline


class ChapterImportWorkflowService:
    def __init__(self, chapter_ai_service):
        self.chapter_ai_service = chapter_ai_service
        self.logger = get_logger(__name__)

    async def execute(
        self,
        chapter,
        raw_text: str,
        fallback_title: str,
        outline_repo,
        global_memory_summary: str,
        global_outline_summary: str,
        recent_chapter_summaries: list[str],
        relevant_characters: list[dict],
        global_constraints: dict,
    ) -> dict:
        self.logger.info(
            "导入章节开始",
            extra=build_log_context(
                event="chapter_import_started",
                chapter_id=chapter.id.value,
                chapter_number=chapter.number,
                plan_id="",
                branch_id="",
                used_structural_fallback=False,
                novel_id=chapter.novel_id.value,
            ),
        )
        parsed = self.chapter_ai_service.parse_imported_chapter(raw_text, fallback_title)
        outline_result = await self.chapter_ai_service.analyze_to_outline(
            parsed.get("title") or fallback_title,
            parsed.get("content") or "",
            global_memory_summary,
            global_outline_summary,
            recent_chapter_summaries,
        )
        continuation_memory = await self.chapter_ai_service.extract_continuation_memory(
            chapter_title=parsed.get("title") or fallback_title,
            chapter_content=parsed.get("content") or "",
            relevant_characters=relevant_characters,
            global_constraints=global_constraints,
        )
        outline_draft = outline_result.get("outline_draft") or {}
        used_fallback = bool(outline_result.get("used_fallback"))
        now = datetime.now()
        existed = outline_repo.find_by_chapter_id(chapter.id)
        outline = ChapterOutline(
            chapter_id=chapter.id,
            goal=outline_draft.get("goal") or "",
            conflict=outline_draft.get("conflict") or "",
            events=[str(x) for x in (outline_draft.get("events") or [])],
            character_progress=outline_draft.get("character_progress") or "",
            ending_hook=outline_draft.get("ending_hook") or "",
            opening_continuation=outline_draft.get("opening_continuation") or "",
            notes=outline_draft.get("notes") or "",
            created_at=existed.created_at if existed else now,
            updated_at=now,
        )
        outline_repo.save(outline)
        payload = {
            "chapter_id": chapter.id.value,
            "action": "import",
            "title": parsed.get("title") or "",
            "content": parsed.get("content") or "",
            "memory_refresh_required": False,
            "used_fallback": used_fallback,
            "continuation_memory": continuation_memory,
            "outline_draft": {
                "goal": outline.goal,
                "conflict": outline.conflict,
                "events": outline.events,
                "character_progress": outline.character_progress,
                "ending_hook": outline.ending_hook,
                "opening_continuation": outline.opening_continuation,
                "notes": outline.notes,
            },
        }
        self.logger.info(
            "导入章节完成",
            extra=build_log_context(
                event="chapter_import_finished",
                chapter_id=chapter.id.value,
                chapter_number=chapter.number,
                plan_id="",
                branch_id="",
                used_structural_fallback=used_fallback,
                novel_id=chapter.novel_id.value,
            ),
        )
        return payload
