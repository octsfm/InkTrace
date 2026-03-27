"""
项目管理服务

作者：孔利群
"""

# 文件路径：application/services/project_service.py


from datetime import datetime
from typing import Optional, List, Dict, Any
import uuid

from domain.entities.project import Project, ProjectConfig
from domain.entities.novel import Novel
from domain.repositories.project_repository import IProjectRepository
from domain.repositories.novel_repository import INovelRepository
from domain.types import ProjectId, NovelId, ProjectStatus, GenreType


class ProjectService:
    """项目管理服务"""
    
    def __init__(
        self,
        project_repo: IProjectRepository,
        novel_repo: INovelRepository
    ):
        self.project_repo = project_repo
        self.novel_repo = novel_repo
    
    def create_project(
        self,
        name: str,
        genre: GenreType = GenreType.XUANHUAN,
        target_words: int = 8000000,
        author: str = ""
    ) -> Project:
        """创建新项目"""
# 文件：模块：project_service

        novel_id = NovelId(str(uuid.uuid4()))
        now = datetime.now()
        novel = Novel(
            id=novel_id,
            title=name,
            author=author,
            genre=genre.value,
            target_word_count=target_words,
            created_at=now,
            updated_at=now
        )
        self.novel_repo.save(novel)
        
        config = ProjectConfig(
            genre=genre,
            target_words=target_words
        )
        
        project = Project(
            id=ProjectId(str(uuid.uuid4())),
            name=name,
            novel_id=novel_id,
            config=config
        )
        
        self.project_repo.save(project)
        return project
    
    def get_project(self, project_id: ProjectId) -> Optional[Project]:
        """获取项目"""
        return self.project_repo.find_by_id(project_id)
    
    def get_project_by_novel(self, novel_id: NovelId) -> Optional[Project]:
        """根据小说ID获取项目"""
        return self.project_repo.find_by_novel_id(novel_id)

    def get_memory_by_novel(self, novel_id: NovelId) -> Dict[str, Any]:
        project = self.project_repo.find_by_novel_id(novel_id)
        if not project:
            raise ValueError(f"项目不存在，novel_id: {novel_id}")
        memory = project.config.memory or {}
        if not isinstance(memory, dict):
            return {}
        return memory

    def bind_memory_to_novel(self, novel_id: NovelId, memory: Dict[str, Any]) -> Project:
        project = self.project_repo.find_by_novel_id(novel_id)
        if not project:
            raise ValueError(f"项目不存在，novel_id: {novel_id}")
        project.config.memory = memory if isinstance(memory, dict) else {}
        project.updated_at = datetime.now()
        self.project_repo.save(project)
        return project

    def ensure_project_for_novel(self, novel_id: NovelId) -> Project:
        project = self.project_repo.find_by_novel_id(novel_id)
        if project:
            return project
        novel = self.novel_repo.find_by_id(novel_id)
        if not novel:
            raise ValueError(f"小说不存在，novel_id: {novel_id}")
        try:
            genre = GenreType(novel.genre)
        except ValueError:
            genre = GenreType.XUANHUAN
        config = ProjectConfig(
            genre=genre,
            target_words=novel.target_word_count
        )
        project = Project(
            id=ProjectId(str(uuid.uuid4())),
            name=novel.title,
            novel_id=novel.id,
            config=config,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        self.project_repo.save(project)
        return project
    
    def list_projects(self, status: Optional[ProjectStatus] = None) -> List[Project]:
        """获取项目列表"""
# 文件：模块：project_service

        return self.project_repo.find_all(status)
    
    def list_active_projects(self) -> List[Project]:
        """获取活跃项目列表"""
        return self.project_repo.find_all(ProjectStatus.ACTIVE)
    
    def update_project_config(
        self,
        project_id: ProjectId,
        config: ProjectConfig
    ) -> Project:
        """更新项目配置"""
# 文件：模块：project_service

        project = self.project_repo.find_by_id(project_id)
        if not project:
            raise ValueError(f"项目不存在: {project_id}")
        
        project.update_config(config)
        self.project_repo.save(project)
        return project
    
    def update_project_name(
        self,
        project_id: ProjectId,
        name: str
    ) -> Project:
        """更新项目名称"""
        project = self.project_repo.find_by_id(project_id)
        if not project:
            raise ValueError(f"项目不存在: {project_id}")
        
        project.update_name(name)
        self.project_repo.save(project)
        return project
    
    def archive_project(self, project_id: ProjectId) -> Project:
        """归档项目"""
# 文件：模块：project_service

        project = self.project_repo.find_by_id(project_id)
        if not project:
            raise ValueError(f"项目不存在: {project_id}")
        
        project.archive()
        self.project_repo.save(project)
        return project
    
    def activate_project(self, project_id: ProjectId) -> Project:
        """激活项目"""
        project = self.project_repo.find_by_id(project_id)
        if not project:
            raise ValueError(f"项目不存在: {project_id}")
        
        project.activate()
        self.project_repo.save(project)
        return project
    
    def delete_project(self, project_id: ProjectId) -> None:
        """删除项目"""
# 文件：模块：project_service

        project = self.project_repo.find_by_id(project_id)
        if not project:
            raise ValueError(f"项目不存在: {project_id}")
        
        self.project_repo.delete(project_id)
        self.novel_repo.delete(project.novel_id)
    
    def get_project_count(self, status: Optional[ProjectStatus] = None) -> int:
        """获取项目数量"""
        return self.project_repo.count(status)
