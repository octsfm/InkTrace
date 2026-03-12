"""
续写服务API路由

作者：孔利群
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException

from application.services.writing_service import WritingService
from application.dto.request_dto import GenerateChapterRequest, PlanPlotRequest
from application.dto.response_dto import GenerateChapterResponse
from presentation.api.dependencies import get_writing_service


router = APIRouter()


@router.post("/plan", response_model=List[dict])
async def plan_plot(
    request: PlanPlotRequest,
    service: WritingService = Depends(get_writing_service)
):
    """
    规划剧情走向
    
    Args:
        request: 规划请求
        service: 续写服务
        
    Returns:
        剧情节点列表
    """
    try:
        return service.plan_plot(request)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/generate", response_model=GenerateChapterResponse)
async def generate_chapter(
    request: GenerateChapterRequest,
    service: WritingService = Depends(get_writing_service)
):
    """
    生成章节
    
    Args:
        request: 生成请求
        service: 续写服务
        
    Returns:
        生成响应
    """
    try:
        return service.generate_chapter(request)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
