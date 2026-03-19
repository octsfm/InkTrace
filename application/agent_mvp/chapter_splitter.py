from __future__ import annotations

from dataclasses import dataclass
import re
import logging
from typing import List

logger = logging.getLogger(__name__)


@dataclass
class Chapter:
    title: str
    content: str
    index: int


@dataclass
class TextChunk:
    content: str
    start: int
    end: int


def split_into_chunks_by_chars(text: str, chunk_size: int = 4000, overlap: int = 500) -> List[dict]:
    source = str(text or "")
    if not source:
        return []
    normalized = source.replace("\r\n", "\n").replace("\r", "\n")
    chunk_size = max(3000, min(5000, int(chunk_size or 4000)))
    overlap = max(0, min(int(overlap or 500), chunk_size // 2))
    chunks: List[dict] = []
    start = 0
    total = len(normalized)
    while start < total:
        end = min(total, start + chunk_size)
        content = normalized[start:end]
        if content.strip():
            chunks.append({"content": content, "start": start, "end": end})
        if end >= total:
            break
        start = max(0, end - overlap)
    logger.info(
        "[Splitter] split_into_chunks_by_chars 完成 total_length=%d chunk_size=%d overlap=%d chunks=%d",
        total,
        chunk_size,
        overlap,
        len(chunks)
    )
    return chunks


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
    chunks = split_into_chunks_by_chars(normalized, chunk_size=4000, overlap=500)
    chapters: List[Chapter] = []
    for idx, chunk in enumerate(chunks, 1):
        body = str(chunk.get("content") or "").strip()
        if body:
            chapters.append(Chapter(title=f"第{idx}段", content=body, index=idx))
    return chapters
