from __future__ import annotations

from dataclasses import dataclass
import re
from typing import List


@dataclass
class Chapter:
    title: str
    content: str
    index: int


def split_into_chapters(text: str) -> List[Chapter]:
    source = str(text or "").strip()
    if not source:
        return []

    normalized = source.replace("\r\n", "\n").replace("\r", "\n")
    heading_pattern = re.compile(
        r"(?im)^(?P<title>\s*(?:第\s*[0-9一二三四五六七八九十百千零两]+[\s　]*章[^\n]*|chapter\s*\d+[^\n]*))\s*$"
    )
    matches = list(heading_pattern.finditer(normalized))
    if matches:
        chapters: List[Chapter] = []
        for idx, match in enumerate(matches):
            start = match.end()
            end = matches[idx + 1].start() if idx + 1 < len(matches) else len(normalized)
            title = match.group("title").strip()
            content = normalized[start:end].strip()
            chapters.append(Chapter(title=title or f"第{idx + 1}章", content=content, index=idx + 1))
        return [chapter for chapter in chapters if chapter.content]

    paragraph_chunks = [item.strip() for item in re.split(r"\n\s*\n+", normalized) if item.strip()]
    if not paragraph_chunks:
        return []
    chunk_size = 6
    chapters = []
    for start in range(0, len(paragraph_chunks), chunk_size):
        idx = len(chapters) + 1
        body = "\n\n".join(paragraph_chunks[start:start + chunk_size]).strip()
        if body:
            chapters.append(Chapter(title=f"第{idx}章", content=body, index=idx))
    return chapters
