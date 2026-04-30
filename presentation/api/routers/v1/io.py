from urllib.parse import quote

from fastapi import APIRouter, File, Form, Query, Response, UploadFile

from application.services.v1 import IOService
from presentation.api.routers.v1.schemas import ImportTxtResponse, V1APIError, serialize_chapter, serialize_work

router = APIRouter(prefix="/api/v1/io", tags=["v1-io"])

@router.post("/import", response_model=ImportTxtResponse)
async def import_txt(
    file: UploadFile = File(...),
    title: str = Form(default=""),
    author: str = Form(default=""),
):
    service = IOService()
    raw_bytes = await file.read()
    try:
        work = service.import_txt_upload(file.filename or "未命名作品.txt", raw_bytes, title=title, author=author)
    except UnicodeDecodeError as exc:
        raise V1APIError("invalid_input", payload={"detail": "txt_decode_failed"}) from exc
    except ValueError as exc:
        if str(exc) in {"txt_file_too_large", "invalid_input"}:
            raise V1APIError("invalid_input", payload={"detail": str(exc)}) from exc
        raise
    chapters = service.chapter_repo.list_by_work(work.id)
    return {
        **serialize_work(work),
        "chapters": [serialize_chapter(chapter) for chapter in chapters],
    }


@router.get("/export/{work_id}")
def export_txt(
    work_id: str,
    include_titles: bool = Query(default=True),
    gap_lines: int = Query(default=1, ge=0, le=2),
):
    service = IOService()
    try:
        filename, content = service.export_txt(
            work_id,
            include_titles=include_titles,
            gap_lines=gap_lines,
        )
    except ValueError as exc:
        if str(exc) == "work_not_found":
            raise V1APIError("work_not_found") from exc
        if str(exc) == "invalid_input":
            raise V1APIError("invalid_input") from exc
        raise
    quoted = quote(filename)
    return Response(
        content=content,
        media_type="text/plain; charset=utf-8",
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{quoted}"
        },
    )
