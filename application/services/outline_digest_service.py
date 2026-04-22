from __future__ import annotations

from typing import Dict, List


class OutlineDigestService:
    digest_version = "v1"

    def build_digest(self, raw_outline: str) -> Dict[str, object]:
        text = str(raw_outline or "").strip()
        paragraphs = [x.strip() for x in text.splitlines() if x.strip()]

        def _take(start: int, size: int, limit: int = 800) -> str:
            slice_text = "\n".join(paragraphs[start:start + size]).strip()
            return slice_text[:limit]

        def _list_chunks(step: int, size: int, per_item_limit: int = 360, max_items: int = 8) -> List[str]:
            results: List[str] = []
            cursor = 0
            while cursor < len(paragraphs) and len(results) < max_items:
                chunk = "\n".join(paragraphs[cursor:cursor + size]).strip()
                if chunk:
                    results.append(chunk[:per_item_limit])
                cursor += step
            return results

        return {
            "premise": _take(0, 2, 600),
            "main_plot_lines": _list_chunks(3, 2, 360, 8),
            "world_rules": _list_chunks(4, 1, 320, 8),
            "character_arcs": _list_chunks(5, 1, 320, 8),
            "foreshadowing_threads": _list_chunks(6, 1, 320, 8),
            "forbidden_jumps": _list_chunks(7, 1, 300, 6),
            "style_guidance": _take(max(0, len(paragraphs) - 3), 3, 600),
            "summary": "\n".join(paragraphs[:12])[:2400],
        }
