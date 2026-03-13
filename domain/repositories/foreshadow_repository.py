"""
伏笔仓储接口

作者：孔利群
"""

from abc import ABC, abstractmethod
from typing import Optional, List

from domain.entities.foreshadow import Foreshadow, ForeshadowStatus
from domain.types import ForeshadowId, NovelId, ChapterId


class IForeshadowRepository(ABC):
    """伏笔仓储接口"""
    
    @abstractmethod
    def find_by_id(self, foreshadow_id: ForeshadowId) -> Optional[Foreshadow]:
        """根据ID查找伏笔"""
        pass
    
    @abstractmethod
    def find_by_novel(self, novel_id: NovelId) -> List[Foreshadow]:
        """根据小说ID查找伏笔列表"""
        pass
    
    @abstractmethod
    def find_pending(self, novel_id: NovelId) -> List[Foreshadow]:
        """查找未回收的伏笔"""
        pass
    
    @abstractmethod
    def find_by_chapter(self, chapter_id: ChapterId) -> List[Foreshadow]:
        """根据章节ID查找伏笔"""
        pass
    
    @abstractmethod
    def save(self, foreshadow: Foreshadow) -> None:
        """保存伏笔"""
        pass
    
    @abstractmethod
    def delete(self, foreshadow_id: ForeshadowId) -> None:
        """删除伏笔"""
        pass
    
    @abstractmethod
    def resolve(self, foreshadow_id: ForeshadowId, chapter_id: ChapterId) -> None:
        """标记伏笔回收"""
        pass
    
    @abstractmethod
    def count(self, novel_id: NovelId) -> int:
        """统计伏笔数量"""
        pass
