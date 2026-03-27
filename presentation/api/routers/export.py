"""
导出服务API路由

作者：孔利群
"""

# 文件路径：presentation/api/routers/export.py


import os
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from application.services.logging_service import build_log_context, get_logger
from application.services.export_service import ExportService
from application.dto.request_dto import ExportNovelRequest
from application.dto.response_dto import ExportResponse
from presentation.api.dependencies import get_export_service


router = APIRouter(prefix="/export", tags=["导出"])
logger = get_logger(__name__)

EXPORTS_DIR = Path("exports")


def _validate_file_path(file_path: str) -> Path:
    """
    验证文件路径安全性
    
    Args:
        file_path: 请求的文件路径
        
    Returns:
        安全的绝对路径
        
    Raises:
        HTTPException: 路径不安全时抛出
    """
# 文件：模块：export

    exports_dir = EXPORTS_DIR.resolve()
    
    try:
        requested_path = (exports_dir / file_path).resolve()
    except (ValueError, OSError):
        raise HTTPException(status_code=400, detail="无效的文件路径")
    
    if not str(requested_path).startswith(str(exports_dir)):
        raise HTTPException(status_code=403, detail="禁止访问该路径")
    
    if not requested_path.exists():
        raise HTTPException(status_code=404, detail="文件不存在")
    
    if not requested_path.is_file():
        raise HTTPException(status_code=400, detail="不是有效的文件")
    
    return requested_path


@router.post("/", response_model=ExportResponse)
async def export_novel(
    request: ExportNovelRequest,
    service: ExportService = Depends(get_export_service)
) -> ExportResponse:
    """
    导出小说
    
    Args:
        request: 导出请求
        service: 导出服务
        
    Returns:
        导出响应
    """
# 文件：模块：export

    logger.info(
        "导出请求已接收",
        extra=build_log_context(
            event="export_request_received",
            novel_id=request.novel_id,
            scope=request.scope,
            format=request.format,
            file_path=request.output_path,
        ),
    )
    try:
        return service.export_novel(request)
    except ValueError as e:
        logger.error(
            "导出请求失败",
            extra=build_log_context(
                event="export_request_failed",
                novel_id=request.novel_id,
                scope=request.scope,
                format=request.format,
                file_path=request.output_path,
                error=str(e),
            ),
        )
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/download/{file_path:path}")
async def download_file(file_path: str) -> FileResponse:
    """
    下载导出文件
    
    Args:
        file_path: 文件路径（相对于exports目录）
        
    Returns:
        文件响应
    """
# 文件：模块：export

    logger.info(
        "导出下载请求",
        extra=build_log_context(event="export_download_requested", file_path=file_path),
    )
    try:
        safe_path = _validate_file_path(file_path)
    except HTTPException as exc:
        logger.error(
            "导出下载失败",
            extra=build_log_context(event="export_download_failed", file_path=file_path, error=str(exc.detail)),
        )
        raise
    
    return FileResponse(
        path=safe_path,
        filename=safe_path.name,
        media_type="application/octet-stream"
    )
