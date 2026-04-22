from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from domain.exceptions import RateLimitError


class ModelRouter:
    def __init__(self, preferred_client=None, fallback_client=None):
        self.preferred_client = preferred_client
        self.fallback_client = fallback_client
        # Legacy aliases for callers that still think in primary/backup terms.
        self.primary_client = preferred_client
        self.backup_client = fallback_client
        self.logger = logging.getLogger(__name__)

    async def generate(
        self,
        prompt: str,
        max_tokens: int = 1600,
        temperature: float = 0.4,
    ) -> Dict[str, Any]:
        preferred_error: Optional[str] = None
        preferred_meta: Dict[str, Any] = {}

        if self.preferred_client is not None:
            try:
                text = await self.preferred_client.generate(
                    prompt,
                    max_tokens=max_tokens,
                    temperature=temperature,
                )
                return {"ok": True, "text": text, "route": "preferred"}
            except Exception as error:  # pragma: no cover - exercised by higher-level tests
                preferred_error = str(error)
                preferred_meta = self._error_meta(error)
                self.logger.warning("preferred_model_failed: %s", preferred_error)
        else:
            preferred_error = "preferred_unavailable"
            preferred_meta = {"error_type": "preferred_unavailable"}

        if self.fallback_client is not None:
            try:
                text = await self.fallback_client.generate(
                    prompt,
                    max_tokens=max_tokens,
                    temperature=temperature,
                )
                return {"ok": True, "text": text, "route": "fallback", "preferred_error": preferred_error}
            except Exception as error:
                fallback_error = str(error)
                fallback_meta = self._error_meta(error)
                self.logger.error("fallback_model_failed: %s", fallback_error)
                return {
                    "ok": False,
                    "route": "terminate",
                    "error": fallback_error,
                    "preferred_error": preferred_error,
                    "preferred_error_meta": preferred_meta,
                    **fallback_meta,
                }
        return {
            "ok": False,
            "route": "terminate",
            "error": preferred_error or "preferred_unavailable",
            **preferred_meta,
        }

    def _error_meta(self, error: Exception) -> Dict[str, Any]:
        if isinstance(error, RateLimitError):
            return {
                "error_type": "rate_limit",
                "retry_after": int(error.retry_after) if error.retry_after else None,
            }
        return {"error_type": error.__class__.__name__}
