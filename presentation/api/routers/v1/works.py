from fastapi import APIRouter

from application.services.v1 import WorkService
from presentation.api.routers.v1.schemas import (
    V1APIError,
    WorkCreateRequest,
    WorkDeleteResponse,
    WorkListResponse,
    WorkResponse,
    WorkUpdateRequest,
    serialize_work,
)

router = APIRouter(prefix="/api/v1/works", tags=["v1-works"])

@router.get("", response_model=WorkListResponse)
def list_works():
    service = WorkService()
    items = service.list_works()
    return {"items": [serialize_work(item) for item in items], "total": len(items)}


@router.post("", response_model=WorkResponse)
def create_work(request: WorkCreateRequest):
    service = WorkService()
    work = service.create_work(request.title, request.author)
    return serialize_work(work)


@router.get("/{work_id}", response_model=WorkResponse)
def get_work(work_id: str):
    service = WorkService()
    try:
        work = service.get_work(work_id)
    except ValueError as exc:
        if str(exc) == "work_not_found":
            raise V1APIError("work_not_found") from exc
        raise
    return serialize_work(work)


@router.put("/{work_id}", response_model=WorkResponse)
def update_work(work_id: str, request: WorkUpdateRequest):
    service = WorkService()
    try:
        work = service.update_work(work_id, title=request.title, author=request.author)
    except ValueError as exc:
        if str(exc) == "work_not_found":
            raise V1APIError("work_not_found") from exc
        raise
    return serialize_work(work)


@router.delete("/{work_id}", response_model=WorkDeleteResponse)
def delete_work(work_id: str):
    service = WorkService()
    try:
        service.delete_work(work_id)
    except ValueError as exc:
        if str(exc) == "work_not_found":
            raise V1APIError("work_not_found") from exc
        raise
    return {"ok": True, "id": work_id}
