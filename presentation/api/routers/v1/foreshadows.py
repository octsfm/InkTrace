from fastapi import APIRouter

from application.services.v1 import build_writing_asset_service
from presentation.api.routers.v1.schemas import (
    ForeshadowCreateRequest,
    ForeshadowDeleteResponse,
    ForeshadowListResponse,
    ForeshadowResponse,
    ForeshadowUpdateRequest,
    V1APIError,
    build_conflict_response,
    serialize_foreshadow,
)

router = APIRouter(prefix="/api/v1", tags=["v1-foreshadows"])


@router.get("/works/{work_id}/foreshadows", response_model=ForeshadowListResponse)
def list_foreshadows(work_id: str, status: str = "open"):
    service = build_writing_asset_service()
    try:
        items = service.list_foreshadows(work_id, status)
    except ValueError as exc:
        code = str(exc)
        if code == "work_not_found":
            raise V1APIError("work_not_found") from exc
        if code == "invalid_input":
            raise V1APIError("invalid_input") from exc
        raise
    return {"work_id": work_id, "items": [serialize_foreshadow(item) for item in items], "total": len(items)}


@router.post("/works/{work_id}/foreshadows", response_model=ForeshadowResponse)
def create_foreshadow(work_id: str, request: ForeshadowCreateRequest):
    service = build_writing_asset_service()
    try:
        item = service.create_foreshadow(work_id, request.model_dump())
    except ValueError as exc:
        code = str(exc)
        if code == "work_not_found":
            raise V1APIError("work_not_found") from exc
        if code == "invalid_input":
            raise V1APIError("invalid_input") from exc
        raise
    return serialize_foreshadow(item)


@router.put("/foreshadows/{foreshadow_id}", response_model=ForeshadowResponse)
def update_foreshadow(foreshadow_id: str, request: ForeshadowUpdateRequest):
    service = build_writing_asset_service()
    try:
        item = service.update_foreshadow(
            foreshadow_id,
            request.model_dump(exclude={"expected_version", "force_override"}, exclude_unset=True),
            expected_version=request.expected_version,
            force_override=request.force_override,
        )
    except ValueError as exc:
        code = str(exc)
        if code == "foreshadow_not_found":
            raise V1APIError("asset_not_found") from exc
        if code == "invalid_input":
            raise V1APIError("invalid_input") from exc
        if code == "asset_version_conflict":
            current = service.foreshadow_repo.find_by_id(foreshadow_id)
            raise V1APIError(
                "asset_version_conflict",
                payload=build_conflict_response(
                    "asset_version_conflict",
                    server_version=int(current.version if current else 1),
                    resource_type="foreshadow",
                    resource_id=foreshadow_id,
                ),
            ) from exc
        raise
    return serialize_foreshadow(item)


@router.delete("/foreshadows/{foreshadow_id}", response_model=ForeshadowDeleteResponse)
def delete_foreshadow(foreshadow_id: str):
    service = build_writing_asset_service()
    try:
        service.delete_foreshadow(foreshadow_id)
    except ValueError as exc:
        if str(exc) == "foreshadow_not_found":
            raise V1APIError("asset_not_found") from exc
        raise
    return {"ok": True, "id": foreshadow_id}
