from __future__ import annotations

import uuid

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from presentation.api import dependencies
from presentation.api.routers.v2.ai.schemas import ReviewCandidateDraftRequest

router = APIRouter(tags=["v2-ai-review"])


def _trace_id(request: Request) -> str:
    header_value = request.headers.get("X-Trace-Id", "").strip()
    return header_value or f"trace_{uuid.uuid4().hex[:12]}"


def _success(request: Request, *, data: dict[str, object]) -> dict[str, object]:
    return {
        "request_id": getattr(request.state, "request_id", ""),
        "trace_id": _trace_id(request),
        "status": "ok",
        "data": data,
    }


def _error(request: Request, *, error_code: str, status_code: int = 400) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "request_id": getattr(request.state, "request_id", ""),
            "trace_id": _trace_id(request),
            "status": "error",
            "error": {
                "error_code": error_code,
                "safe_message": error_code,
                "retryable": False,
            },
        },
    )


def _serialize_review_item(review) -> dict[str, object]:
    return {
        "review_id": review.review_id,
        "work_id": review.work_id,
        "chapter_id": review.chapter_id,
        "candidate_draft_id": review.candidate_draft_id,
        "status": review.status.value,
        "summary": review.summary,
        "issues": [issue.model_dump(mode="json") for issue in review.issues],
        "suggestions": review.suggestions,
        "risk_level": review.risk_level.value,
        "consistency_notes": review.consistency_notes,
        "style_notes": review.style_notes,
        "logic_notes": review.logic_notes,
        "reviewer_model_role": review.reviewer_model_role,
        "provider_name": review.provider_name,
        "model_name": review.model_name,
        "created_at": review.created_at,
        "metadata": review.metadata,
    }


@router.post("/api/v2/ai/reviews/candidate-drafts/{candidate_draft_id}")
def review_candidate_draft(candidate_draft_id: str, payload: ReviewCandidateDraftRequest, request: Request):
    service = dependencies.get_ai_review_service()
    try:
        review = service.review_candidate_draft(
            candidate_draft_id,
            created_by="user_action",
            user_instruction=payload.user_instruction,
        )
    except ValueError as exc:
        error_code = str(exc)
        status_code = 404 if error_code in {"candidate_draft_not_found", "chapter_not_found", "work_not_found"} else 400
        return _error(request, error_code=error_code, status_code=status_code)
    return _success(
        request,
        data={
            "review_id": review.review_id,
            "status": review.status.value,
            "summary": review.summary,
        },
    )


@router.get("/api/v2/ai/reviews/{review_id}")
def get_ai_review(review_id: str, request: Request):
    service = dependencies.get_ai_review_service()
    try:
        review = service.get_ai_review(review_id)
    except ValueError as exc:
        return _error(request, error_code=str(exc), status_code=404)
    return _success(request, data=_serialize_review_item(review))


@router.get("/api/v2/ai/reviews")
def list_ai_reviews(request: Request, work_id: str, chapter_id: str = "", candidate_draft_id: str = ""):
    service = dependencies.get_ai_review_service()
    items = service.list_ai_reviews(
        work_id=work_id,
        chapter_id=chapter_id or None,
        candidate_draft_id=candidate_draft_id or None,
    )
    return _success(request, data={"items": [_serialize_review_item(item) for item in items]})
