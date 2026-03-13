"""
世界观管理服务

作者：孔利群
"""

from typing import Optional, List
import uuid

from domain.entities.worldview import Worldview, PowerSystem
from domain.entities.technique import Technique, TechniqueLevel
from domain.entities.faction import Faction, FactionRelation
from domain.entities.location import Location
from domain.entities.item import Item
from domain.services.worldview_checker import WorldviewChecker, ConsistencyIssue
from domain.repositories.worldview_repository import IWorldviewRepository
from domain.types import (
    WorldviewId, NovelId, TechniqueId, FactionId, LocationId, ItemId, ItemType
)


class WorldviewService:
    """世界观管理服务"""
    
    def __init__(
        self,
        worldview_repo: IWorldviewRepository,
        worldview_checker: WorldviewChecker
    ):
        self.worldview_repo = worldview_repo
        self.worldview_checker = worldview_checker
    
    def get_or_create_worldview(self, novel_id: NovelId) -> Worldview:
        """获取或创建世界观"""
        worldview = self.worldview_repo.find_by_novel_id(novel_id)
        if not worldview:
            worldview = Worldview(
                id=WorldviewId(str(uuid.uuid4())),
                novel_id=novel_id
            )
            self.worldview_repo.save(worldview)
        return worldview
    
    def get_worldview(self, worldview_id: WorldviewId) -> Optional[Worldview]:
        """获取世界观"""
        return self.worldview_repo.find_by_id(worldview_id)
    
    def get_worldview_by_novel(self, novel_id: NovelId) -> Optional[Worldview]:
        """根据小说ID获取世界观"""
        return self.worldview_repo.find_by_novel_id(novel_id)
    
    def update_power_system(
        self,
        novel_id: NovelId,
        name: str,
        levels: List[str]
    ) -> Worldview:
        """更新力量体系"""
        worldview = self.get_or_create_worldview(novel_id)
        worldview.power_system = PowerSystem(name=name, levels=levels)
        self.worldview_repo.save(worldview)
        return worldview
    
    # 功法管理
    def create_technique(
        self,
        novel_id: NovelId,
        name: str,
        level_name: str = "",
        level_rank: int = 0,
        description: str = "",
        effect: str = "",
        requirement: str = ""
    ) -> Technique:
        """创建功法"""
        technique = Technique(
            id=TechniqueId(str(uuid.uuid4())),
            novel_id=novel_id,
            name=name,
            level=TechniqueLevel(name=level_name, rank=level_rank) if level_name else None,
            description=description,
            effect=effect,
            requirement=requirement
        )
        self.worldview_repo.save_technique(technique)
        return technique
    
    def get_technique(self, technique_id: TechniqueId) -> Optional[Technique]:
        """获取功法"""
        return self.worldview_repo.find_technique_by_id(technique_id)
    
    def list_techniques(self, novel_id: NovelId) -> List[Technique]:
        """获取功法列表"""
        return self.worldview_repo.find_techniques_by_novel(novel_id)
    
    def delete_technique(self, technique_id: TechniqueId) -> None:
        """删除功法"""
        self.worldview_repo.delete_technique(technique_id)
    
    # 势力管理
    def create_faction(
        self,
        novel_id: NovelId,
        name: str,
        level: str = "",
        description: str = "",
        territory: str = "",
        leader: str = ""
    ) -> Faction:
        """创建势力"""
        faction = Faction(
            id=FactionId(str(uuid.uuid4())),
            novel_id=novel_id,
            name=name,
            level=level,
            description=description,
            territory=territory,
            leader=leader
        )
        self.worldview_repo.save_faction(faction)
        return faction
    
    def get_faction(self, faction_id: FactionId) -> Optional[Faction]:
        """获取势力"""
        return self.worldview_repo.find_faction_by_id(faction_id)
    
    def list_factions(self, novel_id: NovelId) -> List[Faction]:
        """获取势力列表"""
        return self.worldview_repo.find_factions_by_novel(novel_id)
    
    def delete_faction(self, faction_id: FactionId) -> None:
        """删除势力"""
        self.worldview_repo.delete_faction(faction_id)
    
    # 地点管理
    def create_location(
        self,
        novel_id: NovelId,
        name: str,
        description: str = "",
        faction_id: Optional[FactionId] = None,
        parent_id: Optional[LocationId] = None
    ) -> Location:
        """创建地点"""
        location = Location(
            id=LocationId(str(uuid.uuid4())),
            novel_id=novel_id,
            name=name,
            description=description,
            faction_id=faction_id,
            parent_id=parent_id
        )
        self.worldview_repo.save_location(location)
        return location
    
    def get_location(self, location_id: LocationId) -> Optional[Location]:
        """获取地点"""
        return self.worldview_repo.find_location_by_id(location_id)
    
    def list_locations(self, novel_id: NovelId) -> List[Location]:
        """获取地点列表"""
        return self.worldview_repo.find_locations_by_novel(novel_id)
    
    def delete_location(self, location_id: LocationId) -> None:
        """删除地点"""
        self.worldview_repo.delete_location(location_id)
    
    # 物品管理
    def create_item(
        self,
        novel_id: NovelId,
        name: str,
        item_type: ItemType = ItemType.OTHER,
        description: str = "",
        effect: str = "",
        rarity: str = ""
    ) -> Item:
        """创建物品"""
        item = Item(
            id=ItemId(str(uuid.uuid4())),
            novel_id=novel_id,
            name=name,
            item_type=item_type,
            description=description,
            effect=effect,
            rarity=rarity
        )
        self.worldview_repo.save_item(item)
        return item
    
    def get_item(self, item_id: ItemId) -> Optional[Item]:
        """获取物品"""
        return self.worldview_repo.find_item_by_id(item_id)
    
    def list_items(self, novel_id: NovelId) -> List[Item]:
        """获取物品列表"""
        return self.worldview_repo.find_items_by_novel(novel_id)
    
    def delete_item(self, item_id: ItemId) -> None:
        """删除物品"""
        self.worldview_repo.delete_item(item_id)
    
    # 一致性检查
    def check_consistency(self, novel_id: NovelId) -> List[ConsistencyIssue]:
        """检查世界观一致性"""
        worldview = self.worldview_repo.find_by_novel_id(novel_id)
        if not worldview:
            return []
        return self.worldview_checker.check_worldview(worldview)
