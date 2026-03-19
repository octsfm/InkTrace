"""
地点实体单元测试

作者：孔利群
"""

import pytest
from datetime import datetime

from domain.entities.location import Location
from domain.types import LocationId, NovelId, FactionId


class TestLocation:
    """地点实体测试"""
    
    def test_create_location(self):
        """测试创建地点"""
        location = Location(
            id=LocationId("loc_001"),
            novel_id=NovelId("novel_001"),
            name="青云山",
            description="青云门所在的山脉",
            importance=5
        )
        
        assert str(location.id) == "loc_001"
        assert str(location.novel_id) == "novel_001"
        assert location.name == "青云山"
        assert location.description == "青云门所在的山脉"
        assert location.importance == 5
        assert location.parent_id is None
        assert location.faction_id is None
        assert location.children == []
    
    def test_create_location_with_parent(self):
        """测试创建带父级的地点"""
        parent_id = LocationId("loc_parent")
        location = Location(
            id=LocationId("loc_001"),
            novel_id=NovelId("novel_001"),
            name="青云峰",
            parent_id=parent_id
        )
        
        assert str(location.parent_id) == "loc_parent"
    
    def test_create_location_with_faction(self):
        """测试创建带势力的地点"""
        faction_id = FactionId("faction_001")
        location = Location(
            id=LocationId("loc_001"),
            novel_id=NovelId("novel_001"),
            name="青云门",
            faction_id=faction_id
        )
        
        assert str(location.faction_id) == "faction_001"
    
    def test_set_parent(self):
        """测试设置父级地点"""
        location = Location(
            id=LocationId("loc_001"),
            novel_id=NovelId("novel_001"),
            name="青云峰"
        )
        
        parent_id = LocationId("loc_parent")
        location.set_parent(parent_id)
        
        assert str(location.parent_id) == "loc_parent"
    
    def test_set_faction(self):
        """测试设置势力"""
        location = Location(
            id=LocationId("loc_001"),
            novel_id=NovelId("novel_001"),
            name="青云门"
        )
        
        faction_id = FactionId("faction_001")
        location.set_faction(faction_id)
        
        assert str(location.faction_id) == "faction_001"
    
    def test_add_child(self):
        """测试添加子地点"""
        parent = Location(
            id=LocationId("loc_001"),
            novel_id=NovelId("novel_001"),
            name="青云山"
        )
        
        child_id = LocationId("loc_child")
        parent.add_child(child_id)
        
        assert len(parent.children) == 1
        assert str(parent.children[0]) == "loc_child"
    
    def test_add_child_no_duplicate(self):
        """测试添加子地点不会重复"""
        parent = Location(
            id=LocationId("loc_001"),
            novel_id=NovelId("novel_001"),
            name="青云山"
        )
        
        child_id = LocationId("loc_child")
        parent.add_child(child_id)
        parent.add_child(child_id)
        
        assert len(parent.children) == 1
    
    def test_remove_child(self):
        """测试移除子地点"""
        parent = Location(
            id=LocationId("loc_001"),
            novel_id=NovelId("novel_001"),
            name="青云山"
        )
        
        child_id = LocationId("loc_child")
        parent.add_child(child_id)
        parent.remove_child(child_id)
        
        assert len(parent.children) == 0
    
    def test_remove_child_not_found(self):
        """测试移除不存在的子地点"""
        parent = Location(
            id=LocationId("loc_001"),
            novel_id=NovelId("novel_001"),
            name="青云山"
        )
        
        # 不应该抛出异常
        parent.remove_child(LocationId("loc_nonexistent"))
        
        assert len(parent.children) == 0
    
    def test_set_importance(self):
        """测试设置重要性"""
        location = Location(
            id=LocationId("loc_001"),
            novel_id=NovelId("novel_001"),
            name="青云山"
        )
        
        location.set_importance(8)
        
        assert location.importance == 8
    
    def test_set_importance_negative(self):
        """测试设置负数重要性会变为0"""
        location = Location(
            id=LocationId("loc_001"),
            novel_id=NovelId("novel_001"),
            name="青云山"
        )
        
        location.set_importance(-5)
        
        assert location.importance == 0
    
    def test_set_importance_zero(self):
        """测试设置零重要性"""
        location = Location(
            id=LocationId("loc_001"),
            novel_id=NovelId("novel_001"),
            name="青云山",
            importance=5
        )
        
        location.set_importance(0)
        
        assert location.importance == 0
    
    def test_to_dict(self):
        """测试转换为字典"""
        location = Location(
            id=LocationId("loc_001"),
            novel_id=NovelId("novel_001"),
            name="青云山",
            description="青云门所在的山脉",
            importance=5
        )
        
        result = location.to_dict()
        
        assert result["id"] == "loc_001"
        assert result["novel_id"] == "novel_001"
        assert result["name"] == "青云山"
        assert result["description"] == "青云门所在的山脉"
        assert result["importance"] == 5
        assert result["parent_id"] is None
        assert result["faction_id"] is None
        assert result["children"] == []
        assert "created_at" in result
        assert "updated_at" in result
    
    def test_to_dict_with_relations(self):
        """测试带关系的地点转换为字典"""
        parent_id = LocationId("loc_parent")
        faction_id = FactionId("faction_001")
        child_id = LocationId("loc_child")
        
        location = Location(
            id=LocationId("loc_001"),
            novel_id=NovelId("novel_001"),
            name="青云峰",
            parent_id=parent_id,
            faction_id=faction_id
        )
        location.add_child(child_id)
        
        result = location.to_dict()
        
        assert result["parent_id"] == "loc_parent"
        assert result["faction_id"] == "faction_001"
        assert result["children"] == ["loc_child"]
    
    def test_from_dict(self):
        """测试从字典创建地点"""
        data = {
            "id": "loc_001",
            "novel_id": "novel_001",
            "name": "青云山",
            "description": "青云门所在的山脉",
            "parent_id": "loc_parent",
            "faction_id": "faction_001",
            "children": ["loc_child1", "loc_child2"],
            "importance": 7,
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-02T00:00:00"
        }
        
        location = Location.from_dict(data)
        
        assert str(location.id) == "loc_001"
        assert str(location.novel_id) == "novel_001"
        assert location.name == "青云山"
        assert location.description == "青云门所在的山脉"
        assert str(location.parent_id) == "loc_parent"
        assert str(location.faction_id) == "faction_001"
        assert len(location.children) == 2
        assert location.importance == 7
    
    def test_from_dict_minimal(self):
        """测试从最小字典创建地点"""
        data = {
            "id": "loc_001",
            "novel_id": "novel_001",
            "name": "青云山"
        }
        
        location = Location.from_dict(data)
        
        assert location.description == ""
        assert location.parent_id is None
        assert location.faction_id is None
        assert location.children == []
        assert location.importance == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
