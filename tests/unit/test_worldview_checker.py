"""
世界观一致性检查服务单元测试

作者：孔利群
"""

import pytest
from datetime import datetime

from domain.services.worldview_checker import WorldviewChecker, ConsistencyIssue
from domain.entities.worldview import Worldview, PowerSystem
from domain.entities.technique import Technique, TechniqueLevel
from domain.entities.faction import Faction, FactionRelation
from domain.entities.location import Location
from domain.entities.character import Character
from domain.types import (
    WorldviewId, NovelId, TechniqueId, FactionId, LocationId, CharacterId, ChapterId,
    CharacterRole
)


class TestConsistencyIssue:
    """一致性问题测试"""
    
    def test_create_consistency_issue(self):
        """测试创建一致性问题"""
        issue = ConsistencyIssue(
            issue_type="technique_level",
            severity="warning",
            description="功法等级不在力量体系中",
            location="功法: 青云剑诀",
            suggestion="请修改功法等级"
        )
        
        assert issue.issue_type == "technique_level"
        assert issue.severity == "warning"
        assert issue.description == "功法等级不在力量体系中"
        assert issue.location == "功法: 青云剑诀"
        assert issue.suggestion == "请修改功法等级"


class TestWorldviewChecker:
    """世界观一致性检查服务测试"""
    
    def setup_method(self):
        """测试前准备"""
        self.checker = WorldviewChecker()
    
    def test_check_worldview_empty(self):
        """测试检查空世界观"""
        worldview = Worldview(
            id=WorldviewId("wv_001"),
            novel_id=NovelId("novel_001")
        )
        
        issues = self.checker.check_worldview(worldview)
        
        assert issues == []
    
    def test_check_technique_levels_valid(self):
        """测试检查有效的功法等级"""
        worldview = Worldview(
            id=WorldviewId("wv_001"),
            novel_id=NovelId("novel_001"),
            power_system=PowerSystem(name="修为等级", levels=["练气", "筑基", "金丹"])
        )
        
        technique = Technique(
            id=TechniqueId("tech_001"),
            novel_id=NovelId("novel_001"),
            name="青云剑诀",
            level=TechniqueLevel(name="筑基", rank=2)
        )
        worldview.techniques.append(technique)
        
        issues = self.checker.check_worldview(worldview)
        
        # 应该没有功法等级问题
        technique_issues = [i for i in issues if i.issue_type == "technique_level"]
        assert len(technique_issues) == 0
    
    def test_check_technique_levels_invalid(self):
        """测试检查无效的功法等级"""
        worldview = Worldview(
            id=WorldviewId("wv_001"),
            novel_id=NovelId("novel_001"),
            power_system=PowerSystem(name="修为等级", levels=["练气", "筑基", "金丹"])
        )
        
        technique = Technique(
            id=TechniqueId("tech_001"),
            novel_id=NovelId("novel_001"),
            name="青云剑诀",
            level=TechniqueLevel(name="元婴", rank=4)  # 元婴不在等级列表中
        )
        worldview.techniques.append(technique)
        
        issues = self.checker.check_worldview(worldview)
        
        technique_issues = [i for i in issues if i.issue_type == "technique_level"]
        assert len(technique_issues) == 1
        assert "元婴" in technique_issues[0].description
    
    def test_check_faction_relations_valid(self):
        """测试检查有效的势力关系"""
        worldview = Worldview(
            id=WorldviewId("wv_001"),
            novel_id=NovelId("novel_001")
        )
        
        faction1 = Faction(
            id=FactionId("faction_001"),
            novel_id=NovelId("novel_001"),
            name="青云门"
        )
        faction2 = Faction(
            id=FactionId("faction_002"),
            novel_id=NovelId("novel_001"),
            name="天剑宗"
        )
        
        relation = FactionRelation(
            target_id=FactionId("faction_002"),
            relation_type="ally"
        )
        faction1.add_relation(relation)
        
        worldview.factions = [faction1, faction2]
        
        issues = self.checker.check_worldview(worldview)
        
        faction_issues = [i for i in issues if i.issue_type == "faction_relation"]
        assert len(faction_issues) == 0
    
    def test_check_faction_relations_invalid(self):
        """测试检查无效的势力关系"""
        worldview = Worldview(
            id=WorldviewId("wv_001"),
            novel_id=NovelId("novel_001")
        )
        
        faction1 = Faction(
            id=FactionId("faction_001"),
            novel_id=NovelId("novel_001"),
            name="青云门"
        )
        
        # 指向一个不存在的势力
        relation = FactionRelation(
            target_id=FactionId("faction_999"),
            relation_type="ally"
        )
        faction1.add_relation(relation)
        
        worldview.factions = [faction1]
        
        issues = self.checker.check_worldview(worldview)
        
        faction_issues = [i for i in issues if i.issue_type == "faction_relation"]
        assert len(faction_issues) == 1
        assert faction_issues[0].severity == "error"
    
    def test_check_location_hierarchy_valid(self):
        """测试检查有效的地点层级"""
        worldview = Worldview(
            id=WorldviewId("wv_001"),
            novel_id=NovelId("novel_001")
        )
        
        parent = Location(
            id=LocationId("loc_001"),
            novel_id=NovelId("novel_001"),
            name="青云山脉"
        )
        child = Location(
            id=LocationId("loc_002"),
            novel_id=NovelId("novel_001"),
            name="青云峰",
            parent_id=LocationId("loc_001")
        )
        
        worldview.locations = [parent, child]
        
        issues = self.checker.check_worldview(worldview)
        
        location_issues = [i for i in issues if i.issue_type == "location_hierarchy"]
        assert len(location_issues) == 0
    
    def test_check_location_hierarchy_invalid(self):
        """测试检查无效的地点层级"""
        worldview = Worldview(
            id=WorldviewId("wv_001"),
            novel_id=NovelId("novel_001")
        )
        
        # 子地点指向不存在的父地点
        location = Location(
            id=LocationId("loc_001"),
            novel_id=NovelId("novel_001"),
            name="青云峰",
            parent_id=LocationId("loc_999")
        )
        
        worldview.locations = [location]
        
        issues = self.checker.check_worldview(worldview)
        
        location_issues = [i for i in issues if i.issue_type == "location_hierarchy"]
        assert len(location_issues) == 1
        assert location_issues[0].severity == "warning"
    
    def test_check_character_consistency_valid(self):
        """测试检查有效的人物一致性"""
        worldview = Worldview(
            id=WorldviewId("wv_001"),
            novel_id=NovelId("novel_001")
        )
        
        technique = Technique(
            id=TechniqueId("tech_001"),
            novel_id=NovelId("novel_001"),
            name="青云剑诀"
        )
        faction = Faction(
            id=FactionId("faction_001"),
            novel_id=NovelId("novel_001"),
            name="青云门"
        )
        
        worldview.techniques = [technique]
        worldview.factions = [faction]
        
        character = Character(
            id=CharacterId("char_001"),
            novel_id=NovelId("novel_001"),
            name="张三",
            role=CharacterRole.PROTAGONIST,
            techniques=[TechniqueId("tech_001")],
            faction_id=FactionId("faction_001")
        )
        
        issues = self.checker.check_character_consistency(character, worldview)
        
        assert len(issues) == 0
    
    def test_check_character_consistency_invalid_technique(self):
        """测试检查人物功法不存在"""
        worldview = Worldview(
            id=WorldviewId("wv_001"),
            novel_id=NovelId("novel_001")
        )
        
        character = Character(
            id=CharacterId("char_001"),
            novel_id=NovelId("novel_001"),
            name="张三",
            role=CharacterRole.PROTAGONIST,
            techniques=[TechniqueId("tech_999")]  # 不存在的功法
        )
        
        issues = self.checker.check_character_consistency(character, worldview)
        
        technique_issues = [i for i in issues if i.issue_type == "character_technique"]
        assert len(technique_issues) == 1
    
    def test_check_character_consistency_invalid_faction(self):
        """测试检查人物势力不存在"""
        worldview = Worldview(
            id=WorldviewId("wv_001"),
            novel_id=NovelId("novel_001")
        )
        
        character = Character(
            id=CharacterId("char_001"),
            novel_id=NovelId("novel_001"),
            name="张三",
            role=CharacterRole.PROTAGONIST,
            faction_id=FactionId("faction_999")  # 不存在的势力
        )
        
        issues = self.checker.check_character_consistency(character, worldview)
        
        faction_issues = [i for i in issues if i.issue_type == "character_faction"]
        assert len(faction_issues) == 1
    
    def test_check_worldview_multiple_issues(self):
        """测试检查世界观多个问题"""
        worldview = Worldview(
            id=WorldviewId("wv_001"),
            novel_id=NovelId("novel_001"),
            power_system=PowerSystem(name="修为等级", levels=["练气", "筑基"])
        )
        
        # 无效功法等级
        technique = Technique(
            id=TechniqueId("tech_001"),
            novel_id=NovelId("novel_001"),
            name="青云剑诀",
            level=TechniqueLevel(name="金丹", rank=3)
        )
        worldview.techniques.append(technique)
        
        # 无效势力关系
        faction = Faction(
            id=FactionId("faction_001"),
            novel_id=NovelId("novel_001"),
            name="青云门"
        )
        faction.add_relation(FactionRelation(
            target_id=FactionId("faction_999"),
            relation_type="enemy"
        ))
        worldview.factions.append(faction)
        
        # 无效地点层级
        location = Location(
            id=LocationId("loc_001"),
            novel_id=NovelId("novel_001"),
            name="青云峰",
            parent_id=LocationId("loc_999")
        )
        worldview.locations.append(location)
        
        issues = self.checker.check_worldview(worldview)
        
        assert len(issues) >= 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
