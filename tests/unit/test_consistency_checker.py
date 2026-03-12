"""
连贯性检查领域服务单元测试

作者：孔利群
"""

import unittest
from datetime import datetime

from domain.entities.chapter import Chapter
from domain.entities.character import Character
from domain.types import ChapterId, NovelId, CharacterId, ChapterStatus, CharacterRole
from domain.services.consistency_checker import ConsistencyChecker, ConsistencyReport, Inconsistency


class TestConsistencyChecker(unittest.TestCase):
    """测试ConsistencyChecker"""

    def setUp(self):
        """测试前置设置"""
        self.checker = ConsistencyChecker()
        self.now = datetime.now()

    def _create_chapter(self, content: str, number: int = 1) -> Chapter:
        """创建测试章节"""
        return Chapter(
            id=ChapterId(f"chapter-{number:03d}"),
            novel_id=NovelId("novel-001"),
            number=number,
            title=f"第{number}章",
            content=content,
            status=ChapterStatus.DRAFT,
            created_at=self.now,
            updated_at=self.now
        )

    def _create_character(self, name: str, state: str = "") -> Character:
        """创建测试人物"""
        return Character(
            id=CharacterId(f"char-{name}"),
            novel_id=NovelId("novel-001"),
            name=name,
            role=CharacterRole.PROTAGONIST,
            background="",
            personality="",
            current_state=state,
            created_at=self.now,
            updated_at=self.now
        )

    def test_check_empty_chapter(self):
        """测试检查空章节"""
        chapter = self._create_chapter("", 1)
        report = self.checker.check(chapter, [])
        
        self.assertIsInstance(report, ConsistencyReport)
        self.assertTrue(report.is_valid)

    def test_check_character_state(self):
        """测试检查人物状态"""
        character = self._create_character("孔凡圣", "凡人")
        chapter = self._create_chapter("孔凡圣已经突破到筑基期。", 2)
        
        inconsistencies = self.checker.check_character_state(character, chapter)
        
        self.assertIsInstance(inconsistencies, list)

    def test_check_timeline(self):
        """测试检查时间线"""
        timeline = [
            {"chapter_number": 1, "event_description": "孔凡圣开始修炼"},
            {"chapter_number": 2, "event_description": "孔凡圣突破筑基期"}
        ]
        chapter = self._create_chapter("孔凡圣还是凡人。", 3)
        
        inconsistencies = self.checker.check_timeline(timeline, chapter)
        
        self.assertIsInstance(inconsistencies, list)

    def test_consistency_report(self):
        """测试连贯性报告"""
        report = ConsistencyReport(
            is_valid=True,
            inconsistencies=[],
            warnings=["警告信息"]
        )
        
        self.assertTrue(report.is_valid)
        self.assertEqual(len(report.warnings), 1)

    def test_inconsistency(self):
        """测试不一致项"""
        inconsistency = Inconsistency(
            type="人物状态",
            description="孔凡圣状态不一致",
            severity="高"
        )
        
        self.assertEqual(inconsistency.type, "人物状态")
        self.assertEqual(inconsistency.severity, "高")


class TestCharacterStateCheck(unittest.TestCase):
    """测试人物状态检查"""

    def setUp(self):
        self.checker = ConsistencyChecker()
        self.now = datetime.now()

    def test_detect_cultivation_change(self):
        """测试检测修为变化"""
        character = Character(
            id=CharacterId("char-001"),
            novel_id=NovelId("novel-001"),
            name="孔凡圣",
            role=CharacterRole.PROTAGONIST,
            background="",
            personality="",
            current_state="金丹期",
            created_at=self.now,
            updated_at=self.now
        )
        
        chapter = Chapter(
            id=ChapterId("chapter-001"),
            novel_id=NovelId("novel-001"),
            number=1,
            title="第一章",
            content="孔凡圣还是凡人。",
            status=ChapterStatus.DRAFT,
            created_at=self.now,
            updated_at=self.now
        )
        
        inconsistencies = self.checker.check_character_state(character, chapter)
        
        self.assertTrue(len(inconsistencies) > 0)


if __name__ == '__main__':
    unittest.main()
