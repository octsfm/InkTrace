"""
章节仓储接口模块

作者：孔利群
"""

from abc import ABC, abstractmethod
from typing import Optional, List

from domain.types import ChapterId, NovelId
from domain.entities.chapter import Chapter


class IChapterRepository(ABC):
    """章节仓储接口"""

    @abstractmethod
    def save(self, chapter: Chapter) -> None:
        """
        保存章节
        
        Args:
            chapter: 章节实体
        """
        pass

    @abstractmethod
    def find_by_id(self, chapter_id: ChapterId) -> Optional[Chapter]:
        """
        根据ID查找章节
        
        Args:
            chapter_id: 章节ID
            
        Returns:
            章节实体，不存在则返回None
        """
        pass

    @abstractmethod
    def find_by_novel(self, novel_id: NovelId) -> List[Chapter]:
        """
        查找小说的所有章节
        
        Args:
            novel_id: 小说ID
            
        Returns:
            章节列表
        """
        pass

    @abstractmethod
    def find_latest(self, novel_id: NovelId, count: int) -> List[Chapter]:
        """
        查找小说的最新N个章节
        
        Args:
            novel_id: 小说ID
            count: 数量
            
        Returns:
            章节列表，按章节号倒序
        """
        pass

    @abstractmethod
    def delete(self, chapter_id: ChapterId) -> None:
        """
        删除章节
        
        Args:
            chapter_id: 章节ID
        """
        pass
