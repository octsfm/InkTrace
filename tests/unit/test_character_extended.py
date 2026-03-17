"""
人物实体扩展单元测试

作者：孔利群
"""

# 文件路径：tests/unit/test_character_extended.py


import unittest
from datetime import datetime

from domain.entities.character import Character, CharacterRelation, CharacterRelationship
from domain.types import CharacterId, NovelId, CharacterRole, RelationType, ChapterId, TechniqueId, FactionId


class TestCharacterRelation(unittest.TestCase):
    """人物关系值对象测试"""
    
    def test_create_character_relation(self):
        """测试创建人物关系"""
# 文件：模块：test_character_extended

        target_id = CharacterId("char_002")
        relation = CharacterRelation(
            target_id=target_id,
            relation_type=RelationType.FRIEND,
            description="生死之交"
        )
        self.assertEqual(str(relation.target_id), "char_002")
        self.assertEqual(relation.relation_type, RelationType.FRIEND)
        self.assertEqual(relation.description, "生死之交")
    
    def test_relation_to_dict(self):
        """测试关系转字典"""
        relation = CharacterRelation(
            target_id=CharacterId("char_003"),
            relation_type=RelationType.ENEMY,
            description="宿敌"
        )
        data = relation.to_dict()
        self.assertEqual(data["target_id"], "char_003")
        self.assertEqual(data["relation_type"], "enemy")
    
    def test_relation_from_dict(self):
        """测试从字典创建关系"""
# 文件：模块：test_character_extended

        data = {
            "target_id": "char_004",
            "relation_type": "master_disciple",
            "description": "师徒关系",
            "start_chapter": "chapter_001"
        }
        relation = CharacterRelation.from_dict(data)
        self.assertEqual(str(relation.target_id), "char_004")
        self.assertEqual(relation.relation_type, RelationType.MASTER_DISCIPLE)


class TestCharacterExtended(unittest.TestCase):
    """人物实体扩展测试"""
    
    def setUp(self):
        """测试前置"""
# 文件：模块：test_character_extended

        self.character_id = CharacterId("char_001")
        self.novel_id = NovelId("novel_001")
        self.character = Character(
            id=self.character_id,
            novel_id=self.novel_id,
            name="林轩",
            role=CharacterRole.PROTAGONIST
        )
    
    def test_create_character_with_defaults(self):
        """测试创建带默认值的人物"""
        self.assertEqual(self.character.name, "林轩")
        self.assertEqual(self.character.role, CharacterRole.PROTAGONIST)
        self.assertEqual(self.character.background, "")
        self.assertEqual(self.character.personality, "")
        self.assertEqual(self.character.appearance, "")
    
    def test_create_character_with_extended_fields(self):
        """测试创建带扩展字段的人物"""
# 文件：模块：test_character_extended

        character = Character(
            id=self.character_id,
            novel_id=self.novel_id,
            name="苏婉",
            role=CharacterRole.SUPPORTING,
            appearance="容貌绝美，气质出尘",
            personality="温柔善良，聪慧过人",
            background="出身名门，自幼习武",
            age=18,
            gender="女",
            title="仙子"
        )
        self.assertEqual(character.appearance, "容貌绝美，气质出尘")
        self.assertEqual(character.personality, "温柔善良，聪慧过人")
        self.assertEqual(character.age, 18)
        self.assertEqual(character.gender, "女")
        self.assertEqual(character.title, "仙子")
    
    def test_add_technique(self):
        """测试添加功法"""
        tech_id = TechniqueId("tech_001")
        self.character.add_technique(tech_id)
        self.assertEqual(len(self.character.techniques), 1)
        self.assertIn(tech_id, self.character.techniques)
    
    def test_remove_technique(self):
        """测试移除功法"""
# 文件：模块：test_character_extended

        tech_id = TechniqueId("tech_001")
        self.character.add_technique(tech_id)
        self.character.remove_technique(tech_id)
        self.assertEqual(len(self.character.techniques), 0)
    
    def test_set_faction(self):
        """测试设置势力"""
        faction_id = FactionId("faction_001")
        self.character.set_faction(faction_id)
        self.assertEqual(str(self.character.faction_id), "faction_001")
    
    def test_add_detailed_relation(self):
        """测试添加详细关系"""
# 文件：模块：test_character_extended

        relation = CharacterRelation(
            target_id=CharacterId("char_002"),
            relation_type=RelationType.LOVER,
            description="青梅竹马"
        )
        self.character.add_detailed_relation(relation)
        self.assertEqual(len(self.character.detailed_relations), 1)
    
    def test_get_detailed_relation(self):
        """测试获取详细关系"""
        target_id = CharacterId("char_002")
        relation = CharacterRelation(
            target_id=target_id,
            relation_type=RelationType.FRIEND
        )
        self.character.add_detailed_relation(relation)
        
        found = self.character.get_detailed_relation(target_id)
        self.assertIsNotNone(found)
        self.assertEqual(found.relation_type, RelationType.FRIEND)
    
    def test_remove_detailed_relation(self):
        """测试移除详细关系"""
# 文件：模块：test_character_extended

        target_id = CharacterId("char_002")
        relation = CharacterRelation(
            target_id=target_id,
            relation_type=RelationType.ENEMY
        )
        self.character.add_detailed_relation(relation)
        self.character.remove_detailed_relation(target_id)
        self.assertEqual(len(self.character.detailed_relations), 0)
    
    def test_update_state_with_history(self):
        """测试更新状态并记录历史"""
        self.character.update_state("筑基期")
        self.assertEqual(self.character.current_state, "筑基期")
        
        self.character.update_state("金丹期")
        self.assertEqual(self.character.current_state, "金丹期")
        self.assertEqual(len(self.character.state_history), 1)
        self.assertEqual(self.character.state_history[0], "筑基期")
    
    def test_character_to_dict(self):
        """测试人物转字典"""
# 文件：模块：test_character_extended

        self.character.appearance = "英俊潇洒"
        self.character.age = 25
        data = self.character.to_dict()
        
        self.assertEqual(data["id"], "char_001")
        self.assertEqual(data["name"], "林轩")
        self.assertEqual(data["appearance"], "英俊潇洒")
        self.assertEqual(data["age"], 25)
        self.assertIn("techniques", data)
        self.assertIn("detailed_relations", data)
    
    def test_character_from_dict(self):
        """测试从字典创建人物"""
        data = {
            "id": "char_005",
            "novel_id": "novel_001",
            "name": "测试人物",
            "role": "supporting",
            "background": "测试背景",
            "personality": "测试性格",
            "appearance": "测试外貌",
            "age": 30,
            "gender": "男",
            "title": "测试称号",
            "abilities": ["能力1", "能力2"],
            "techniques": ["tech_001"],
            "faction_id": "faction_001",
            "detailed_relations": [
                {"target_id": "char_006", "relation_type": "friend", "description": "朋友"}
            ],
            "state_history": ["状态1", "状态2"],
            "created_at": "2026-01-01T00:00:00",
            "updated_at": "2026-01-01T00:00:00"
        }
        character = Character.from_dict(data)
        
        self.assertEqual(character.name, "测试人物")
        self.assertEqual(character.age, 30)
        self.assertEqual(len(character.abilities), 2)
        self.assertEqual(len(character.techniques), 1)
        self.assertEqual(len(character.detailed_relations), 1)
        self.assertEqual(len(character.state_history), 2)


if __name__ == "__main__":
    unittest.main()
