from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from application.services.v1 import WorkService

router = APIRouter(prefix="/api/v1/works", tags=["v1-works"])


class CreateWorkRequest(BaseModel):
    title: str
    author: str = ""


@router.get("")
def list_works():
    service = WorkService()
    items = service.list_works()
    return {
        "items": [
            {
                "id": item.id,
                "title": item.title,
                "author": item.author,
                "current_word_count": item.current_word_count,
                "created_at": item.created_at.isoformat(),
                "updated_at": item.updated_at.isoformat(),
            }
            for item in items
        ],
        "total": len(items),
    }


@router.post("")
def create_work(request: CreateWorkRequest):
    service = WorkService()
    work = service.create_work(request.title, request.author)
    return {
        "id": work.id,
        "title": work.title,
        "author": work.author,
        "current_word_count": work.current_word_count,
        "created_at": work.created_at.isoformat(),
        "updated_at": work.updated_at.isoformat(),
    }


@router.get("/{work_id}")
def get_work(work_id: str):
    service = WorkService()
    work = next((item for item in service.list_works() if item.id == work_id), None)
    if not work:
        raise HTTPException(status_code=404, detail="work_not_found")
    return {
        "id": work.id,
        "title": work.title,
        "author": work.author,
        "current_word_count": work.current_word_count,
        "created_at": work.created_at.isoformat(),
        "updated_at": work.updated_at.isoformat(),
    }


@router.delete("/{work_id}")
def delete_work(work_id: str):
    service = WorkService()
    service.delete_work(work_id)
    return {"ok": True, "id": work_id}
