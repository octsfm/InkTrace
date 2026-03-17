"""
小说管理API路由

作者：孔利群
"""

# 文件路径：presentation/api/routers/novel.py


from typing import List
from fastapi import APIRouter, Depends, HTTPException

from application.services.project_service import ProjectService
from application.dto.request_dto import CreateNovelRequest
from application.dto.response_dto import NovelResponse
from domain.repositories.chapter_repository import IChapterRepository
from presentation.api.dependencies import get_chapter_repo, get_project_service
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
# 文件：模块：novel

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
        word_count=0,
        target_word_count=project.config.target_words,
        current_word_count=0,
        chapter_count=0,
        chapters=[],
        memory=project.config.memory,
        status=project.status.value,
        created_at=project.created_at.isoformat(),
        updated_at=project.updated_at.isoformat()
    )


@router.get("/", response_model=List[NovelResponse])
async def list_novels(
    service: ProjectService = Depends(get_project_service),
    chapter_repo: IChapterRepository = Depends(get_chapter_repo)
) -> List[NovelResponse]:
    """
    列出所有小说
    
    Args:
        service: 项目服务
        
    Returns:
        小说列表
    """
# 文件：模块：novel

    projects = service.list_projects()
    
    return [
        _project_to_novel_response(project, chapter_repo)
        for project in projects
    ]


@router.get("/{novel_id}", response_model=NovelResponse)
async def get_novel(
    novel_id: str,
    service: ProjectService = Depends(get_project_service),
    chapter_repo: IChapterRepository = Depends(get_chapter_repo)
) -> NovelResponse:
    """
    获取小说详情
    
    Args:
        novel_id: 小说ID
        service: 项目服务
        
    Returns:
        小说响应
    """
# 文件：模块：novel

    project = service.get_project_by_novel(NovelId(novel_id))
    if not project:
        raise HTTPException(status_code=404, detail="小说不存在")
    
    return _project_to_novel_response(project, chapter_repo)


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
# 文件：模块：novel

    project = service.get_project_by_novel(NovelId(novel_id))
    if not project:
        raise HTTPException(status_code=404, detail="小说不存在")
    
    service.delete_project(project.id)
    return {"message": "删除成功"}


def _project_to_novel_response(project, chapter_repo: IChapterRepository) -> NovelResponse:
    chapters = chapter_repo.find_by_novel(project.novel_id)
    chapter_items = [
        {
            "id": str(chapter.id),
            "number": chapter.number,
            "title": chapter.title,
            "word_count": chapter.word_count
        }
        for chapter in chapters
    ]
    current_word_count = sum([item["word_count"] for item in chapter_items])
    return NovelResponse(
        id=str(project.novel_id),
        title=project.name,
        author="",
        genre=project.config.genre.value,
        word_count=current_word_count,
        target_word_count=project.config.target_words,
        current_word_count=current_word_count,
        chapter_count=len(chapter_items),
        chapters=chapter_items,
        memory=project.config.memory,
        status=project.status.value,
        created_at=project.created_at.isoformat(),
        updated_at=project.updated_at.isoformat()
    )
