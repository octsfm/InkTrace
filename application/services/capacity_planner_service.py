from __future__ import annotations

from typing import Any, Dict


class CapacityPlannerService:
    def build_plan(self, model_name: str, max_context_tokens: int) -> Dict[str, Any]:
        tokens = int(max_context_tokens or 0)
        if tokens <= 0:
            tokens = 8000
        if tokens <= 10000:
            chapter_soft_limit = 12000
            chunk_size = 4000
            batch_size = 8
        elif tokens <= 50000:
            chapter_soft_limit = 30000
            chunk_size = 9000
            batch_size = 12
        else:
            chapter_soft_limit = 90000
            chunk_size = 24000
            batch_size = 20
        return {
            "model_name": str(model_name or ""),
            "max_context_tokens": tokens,
            "chapter_soft_limit_chars": chapter_soft_limit,
            "chunk_size_chars": chunk_size,
            "batch_size_chapters": batch_size,
            "need_outline_digest": True,
            "enable_chunking": True,
            "strategy": "chunked_chapter_first",
        }
