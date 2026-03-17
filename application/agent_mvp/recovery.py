from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Dict, Optional


@dataclass
class RecoveryResult:
    ok: bool
    data: Optional[Dict[str, Any]] = None
    stage: str = "terminate"
    error: str = ""


class RecoveryPipeline:
    def __init__(self, max_retries: int = 2):
        self.max_retries = max_retries

    async def run(
        self,
        execute: Callable[[], Awaitable[Dict[str, Any]]],
        repair: Callable[[], Awaitable[Dict[str, Any]]],
        fallback: Callable[[], Awaitable[Dict[str, Any]]],
        degrade: Callable[[], Dict[str, Any]]
    ) -> RecoveryResult:
        retry_error = ""
        for _ in range(self.max_retries + 1):
            try:
                data = await execute()
                return RecoveryResult(ok=True, data=data, stage="retry")
            except Exception as error:
                retry_error = str(error)

        try:
            data = await repair()
            return RecoveryResult(ok=True, data=data, stage="repair")
        except Exception:
            pass

        try:
            data = await fallback()
            return RecoveryResult(ok=True, data=data, stage="fallback")
        except Exception:
            pass

        try:
            data = degrade()
            return RecoveryResult(ok=True, data=data, stage="degrade")
        except Exception as error:
            return RecoveryResult(ok=False, error=str(error) or retry_error, stage="terminate")
