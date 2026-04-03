from __future__ import annotations

import logging
from typing import Any, Dict, Optional


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
                self.logger.warning("preferred_model_failed: %s", preferred_error)
        else:
            preferred_error = "preferred_unavailable"

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
                self.logger.error("fallback_model_failed: %s", fallback_error)
                return {
                    "ok": False,
                    "route": "terminate",
                    "error": fallback_error,
                    "preferred_error": preferred_error,
                }

        return {"ok": False, "route": "terminate", "error": preferred_error or "preferred_unavailable"}
