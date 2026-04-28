from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from application.services.v1 import IOService

router = APIRouter(prefix="/api/v1/io", tags=["v1-io"])


class ImportTxtRequest(BaseModel):
    file_path: str
    title: str = ""
    author: str = ""


@router.post("/import")
def import_txt(request: ImportTxtRequest):
    service = IOService()
    work = service.import_txt(request.file_path, title=request.title, author=request.author)
    return {
        "id": work.id,
        "title": work.title,
        "author": work.author,
        "current_word_count": work.current_word_count,
        "created_at": work.created_at.isoformat(),
        "updated_at": work.updated_at.isoformat(),
    }


@router.get("/export/{work_id}")
def export_txt(work_id: str, output_path: str = Query(default="")):
    service = IOService()
    try:
        file_path = service.export_txt(work_id, output_path)
    except ValueError as exc:
        if str(exc) == "work_not_found":
            raise HTTPException(status_code=404, detail="work_not_found") from exc
        raise
    return {"work_id": work_id, "file_path": file_path}
