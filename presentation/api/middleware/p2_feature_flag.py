from __future__ import annotations

import os

from fastapi import Request
from fastapi.responses import JSONResponse

from presentation.api.routers.v2.ai.response_utils import resolve_safe_message, trace_id_from_request

P2_PATH_FLAG_MAP: tuple[tuple[str, str], ...] = (
    ("/api/v2/ai/multi-chapter", "INKTRACE_P2_ENABLE_MULTI_CHAPTER"),
    ("/api/v2/ai/citations", "INKTRACE_P2_ENABLE_CITATION_LINK"),
    ("/api/v2/ai/style-dna", "INKTRACE_P2_ENABLE_STYLE_DNA"),
    ("/api/v2/ai/auto-queues", "INKTRACE_P2_ENABLE_AUTO_QUEUE"),
    ("/api/v2/mentions", "INKTRACE_P2_ENABLE_MENTIONS"),
    ("/api/v2/chapters/", "INKTRACE_P2_ENABLE_MENTIONS"),
    ("/api/v2/ai/opening", "INKTRACE_P2_ENABLE_OPENING_AGENT"),
    ("/api/v2/ai/outline-assist", "INKTRACE_P2_ENABLE_OUTLINE_ASSIST"),
    ("/api/v2/ai/selection-rewrite", "INKTRACE_P2_ENABLE_SELECTION_REWRITE"),
    ("/api/v2/ai/cost-dashboard", "INKTRACE_P2_ENABLE_COST_DASHBOARD"),
    ("/api/v2/ai/cost-budget", "INKTRACE_P2_ENABLE_COST_DASHBOARD"),
    ("/api/v2/ai/analysis-dashboard", "INKTRACE_P2_ENABLE_ANALYSIS_DASHBOARD"),
)


def _is_enabled(env_name: str) -> bool:
    return str(os.getenv(env_name, "0")).strip().lower() in {"1", "true", "yes", "on"}


def _match_flag(path: str) -> str:
    normalized_path = str(path or "")
    for prefix, env_name in P2_PATH_FLAG_MAP:
        if prefix == "/api/v2/chapters/":
            if normalized_path.startswith(prefix) and "/mentions" in normalized_path:
                return env_name
            continue
        if normalized_path.startswith(prefix):
            return env_name
    return ""


async def p2_feature_flag_middleware(request: Request, call_next):
    env_name = _match_flag(request.url.path)
    if env_name and not _is_enabled(env_name):
        return JSONResponse(
            status_code=503,
            content={
                "request_id": getattr(request.state, "request_id", ""),
                "trace_id": trace_id_from_request(request),
                "status": "error",
                "error": {
                    "error_code": "P2_FEATURE_DISABLED",
                    "safe_message": resolve_safe_message("P2 功能暂未开启，请稍后再试。"),
                    "retryable": False,
                },
            },
        )
    return await call_next(request)

