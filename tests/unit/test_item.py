"""
物品实体单元测试

作者：孔利群
"""

import pytest
from datetime import datetime

from domain.entities.item import Item
from domain.types import ItemId, NovelId, ItemType


class TestItem:
    """物品实体测试"""
    
    def test_create_item(self):
        """测试创建物品"""
        item = Item(
            id=ItemId("item_001"),
            novel_id=NovelId("novel_001"),
            name="玄铁剑",
            item_type=ItemType.ARTIFACT,
            description="一把锋利的玄铁剑",
            effect="增加攻击力50%",
            rarity="稀有",
            owner="张三",
            origin="青云门"
        )
        
        assert str(item.id) == "item_001"
        assert str(item.novel_id) == "novel_001"
        assert item.name == "玄铁剑"
        assert item.item_type == ItemType.ARTIFACT
        assert item.description == "一把锋利的玄铁剑"
        assert item.effect == "增加攻击力50%"
        assert item.rarity == "稀有"
        assert item.owner == "张三"
        assert item.origin == "青云门"
    
    def test_create_item_default_type(self):
        """测试创建物品默认类型"""
        item = Item(
            id=ItemId("item_002"),
            novel_id=NovelId("novel_001"),
            name="普通物品"
        )
        
        assert item.item_type == ItemType.OTHER
        assert item.description == ""
        assert item.effect == ""
        assert item.rarity == ""
        assert item.owner == ""
    
    def test_update_type(self):
        """测试更新物品类型"""
        item = Item(
            id=ItemId("item_001"),
            novel_id=NovelId("novel_001"),
            name="丹药",
            item_type=ItemType.OTHER
        )
        
        item.update_type(ItemType.PILL)
        
        assert item.item_type == ItemType.PILL
    
    def test_update_description(self):
        """测试更新物品描述"""
        item = Item(
            id=ItemId("item_001"),
            novel_id=NovelId("novel_001"),
            name="玄铁剑"
        )
        
        item.update_description("这是一把传说中的神剑")
        
        assert item.description == "这是一把传说中的神剑"
    
    def test_update_effect(self):
        """测试更新物品效果"""
        item = Item(
            id=ItemId("item_001"),
            novel_id=NovelId("novel_001"),
            name="玄铁剑"
        )
        
        item.update_effect("提升修为速度一倍")
        
        assert item.effect == "提升修为速度一倍"
    
    def test_set_owner(self):
        """测试设置物品拥有者"""
        item = Item(
            id=ItemId("item_001"),
            novel_id=NovelId("novel_001"),
            name="玄铁剑"
        )
        
        item.set_owner("李四")
        
        assert item.owner == "李四"
    
    def test_to_dict(self):
        """测试转换为字典"""
        item = Item(
            id=ItemId("item_001"),
            novel_id=NovelId("novel_001"),
            name="玄铁剑",
            item_type=ItemType.ARTIFACT,
            description="一把锋利的玄铁剑",
            effect="增加攻击力50%",
            rarity="稀有",
            owner="张三",
            origin="青云门"
        )
        
        result = item.to_dict()
        
        assert result["id"] == "item_001"
        assert result["novel_id"] == "novel_001"
        assert result["name"] == "玄铁剑"
        assert result["item_type"] == "artifact"
        assert result["description"] == "一把锋利的玄铁剑"
        assert result["effect"] == "增加攻击力50%"
        assert result["rarity"] == "稀有"
        assert result["owner"] == "张三"
        assert result["origin"] == "青云门"
        assert "created_at" in result
        assert "updated_at" in result
    
    def test_from_dict(self):
        """测试从字典创建物品"""
        data = {
            "id": "item_001",
            "novel_id": "novel_001",
            "name": "筑基丹",
            "item_type": "pill",
            "description": "帮助突破筑基期",
            "effect": "增加筑基成功率",
            "rarity": "珍贵",
            "owner": "王五",
            "origin": "丹阁",
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-02T00:00:00"
        }
        
        item = Item.from_dict(data)
        
        assert str(item.id) == "item_001"
        assert str(item.novel_id) == "novel_001"
        assert item.name == "筑基丹"
        assert item.item_type == ItemType.PILL
        assert item.description == "帮助突破筑基期"
        assert item.effect == "增加筑基成功率"
        assert item.rarity == "珍贵"
        assert item.owner == "王五"
        assert item.origin == "丹阁"
    
    def test_from_dict_default_type(self):
        """测试从字典创建物品默认类型"""
        data = {
            "id": "item_002",
            "novel_id": "novel_001",
            "name": "未知物品"
        }
        
        item = Item.from_dict(data)
        
        assert item.item_type == ItemType.OTHER
    
    def test_item_type_enum_values(self):
        """测试物品类型枚举值"""
        assert ItemType.ARTIFACT.value == "artifact"
        assert ItemType.PILL.value == "pill"
        assert ItemType.MATERIAL.value == "material"
        assert ItemType.SCRIPTURE.value == "scripture"
        assert ItemType.OTHER.value == "other"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
