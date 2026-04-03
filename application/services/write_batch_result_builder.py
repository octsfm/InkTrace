from __future__ import annotations

from application.services.logging_service import build_log_context, get_logger


class WriteBatchResultBuilder:
    def __init__(self):
        self.logger = get_logger(__name__)

    def build(
        self,
        project_id: str,
        generated_chapters: list[dict],
        latest_chapter: dict,
        latest_structural_draft: dict,
        latest_detemplated_draft: dict,
        latest_draft_integrity_check: dict,
        memory_view: dict,
        used_structural_fallback: bool,
        chapter_saved: bool,
        memory_refreshed: bool,
        saved_chapter_ids: list[str],
    ) -> dict:
        result = {
            "project_id": project_id,
            "generated_chapters": generated_chapters,
            "latest_chapter": latest_chapter,
            "latest_structural_draft": latest_structural_draft,
            "latest_detemplated_draft": latest_detemplated_draft,
            "latest_draft_integrity_check": latest_draft_integrity_check,
            "used_structural_fallback": used_structural_fallback,
            "memory_view": memory_view,
            "chapter_saved": chapter_saved,
            "memory_refreshed": memory_refreshed,
            "saved_chapter_ids": saved_chapter_ids,
        }
        self.logger.info(
            "批量续写结果已构建",
            extra=build_log_context(
                event="write_batch_result_built",
                project_id=project_id,
                chapter_id=str((latest_chapter or {}).get("chapter_id") or ""),
                chapter_number=int((latest_chapter or {}).get("chapter_number") or 0),
                plan_id="",
                branch_id="",
                used_structural_fallback=used_structural_fallback,
            ),
        )
        return result
