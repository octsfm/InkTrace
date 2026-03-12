"""
领域基础类型单元测试

作者：孔利群
"""

import unittest
from datetime import datetime

from domain.types import (
    NovelId, ChapterId, CharacterId, OutlineId,
    ChapterStatus, PlotType, PlotStatus, CharacterRole
)
from domain.exceptions import (
    DomainException, EntityNotFoundError, InvalidEntityStateError,
    InvalidOperationError, ValidationError
)


class TestNovelId(unittest.TestCase):
    """测试NovelId"""

    def test_create_novel_id(self):
        """测试创建小说ID"""
        novel_id = NovelId("novel-001")
        self.assertEqual(novel_id.value, "novel-001")

    def test_novel_id_equality(self):
        """测试小说ID相等性"""
        id1 = NovelId("novel-001")
        id2 = NovelId("novel-001")
        id3 = NovelId("novel-002")
        self.assertEqual(id1, id2)
        self.assertNotEqual(id1, id3)

    def test_novel_id_hash(self):
        """测试小说ID哈希"""
        id1 = NovelId("novel-001")
        id2 = NovelId("novel-001")
        self.assertEqual(hash(id1), hash(id2))

    def test_novel_id_str(self):
        """测试小说ID字符串表示"""
        novel_id = NovelId("novel-001")
        self.assertEqual(str(novel_id), "novel-001")


class TestChapterId(unittest.TestCase):
    """测试ChapterId"""

    def test_create_chapter_id(self):
        """测试创建章节ID"""
        chapter_id = ChapterId("chapter-001")
        self.assertEqual(chapter_id.value, "chapter-001")

    def test_chapter_id_equality(self):
        """测试章节ID相等性"""
        id1 = ChapterId("chapter-001")
        id2 = ChapterId("chapter-001")
        id3 = ChapterId("chapter-002")
        self.assertEqual(id1, id2)
        self.assertNotEqual(id1, id3)


class TestCharacterId(unittest.TestCase):
    """测试CharacterId"""

    def test_create_character_id(self):
        """测试创建人物ID"""
        character_id = CharacterId("char-001")
        self.assertEqual(character_id.value, "char-001")


class TestOutlineId(unittest.TestCase):
    """测试OutlineId"""

    def test_create_outline_id(self):
        """测试创建大纲ID"""
        outline_id = OutlineId("outline-001")
        self.assertEqual(outline_id.value, "outline-001")


class TestChapterStatus(unittest.TestCase):
    """测试ChapterStatus枚举"""

    def test_draft_status(self):
        """测试草稿状态"""
        self.assertEqual(ChapterStatus.DRAFT.value, "draft")

    def test_published_status(self):
        """测试已发布状态"""
        self.assertEqual(ChapterStatus.PUBLISHED.value, "published")

    def test_all_statuses(self):
        """测试所有状态"""
        statuses = list(ChapterStatus)
        self.assertEqual(len(statuses), 2)


class TestPlotType(unittest.TestCase):
    """测试PlotType枚举"""

    def test_main_plot(self):
        """测试主线剧情"""
        self.assertEqual(PlotType.MAIN.value, "main")

    def test_sub_plot(self):
        """测试支线剧情"""
        self.assertEqual(PlotType.SUB.value, "sub")

    def test_foreshadowing_plot(self):
        """测试伏笔剧情"""
        self.assertEqual(PlotType.FORESHADOWING.value, "foreshadowing")


class TestPlotStatus(unittest.TestCase):
    """测试PlotStatus枚举"""

    def test_planned_status(self):
        """测试计划状态"""
        self.assertEqual(PlotStatus.PLANNED.value, "planned")

    def test_ongoing_status(self):
        """测试进行中状态"""
        self.assertEqual(PlotStatus.ONGOING.value, "ongoing")

    def test_completed_status(self):
        """测试完成状态"""
        self.assertEqual(PlotStatus.COMPLETED.value, "completed")


class TestCharacterRole(unittest.TestCase):
    """测试CharacterRole枚举"""

    def test_protagonist_role(self):
        """测试主角"""
        self.assertEqual(CharacterRole.PROTAGONIST.value, "protagonist")

    def test_antagonist_role(self):
        """测试反派"""
        self.assertEqual(CharacterRole.ANTAGONIST.value, "antagonist")

    def test_supporting_role(self):
        """测试配角"""
        self.assertEqual(CharacterRole.SUPPORTING.value, "supporting")


class TestDomainExceptions(unittest.TestCase):
    """测试领域异常"""

    def test_domain_exception(self):
        """测试基础领域异常"""
        exc = DomainException("测试异常")
        self.assertEqual(str(exc), "测试异常")

    def test_entity_not_found_error(self):
        """测试实体未找到异常"""
        exc = EntityNotFoundError("Novel", "novel-001")
        self.assertIn("Novel", str(exc))
        self.assertIn("novel-001", str(exc))

    def test_invalid_entity_state_error(self):
        """测试无效实体状态异常"""
        exc = InvalidEntityStateError("Chapter", "draft", "published")
        self.assertIn("Chapter", str(exc))

    def test_invalid_operation_error(self):
        """测试无效操作异常"""
        exc = InvalidOperationError("不能删除已发布章节")
        self.assertEqual(str(exc), "不能删除已发布章节")

    def test_validation_error(self):
        """测试验证异常"""
        exc = ValidationError("标题不能为空")
        self.assertEqual(str(exc), "标题不能为空")


if __name__ == '__main__':
    unittest.main()
