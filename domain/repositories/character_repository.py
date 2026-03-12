"""
人物仓储接口模块

作者：孔利群
"""

from abc import ABC, abstractmethod
from typing import Optional, List

from domain.types import CharacterId, NovelId
from domain.entities.character import Character


class ICharacterRepository(ABC):
    """人物仓储接口"""

    @abstractmethod
    def save(self, character: Character) -> None:
        """
        保存人物
        
        Args:
            character: 人物实体
        """
        pass

    @abstractmethod
    def find_by_id(self, character_id: CharacterId) -> Optional[Character]:
        """
        根据ID查找人物
        
        Args:
            character_id: 人物ID
            
        Returns:
            人物实体，不存在则返回None
        """
        pass

    @abstractmethod
    def find_by_novel(self, novel_id: NovelId) -> List[Character]:
        """
        查找小说的所有人物
        
        Args:
            novel_id: 小说ID
            
        Returns:
            人物列表
        """
        pass

    @abstractmethod
    def delete(self, character_id: CharacterId) -> None:
        """
        删除人物
        
        Args:
            character_id: 人物ID
        """
        pass
