"""
Character实体单元测试

作者：孔利群
"""

import unittest
from datetime import datetime

from domain.entities.character import Character, CharacterRelationship
from domain.types import CharacterId, NovelId, ChapterId, CharacterRole
from domain.exceptions import InvalidOperationError


class TestCharacter(unittest.TestCase):
    """测试Character实体"""

    def setUp(self):
        """测试前置设置"""
        self.character_id = CharacterId("char-001")
        self.novel_id = NovelId("novel-001")
        self.now = datetime.now()

    def test_create_character(self):
        """测试创建人物"""
        character = Character(
            id=self.character_id,
            novel_id=self.novel_id,
            name="孔凡圣",
            role=CharacterRole.PROTAGONIST,
            background="蓝星龙国东北春泽市的一名普通的中年人",
            personality="坚韧不拔，越挫越勇",
            created_at=self.now,
            updated_at=self.now
        )
        self.assertEqual(character.id, self.character_id)
        self.assertEqual(character.novel_id, self.novel_id)
        self.assertEqual(character.name, "孔凡圣")
        self.assertEqual(character.role, CharacterRole.PROTAGONIST)

    def test_add_alias(self):
        """测试添加别名"""
        character = Character(
            id=self.character_id,
            novel_id=self.novel_id,
            name="孔凡圣",
            role=CharacterRole.PROTAGONIST,
            background="",
            personality="",
            created_at=self.now,
            updated_at=self.now
        )
        character.add_alias("凡圣", self.now)
        self.assertIn("凡圣", character.aliases)

    def test_add_duplicate_alias(self):
        """测试添加重复别名"""
        character = Character(
            id=self.character_id,
            novel_id=self.novel_id,
            name="孔凡圣",
            role=CharacterRole.PROTAGONIST,
            background="",
            personality="",
            aliases=["凡圣"],
            created_at=self.now,
            updated_at=self.now
        )
        character.add_alias("凡圣", self.now)
        self.assertEqual(character.aliases.count("凡圣"), 1)

    def test_add_ability(self):
        """测试添加能力"""
        character = Character(
            id=self.character_id,
            novel_id=self.novel_id,
            name="孔凡圣",
            role=CharacterRole.PROTAGONIST,
            background="",
            personality="",
            created_at=self.now,
            updated_at=self.now
        )
        character.add_ability("菩提大法", self.now)
        self.assertIn("菩提大法", character.abilities)

    def test_add_relationship(self):
        """测试添加人物关系"""
        character = Character(
            id=self.character_id,
            novel_id=self.novel_id,
            name="孔凡圣",
            role=CharacterRole.PROTAGONIST,
            background="",
            personality="",
            created_at=self.now,
            updated_at=self.now
        )
        other_id = CharacterId("char-002")
        relationship = CharacterRelationship(
            target_id=other_id,
            relation_type="师徒",
            description="菩提老祖是孔凡圣的师父"
        )
        character.add_relationship(relationship, self.now)
        self.assertEqual(len(character.relationships), 1)

    def test_get_relationship(self):
        """测试获取人物关系"""
        character = Character(
            id=self.character_id,
            novel_id=self.novel_id,
            name="孔凡圣",
            role=CharacterRole.PROTAGONIST,
            background="",
            personality="",
            created_at=self.now,
            updated_at=self.now
        )
        other_id = CharacterId("char-002")
        relationship = CharacterRelationship(
            target_id=other_id,
            relation_type="师徒",
            description="菩提老祖是孔凡圣的师父"
        )
        character.add_relationship(relationship, self.now)
        found = character.get_relationship(other_id)
        self.assertIsNotNone(found)
        self.assertEqual(found.relation_type, "师徒")

    def test_update_state(self):
        """测试更新状态"""
        character = Character(
            id=self.character_id,
            novel_id=self.novel_id,
            name="孔凡圣",
            role=CharacterRole.PROTAGONIST,
            background="",
            personality="",
            current_state="凡人",
            created_at=self.now,
            updated_at=self.now
        )
        character.update_state("筑基期", self.now)
        self.assertEqual(character.current_state, "筑基期")

    def test_increment_appearance(self):
        """测试增加出场次数"""
        character = Character(
            id=self.character_id,
            novel_id=self.novel_id,
            name="孔凡圣",
            role=CharacterRole.PROTAGONIST,
            background="",
            personality="",
            appearance_count=0,
            created_at=self.now,
            updated_at=self.now
        )
        chapter_id = ChapterId("chapter-001")
        character.increment_appearance(chapter_id, self.now)
        self.assertEqual(character.appearance_count, 1)
        self.assertEqual(character.first_appearance, chapter_id)

    def test_increment_appearance_keeps_first(self):
        """测试增加出场次数保持首次出场"""
        first_chapter = ChapterId("chapter-001")
        character = Character(
            id=self.character_id,
            novel_id=self.novel_id,
            name="孔凡圣",
            role=CharacterRole.PROTAGONIST,
            background="",
            personality="",
            appearance_count=1,
            first_appearance=first_chapter,
            created_at=self.now,
            updated_at=self.now
        )
        new_chapter = ChapterId("chapter-002")
        character.increment_appearance(new_chapter, self.now)
        self.assertEqual(character.appearance_count, 2)
        self.assertEqual(character.first_appearance, first_chapter)

    def test_is_protagonist(self):
        """测试是否主角"""
        protagonist = Character(
            id=self.character_id,
            novel_id=self.novel_id,
            name="孔凡圣",
            role=CharacterRole.PROTAGONIST,
            background="",
            personality="",
            created_at=self.now,
            updated_at=self.now
        )
        antagonist = Character(
            id=CharacterId("char-002"),
            novel_id=self.novel_id,
            name="反派",
            role=CharacterRole.ANTAGONIST,
            background="",
            personality="",
            created_at=self.now,
            updated_at=self.now
        )
        self.assertTrue(protagonist.is_protagonist)
        self.assertFalse(antagonist.is_protagonist)


class TestCharacterRelationship(unittest.TestCase):
    """测试CharacterRelationship值对象"""

    def test_create_relationship(self):
        """测试创建人物关系"""
        target_id = CharacterId("char-002")
        relationship = CharacterRelationship(
            target_id=target_id,
            relation_type="师徒",
            description="菩提老祖是孔凡圣的师父"
        )
        self.assertEqual(relationship.target_id, target_id)
        self.assertEqual(relationship.relation_type, "师徒")


if __name__ == '__main__':
    unittest.main()
