"""
小说管理API路由

作者：孔利群
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException

from application.services.project_service import ProjectService
from application.dto.request_dto import CreateNovelRequest
from application.dto.response_dto import NovelResponse
from presentation.api.dependencies import get_project_service


router = APIRouter()


@router.post("/", response_model=NovelResponse)
async def create_novel(
    request: CreateNovelRequest,
    service: ProjectService = Depends(get_project_service)
):
    """
    创建小说项目
    
    Args:
        request: 创建请求
        service: 项目服务
        
    Returns:
        小说响应
    """
    return service.create_novel(request)


@router.get("/", response_model=List[NovelResponse])
async def list_novels(
    service: ProjectService = Depends(get_project_service)
):
    """
    列出所有小说
    
    Args:
        service: 项目服务
        
    Returns:
        小说列表
    """
    return service.list_novels()


@router.get("/{novel_id}", response_model=NovelResponse)
async def get_novel(
    novel_id: str,
    service: ProjectService = Depends(get_project_service)
):
    """
    获取小说详情
    
    Args:
        novel_id: 小说ID
        service: 项目服务
        
    Returns:
        小说响应
    """
    novel = service.get_novel(novel_id)
    if not novel:
        raise HTTPException(status_code=404, detail="小说不存在")
    return novel


@router.delete("/{novel_id}")
async def delete_novel(
    novel_id: str,
    service: ProjectService = Depends(get_project_service)
):
    """
    删除小说
    
    Args:
        novel_id: 小说ID
        service: 项目服务
    """
    service.delete_novel(novel_id)
    return {"message": "删除成功"}
