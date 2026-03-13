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
from domain.types import NovelId


router = APIRouter(prefix="/novels", tags=["小说管理"])


@router.post("/", response_model=NovelResponse)
async def create_novel(
    request: CreateNovelRequest,
    service: ProjectService = Depends(get_project_service)
) -> NovelResponse:
    """
    创建小说项目
    
    Args:
        request: 创建请求
        service: 项目服务
        
    Returns:
        小说响应
    """
    project = service.create_project(
        name=request.title,
        genre=request.genre,
        target_words=request.target_word_count
    )
    
    return NovelResponse(
        id=str(project.novel_id),
        title=project.name,
        author="",
        genre=project.config.genre.value,
        target_word_count=project.config.target_words,
        current_word_count=0,
        chapter_count=0,
        created_at=project.created_at.isoformat(),
        updated_at=project.updated_at.isoformat()
    )


@router.get("/", response_model=List[NovelResponse])
async def list_novels(
    service: ProjectService = Depends(get_project_service)
) -> List[NovelResponse]:
    """
    列出所有小说
    
    Args:
        service: 项目服务
        
    Returns:
        小说列表
    """
    projects = service.list_projects()
    
    return [
        NovelResponse(
            id=str(project.novel_id),
            title=project.name,
            author="",
            genre=project.config.genre.value,
            target_word_count=project.config.target_words,
            current_word_count=0,
            chapter_count=0,
            created_at=project.created_at.isoformat(),
            updated_at=project.updated_at.isoformat()
        )
        for project in projects
    ]


@router.get("/{novel_id}", response_model=NovelResponse)
async def get_novel(
    novel_id: str,
    service: ProjectService = Depends(get_project_service)
) -> NovelResponse:
    """
    获取小说详情
    
    Args:
        novel_id: 小说ID
        service: 项目服务
        
    Returns:
        小说响应
    """
    project = service.get_project_by_novel(NovelId(novel_id))
    if not project:
        raise HTTPException(status_code=404, detail="小说不存在")
    
    return NovelResponse(
        id=str(project.novel_id),
        title=project.name,
        author="",
        genre=project.config.genre.value,
        target_word_count=project.config.target_words,
        current_word_count=0,
        chapter_count=0,
        created_at=project.created_at.isoformat(),
        updated_at=project.updated_at.isoformat()
    )


@router.delete("/{novel_id}")
async def delete_novel(
    novel_id: str,
    service: ProjectService = Depends(get_project_service)
) -> dict:
    """
    删除小说
    
    Args:
        novel_id: 小说ID
        service: 项目服务
    """
    project = service.get_project_by_novel(NovelId(novel_id))
    if not project:
        raise HTTPException(status_code=404, detail="小说不存在")
    
    service.delete_project(project.id)
    return {"message": "删除成功"}
