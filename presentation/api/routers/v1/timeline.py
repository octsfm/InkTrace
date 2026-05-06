from fastapi import APIRouter

from application.services.v1 import build_writing_asset_service
from presentation.api.routers.v1.schemas import (
    TimelineEventCreateRequest,
    TimelineEventDeleteResponse,
    TimelineEventListResponse,
    TimelineEventReorderRequest,
    TimelineEventResponse,
    TimelineEventUpdateRequest,
    V1APIError,
    build_conflict_response,
    serialize_timeline_event,
)

router = APIRouter(prefix="/api/v1", tags=["v1-timeline"])


@router.get("/works/{work_id}/timeline-events", response_model=TimelineEventListResponse)
def list_timeline_events(work_id: str):
    service = build_writing_asset_service()
    try:
        items = service.list_timeline_events(work_id)
    except ValueError as exc:
        if str(exc) == "work_not_found":
            raise V1APIError("work_not_found") from exc
        raise
    return {"work_id": work_id, "items": [serialize_timeline_event(item) for item in items], "total": len(items)}


@router.post("/works/{work_id}/timeline-events", response_model=TimelineEventResponse)
def create_timeline_event(work_id: str, request: TimelineEventCreateRequest):
    service = build_writing_asset_service()
    try:
        item = service.create_timeline_event(work_id, request.model_dump())
    except ValueError as exc:
        code = str(exc)
        if code == "work_not_found":
            raise V1APIError("work_not_found") from exc
        if code == "invalid_input":
            raise V1APIError("invalid_input") from exc
        raise
    return serialize_timeline_event(item)


@router.put("/timeline-events/{event_id}", response_model=TimelineEventResponse)
def update_timeline_event(event_id: str, request: TimelineEventUpdateRequest):
    service = build_writing_asset_service()
    try:
        item = service.update_timeline_event(
            event_id,
            request.model_dump(exclude={"expected_version", "force_override"}, exclude_unset=True),
            expected_version=request.expected_version,
            force_override=request.force_override,
        )
    except ValueError as exc:
        code = str(exc)
        if code == "timeline_event_not_found":
            raise V1APIError("asset_not_found") from exc
        if code == "invalid_input":
            raise V1APIError("invalid_input") from exc
        if code == "asset_version_conflict":
            current = service.timeline_event_repo.find_by_id(event_id)
            raise V1APIError(
                "asset_version_conflict",
                payload=build_conflict_response(
                    "asset_version_conflict",
                    server_version=int(current.version if current else 1),
                    resource_type="timeline_event",
                    resource_id=event_id,
                ),
            ) from exc
        raise
    return serialize_timeline_event(item)


@router.delete("/timeline-events/{event_id}", response_model=TimelineEventDeleteResponse)
def delete_timeline_event(event_id: str):
    service = build_writing_asset_service()
    try:
        service.delete_timeline_event(event_id)
    except ValueError as exc:
        if str(exc) == "timeline_event_not_found":
            raise V1APIError("asset_not_found") from exc
        raise
    return {"ok": True, "id": event_id}


@router.put("/works/{work_id}/timeline-events/reorder", response_model=TimelineEventListResponse)
def reorder_timeline_events(work_id: str, request: TimelineEventReorderRequest):
    service = build_writing_asset_service()
    try:
        items = service.reorder_timeline_events(
            work_id,
            [{"id": item.id, "order_index": item.order_index} for item in request.items],
        )
    except ValueError as exc:
        code = str(exc)
        if code == "work_not_found":
            raise V1APIError("work_not_found") from exc
        if code == "invalid_input":
            raise V1APIError("invalid_input") from exc
        raise
    return {"work_id": work_id, "items": [serialize_timeline_event(item) for item in items], "total": len(items)}
