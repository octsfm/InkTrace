from __future__ import annotations

import uuid

from fastapi import Request
from fastapi.responses import JSONResponse


def trace_id_from_request(request: Request) -> str:
    header_value = request.headers.get("X-Trace-Id", "").strip()
    return header_value or f"trace_{uuid.uuid4().hex[:12]}"


SAFE_MESSAGE_MAP = {
    "caller_type_not_allowed": "当前请求来源不被允许。",
    "work_not_found": "未找到对应作品。",
    "chapter_not_found": "未找到对应章节。",
    "candidate_draft_not_found": "未找到候选稿。",
    "context_pack_not_found": "未找到上下文包。",
    "internal_error": "服务暂时不可用，请稍后重试。",
}


def resolve_safe_message(code_or_message: str) -> str:
    normalized = str(code_or_message or "").strip()
    return SAFE_MESSAGE_MAP.get(normalized, normalized)


def success_response(
    request: Request,
    *,
    data: dict[str, object],
    extra: dict[str, object] | None = None,
) -> dict[str, object]:
    payload = {
        "request_id": getattr(request.state, "request_id", ""),
        "trace_id": trace_id_from_request(request),
        "status": "ok",
        "data": data,
    }
    if extra:
        payload.update(extra)
    return payload


def error_response(
    request: Request,
    *,
    error_code: str,
    status_code: int = 400,
    retryable: bool = False,
    safe_message: str | None = None,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "request_id": getattr(request.state, "request_id", ""),
            "trace_id": trace_id_from_request(request),
            "status": "error",
            "error": {
                "error_code": error_code,
                "safe_message": resolve_safe_message(safe_message or error_code),
                "retryable": retryable,
            },
        },
    )
