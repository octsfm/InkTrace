from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from presentation.api import dependencies
from presentation.api.routers.v2.ai.response_utils import error_response, success_response
from presentation.api.routers.v2.ai.schemas import ReviewCandidateDraftRequest

router = APIRouter(tags=["v2-ai-review"])


def _reject_invalid_caller_type(request: Request, *, caller_type: str) -> JSONResponse | None:
    if caller_type and caller_type != "user_action":
        return error_response(request, error_code="caller_type_not_allowed", status_code=403)
    return None


def _serialize_review_item(review) -> dict[str, object]:
    return {
        "review_id": review.review_id,
        "work_id": review.work_id,
        "chapter_id": review.chapter_id,
        "candidate_draft_id": review.candidate_draft_id,
        "status": review.status.value,
        "summary": review.summary,
        "warnings": review.warnings,
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
    denied = _reject_invalid_caller_type(request, caller_type=payload.caller_type)
    if denied is not None:
        return denied
    service = dependencies.get_ai_review_service()
    try:
        review = service.review_candidate_draft(
            candidate_draft_id,
            created_by=payload.caller_type or "user_action",
            user_instruction=payload.user_instruction,
            idempotency_key=payload.idempotency_key,
        )
    except ValueError as exc:
        error_code = str(exc)
        status_code = 404 if error_code in {"candidate_draft_not_found", "chapter_not_found", "work_not_found"} else 403 if error_code == "caller_type_not_allowed" else 409 if error_code == "review_idempotency_conflict" else 400
        return error_response(request, error_code=error_code, status_code=status_code)
    return success_response(
        request,
        data={
            "review_id": review.review_id,
            "status": review.status.value,
            "summary": review.summary,
            "warnings": review.warnings,
            "caller_type": payload.caller_type,
            "idempotency_key": payload.idempotency_key,
        },
    )


@router.get("/api/v2/ai/reviews/{review_id}")
def get_ai_review(review_id: str, request: Request):
    service = dependencies.get_ai_review_service()
    try:
        review = service.get_ai_review(review_id)
    except ValueError as exc:
        return error_response(request, error_code=str(exc), status_code=404)
    return success_response(request, data=_serialize_review_item(review))


@router.get("/api/v2/ai/reviews")
def list_ai_reviews(request: Request, work_id: str, chapter_id: str = "", candidate_draft_id: str = ""):
    service = dependencies.get_ai_review_service()
    items = service.list_ai_reviews(
        work_id=work_id,
        chapter_id=chapter_id or None,
        candidate_draft_id=candidate_draft_id or None,
    )
    return success_response(request, data={"items": [_serialize_review_item(item) for item in items]})
