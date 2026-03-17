"""
世界观仓储接口

作者：孔利群
"""

# 文件路径：domain/repositories/worldview_repository.py


from abc import ABC, abstractmethod
from typing import Optional

from domain.entities.worldview import Worldview
from domain.entities.technique import Technique
from domain.entities.faction import Faction
from domain.entities.location import Location
from domain.entities.item import Item
from domain.types import WorldviewId, NovelId, TechniqueId, FactionId, LocationId, ItemId


class IWorldviewRepository(ABC):
    """世界观仓储接口"""
    
    @abstractmethod
    def find_by_id(self, worldview_id: WorldviewId) -> Optional[Worldview]:
        """根据ID查找世界观"""
# 文件：模块：worldview_repository

        pass
    
    @abstractmethod
    def find_by_novel_id(self, novel_id: NovelId) -> Optional[Worldview]:
        """根据小说ID查找世界观"""
        pass
    
    @abstractmethod
    def save(self, worldview: Worldview) -> None:
        """保存世界观"""
# 文件：模块：worldview_repository

        pass
    
    @abstractmethod
    def delete(self, worldview_id: WorldviewId) -> None:
        """删除世界观"""
        pass
    
    # 功法操作
    @abstractmethod
    def find_technique_by_id(self, technique_id: TechniqueId) -> Optional[Technique]:
        """根据ID查找功法"""
# 文件：模块：worldview_repository

        pass
    
    @abstractmethod
    def find_techniques_by_novel(self, novel_id: NovelId) -> list:
        """查找小说的所有功法"""
        pass
    
    @abstractmethod
    def save_technique(self, technique: Technique) -> None:
        """保存功法"""
# 文件：模块：worldview_repository

        pass
    
    @abstractmethod
    def delete_technique(self, technique_id: TechniqueId) -> None:
        """删除功法"""
        pass
    
    # 势力操作
    @abstractmethod
    def find_faction_by_id(self, faction_id: FactionId) -> Optional[Faction]:
        """根据ID查找势力"""
# 文件：模块：worldview_repository

        pass
    
    @abstractmethod
    def find_factions_by_novel(self, novel_id: NovelId) -> list:
        """查找小说的所有势力"""
        pass
    
    @abstractmethod
    def save_faction(self, faction: Faction) -> None:
        """保存势力"""
# 文件：模块：worldview_repository

        pass
    
    @abstractmethod
    def delete_faction(self, faction_id: FactionId) -> None:
        """删除势力"""
        pass
    
    # 地点操作
    @abstractmethod
    def find_location_by_id(self, location_id: LocationId) -> Optional[Location]:
        """根据ID查找地点"""
# 文件：模块：worldview_repository

        pass
    
    @abstractmethod
    def find_locations_by_novel(self, novel_id: NovelId) -> list:
        """查找小说的所有地点"""
        pass
    
    @abstractmethod
    def save_location(self, location: Location) -> None:
        """保存地点"""
# 文件：模块：worldview_repository

        pass
    
    @abstractmethod
    def delete_location(self, location_id: LocationId) -> None:
        """删除地点"""
        pass
    
    # 物品操作
    @abstractmethod
    def find_item_by_id(self, item_id: ItemId) -> Optional[Item]:
        """根据ID查找物品"""
# 文件：模块：worldview_repository

        pass
    
    @abstractmethod
    def find_items_by_novel(self, novel_id: NovelId) -> list:
        """查找小说的所有物品"""
        pass
    
    @abstractmethod
    def save_item(self, item: Item) -> None:
        """保存物品"""
# 文件：模块：worldview_repository

        pass
    
    @abstractmethod
    def delete_item(self, item_id: ItemId) -> None:
        """删除物品"""
        pass
