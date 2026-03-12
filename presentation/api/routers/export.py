"""
导出服务API路由

作者：孔利群
"""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from application.services.export_service import ExportService
from application.dto.request_dto import ExportNovelRequest
from application.dto.response_dto import ExportResponse
from presentation.api.dependencies import get_export_service


router = APIRouter()


@router.post("/", response_model=ExportResponse)
async def export_novel(
    request: ExportNovelRequest,
    service: ExportService = Depends(get_export_service)
):
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
async def download_file(file_path: str):
    """
    下载导出文件
    
    Args:
        file_path: 文件路径
    """
    import os
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="文件不存在")
    return FileResponse(file_path)
