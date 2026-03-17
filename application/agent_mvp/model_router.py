from __future__ import annotations

from typing import Any, Dict, Optional


class ModelRouter:
    def __init__(self, primary_client=None, backup_client=None):
        self.primary_client = primary_client
        self.backup_client = backup_client

    async def generate(
        self,
        prompt: str,
        max_tokens: int = 1600,
        temperature: float = 0.4
    ) -> Dict[str, Any]:
        if self.primary_client is not None:
            try:
                text = await self.primary_client.generate(
                    prompt,
                    max_tokens=max_tokens,
                    temperature=temperature
                )
                return {"ok": True, "text": text, "route": "primary"}
            except Exception as error:
                primary_error = str(error)
        else:
            primary_error = "primary_unavailable"

        if self.backup_client is not None:
            try:
                text = await self.backup_client.generate(
                    prompt,
                    max_tokens=max_tokens,
                    temperature=temperature
                )
                return {"ok": True, "text": text, "route": "backup"}
            except Exception as error:
                return {"ok": False, "route": "terminate", "error": str(error), "primary_error": primary_error}

        return {"ok": False, "route": "terminate", "error": primary_error}
