from __future__ import annotations

from fastapi import APIRouter, Request
from pydantic import Field

from domain.entities.ai.models import ChapterMention
from presentation.api import dependencies
from presentation.api.routers.v2.ai.response_utils import error_response, success_response
from presentation.api.routers.v2.ai.schemas import V2AIBaseModel

router = APIRouter(tags=["v2-mentions"])


class MentionItemPayload(V2AIBaseModel):
    mention_id: str = ""
    entity_type: str
    entity_id: str
    entity_name_snapshot: str = ""
    start_pos: int
    end_pos: int
    source: str = "user_input"
    ai_suggestion_id: str = ""
    status: str = "active"


class ReplaceMentionsRequest(V2AIBaseModel):
    chapter_revision: int
    mentions: list[MentionItemPayload] = Field(default_factory=list)


def _serialize_mention(item: ChapterMention) -> dict[str, object]:
    return {
        "mention_id": item.mention_id,
        "chapter_id": item.chapter_id,
        "work_id": item.work_id,
        "entity_type": item.entity_type.value,
        "entity_id": item.entity_id,
        "entity_name_snapshot": item.entity_name_snapshot,
        "start_pos": item.start_pos,
        "end_pos": item.end_pos,
        "source": item.source.value,
        "ai_suggestion_id": item.ai_suggestion_id,
        "status": item.status.value,
        "is_active": item.is_active,
        "validation_detail": item.validation_detail,
        "created_at": item.created_at,
        "updated_at": item.updated_at,
    }


@router.get("/api/v2/mentions/suggest")
def suggest_mentions(work_id: str, q: str, request: Request, types: str = "", limit: int = 10):
    service = dependencies.get_mention_service()
    try:
        suggestions = service.suggest(
            work_id=work_id,
            query=q,
            entity_types=[item for item in str(types or "").split(",") if item],
            limit=limit,
        )
    except ValueError as exc:
        return error_response(request, error_code=str(exc), status_code=400)
    return success_response(
        request,
        data={
            "suggestions": [
                {
                    "entity_type": item.entity_type.value,
                    "entity_id": item.entity_id,
                    "entity_name": item.entity_name,
                    "match_type": item.match_type,
                    "last_used_at": item.last_used_at,
                    "summary_preview": item.summary_preview,
                }
                for item in suggestions
            ]
        },
    )


@router.get("/api/v2/chapters/{chapter_id}/mentions")
def get_mentions_by_chapter(chapter_id: str, request: Request):
    service = dependencies.get_mention_service()
    return success_response(
        request,
        data={"mentions": [_serialize_mention(item) for item in service.get_by_chapter(chapter_id)]},
    )


@router.put("/api/v2/chapters/{chapter_id}/mentions")
def replace_mentions_by_chapter(chapter_id: str, payload: ReplaceMentionsRequest, request: Request):
    service = dependencies.get_mention_service()
    try:
        mentions = service.replace_mentions(
            chapter_id=chapter_id,
            chapter_revision=payload.chapter_revision,
            mentions=[
                ChapterMention.model_validate(
                    {
                        **item.model_dump(),
                        "chapter_id": chapter_id,
                        "work_id": "",
                    }
                )
                for item in payload.mentions
            ],
        )
    except ValueError as exc:
        error_code = str(exc)
        if error_code in {"chapter_not_found", "mention_not_found"}:
            return error_response(request, error_code=error_code, status_code=404)
        if error_code == "mention_conflict":
            return error_response(request, error_code=error_code, status_code=409)
        return error_response(request, error_code=error_code, status_code=400)
    return success_response(request, data={"mentions": [_serialize_mention(item) for item in mentions]})


@router.get("/api/v2/mentions/{mention_id}/summary")
def get_mention_summary(mention_id: str, request: Request):
    service = dependencies.get_mention_service()
    try:
        summary = service.get_summary(mention_id)
    except ValueError as exc:
        return error_response(request, error_code=str(exc), status_code=404)
    return success_response(
        request,
        data={
            "summary": {
                "mention_id": summary.mention_id,
                "entity_type": summary.entity_type.value,
                "entity_id": summary.entity_id,
                "entity_name_snapshot": summary.entity_name_snapshot,
                "entity_current_name": summary.entity_current_name,
                "summary_text": summary.summary_text,
                "status": summary.status.value,
                "is_active": summary.is_active,
                "last_updated": summary.last_updated,
            }
        },
    )
