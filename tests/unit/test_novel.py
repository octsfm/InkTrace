"""
Novel聚合根单元测试

作者：孔利群
"""

import unittest
from datetime import datetime

from domain.entities.novel import Novel
from domain.entities.chapter import Chapter
from domain.entities.character import Character
from domain.entities.outline import Outline
from domain.types import (
    NovelId, ChapterId, CharacterId, OutlineId,
    ChapterStatus, CharacterRole
)


class TestNovel(unittest.TestCase):
    """测试Novel聚合根"""

    def setUp(self):
        """测试前置设置"""
        self.novel_id = NovelId("novel-001")
        self.now = datetime.now()

    def test_create_novel(self):
        """测试创建小说"""
        novel = Novel(
            id=self.novel_id,
            title="修仙从逃出生天开始",
            author="孔利群",
            genre="现代修真",
            target_word_count=8000000,
            created_at=self.now,
            updated_at=self.now
        )
        self.assertEqual(novel.id, self.novel_id)
        self.assertEqual(novel.title, "修仙从逃出生天开始")
        self.assertEqual(novel.author, "孔利群")
        self.assertEqual(novel.genre, "现代修真")
        self.assertEqual(novel.target_word_count, 8000000)
        self.assertEqual(novel.current_word_count, 0)

    def test_add_chapter(self):
        """测试添加章节"""
        novel = Novel(
            id=self.novel_id,
            title="测试小说",
            author="作者",
            genre="玄幻",
            target_word_count=100000,
            created_at=self.now,
            updated_at=self.now
        )
        chapter = Chapter(
            id=ChapterId("chapter-001"),
            novel_id=self.novel_id,
            number=1,
            title="第一章",
            content="这是第一章的内容，共十个字。",
            status=ChapterStatus.DRAFT,
            created_at=self.now,
            updated_at=self.now
        )
        novel.add_chapter(chapter, self.now)
        self.assertEqual(len(novel.chapters), 1)
        self.assertEqual(novel.current_word_count, 14)

    def test_get_chapter(self):
        """测试获取章节"""
        novel = Novel(
            id=self.novel_id,
            title="测试小说",
            author="作者",
            genre="玄幻",
            target_word_count=100000,
            created_at=self.now,
            updated_at=self.now
        )
        chapter = Chapter(
            id=ChapterId("chapter-001"),
            novel_id=self.novel_id,
            number=1,
            title="第一章",
            content="内容",
            status=ChapterStatus.DRAFT,
            created_at=self.now,
            updated_at=self.now
        )
        novel.add_chapter(chapter, self.now)
        found = novel.get_chapter(ChapterId("chapter-001"))
        self.assertIsNotNone(found)
        self.assertEqual(found.title, "第一章")

    def test_get_chapter_by_number(self):
        """测试根据章节号获取章节"""
        novel = Novel(
            id=self.novel_id,
            title="测试小说",
            author="作者",
            genre="玄幻",
            target_word_count=100000,
            created_at=self.now,
            updated_at=self.now
        )
        chapter = Chapter(
            id=ChapterId("chapter-001"),
            novel_id=self.novel_id,
            number=1,
            title="第一章",
            content="内容",
            status=ChapterStatus.DRAFT,
            created_at=self.now,
            updated_at=self.now
        )
        novel.add_chapter(chapter, self.now)
        found = novel.get_chapter_by_number(1)
        self.assertIsNotNone(found)
        self.assertEqual(found.id.value, "chapter-001")

    def test_get_latest_chapters(self):
        """测试获取最新章节"""
        novel = Novel(
            id=self.novel_id,
            title="测试小说",
            author="作者",
            genre="玄幻",
            target_word_count=100000,
            created_at=self.now,
            updated_at=self.now
        )
        for i in range(1, 6):
            chapter = Chapter(
                id=ChapterId(f"chapter-{i:03d}"),
                novel_id=self.novel_id,
                number=i,
                title=f"第{i}章",
                content="内容",
                status=ChapterStatus.DRAFT,
                created_at=self.now,
                updated_at=self.now
            )
            novel.add_chapter(chapter, self.now)
        
        latest = novel.get_latest_chapters(3)
        self.assertEqual(len(latest), 3)
        self.assertEqual(latest[0].number, 5)
        self.assertEqual(latest[1].number, 4)
        self.assertEqual(latest[2].number, 3)

    def test_add_character(self):
        """测试添加人物"""
        novel = Novel(
            id=self.novel_id,
            title="测试小说",
            author="作者",
            genre="玄幻",
            target_word_count=100000,
            created_at=self.now,
            updated_at=self.now
        )
        character = Character(
            id=CharacterId("char-001"),
            novel_id=self.novel_id,
            name="孔凡圣",
            role=CharacterRole.PROTAGONIST,
            background="普通程序员",
            personality="坚韧不拔",
            created_at=self.now,
            updated_at=self.now
        )
        novel.add_character(character, self.now)
        self.assertEqual(len(novel.characters), 1)

    def test_get_character(self):
        """测试获取人物"""
        novel = Novel(
            id=self.novel_id,
            title="测试小说",
            author="作者",
            genre="玄幻",
            target_word_count=100000,
            created_at=self.now,
            updated_at=self.now
        )
        character = Character(
            id=CharacterId("char-001"),
            novel_id=self.novel_id,
            name="孔凡圣",
            role=CharacterRole.PROTAGONIST,
            background="",
            personality="",
            created_at=self.now,
            updated_at=self.now
        )
        novel.add_character(character, self.now)
        found = novel.get_character(CharacterId("char-001"))
        self.assertIsNotNone(found)
        self.assertEqual(found.name, "孔凡圣")

    def test_get_protagonist(self):
        """测试获取主角"""
        novel = Novel(
            id=self.novel_id,
            title="测试小说",
            author="作者",
            genre="玄幻",
            target_word_count=100000,
            created_at=self.now,
            updated_at=self.now
        )
        protagonist = Character(
            id=CharacterId("char-001"),
            novel_id=self.novel_id,
            name="孔凡圣",
            role=CharacterRole.PROTAGONIST,
            background="",
            personality="",
            created_at=self.now,
            updated_at=self.now
        )
        supporting = Character(
            id=CharacterId("char-002"),
            novel_id=self.novel_id,
            name="配角",
            role=CharacterRole.SUPPORTING,
            background="",
            personality="",
            created_at=self.now,
            updated_at=self.now
        )
        novel.add_character(protagonist, self.now)
        novel.add_character(supporting, self.now)
        
        found = novel.get_protagonist()
        self.assertIsNotNone(found)
        self.assertEqual(found.name, "孔凡圣")

    def test_set_outline(self):
        """测试设置大纲"""
        novel = Novel(
            id=self.novel_id,
            title="测试小说",
            author="作者",
            genre="玄幻",
            target_word_count=100000,
            created_at=self.now,
            updated_at=self.now
        )
        outline = Outline(
            id=OutlineId("outline-001"),
            novel_id=self.novel_id,
            premise="核心设定",
            story_background="故事背景",
            world_setting="世界观",
            created_at=self.now,
            updated_at=self.now
        )
        novel.set_outline(outline, self.now)
        self.assertIsNotNone(novel.outline)
        self.assertEqual(novel.outline.premise, "核心设定")

    def test_chapter_count(self):
        """测试章节计数"""
        novel = Novel(
            id=self.novel_id,
            title="测试小说",
            author="作者",
            genre="玄幻",
            target_word_count=100000,
            created_at=self.now,
            updated_at=self.now
        )
        for i in range(1, 4):
            chapter = Chapter(
                id=ChapterId(f"chapter-{i:03d}"),
                novel_id=self.novel_id,
                number=i,
                title=f"第{i}章",
                content="内容",
                status=ChapterStatus.DRAFT,
                created_at=self.now,
                updated_at=self.now
            )
            novel.add_chapter(chapter, self.now)
        
        self.assertEqual(novel.chapter_count, 3)

    def test_update_word_count(self):
        """测试更新字数统计"""
        novel = Novel(
            id=self.novel_id,
            title="测试小说",
            author="作者",
            genre="玄幻",
            target_word_count=100000,
            created_at=self.now,
            updated_at=self.now
        )
        chapter1 = Chapter(
            id=ChapterId("chapter-001"),
            novel_id=self.novel_id,
            number=1,
            title="第一章",
            content="这是第一章的内容。",
            status=ChapterStatus.DRAFT,
            created_at=self.now,
            updated_at=self.now
        )
        chapter2 = Chapter(
            id=ChapterId("chapter-002"),
            novel_id=self.novel_id,
            number=2,
            title="第二章",
            content="这是第二章的内容。",
            status=ChapterStatus.DRAFT,
            created_at=self.now,
            updated_at=self.now
        )
        novel.add_chapter(chapter1, self.now)
        novel.add_chapter(chapter2, self.now)
        
        self.assertEqual(novel.current_word_count, 18)


if __name__ == '__main__':
    unittest.main()
