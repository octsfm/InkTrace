"""
小说仓储接口模块

作者：孔利群
"""

# 文件路径：domain/repositories/novel_repository.py


from abc import ABC, abstractmethod
from typing import Optional, List

from domain.types import NovelId
from domain.entities.novel import Novel


class INovelRepository(ABC):
    """小说仓储接口"""

    @abstractmethod
    def save(self, novel: Novel) -> None:
        """
# 文件：模块：novel_repository

        保存小说
        
        Args:
            novel: 小说实体
        """
        pass

    @abstractmethod
    def find_by_id(self, novel_id: NovelId) -> Optional[Novel]:
        """
# 文件：模块：novel_repository

        根据ID查找小说
        
        Args:
            novel_id: 小说ID
            
        Returns:
            小说实体，不存在则返回None
        """
        pass

    @abstractmethod
    def find_all(self) -> List[Novel]:
        """
# 文件：模块：novel_repository

        查找所有小说
        
        Returns:
            小说列表
        """
        pass

    @abstractmethod
    def delete(self, novel_id: NovelId) -> None:
        """
# 文件：模块：novel_repository

        删除小说
        
        Args:
            novel_id: 小说ID
        """
        pass
