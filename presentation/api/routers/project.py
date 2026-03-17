"""
项目管理API路由

作者：孔利群
"""

# 文件路径：presentation/api/routers/project.py


from datetime import datetime
from typing import Optional, List, Dict, Any
import uuid
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from application.agent_mvp import ContinueWritingTool, NovelMemory, ProjectInitTool, TaskContext
from application.services.project_service import ProjectService
from domain.entities.chapter import Chapter
from domain.entities.project import Project, ProjectConfig
from domain.repositories.chapter_repository import IChapterRepository
from domain.repositories.novel_repository import INovelRepository
from domain.types import ProjectId, ProjectStatus, GenreType, ChapterId, ChapterStatus
from infrastructure.llm.llm_factory import LLMFactory


router = APIRouter(prefix="/api/projects", tags=["projects"])


class CreateProjectRequest(BaseModel):
    name: str
    genre: str = "xuanhuan"
    target_words: int = 8000000
    style: str
    protagonist_setting: str
    worldview: Optional[str] = None


class UpdateProjectRequest(BaseModel):
    name: Optional[str] = None
    genre: Optional[str] = None
    target_words: Optional[int] = None
    chapter_words: Optional[int] = None
    style_intensity: Optional[float] = None


class ProjectResponse(BaseModel):
    id: str
    name: str
    novel_id: str
    genre: str
    target_words: int
    chapter_words: int
    style_intensity: float
    status: str
    created_at: str
    updated_at: str


class InitialChapterResponse(BaseModel):
    title: str
    content: str
    word_count: int


class CreateProjectAIResponse(BaseModel):
    project: ProjectResponse
    memory: Dict[str, Any]
    first_chapter: InitialChapterResponse


def get_project_service() -> ProjectService:
    from presentation.api.dependencies import get_project_service
    return get_project_service()


def get_llm_factory() -> LLMFactory:
    from presentation.api.dependencies import get_llm_factory
    return get_llm_factory()


def get_chapter_repo() -> IChapterRepository:
    from presentation.api.dependencies import get_chapter_repo
    return get_chapter_repo()


def get_novel_repo() -> INovelRepository:
    from presentation.api.dependencies import get_novel_repo
    return get_novel_repo()


@router.post("", response_model=CreateProjectAIResponse)
async def create_project(
    request: CreateProjectRequest,
    service: ProjectService = Depends(get_project_service),
    llm_factory: LLMFactory = Depends(get_llm_factory),
    chapter_repo: IChapterRepository = Depends(get_chapter_repo),
    novel_repo: INovelRepository = Depends(get_novel_repo)
):
    """创建项目"""
    try:
        genre = GenreType(request.genre)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"无效的题材类型: {request.genre}")
    
    project = service.create_project(
        name=request.name,
        genre=genre,
        target_words=request.target_words
    )
    init_tool = ProjectInitTool(llm_factory.primary_client, llm_factory.backup_client)
    init_result = await init_tool.execute_async(
        TaskContext(novel_id=str(project.novel_id), goal="新建项目初始化"),
        {
            "name": request.name,
            "genre": request.genre,
            "style": request.style,
            "protagonist": request.protagonist_setting,
            "worldview": request.worldview or ""
        }
    )
    if init_result.status != "success":
        raise HTTPException(status_code=500, detail="初始化设定生成失败")

    memory_manager = NovelMemory()
    memory = memory_manager.merge_analysis(
        {
            "characters": init_result.payload.get("characters") or [],
            "world_settings": init_result.payload.get("world_settings") or [],
            "plot_outline": init_result.payload.get("plot_outline") or [],
            "writing_style": init_result.payload.get("writing_style") or {}
        }
    )
    memory["current_progress"] = {
        "latest_chapter_number": 0,
        "latest_goal": "",
        "last_summary": "已完成故事设定初始化"
    }
    service.bind_memory_to_novel(project.novel_id, memory)

    continue_tool = ContinueWritingTool()
    first_goal = "第1章：命运的开端"
    chapter_result = continue_tool.execute(
        TaskContext(novel_id=str(project.novel_id), goal=first_goal, target_word_count=project.config.chapter_words),
        {"goal": first_goal, "memory": memory, "target_word_count": project.config.chapter_words}
    )
    if chapter_result.status != "success":
        raise HTTPException(status_code=500, detail="首章生成失败")

    first_content = str(chapter_result.payload.get("chapter_text") or "")
    now = datetime.now()
    chapter = Chapter(
        id=ChapterId(str(uuid.uuid4())),
        novel_id=project.novel_id,
        number=1,
        title="第1章 命运的开端",
        content=first_content,
        status=ChapterStatus.DRAFT,
        created_at=now,
        updated_at=now
    )
    chapter_repo.save(chapter)
    novel = novel_repo.find_by_id(project.novel_id)
    if novel:
        novel.add_chapter(chapter, now)
        novel_repo.save(novel)
    memory["current_progress"] = {
        "latest_chapter_number": 1,
        "latest_goal": first_goal,
        "last_summary": first_content[:120]
    }
    service.bind_memory_to_novel(project.novel_id, memory)

    return CreateProjectAIResponse(
        project=_project_to_response(project),
        memory=memory,
        first_chapter=InitialChapterResponse(
            title=chapter.title,
            content=first_content,
            word_count=len(first_content)
        )
    )


@router.get("", response_model=List[ProjectResponse])
def list_projects(
    status: Optional[str] = None,
    service: ProjectService = Depends(get_project_service)
):
    """获取项目列表"""
# 文件：模块：project

    project_status = None
    if status:
        try:
            project_status = ProjectStatus(status)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"无效的状态: {status}")
    
    projects = service.list_projects(project_status)
    return [_project_to_response(p) for p in projects]


@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(project_id: str, service: ProjectService = Depends(get_project_service)):
    """获取项目详情"""
    project = service.get_project(ProjectId(project_id))
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    return _project_to_response(project)


@router.put("/{project_id}", response_model=ProjectResponse)
def update_project(
    project_id: str,
    request: UpdateProjectRequest,
    service: ProjectService = Depends(get_project_service)
):
    """更新项目"""
# 文件：模块：project

    project = service.get_project(ProjectId(project_id))
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    
    config = project.config
    if request.genre:
        try:
            config.genre = GenreType(request.genre)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"无效的题材类型: {request.genre}")
    if request.target_words is not None:
        config.target_words = request.target_words
    if request.chapter_words is not None:
        config.chapter_words = request.chapter_words
    if request.style_intensity is not None:
        config.style_intensity = request.style_intensity
    
    if request.name:
        project = service.update_project_name(ProjectId(project_id), request.name)
    
    project = service.update_project_config(ProjectId(project_id), config)
    return _project_to_response(project)


@router.post("/{project_id}/archive", response_model=ProjectResponse)
def archive_project(project_id: str, service: ProjectService = Depends(get_project_service)):
    """归档项目"""
    try:
        project = service.archive_project(ProjectId(project_id))
        return _project_to_response(project)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{project_id}/activate", response_model=ProjectResponse)
def activate_project(project_id: str, service: ProjectService = Depends(get_project_service)):
    """激活项目"""
# 文件：模块：project

    try:
        project = service.activate_project(ProjectId(project_id))
        return _project_to_response(project)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{project_id}")
def delete_project(project_id: str, service: ProjectService = Depends(get_project_service)):
    """删除项目"""
    try:
        service.delete_project(ProjectId(project_id))
        return {"message": "项目已删除"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


def _project_to_response(project: Project) -> ProjectResponse:
    return ProjectResponse(
        id=str(project.id),
        name=project.name,
        novel_id=str(project.novel_id),
        genre=project.config.genre.value,
        target_words=project.config.target_words,
        chapter_words=project.config.chapter_words,
        style_intensity=project.config.style_intensity,
        status=project.status.value,
        created_at=project.created_at.isoformat(),
        updated_at=project.updated_at.isoformat()
    )
