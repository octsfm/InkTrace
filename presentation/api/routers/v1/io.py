from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile
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
    if not service.path_import_allowed():
        raise HTTPException(status_code=400, detail="path_import_not_supported_in_web")
    work = service.import_txt(request.file_path, title=request.title, author=request.author)
    return {
        "id": work.id,
        "title": work.title,
        "author": work.author,
        "current_word_count": work.current_word_count,
        "created_at": work.created_at.isoformat(),
        "updated_at": work.updated_at.isoformat(),
    }


@router.post("/import-upload")
async def import_txt_upload(
    txt_file: UploadFile = File(...),
    title: str = Form(default=""),
    author: str = Form(default=""),
):
    service = IOService()
    raw_bytes = await txt_file.read()
    try:
        work = service.import_txt_upload(txt_file.filename or "未命名作品.txt", raw_bytes, title=title, author=author)
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=400, detail="txt_decode_failed") from exc
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
