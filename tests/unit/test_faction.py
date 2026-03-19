"""
势力实体单元测试

作者：孔利群
"""

import pytest
from datetime import datetime

from domain.entities.faction import Faction, FactionRelation
from domain.types import FactionId, NovelId, LocationId


class TestFactionRelation:
    """势力关系值对象测试"""
    
    def test_create_faction_relation(self):
        """测试创建势力关系"""
        target_id = FactionId("faction_002")
        relation = FactionRelation(
            target_id=target_id,
            relation_type="ally",
            description="结盟关系"
        )
        
        assert str(relation.target_id) == "faction_002"
        assert relation.relation_type == "ally"
        assert relation.description == "结盟关系"
    
    def test_faction_relation_to_dict(self):
        """测试势力关系转换为字典"""
        relation = FactionRelation(
            target_id=FactionId("target_001"),
            relation_type="enemy",
            description="敌对势力"
        )
        
        result = relation.to_dict()
        
        assert result["target_id"] == "target_001"
        assert result["relation_type"] == "enemy"
        assert result["description"] == "敌对势力"
    
    def test_faction_relation_from_dict(self):
        """测试从字典创建势力关系"""
        data = {
            "target_id": "target_002",
            "relation_type": "neutral",
            "description": "中立关系"
        }
        
        relation = FactionRelation.from_dict(data)
        
        assert str(relation.target_id) == "target_002"
        assert relation.relation_type == "neutral"
        assert relation.description == "中立关系"
    
    def test_faction_relation_default_description(self):
        """测试势力关系默认描述"""
        relation = FactionRelation(
            target_id=FactionId("target_003"),
            relation_type="vassal"
        )
        
        assert relation.description == ""


class TestFaction:
    """势力实体测试"""
    
    def test_create_faction(self):
        """测试创建势力"""
        faction = Faction(
            id=FactionId("faction_001"),
            novel_id=NovelId("novel_001"),
            name="青云门",
            level="一流宗门",
            description="修仙界顶尖宗门",
            territory="青云山脉",
            leader="青云真人"
        )
        
        assert str(faction.id) == "faction_001"
        assert str(faction.novel_id) == "novel_001"
        assert faction.name == "青云门"
        assert faction.level == "一流宗门"
        assert faction.description == "修仙界顶尖宗门"
        assert faction.territory == "青云山脉"
        assert faction.leader == "青云真人"
        assert faction.relations == []
        assert faction.members_count == 0
    
    def test_add_relation(self):
        """测试添加势力关系"""
        faction = Faction(
            id=FactionId("faction_001"),
            novel_id=NovelId("novel_001"),
            name="青云门"
        )
        
        relation = FactionRelation(
            target_id=FactionId("faction_002"),
            relation_type="ally",
            description="结盟"
        )
        
        faction.add_relation(relation)
        
        assert len(faction.relations) == 1
        assert faction.relations[0].relation_type == "ally"
    
    def test_add_relation_replaces_existing(self):
        """测试添加关系会替换已存在的关系"""
        faction = Faction(
            id=FactionId("faction_001"),
            novel_id=NovelId("novel_001"),
            name="青云门"
        )
        
        relation1 = FactionRelation(
            target_id=FactionId("faction_002"),
            relation_type="ally",
            description="结盟"
        )
        relation2 = FactionRelation(
            target_id=FactionId("faction_002"),
            relation_type="enemy",
            description="敌对"
        )
        
        faction.add_relation(relation1)
        faction.add_relation(relation2)
        
        assert len(faction.relations) == 1
        assert faction.relations[0].relation_type == "enemy"
    
    def test_get_relation(self):
        """测试获取势力关系"""
        faction = Faction(
            id=FactionId("faction_001"),
            novel_id=NovelId("novel_001"),
            name="青云门"
        )
        
        relation = FactionRelation(
            target_id=FactionId("faction_002"),
            relation_type="ally"
        )
        faction.add_relation(relation)
        
        found = faction.get_relation(FactionId("faction_002"))
        assert found is not None
        assert found.relation_type == "ally"
    
    def test_get_relation_not_found(self):
        """测试获取不存在的势力关系"""
        faction = Faction(
            id=FactionId("faction_001"),
            novel_id=NovelId("novel_001"),
            name="青云门"
        )
        
        found = faction.get_relation(FactionId("faction_999"))
        assert found is None
    
    def test_remove_relation(self):
        """测试移除势力关系"""
        faction = Faction(
            id=FactionId("faction_001"),
            novel_id=NovelId("novel_001"),
            name="青云门"
        )
        
        relation = FactionRelation(
            target_id=FactionId("faction_002"),
            relation_type="ally"
        )
        faction.add_relation(relation)
        
        faction.remove_relation(FactionId("faction_002"))
        
        assert len(faction.relations) == 0
    
    def test_remove_relation_not_found(self):
        """测试移除不存在的势力关系"""
        faction = Faction(
            id=FactionId("faction_001"),
            novel_id=NovelId("novel_001"),
            name="青云门"
        )
        
        # 不应该抛出异常
        faction.remove_relation(FactionId("faction_999"))
        
        assert len(faction.relations) == 0
    
    def test_set_headquarters(self):
        """测试设置总部"""
        faction = Faction(
            id=FactionId("faction_001"),
            novel_id=NovelId("novel_001"),
            name="青云门"
        )
        
        location_id = LocationId("location_001")
        faction.set_headquarters(location_id)
        
        assert str(faction.headquarters) == "location_001"
    
    def test_to_dict(self):
        """测试转换为字典"""
        faction = Faction(
            id=FactionId("faction_001"),
            novel_id=NovelId("novel_001"),
            name="青云门",
            level="一流宗门",
            description="修仙界顶尖宗门",
            territory="青云山脉",
            leader="青云真人",
            members_count=1000
        )
        
        result = faction.to_dict()
        
        assert result["id"] == "faction_001"
        assert result["novel_id"] == "novel_001"
        assert result["name"] == "青云门"
        assert result["level"] == "一流宗门"
        assert result["description"] == "修仙界顶尖宗门"
        assert result["territory"] == "青云山脉"
        assert result["leader"] == "青云真人"
        assert result["members_count"] == 1000
        assert result["relations"] == []
        assert "created_at" in result
        assert "updated_at" in result
    
    def test_from_dict(self):
        """测试从字典创建势力"""
        data = {
            "id": "faction_001",
            "novel_id": "novel_001",
            "name": "青云门",
            "level": "一流宗门",
            "description": "修仙界顶尖宗门",
            "territory": "青云山脉",
            "leader": "青云真人",
            "headquarters": "location_001",
            "relations": [
                {"target_id": "faction_002", "relation_type": "ally", "description": "结盟"}
            ],
            "members_count": 500,
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-02T00:00:00"
        }
        
        faction = Faction.from_dict(data)
        
        assert str(faction.id) == "faction_001"
        assert str(faction.novel_id) == "novel_001"
        assert faction.name == "青云门"
        assert faction.level == "一流宗门"
        assert str(faction.headquarters) == "location_001"
        assert len(faction.relations) == 1
        assert faction.members_count == 500


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
