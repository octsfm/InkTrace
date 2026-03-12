"""
SQLite仓储单元测试

作者：孔利群
"""

import unittest
import os
import tempfile
from datetime import datetime

from domain.types import NovelId, ChapterId, CharacterId, OutlineId, ChapterStatus, CharacterRole
from domain.entities.novel import Novel
from domain.entities.chapter import Chapter
from domain.entities.character import Character
from domain.entities.outline import Outline
from infrastructure.persistence.sqlite_novel_repo import SQLiteNovelRepository
from infrastructure.persistence.sqlite_chapter_repo import SQLiteChapterRepository
from infrastructure.persistence.sqlite_character_repo import SQLiteCharacterRepository
from infrastructure.persistence.sqlite_outline_repo import SQLiteOutlineRepository


class TestSQLiteNovelRepository(unittest.TestCase):
    """测试SQLite小说仓储"""

    def setUp(self):
        """测试前置设置"""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test.db")
        self.repo = SQLiteNovelRepository(self.db_path)
        self.now = datetime.now()

    def tearDown(self):
        """测试后清理"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_save_and_find_novel(self):
        """测试保存和查找小说"""
        novel = Novel(
            id=NovelId("novel-001"),
            title="测试小说",
            author="孔利群",
            genre="玄幻",
            target_word_count=100000,
            created_at=self.now,
            updated_at=self.now
        )
        
        self.repo.save(novel)
        found = self.repo.find_by_id(NovelId("novel-001"))
        
        self.assertIsNotNone(found)
        self.assertEqual(found.title, "测试小说")
        self.assertEqual(found.author, "孔利群")

    def test_find_all_novels(self):
        """测试查找所有小说"""
        novel1 = Novel(
            id=NovelId("novel-001"),
            title="小说1",
            author="作者1",
            genre="玄幻",
            target_word_count=100000,
            created_at=self.now,
            updated_at=self.now
        )
        novel2 = Novel(
            id=NovelId("novel-002"),
            title="小说2",
            author="作者2",
            genre="仙侠",
            target_word_count=200000,
            created_at=self.now,
            updated_at=self.now
        )
        
        self.repo.save(novel1)
        self.repo.save(novel2)
        
        novels = self.repo.find_all()
        self.assertEqual(len(novels), 2)

    def test_delete_novel(self):
        """测试删除小说"""
        novel = Novel(
            id=NovelId("novel-001"),
            title="测试小说",
            author="作者",
            genre="玄幻",
            target_word_count=100000,
            created_at=self.now,
            updated_at=self.now
        )
        
        self.repo.save(novel)
        self.repo.delete(NovelId("novel-001"))
        
        found = self.repo.find_by_id(NovelId("novel-001"))
        self.assertIsNone(found)


class TestSQLiteChapterRepository(unittest.TestCase):
    """测试SQLite章节仓储"""

    def setUp(self):
        """测试前置设置"""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test.db")
        self.repo = SQLiteChapterRepository(self.db_path)
        self.now = datetime.now()
        self.novel_id = NovelId("novel-001")

    def tearDown(self):
        """测试后清理"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_save_and_find_chapter(self):
        """测试保存和查找章节"""
        chapter = Chapter(
            id=ChapterId("chapter-001"),
            novel_id=self.novel_id,
            number=1,
            title="第一章",
            content="这是第一章的内容",
            status=ChapterStatus.DRAFT,
            created_at=self.now,
            updated_at=self.now
        )
        
        self.repo.save(chapter)
        found = self.repo.find_by_id(ChapterId("chapter-001"))
        
        self.assertIsNotNone(found)
        self.assertEqual(found.title, "第一章")
        self.assertEqual(found.number, 1)

    def test_find_by_novel(self):
        """测试查找小说的所有章节"""
        for i in range(1, 4):
            chapter = Chapter(
                id=ChapterId(f"chapter-{i:03d}"),
                novel_id=self.novel_id,
                number=i,
                title=f"第{i}章",
                content=f"第{i}章内容",
                status=ChapterStatus.DRAFT,
                created_at=self.now,
                updated_at=self.now
            )
            self.repo.save(chapter)
        
        chapters = self.repo.find_by_novel(self.novel_id)
        self.assertEqual(len(chapters), 3)

    def test_find_latest(self):
        """测试查找最新章节"""
        for i in range(1, 6):
            chapter = Chapter(
                id=ChapterId(f"chapter-{i:03d}"),
                novel_id=self.novel_id,
                number=i,
                title=f"第{i}章",
                content=f"内容{i}",
                status=ChapterStatus.DRAFT,
                created_at=self.now,
                updated_at=self.now
            )
            self.repo.save(chapter)
        
        latest = self.repo.find_latest(self.novel_id, 3)
        self.assertEqual(len(latest), 3)
        self.assertEqual(latest[0].number, 5)


class TestSQLiteCharacterRepository(unittest.TestCase):
    """测试SQLite人物仓储"""

    def setUp(self):
        """测试前置设置"""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test.db")
        self.repo = SQLiteCharacterRepository(self.db_path)
        self.now = datetime.now()
        self.novel_id = NovelId("novel-001")

    def tearDown(self):
        """测试后清理"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_save_and_find_character(self):
        """测试保存和查找人物"""
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
        
        self.repo.save(character)
        found = self.repo.find_by_id(CharacterId("char-001"))
        
        self.assertIsNotNone(found)
        self.assertEqual(found.name, "孔凡圣")
        self.assertEqual(found.role, CharacterRole.PROTAGONIST)

    def test_find_by_novel(self):
        """测试查找小说的所有人物"""
        for i in range(1, 4):
            character = Character(
                id=CharacterId(f"char-{i:03d}"),
                novel_id=self.novel_id,
                name=f"人物{i}",
                role=CharacterRole.SUPPORTING,
                background="",
                personality="",
                created_at=self.now,
                updated_at=self.now
            )
            self.repo.save(character)
        
        characters = self.repo.find_by_novel(self.novel_id)
        self.assertEqual(len(characters), 3)


class TestSQLiteOutlineRepository(unittest.TestCase):
    """测试SQLite大纲仓储"""

    def setUp(self):
        """测试前置设置"""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test.db")
        self.repo = SQLiteOutlineRepository(self.db_path)
        self.now = datetime.now()
        self.novel_id = NovelId("novel-001")

    def tearDown(self):
        """测试后清理"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_save_and_find_outline(self):
        """测试保存和查找大纲"""
        outline = Outline(
            id=OutlineId("outline-001"),
            novel_id=self.novel_id,
            premise="修仙故事",
            story_background="现代都市",
            world_setting="蓝星",
            created_at=self.now,
            updated_at=self.now
        )
        
        self.repo.save(outline)
        found = self.repo.find_by_id(OutlineId("outline-001"))
        
        self.assertIsNotNone(found)
        self.assertEqual(found.premise, "修仙故事")

    def test_find_by_novel(self):
        """测试查找小说的大纲"""
        outline = Outline(
            id=OutlineId("outline-001"),
            novel_id=self.novel_id,
            premise="测试大纲",
            story_background="",
            world_setting="",
            created_at=self.now,
            updated_at=self.now
        )
        
        self.repo.save(outline)
        found = self.repo.find_by_novel(self.novel_id)
        
        self.assertIsNotNone(found)
        self.assertEqual(found.premise, "测试大纲")


if __name__ == '__main__':
    unittest.main()
