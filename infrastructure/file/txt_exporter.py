from __future__ import annotations

import os
import re
from typing import List

from domain.entities.chapter import Chapter
from domain.entities.novel import Novel


class TxtExporter:
    def _display_title(self, chapter: Chapter) -> str:
        raw_title = (chapter.title or "").strip()
        normalized = re.sub(r"^第[一二三四五六七八九十百千万零\d]+章\s*", "", raw_title).strip()
        return f"第{chapter.number}章 {normalized or raw_title or f'章节{chapter.number}'}"

    def export_novel(self, novel: Novel, chapters: List[Chapter], output_path: str) -> None:
        lines = [
            f"{novel.title}",
            f"作者：{novel.author or '未知'}",
            f"题材：{novel.genre}",
            f"字数：{novel.current_word_count} / {novel.target_word_count}",
            "",
        ]
        for chapter in chapters:
            lines.extend(self.export_chapter_lines(chapter))
            lines.append("")
        output_dir = os.path.dirname(output_path)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

    def export_chapter(self, chapter: Chapter, output_path: str) -> None:
        output_dir = os.path.dirname(output_path)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("\n".join(self.export_chapter_lines(chapter)))

    def export_chapter_lines(self, chapter: Chapter) -> List[str]:
        return [
            self._display_title(chapter),
            "",
            chapter.content or "",
        ]
