"""
项目仓储接口

作者：孔利群
"""

from abc import ABC, abstractmethod
from typing import Optional, List

from domain.entities.project import Project
from domain.types import ProjectId, NovelId, ProjectStatus


class IProjectRepository(ABC):
    """项目仓储接口"""
    
    @abstractmethod
    def find_by_id(self, project_id: ProjectId) -> Optional[Project]:
        """根据ID查找项目"""
        pass
    
    @abstractmethod
    def find_by_novel_id(self, novel_id: NovelId) -> Optional[Project]:
        """根据小说ID查找项目"""
        pass
    
    @abstractmethod
    def find_all(self, status: Optional[ProjectStatus] = None) -> List[Project]:
        """查找所有项目"""
        pass
    
    @abstractmethod
    def save(self, project: Project) -> None:
        """保存项目"""
        pass
    
    @abstractmethod
    def delete(self, project_id: ProjectId) -> None:
        """删除项目"""
        pass
    
    @abstractmethod
    def count(self, status: Optional[ProjectStatus] = None) -> int:
        """统计项目数量"""
        pass
