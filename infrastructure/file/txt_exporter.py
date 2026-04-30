from __future__ import annotations

import re
from typing import List

from domain.entities.chapter import Chapter


class TxtExporter:
    def _display_title(self, chapter: Chapter) -> str:
        raw_title = (chapter.title or "").strip()
        normalized = re.sub(r"^第[一二三四五六七八九十百千万零\d]+章\s*", "", raw_title).strip()
        display_number = int(getattr(chapter, "order_index", 0) or getattr(chapter, "number", 0) or 1)
        return f"第{display_number}章 {normalized or raw_title or f'章节{display_number}'}"

    def build_novel_text(
        self,
        chapters: List[Chapter],
        *,
        include_titles: bool = True,
        gap_lines: int = 1,
    ) -> str:
        ordered_chapters = sorted(chapters, key=lambda item: (item.order_index, item.created_at))
        if not ordered_chapters:
            return ""

        separator = "\n" * max(1, int(gap_lines) + 1)
        blocks = [self.build_chapter_text(chapter, include_title=include_titles) for chapter in ordered_chapters]
        return separator.join(blocks)

    def build_chapter_text(self, chapter: Chapter, *, include_title: bool = True) -> str:
        content = str(chapter.content or "")
        if not include_title:
            return content
        return f"{self._display_title(chapter)}\n\n{content}"
