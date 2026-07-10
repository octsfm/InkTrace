from __future__ import annotations

from fastapi import APIRouter, Request
from pydantic import Field

from presentation.api import dependencies
from presentation.api.routers.v2.ai.response_utils import error_response, success_response
from presentation.api.routers.v2.ai.schemas import V2AIBaseModel

router = APIRouter(prefix="/api/v2/ai/opening", tags=["v2-ai-opening"])


class PrepareBriefRequest(V2AIBaseModel):
    work_id: str
    story_premise: str
    protagonist_desire: str
    third_chapter_expectation: str
    source_outline_version: str = ""
    source_asset_versions: dict[str, str] = Field(default_factory=dict)
    idempotency_key: str = Field(min_length=1, max_length=256)


class ReferenceInput(V2AIBaseModel):
    title: str
    chapters_text: list[str]


class ImportReferencesRequest(V2AIBaseModel):
    references: list[ReferenceInput]
    rights_confirmed: bool
    rights_text_version: str
    idempotency_key: str = Field(min_length=1, max_length=256)


class IdempotentRequest(V2AIBaseModel):
    idempotency_key: str = Field(min_length=1, max_length=256)


class UserActionRequest(V2AIBaseModel):
    caller_type: str
    user_action: bool
    user_id: str
    idempotency_key: str = Field(min_length=1, max_length=256)


class ReviseDirectionRequest(V2AIBaseModel):
    name: str = Field(min_length=1, max_length=120)
    summary: str = Field(min_length=1, max_length=2000)
    chapter_goals: list[str] = Field(min_length=3, max_length=3)
    advantages: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    idempotency_key: str = Field(min_length=1, max_length=256)


def _data(value):
    if value is None:
        return None
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if isinstance(value, dict):
        return {key: _data(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_data(item) for item in value]
    return value


def _error(request: Request, exc: ValueError):
    code = str(exc)
    if code == "P2_CALLER_FORBIDDEN":
        status = 403
    elif code.endswith("NOT_FOUND"):
        status = 404
    elif code in {"P2_OPENING_DIRECTION_STALE", "P2_OPENING_DRAFT_BATCH_NOT_RUNNING", "P2_OPENING_STRATEGY_SIMILARITY_BLOCKED"}:
        status = 409
    else:
        status = 400
    return error_response(request, error_code=code, status_code=status)


@router.post("/briefs")
def prepare_brief(payload: PrepareBriefRequest, request: Request):
    try:
        value = dependencies.get_opening_agent_service().prepare_brief(**payload.model_dump())
        return success_response(request, data=_data(value))
    except ValueError as exc:
        return _error(request, exc)


@router.post("/briefs/{brief_id}/references")
def import_references(brief_id: str, payload: ImportReferencesRequest, request: Request):
    try:
        value = dependencies.get_opening_agent_service().import_references(
            brief_id=brief_id, references=[item.model_dump() for item in payload.references],
            rights_confirmed=payload.rights_confirmed, rights_text_version=payload.rights_text_version,
            idempotency_key=payload.idempotency_key,
        )
        return success_response(request, data=_data(value))
    except ValueError as exc:
        return _error(request, exc)


@router.post("/briefs/{brief_id}/directions:generate")
def generate_directions(brief_id: str, payload: IdempotentRequest, request: Request):
    try:
        value = dependencies.get_opening_agent_service().generate_directions(brief_id=brief_id, idempotency_key=payload.idempotency_key)
        return success_response(request, data=_data(value))
    except ValueError as exc:
        return _error(request, exc)


@router.get("/direction-batches/{batch_id}")
def get_direction_batch(batch_id: str, request: Request):
    try:
        return success_response(request, data=_data(dependencies.get_opening_agent_service().get_direction_batch(batch_id)))
    except ValueError as exc:
        return _error(request, exc)


@router.post("/directions/{direction_id}:confirm")
def confirm_direction(direction_id: str, payload: UserActionRequest, request: Request):
    if payload.caller_type != "user_action" or not payload.user_action:
        return error_response(request, error_code="P2_CALLER_FORBIDDEN", status_code=403)
    try:
        value = dependencies.get_opening_agent_service().confirm_direction(direction_id=direction_id, **payload.model_dump())
        return success_response(request, data=_data(value))
    except ValueError as exc:
        return _error(request, exc)


@router.post("/directions/{direction_id}:revise")
def revise_direction(direction_id: str, payload: ReviseDirectionRequest, request: Request):
    try:
        value = dependencies.get_opening_agent_service().revise_direction(
            direction_id=direction_id, **payload.model_dump()
        )
        return success_response(request, data=_data(value))
    except ValueError as exc:
        return _error(request, exc)


@router.post("/directions/{direction_id}/drafts:generate")
def generate_drafts(direction_id: str, payload: IdempotentRequest, request: Request):
    try:
        value = dependencies.get_opening_agent_service().generate_drafts(direction_id=direction_id, idempotency_key=payload.idempotency_key)
        return success_response(request, data=_data(value))
    except ValueError as exc:
        return _error(request, exc)


@router.get("/draft-batches/{batch_id}")
def get_draft_batch(batch_id: str, request: Request):
    try:
        return success_response(request, data=_data(dependencies.get_opening_agent_service().get_draft_batch(batch_id)))
    except ValueError as exc:
        return _error(request, exc)


@router.post("/draft-batches/{batch_id}:stop")
def stop_draft_batch(batch_id: str, payload: UserActionRequest, request: Request):
    if payload.caller_type != "user_action" or not payload.user_action:
        return error_response(request, error_code="P2_CALLER_FORBIDDEN", status_code=403)
    try:
        value = dependencies.get_opening_agent_service().stop_draft_batch(batch_id=batch_id, **payload.model_dump())
        return success_response(request, data=_data(value))
    except ValueError as exc:
        return _error(request, exc)


@router.get("/works/{work_id}/latest")
def get_latest(work_id: str, request: Request):
    return success_response(request, data=_data(dependencies.get_opening_agent_service().get_latest(work_id)))
