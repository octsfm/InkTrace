"""
世界观实体与服务单元测试

作者：孔利群
"""

# 文件路径：tests/unit/test_worldview.py


import unittest
from datetime import datetime

from domain.entities.worldview import Worldview, PowerSystem
from domain.entities.technique import Technique, TechniqueLevel
from domain.entities.faction import Faction, FactionRelation
from domain.entities.location import Location
from domain.entities.item import Item
from domain.services.worldview_checker import WorldviewChecker, ConsistencyIssue
from domain.types import (
    WorldviewId, NovelId, TechniqueId, FactionId, LocationId, ItemId, ItemType
)


class TestTechniqueLevel(unittest.TestCase):
    """功法等级值对象测试"""
    
    def test_create_technique_level(self):
        """测试创建功法等级"""
# 文件：模块：test_worldview

        level = TechniqueLevel(name="天阶", rank=5)
        self.assertEqual(level.name, "天阶")
        self.assertEqual(level.rank, 5)
    
    def test_level_comparison(self):
        """测试等级比较"""
        level1 = TechniqueLevel(name="地阶", rank=4)
        level2 = TechniqueLevel(name="天阶", rank=5)
        
        self.assertTrue(level1 < level2)
        self.assertTrue(level2 > level1)
        self.assertTrue(level1 <= level2)
        self.assertTrue(level2 >= level1)


class TestTechnique(unittest.TestCase):
    """功法实体测试"""
    
    def setUp(self):
        self.technique_id = TechniqueId("tech_001")
        self.novel_id = NovelId("novel_001")
    
    def test_create_technique(self):
        """测试创建功法"""
        technique = Technique(
            id=self.technique_id,
            novel_id=self.novel_id,
            name="太乙真经",
            level=TechniqueLevel(name="天阶", rank=5),
            description="上古传承功法",
            effect="提升修为"
        )
        self.assertEqual(technique.name, "太乙真经")
        self.assertEqual(technique.level.name, "天阶")
    
    def test_technique_to_dict(self):
        """测试功法转字典"""
# 文件：模块：test_worldview

        technique = Technique(
            id=self.technique_id,
            novel_id=self.novel_id,
            name="测试功法",
            level=TechniqueLevel(name="玄阶", rank=3)
        )
        data = technique.to_dict()
        self.assertEqual(data["name"], "测试功法")
        self.assertEqual(data["level"]["name"], "玄阶")


class TestFaction(unittest.TestCase):
    """势力实体测试"""
    
    def setUp(self):
        self.faction_id = FactionId("faction_001")
        self.novel_id = NovelId("novel_001")
    
    def test_create_faction(self):
        """测试创建势力"""
# 文件：模块：test_worldview

        faction = Faction(
            id=self.faction_id,
            novel_id=self.novel_id,
            name="天剑宗",
            level="一流势力",
            description="剑道圣地",
            territory="东域",
            leader="剑圣"
        )
        self.assertEqual(faction.name, "天剑宗")
        self.assertEqual(faction.leader, "剑圣")
    
    def test_add_faction_relation(self):
        """测试添加势力关系"""
        faction = Faction(
            id=self.faction_id,
            novel_id=self.novel_id,
            name="测试势力"
        )
        relation = FactionRelation(
            target_id=FactionId("faction_002"),
            relation_type="ally",
            description="同盟"
        )
        faction.add_relation(relation)
        self.assertEqual(len(faction.relations), 1)


class TestLocation(unittest.TestCase):
    """地点实体测试"""
    
    def setUp(self):
        self.location_id = LocationId("loc_001")
        self.novel_id = NovelId("novel_001")
    
    def test_create_location(self):
        """测试创建地点"""
        location = Location(
            id=self.location_id,
            novel_id=self.novel_id,
            name="青云山",
            description="灵气充沛的仙山",
            importance=5
        )
        self.assertEqual(location.name, "青云山")
        self.assertEqual(location.importance, 5)
    
    def test_location_hierarchy(self):
        """测试地点层级"""
# 文件：模块：test_worldview

        parent = Location(
            id=self.location_id,
            novel_id=self.novel_id,
            name="东域"
        )
        child = Location(
            id=LocationId("loc_002"),
            novel_id=self.novel_id,
            name="青云山",
            parent_id=self.location_id
        )
        self.assertEqual(str(child.parent_id), "loc_001")


class TestItem(unittest.TestCase):
    """物品实体测试"""
    
    def setUp(self):
        self.item_id = ItemId("item_001")
        self.novel_id = NovelId("novel_001")
    
    def test_create_item(self):
        """测试创建物品"""
# 文件：模块：test_worldview

        item = Item(
            id=self.item_id,
            novel_id=self.novel_id,
            name="诛仙剑",
            item_type=ItemType.ARTIFACT,
            description="上古神剑",
            effect="斩妖除魔",
            rarity="神器"
        )
        self.assertEqual(item.name, "诛仙剑")
        self.assertEqual(item.item_type, ItemType.ARTIFACT)
        self.assertEqual(item.rarity, "神器")


class TestPowerSystem(unittest.TestCase):
    """力量体系值对象测试"""
    
    def test_create_power_system(self):
        """测试创建力量体系"""
# 文件：模块：test_worldview

        power = PowerSystem(
            name="修炼境界",
            levels=["练气", "筑基", "金丹", "元婴"],
            description="修仙者的境界划分"
        )
        self.assertEqual(power.name, "修炼境界")
        self.assertEqual(len(power.levels), 4)
    
    def test_power_system_to_dict(self):
        """测试力量体系转字典"""
        power = PowerSystem(name="测试体系", levels=["一级", "二级"])
        data = power.to_dict()
        self.assertEqual(data["name"], "测试体系")
        self.assertEqual(len(data["levels"]), 2)


class TestWorldview(unittest.TestCase):
    """世界观聚合根测试"""
    
    def setUp(self):
        self.worldview_id = WorldviewId("wv_001")
        self.novel_id = NovelId("novel_001")
        self.worldview = Worldview(
            id=self.worldview_id,
            novel_id=self.novel_id,
            name="修仙世界"
        )
    
    def test_create_worldview(self):
        """测试创建世界观"""
        self.assertEqual(self.worldview.name, "修仙世界")
        self.assertEqual(len(self.worldview.techniques), 0)
        self.assertEqual(len(self.worldview.factions), 0)
    
    def test_add_technique(self):
        """测试添加功法"""
# 文件：模块：test_worldview

        technique = Technique(
            id=TechniqueId("tech_001"),
            novel_id=self.novel_id,
            name="测试功法"
        )
        self.worldview.add_technique(technique)
        self.assertEqual(len(self.worldview.techniques), 1)
    
    def test_remove_technique(self):
        """测试移除功法"""
        technique = Technique(
            id=TechniqueId("tech_001"),
            novel_id=self.novel_id,
            name="测试功法"
        )
        self.worldview.add_technique(technique)
        self.worldview.remove_technique("tech_001")
        self.assertEqual(len(self.worldview.techniques), 0)
    
    def test_set_power_system(self):
        """测试设置力量体系"""
# 文件：模块：test_worldview

        power = PowerSystem(
            name="修炼境界",
            levels=["练气", "筑基", "金丹"]
        )
        self.worldview.set_power_system(power)
        self.assertEqual(self.worldview.power_system.name, "修炼境界")
        self.assertEqual(len(self.worldview.power_system.levels), 3)


class TestWorldviewChecker(unittest.TestCase):
    """世界观一致性检查服务测试"""
    
    def setUp(self):
        self.checker = WorldviewChecker()
        self.novel_id = NovelId("novel_001")
        self.worldview = Worldview(
            id=WorldviewId("wv_001"),
            novel_id=self.novel_id
        )
    
    def test_check_technique_level_consistency(self):
        """测试功法等级一致性检查"""
# 文件：模块：test_worldview

        self.worldview.power_system = PowerSystem(
            name="修炼境界",
            levels=["练气", "筑基", "金丹"]
        )
        
        technique = Technique(
            id=TechniqueId("tech_001"),
            novel_id=self.novel_id,
            name="测试功法",
            level=TechniqueLevel(name="元婴", rank=4)
        )
        self.worldview.add_technique(technique)
        
        issues = self.checker.check_worldview(self.worldview)
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0].issue_type, "technique_level")
    
    def test_check_faction_relation_consistency(self):
        """测试势力关系一致性检查"""
        faction = Faction(
            id=FactionId("faction_001"),
            novel_id=self.novel_id,
            name="测试势力"
        )
        relation = FactionRelation(
            target_id=FactionId("faction_999"),
            relation_type="ally"
        )
        faction.add_relation(relation)
        self.worldview.add_faction(faction)
        
        issues = self.checker.check_worldview(self.worldview)
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0].issue_type, "faction_relation")
    
    def test_check_no_issues(self):
        """测试无一致性问题时"""
# 文件：模块：test_worldview

        self.worldview.power_system = PowerSystem(
            name="修炼境界",
            levels=["练气", "筑基", "金丹"]
        )
        
        technique = Technique(
            id=TechniqueId("tech_001"),
            novel_id=self.novel_id,
            name="测试功法",
            level=TechniqueLevel(name="金丹", rank=3)
        )
        self.worldview.add_technique(technique)
        
        issues = self.checker.check_worldview(self.worldview)
        self.assertEqual(len(issues), 0)


if __name__ == "__main__":
    unittest.main()
