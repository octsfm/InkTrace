"""
大纲仓储接口模块

作者：孔利群
"""

from abc import ABC, abstractmethod
from typing import Optional

from domain.types import OutlineId, NovelId
from domain.entities.outline import Outline


class IOutlineRepository(ABC):
    """大纲仓储接口"""

    @abstractmethod
    def save(self, outline: Outline) -> None:
        """
        保存大纲
        
        Args:
            outline: 大纲实体
        """
        pass

    @abstractmethod
    def find_by_id(self, outline_id: OutlineId) -> Optional[Outline]:
        """
        根据ID查找大纲
        
        Args:
            outline_id: 大纲ID
            
        Returns:
            大纲实体，不存在则返回None
        """
        pass

    @abstractmethod
    def find_by_novel(self, novel_id: NovelId) -> Optional[Outline]:
        """
        查找小说的大纲
        
        Args:
            novel_id: 小说ID
            
        Returns:
            大纲实体，不存在则返回None
        """
        pass

    @abstractmethod
    def delete(self, outline_id: OutlineId) -> None:
        """
        删除大纲
        
        Args:
            outline_id: 大纲ID
        """
        pass
