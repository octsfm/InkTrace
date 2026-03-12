"""
内容管理API路由

作者：孔利群
"""

from fastapi import APIRouter, Depends, HTTPException

from application.services.content_service import ContentService
from application.dto.request_dto import ImportNovelRequest
from application.dto.response_dto import NovelResponse, StyleAnalysisResponse, PlotAnalysisResponse
from presentation.api.dependencies import get_content_service


router = APIRouter()


@router.post("/import", response_model=NovelResponse)
async def import_novel(
    request: ImportNovelRequest,
    service: ContentService = Depends(get_content_service)
):
    """
    导入小说文件
    
    Args:
        request: 导入请求
        service: 内容服务
        
    Returns:
        小说响应
    """
    try:
        return service.import_novel(request)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/style/{novel_id}", response_model=StyleAnalysisResponse)
async def analyze_style(
    novel_id: str,
    service: ContentService = Depends(get_content_service)
):
    """
    分析小说文风
    
    Args:
        novel_id: 小说ID
        service: 内容服务
        
    Returns:
        文风分析响应
    """
    try:
        return service.analyze_style(novel_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/plot/{novel_id}", response_model=PlotAnalysisResponse)
async def analyze_plot(
    novel_id: str,
    service: ContentService = Depends(get_content_service)
):
    """
    分析小说剧情
    
    Args:
        novel_id: 小说ID
        service: 内容服务
        
    Returns:
        剧情分析响应
    """
    try:
        return service.analyze_plot(novel_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
