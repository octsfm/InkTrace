"""
导出服务API路由

作者：孔利群
"""

import os
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from application.services.export_service import ExportService
from application.dto.request_dto import ExportNovelRequest
from application.dto.response_dto import ExportResponse
from presentation.api.dependencies import get_export_service


router = APIRouter(prefix="/export", tags=["导出"])

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
    try:
        return service.export_novel(request)
    except ValueError as e:
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
    safe_path = _validate_file_path(file_path)
    
    return FileResponse(
        path=safe_path,
        filename=safe_path.name,
        media_type="application/octet-stream"
    )
