from fastapi import APIRouter

from application.services.v1 import build_writing_asset_service
from presentation.api.routers.v1.schemas import (
    CharacterCreateRequest,
    CharacterDeleteResponse,
    CharacterListResponse,
    CharacterResponse,
    CharacterUpdateRequest,
    V1APIError,
    build_conflict_response,
    serialize_character,
)

router = APIRouter(prefix="/api/v1", tags=["v1-characters"])


@router.get("/works/{work_id}/characters", response_model=CharacterListResponse)
def list_characters(work_id: str, keyword: str = ""):
    service = build_writing_asset_service()
    try:
        items = service.list_characters(work_id, keyword)
    except ValueError as exc:
        if str(exc) == "work_not_found":
            raise V1APIError("work_not_found") from exc
        raise
    return {"work_id": work_id, "items": [serialize_character(item) for item in items], "total": len(items)}


@router.post("/works/{work_id}/characters", response_model=CharacterResponse)
def create_character(work_id: str, request: CharacterCreateRequest):
    service = build_writing_asset_service()
    try:
        item = service.create_character(work_id, request.model_dump())
    except ValueError as exc:
        code = str(exc)
        if code == "work_not_found":
            raise V1APIError("work_not_found") from exc
        if code == "invalid_input":
            raise V1APIError("invalid_input") from exc
        raise
    return serialize_character(item)


@router.put("/characters/{character_id}", response_model=CharacterResponse)
def update_character(character_id: str, request: CharacterUpdateRequest):
    service = build_writing_asset_service()
    try:
        item = service.update_character(
            character_id,
            request.model_dump(exclude={"expected_version", "force_override"}, exclude_unset=True),
            expected_version=request.expected_version,
            force_override=request.force_override,
        )
    except ValueError as exc:
        code = str(exc)
        if code == "character_not_found":
            raise V1APIError("asset_not_found") from exc
        if code == "invalid_input":
            raise V1APIError("invalid_input") from exc
        if code == "asset_version_conflict":
            current = service.character_repo.find_by_id(character_id)
            raise V1APIError(
                "asset_version_conflict",
                payload=build_conflict_response(
                    "asset_version_conflict",
                    server_version=int(current.version if current else 1),
                    resource_type="character",
                    resource_id=character_id,
                ),
            ) from exc
        raise
    return serialize_character(item)


@router.delete("/characters/{character_id}", response_model=CharacterDeleteResponse)
def delete_character(character_id: str):
    service = build_writing_asset_service()
    try:
        service.delete_character(character_id)
    except ValueError as exc:
        if str(exc) == "character_not_found":
            raise V1APIError("asset_not_found") from exc
        raise
    return {"ok": True, "id": character_id}
