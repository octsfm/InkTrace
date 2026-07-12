from __future__ import annotations

import os
import uuid

from fastapi import Request
from fastapi.responses import JSONResponse

OUTLINE_ASSIST_FLAG_ENV = "INKTRACE_P2_ENABLE_OUTLINE_ASSIST"

P2_PATH_FLAG_MAP: tuple[tuple[str, str], ...] = (
    ("/api/v2/ai/multi-chapter", "INKTRACE_P2_ENABLE_MULTI_CHAPTER"),
    ("/api/v2/ai/citations", "INKTRACE_P2_ENABLE_CITATION_LINK"),
    ("/api/v2/ai/style-dna", "INKTRACE_P2_ENABLE_STYLE_DNA"),
    ("/api/v2/ai/auto-queues", "INKTRACE_P2_ENABLE_AUTO_QUEUE"),
    ("/api/v2/mentions", "INKTRACE_P2_ENABLE_MENTIONS"),
    ("/api/v2/chapters/", "INKTRACE_P2_ENABLE_MENTIONS"),
    ("/api/v2/ai/opening", "INKTRACE_P2_ENABLE_OPENING_AGENT"),
    ("/api/v2/ai/outline-assist", OUTLINE_ASSIST_FLAG_ENV),
    ("/api/v2/ai/selection-rewrite", "INKTRACE_P2_ENABLE_SELECTION_REWRITE"),
    ("/api/v2/ai/cost-dashboard", "INKTRACE_P2_ENABLE_COST_DASHBOARD"),
    ("/api/v2/ai/cost-budget", "INKTRACE_P2_ENABLE_COST_DASHBOARD"),
    ("/api/v2/ai/analysis-dashboard", "INKTRACE_P2_ENABLE_ANALYSIS_DASHBOARD"),
)


def _is_enabled(env_name: str) -> bool:
    return str(os.getenv(env_name, "0")).strip().lower() in {"1", "true", "yes", "on"}


def is_outline_assist_enabled() -> bool:
    return _is_enabled(OUTLINE_ASSIST_FLAG_ENV)


def _trace_id_from_request(request: Request) -> str:
    header_value = request.headers.get("X-Trace-Id", "").strip()
    return header_value or f"trace_{uuid.uuid4().hex[:12]}"


def outline_assist_feature_disabled_response(request: Request) -> JSONResponse:
    return JSONResponse(
        status_code=503,
        content={
            "request_id": getattr(request.state, "request_id", ""),
            "trace_id": _trace_id_from_request(request),
            "status": "error",
            "error": {
                "error_code": "P2_FEATURE_DISABLED",
                "safe_message": "P2 功能暂未开启，请稍后再试。",
                "retryable": False,
            },
        },
    )


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
        return outline_assist_feature_disabled_response(request)
    return await call_next(request)
