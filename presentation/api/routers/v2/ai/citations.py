from __future__ import annotations

from fastapi import APIRouter, Request

from presentation.api import dependencies
from presentation.api.routers.v2.ai.response_utils import error_response, success_response

router = APIRouter(tags=["v2-ai-citations"])


def _serialize_citation(item) -> dict[str, object]:
    return {
        "citation_id": item.citation_id,
        "candidate_version_id": item.candidate_version_id,
        "candidate_draft_id": item.candidate_draft_id,
        "work_id": item.work_id,
        "source_type": item.source_type.value,
        "source_id": item.source_id,
        "source_name": item.source_name_snapshot,
        "source_name_snapshot": item.source_name_snapshot,
        "source_span": item.source_span,
        "source_excerpt": item.source_excerpt,
        "context_in_draft": item.context_in_draft,
        "verification_status": item.verification_status.value,
        "verification_detail": item.verification_detail,
        "confidence": item.confidence,
        "verified_at": item.verified_at,
        "created_at": item.created_at,
    }


def _serialize_batch(batch) -> dict[str, object]:
    return {
        "batch_id": batch.batch_id,
        "candidate_version_id": batch.candidate_version_id,
        "candidate_draft_id": batch.candidate_draft_id,
        "total_count": batch.total_count,
        "verified_count": batch.verified_count,
        "unknown_count": batch.unknown_count,
        "citations": [_serialize_citation(item) for item in batch.citations],
    }


@router.get("/api/v2/ai/citations/candidate-version/{candidate_version_id}")
def get_citations_by_candidate_version(candidate_version_id: str, request: Request):
    service = dependencies.get_citation_link_service()
    try:
        batch = service.get_by_candidate_version(candidate_version_id)
    except ValueError as exc:
        return error_response(request, error_code=str(exc), status_code=404)
    return success_response(request, data={"batch": _serialize_batch(batch)})


@router.get("/api/v2/ai/citations/candidate-draft/{candidate_draft_id}")
def get_citations_by_candidate_draft(candidate_draft_id: str, request: Request):
    service = dependencies.get_citation_link_service()
    try:
        batches = service.get_by_candidate_draft(candidate_draft_id)
    except ValueError as exc:
        return error_response(request, error_code=str(exc), status_code=404)
    return success_response(request, data={"batches": [_serialize_batch(item) for item in batches]})


@router.get("/api/v2/ai/citations/source")
def get_citations_by_source(source_type: str, source_id: str, request: Request):
    service = dependencies.get_citation_link_service()
    try:
        citations = service.get_by_source(source_type, source_id)
    except ValueError as exc:
        return error_response(request, error_code=str(exc), status_code=400)
    return success_response(request, data={"citations": [_serialize_citation(item) for item in citations]})


@router.get("/api/v2/ai/citations/{citation_id}/source-detail")
def get_citation_source_detail(citation_id: str, request: Request):
    service = dependencies.get_citation_link_service()
    try:
        payload = service.get_citation_source_detail(citation_id)
    except ValueError as exc:
        return error_response(request, error_code=str(exc), status_code=404)
    return success_response(request, data=payload)

