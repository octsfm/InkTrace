from __future__ import annotations

import json
from typing import Any, Dict, Iterable


class TokenBudgetManager:
    def _normalize_context_tokens(self, model_name: str, max_context_tokens: int) -> int:
        tokens = int(max_context_tokens or 0)
        if tokens > 0:
            return tokens
        lowered = str(model_name or "").lower()
        if "128k" in lowered:
            return 131072
        if "32k" in lowered:
            return 32768
        return 8192

    def _profile(self, context_tokens: int) -> Dict[str, Any]:
        if context_tokens <= 10000:
            return {
                "model_tier": "8k",
                "reserve_tokens": 800,
                "stage_ratio": {"chapter_analysis": 0.66, "batch_digest": 0.56, "global_analysis": 0.52},
                "batch_size_chapters": 6,
            }
        if context_tokens <= 50000:
            return {
                "model_tier": "32k",
                "reserve_tokens": 1800,
                "stage_ratio": {"chapter_analysis": 0.72, "batch_digest": 0.60, "global_analysis": 0.56},
                "batch_size_chapters": 8,
            }
        return {
            "model_tier": "128k",
            "reserve_tokens": 4000,
            "stage_ratio": {"chapter_analysis": 0.78, "batch_digest": 0.68, "global_analysis": 0.64},
            "batch_size_chapters": 14,
        }

    def build_capacity_plan(self, model_name: str, max_context_tokens: int) -> Dict[str, Any]:
        context_tokens = self._normalize_context_tokens(model_name, max_context_tokens)
        profile = self._profile(context_tokens)
        reserve_tokens = int(profile["reserve_tokens"])
        stage_ratio = profile["stage_ratio"]
        stage_cap_tokens = {
            stage: max(512, int(context_tokens * float(ratio)) - reserve_tokens)
            for stage, ratio in stage_ratio.items()
        }
        chapter_soft_limit_chars = max(12000, int(stage_cap_tokens["chapter_analysis"] * 2.4))
        chunk_size_chars = max(3500, int(chapter_soft_limit_chars * 0.38))
        return {
            "model_name": str(model_name or ""),
            "model_context_tokens": context_tokens,
            "model_tier": profile["model_tier"],
            "reserve_tokens": reserve_tokens,
            "budget_tokens": stage_cap_tokens.get("global_analysis", 0),
            "stage_cap_tokens": stage_cap_tokens,
            "batch_size": int(profile["batch_size_chapters"]),
            "batch_size_chapters": int(profile["batch_size_chapters"]),
            "chapter_soft_limit_chars": int(chapter_soft_limit_chars),
            "chunk_size_chars": int(chunk_size_chars),
            "enable_chunking": True,
            "need_outline_digest": True,
            "strategy": "batch_digest_first",
            "suggested_model": self._suggest_model(context_tokens),
            "suggested_continue_strategy": [
                "reduce_batch_size",
                "raise_digest_abstraction",
                "enable_two_level_summary",
            ],
        }

    def estimate_stage_tokens(self, payload: Any, *, extra_items: Iterable[str] | None = None) -> int:
        try:
            payload_text = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        except Exception:
            payload_text = str(payload)
        extras = "".join([str(item) for item in (extra_items or []) if str(item)])
        chars = len(payload_text) + len(extras)
        return int(chars / 3) + 80

    def _suggest_model(self, context_tokens: int) -> str:
        if context_tokens <= 10000:
            return "moonshot-v1-32k"
        if context_tokens <= 50000:
            return "moonshot-v1-128k"
        return "current_model_ok"
