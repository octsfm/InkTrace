"""
功法实体单元测试

作者：孔利群
"""

import pytest
from datetime import datetime

from domain.entities.technique import Technique, TechniqueLevel
from domain.types import TechniqueId, NovelId


class TestTechniqueLevel:
    """功法等级值对象测试"""
    
    def test_create_technique_level(self):
        """测试创建功法等级"""
        level = TechniqueLevel(name="天级", rank=3)
        
        assert level.name == "天级"
        assert level.rank == 3
    
    def test_technique_level_comparison(self):
        """测试功法等级比较"""
        level1 = TechniqueLevel(name="地级", rank=2)
        level2 = TechniqueLevel(name="天级", rank=3)
        level3 = TechniqueLevel(name="地级", rank=2)
        
        assert level1 < level2
        assert level2 > level1
        assert level1 <= level2
        assert level2 >= level1
        assert level1 <= level3
        assert level1 >= level3
    
    def test_technique_level_to_dict(self):
        """测试功法等级转换为字典"""
        level = TechniqueLevel(name="天级", rank=3)
        
        result = level.to_dict()
        
        assert result["name"] == "天级"
        assert result["rank"] == 3
    
    def test_technique_level_from_dict(self):
        """测试从字典创建功法等级"""
        data = {"name": "玄级", "rank": 1}
        
        level = TechniqueLevel.from_dict(data)
        
        assert level.name == "玄级"
        assert level.rank == 1


class TestTechnique:
    """功法实体测试"""
    
    def test_create_technique(self):
        """测试创建功法"""
        level = TechniqueLevel(name="天级", rank=3)
        technique = Technique(
            id=TechniqueId("tech_001"),
            novel_id=NovelId("novel_001"),
            name="青云剑诀",
            level=level,
            description="青云门镇派绝学",
            effect="剑气纵横，威力惊人",
            requirement="筑基期以上",
            creator="青云真人"
        )
        
        assert str(technique.id) == "tech_001"
        assert str(technique.novel_id) == "novel_001"
        assert technique.name == "青云剑诀"
        assert technique.level.name == "天级"
        assert technique.description == "青云门镇派绝学"
        assert technique.effect == "剑气纵横，威力惊人"
        assert technique.requirement == "筑基期以上"
        assert technique.creator == "青云真人"
    
    def test_create_technique_without_level(self):
        """测试创建没有等级的功法"""
        technique = Technique(
            id=TechniqueId("tech_001"),
            novel_id=NovelId("novel_001"),
            name="基础功法"
        )
        
        assert technique.level is None
        assert technique.description == ""
        assert technique.effect == ""
        assert technique.requirement == ""
        assert technique.creator == ""
    
    def test_update_level(self):
        """测试更新功法等级"""
        technique = Technique(
            id=TechniqueId("tech_001"),
            novel_id=NovelId("novel_001"),
            name="青云剑诀"
        )
        
        new_level = TechniqueLevel(name="天级", rank=3)
        technique.update_level(new_level)
        
        assert technique.level.name == "天级"
    
    def test_update_description(self):
        """测试更新功法描述"""
        technique = Technique(
            id=TechniqueId("tech_001"),
            novel_id=NovelId("novel_001"),
            name="青云剑诀"
        )
        
        technique.update_description("这是一门强大的剑法")
        
        assert technique.description == "这是一门强大的剑法"
    
    def test_update_effect(self):
        """测试更新功法效果"""
        technique = Technique(
            id=TechniqueId("tech_001"),
            novel_id=NovelId("novel_001"),
            name="青云剑诀"
        )
        
        technique.update_effect("可召唤青云剑气")
        
        assert technique.effect == "可召唤青云剑气"
    
    def test_update_requirement(self):
        """测试更新功法要求"""
        technique = Technique(
            id=TechniqueId("tech_001"),
            novel_id=NovelId("novel_001"),
            name="青云剑诀"
        )
        
        technique.update_requirement("需要金丹期修为")
        
        assert technique.requirement == "需要金丹期修为"
    
    def test_to_dict(self):
        """测试转换为字典"""
        level = TechniqueLevel(name="天级", rank=3)
        technique = Technique(
            id=TechniqueId("tech_001"),
            novel_id=NovelId("novel_001"),
            name="青云剑诀",
            level=level,
            description="青云门镇派绝学",
            effect="剑气纵横",
            requirement="筑基期以上",
            creator="青云真人"
        )
        
        result = technique.to_dict()
        
        assert result["id"] == "tech_001"
        assert result["novel_id"] == "novel_001"
        assert result["name"] == "青云剑诀"
        assert result["level"]["name"] == "天级"
        assert result["level"]["rank"] == 3
        assert result["description"] == "青云门镇派绝学"
        assert result["effect"] == "剑气纵横"
        assert result["requirement"] == "筑基期以上"
        assert result["creator"] == "青云真人"
        assert "created_at" in result
        assert "updated_at" in result
    
    def test_to_dict_without_level(self):
        """测试没有等级时转换为字典"""
        technique = Technique(
            id=TechniqueId("tech_001"),
            novel_id=NovelId("novel_001"),
            name="基础功法"
        )
        
        result = technique.to_dict()
        
        assert result["level"] is None
    
    def test_from_dict(self):
        """测试从字典创建功法"""
        data = {
            "id": "tech_001",
            "novel_id": "novel_001",
            "name": "青云剑诀",
            "level": {"name": "天级", "rank": 3},
            "description": "青云门镇派绝学",
            "effect": "剑气纵横",
            "requirement": "筑基期以上",
            "creator": "青云真人",
            "techniques": ["tech_002", "tech_003"],
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-02T00:00:00"
        }
        
        technique = Technique.from_dict(data)
        
        assert str(technique.id) == "tech_001"
        assert str(technique.novel_id) == "novel_001"
        assert technique.name == "青云剑诀"
        assert technique.level.name == "天级"
        assert technique.level.rank == 3
        assert technique.description == "青云门镇派绝学"
        assert len(technique.techniques) == 2
    
    def test_from_dict_without_level(self):
        """测试从字典创建没有等级的功法"""
        data = {
            "id": "tech_001",
            "novel_id": "novel_001",
            "name": "基础功法"
        }
        
        technique = Technique.from_dict(data)
        
        assert technique.level is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
