"""
世界观API路由

作者：孔利群
"""

# 文件路径：presentation/api/routers/worldview.py


from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from application.services.worldview_service import WorldviewService
from domain.entities.worldview import Worldview, PowerSystem
from domain.entities.technique import Technique
from domain.entities.faction import Faction
from domain.entities.location import Location
from domain.entities.item import Item
from domain.types import (
    WorldviewId, NovelId, TechniqueId, FactionId, LocationId, ItemId, ItemType
)


router = APIRouter(prefix="/api/novels/{novel_id}/worldview", tags=["worldview"])


class UpdatePowerSystemRequest(BaseModel):
    name: str
    levels: List[str]


class CreateTechniqueRequest(BaseModel):
    name: str
    level_name: str = ""
    level_rank: int = 0
    description: str = ""
    effect: str = ""
    requirement: str = ""


class CreateFactionRequest(BaseModel):
    name: str
    level: str = ""
    description: str = ""
    territory: str = ""
    leader: str = ""


class CreateLocationRequest(BaseModel):
    name: str
    description: str = ""
    faction_id: Optional[str] = None
    parent_id: Optional[str] = None


class CreateItemRequest(BaseModel):
    name: str
    item_type: str = "other"
    description: str = ""
    effect: str = ""
    rarity: str = ""


class TechniqueResponse(BaseModel):
    id: str
    name: str
    level: Optional[dict]
    description: str
    effect: str


class FactionResponse(BaseModel):
    id: str
    name: str
    level: str
    description: str
    territory: str
    leader: str


class LocationResponse(BaseModel):
    id: str
    name: str
    description: str
    faction_id: Optional[str]
    parent_id: Optional[str]


class ItemResponse(BaseModel):
    id: str
    name: str
    item_type: str
    description: str
    effect: str
    rarity: str


class WorldviewResponse(BaseModel):
    id: str
    novel_id: str
    name: str
    power_system: Optional[dict]


class ConsistencyIssueResponse(BaseModel):
    issue_type: str
    severity: str
    description: str
    location: str
    suggestion: str


def get_worldview_service() -> WorldviewService:
    from presentation.api.dependencies import get_worldview_service
    return get_worldview_service()


@router.get("", response_model=WorldviewResponse)
def get_worldview(novel_id: str, service: WorldviewService = Depends(get_worldview_service)):
    """获取世界观"""
    worldview = service.get_or_create_worldview(NovelId(novel_id))
    return _worldview_to_response(worldview)


@router.put("/power-system")
def update_power_system(
    novel_id: str,
    request: UpdatePowerSystemRequest,
    service: WorldviewService = Depends(get_worldview_service)
):
    """更新力量体系"""
# 文件：模块：worldview

    worldview = service.update_power_system(
        NovelId(novel_id),
        request.name,
        request.levels
    )
    return {"message": "力量体系已更新", "levels": worldview.power_system.levels}


@router.post("/check", response_model=List[ConsistencyIssueResponse])
def check_consistency(
    novel_id: str,
    service: WorldviewService = Depends(get_worldview_service)
):
    """检查世界观一致性"""
    issues = service.check_consistency(NovelId(novel_id))
    return [
        ConsistencyIssueResponse(
            issue_type=i.issue_type,
            severity=i.severity,
            description=i.description,
            location=i.location,
            suggestion=i.suggestion
        ) for i in issues
    ]


# 功法接口
@router.post("/techniques", response_model=TechniqueResponse)
def create_technique(
    novel_id: str,
    request: CreateTechniqueRequest,
    service: WorldviewService = Depends(get_worldview_service)
):
    """创建功法"""
# 文件：模块：worldview

    technique = service.create_technique(
        NovelId(novel_id),
        request.name,
        request.level_name,
        request.level_rank,
        request.description,
        request.effect,
        request.requirement
    )
    return _technique_to_response(technique)


@router.get("/techniques", response_model=List[TechniqueResponse])
def list_techniques(novel_id: str, service: WorldviewService = Depends(get_worldview_service)):
    """获取功法列表"""
    techniques = service.list_techniques(NovelId(novel_id))
    return [_technique_to_response(t) for t in techniques]


@router.delete("/techniques/{technique_id}")
def delete_technique(
    novel_id: str,
    technique_id: str,
    service: WorldviewService = Depends(get_worldview_service)
):
    """删除功法"""
# 文件：模块：worldview

    service.delete_technique(TechniqueId(technique_id))
    return {"message": "功法已删除"}


# 势力接口
@router.post("/factions", response_model=FactionResponse)
def create_faction(
    novel_id: str,
    request: CreateFactionRequest,
    service: WorldviewService = Depends(get_worldview_service)
):
    """创建势力"""
    faction = service.create_faction(
        NovelId(novel_id),
        request.name,
        request.level,
        request.description,
        request.territory,
        request.leader
    )
    return _faction_to_response(faction)


@router.get("/factions", response_model=List[FactionResponse])
def list_factions(novel_id: str, service: WorldviewService = Depends(get_worldview_service)):
    """获取势力列表"""
# 文件：模块：worldview

    factions = service.list_factions(NovelId(novel_id))
    return [_faction_to_response(f) for f in factions]


@router.delete("/factions/{faction_id}")
def delete_faction(
    novel_id: str,
    faction_id: str,
    service: WorldviewService = Depends(get_worldview_service)
):
    """删除势力"""
    service.delete_faction(FactionId(faction_id))
    return {"message": "势力已删除"}


# 地点接口
@router.post("/locations", response_model=LocationResponse)
def create_location(
    novel_id: str,
    request: CreateLocationRequest,
    service: WorldviewService = Depends(get_worldview_service)
):
    """创建地点"""
# 文件：模块：worldview

    location = service.create_location(
        NovelId(novel_id),
        request.name,
        request.description,
        FactionId(request.faction_id) if request.faction_id else None,
        LocationId(request.parent_id) if request.parent_id else None
    )
    return _location_to_response(location)


@router.get("/locations", response_model=List[LocationResponse])
def list_locations(novel_id: str, service: WorldviewService = Depends(get_worldview_service)):
    """获取地点列表"""
    locations = service.list_locations(NovelId(novel_id))
    return [_location_to_response(l) for l in locations]


@router.delete("/locations/{location_id}")
def delete_location(
    novel_id: str,
    location_id: str,
    service: WorldviewService = Depends(get_worldview_service)
):
    """删除地点"""
# 文件：模块：worldview

    service.delete_location(LocationId(location_id))
    return {"message": "地点已删除"}


# 物品接口
@router.post("/items", response_model=ItemResponse)
def create_item(
    novel_id: str,
    request: CreateItemRequest,
    service: WorldviewService = Depends(get_worldview_service)
):
    """创建物品"""
    try:
        item_type = ItemType(request.item_type)
    except ValueError:
        item_type = ItemType.OTHER
    
    item = service.create_item(
        NovelId(novel_id),
        request.name,
        item_type,
        request.description,
        request.effect,
        request.rarity
    )
    return _item_to_response(item)


@router.get("/items", response_model=List[ItemResponse])
def list_items(novel_id: str, service: WorldviewService = Depends(get_worldview_service)):
    """获取物品列表"""
# 文件：模块：worldview

    items = service.list_items(NovelId(novel_id))
    return [_item_to_response(i) for i in items]


@router.delete("/items/{item_id}")
def delete_item(
    novel_id: str,
    item_id: str,
    service: WorldviewService = Depends(get_worldview_service)
):
    """删除物品"""
    service.delete_item(ItemId(item_id))
    return {"message": "物品已删除"}


def _worldview_to_response(worldview: Worldview) -> WorldviewResponse:
    return WorldviewResponse(
        id=str(worldview.id),
        novel_id=str(worldview.novel_id),
        name=worldview.name,
        power_system=worldview.power_system.to_dict() if worldview.power_system else None
    )


def _technique_to_response(technique: Technique) -> TechniqueResponse:
    return TechniqueResponse(
        id=str(technique.id),
        name=technique.name,
        level=technique.level.to_dict() if technique.level else None,
        description=technique.description,
        effect=technique.effect
    )


def _faction_to_response(faction: Faction) -> FactionResponse:
    return FactionResponse(
        id=str(faction.id),
        name=faction.name,
        level=faction.level,
        description=faction.description,
        territory=faction.territory,
        leader=faction.leader
    )


def _location_to_response(location: Location) -> LocationResponse:
    return LocationResponse(
        id=str(location.id),
        name=location.name,
        description=location.description,
        faction_id=str(location.faction_id) if location.faction_id else None,
        parent_id=str(location.parent_id) if location.parent_id else None
    )


def _item_to_response(item: Item) -> ItemResponse:
    return ItemResponse(
        id=str(item.id),
        name=item.name,
        item_type=item.item_type.value,
        description=item.description,
        effect=item.effect,
        rarity=item.rarity
    )
