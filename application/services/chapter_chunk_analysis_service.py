from __future__ import annotations

from typing import Any, Dict, List


class ChapterChunkAnalysisService:
    def split_chapter(self, chapter_content: str, chunk_size_chars: int) -> List[str]:
        text = str(chapter_content or "").strip()
        if not text:
            return []
        chunk_size = max(1200, int(chunk_size_chars or 0))
        paragraphs = [p for p in text.split("\n\n") if p.strip()]
        chunks: List[str] = []
        current = ""
        for p in paragraphs:
            candidate = f"{current}\n\n{p}".strip() if current else p
            if len(candidate) <= chunk_size:
                current = candidate
                continue
            if current:
                chunks.append(current)
                current = p
            else:
                for i in range(0, len(p), chunk_size):
                    chunks.append(p[i:i + chunk_size])
                current = ""
        if current:
            chunks.append(current)
        if not chunks:
            chunks = [text[i:i + chunk_size] for i in range(0, len(text), chunk_size)]
        return [c for c in chunks if str(c).strip()]

    async def analyze_by_chunks(
        self,
        *,
        chapter_memory_service,
        chapter_title: str,
        chapter_content: str,
        constraints: Dict[str, object],
        global_memory_summary: str,
        global_outline_summary: str,
        recent_chapter_summaries: List[str],
        require_model_success: bool,
        chunk_size_chars: int,
    ) -> Dict[str, object]:
        chunks = self.split_chapter(chapter_content, chunk_size_chars)
        if not chunks:
            raise ValueError(f"章节《{chapter_title}》内容为空，无法分块分析。")
        partials: List[Dict[str, object]] = []
        for idx, chunk in enumerate(chunks, 1):
            last_error: Exception | None = None
            for _ in range(3):
                try:
                    partial = await chapter_memory_service.build_memories(
                        chapter_title=f"{chapter_title}（分块{idx}/{len(chunks)}）",
                        chapter_content=chunk,
                        constraints=constraints,
                        global_memory_summary=global_memory_summary,
                        global_outline_summary=global_outline_summary,
                        recent_chapter_summaries=recent_chapter_summaries,
                        require_model_success=require_model_success,
                    )
                    partials.append(partial)
                    last_error = None
                    break
                except Exception as exc:
                    last_error = exc
            if last_error is not None:
                raise ValueError(f"章节《{chapter_title}》第{idx}块分析失败：{last_error}") from last_error

        merged_outline_events: List[str] = []
        merged_must_continue: List[str] = []
        summaries: List[str] = []
        for partial in partials:
            outline_draft = partial.get("outline_draft") if isinstance(partial, dict) else {}
            continuation = partial.get("continuation_memory") if isinstance(partial, dict) else {}
            analysis_summary = partial.get("analysis_summary") if isinstance(partial, dict) else {}
            merged_outline_events.extend([str(x).strip() for x in (outline_draft or {}).get("events", []) if str(x).strip()])
            merged_must_continue.extend([str(x).strip() for x in (continuation or {}).get("must_continue_points", []) if str(x).strip()])
            summary_text = str((analysis_summary or {}).get("summary") or (continuation or {}).get("scene_summary") or "").strip()
            if summary_text:
                summaries.append(summary_text)

        last_partial = partials[-1] if partials else {}
        last_outline = dict(last_partial.get("outline_draft") or {})
        last_continuation = dict(last_partial.get("continuation_memory") or {})
        last_analysis = dict(last_partial.get("analysis_summary") or {})
        last_outline["events"] = list(dict.fromkeys(merged_outline_events))[:10]
        last_continuation["must_continue_points"] = list(dict.fromkeys(merged_must_continue))[:8]
        last_analysis["summary"] = "；".join(summaries)[:1200]
        return {
            "analysis_summary": last_analysis,
            "continuation_memory": last_continuation,
            "outline_draft": last_outline,
            "used_fallback": any(bool((partial or {}).get("used_fallback")) for partial in partials),
            "chunk_count": len(chunks),
        }
