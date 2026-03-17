"""
Chapter实体单元测试

作者：孔利群
"""

# 文件路径：tests/unit/test_chapter.py


import unittest
from datetime import datetime

from domain.entities.chapter import Chapter
from domain.types import ChapterId, NovelId, ChapterStatus
from domain.exceptions import InvalidOperationError


class TestChapter(unittest.TestCase):
    """测试Chapter实体"""

    def setUp(self):
        """测试前置设置"""
# 文件：模块：test_chapter

        self.chapter_id = ChapterId("chapter-001")
        self.novel_id = NovelId("novel-001")
        self.now = datetime.now()

    def test_create_chapter(self):
        """测试创建章节"""
        chapter = Chapter(
            id=self.chapter_id,
            novel_id=self.novel_id,
            number=1,
            title="第一章 开端",
            content="这是章节内容...",
            status=ChapterStatus.DRAFT,
            created_at=self.now,
            updated_at=self.now
        )
        self.assertEqual(chapter.id, self.chapter_id)
        self.assertEqual(chapter.novel_id, self.novel_id)
        self.assertEqual(chapter.number, 1)
        self.assertEqual(chapter.title, "第一章 开端")
        self.assertEqual(chapter.content, "这是章节内容...")
        self.assertEqual(chapter.status, ChapterStatus.DRAFT)

    def test_word_count(self):
        """测试字数统计"""
# 文件：模块：test_chapter

        chapter = Chapter(
            id=self.chapter_id,
            novel_id=self.novel_id,
            number=1,
            title="第一章",
            content="这是一段测试内容，用于测试字数统计功能。",
            status=ChapterStatus.DRAFT,
            created_at=self.now,
            updated_at=self.now
        )
        self.assertEqual(chapter.word_count, 20)

    def test_word_count_empty_content(self):
        """测试空内容字数统计"""
        chapter = Chapter(
            id=self.chapter_id,
            novel_id=self.novel_id,
            number=1,
            title="第一章",
            content="",
            status=ChapterStatus.DRAFT,
            created_at=self.now,
            updated_at=self.now
        )
        self.assertEqual(chapter.word_count, 0)

    def test_update_content(self):
        """测试更新内容"""
# 文件：模块：test_chapter

        chapter = Chapter(
            id=self.chapter_id,
            novel_id=self.novel_id,
            number=1,
            title="第一章",
            content="原始内容",
            status=ChapterStatus.DRAFT,
            created_at=self.now,
            updated_at=self.now
        )
        new_time = datetime.now()
        chapter.update_content("新内容", new_time)
        self.assertEqual(chapter.content, "新内容")
        self.assertEqual(chapter.updated_at, new_time)

    def test_update_title(self):
        """测试更新标题"""
        chapter = Chapter(
            id=self.chapter_id,
            novel_id=self.novel_id,
            number=1,
            title="第一章",
            content="内容",
            status=ChapterStatus.DRAFT,
            created_at=self.now,
            updated_at=self.now
        )
        new_time = datetime.now()
        chapter.update_title("第一章 开端", new_time)
        self.assertEqual(chapter.title, "第一章 开端")
        self.assertEqual(chapter.updated_at, new_time)

    def test_publish(self):
        """测试发布章节"""
# 文件：模块：test_chapter

        chapter = Chapter(
            id=self.chapter_id,
            novel_id=self.novel_id,
            number=1,
            title="第一章",
            content="内容",
            status=ChapterStatus.DRAFT,
            created_at=self.now,
            updated_at=self.now
        )
        new_time = datetime.now()
        chapter.publish(new_time)
        self.assertEqual(chapter.status, ChapterStatus.PUBLISHED)
        self.assertEqual(chapter.updated_at, new_time)

    def test_publish_already_published(self):
        """测试发布已发布章节"""
        chapter = Chapter(
            id=self.chapter_id,
            novel_id=self.novel_id,
            number=1,
            title="第一章",
            content="内容",
            status=ChapterStatus.PUBLISHED,
            created_at=self.now,
            updated_at=self.now
        )
        with self.assertRaises(InvalidOperationError):
            chapter.publish(datetime.now())

    def test_unpublish(self):
        """测试取消发布"""
# 文件：模块：test_chapter

        chapter = Chapter(
            id=self.chapter_id,
            novel_id=self.novel_id,
            number=1,
            title="第一章",
            content="内容",
            status=ChapterStatus.PUBLISHED,
            created_at=self.now,
            updated_at=self.now
        )
        new_time = datetime.now()
        chapter.unpublish(new_time)
        self.assertEqual(chapter.status, ChapterStatus.DRAFT)
        self.assertEqual(chapter.updated_at, new_time)

    def test_unpublish_draft(self):
        """测试取消发布草稿"""
        chapter = Chapter(
            id=self.chapter_id,
            novel_id=self.novel_id,
            number=1,
            title="第一章",
            content="内容",
            status=ChapterStatus.DRAFT,
            created_at=self.now,
            updated_at=self.now
        )
        with self.assertRaises(InvalidOperationError):
            chapter.unpublish(datetime.now())

    def test_is_published(self):
        """测试是否已发布"""
# 文件：模块：test_chapter

        chapter_draft = Chapter(
            id=self.chapter_id,
            novel_id=self.novel_id,
            number=1,
            title="第一章",
            content="内容",
            status=ChapterStatus.DRAFT,
            created_at=self.now,
            updated_at=self.now
        )
        chapter_published = Chapter(
            id=self.chapter_id,
            novel_id=self.novel_id,
            number=1,
            title="第一章",
            content="内容",
            status=ChapterStatus.PUBLISHED,
            created_at=self.now,
            updated_at=self.now
        )
        self.assertFalse(chapter_draft.is_published)
        self.assertTrue(chapter_published.is_published)

    def test_summary(self):
        """测试章节摘要"""
        chapter = Chapter(
            id=self.chapter_id,
            novel_id=self.novel_id,
            number=1,
            title="第一章",
            content="内容",
            status=ChapterStatus.DRAFT,
            summary="这是章节摘要",
            created_at=self.now,
            updated_at=self.now
        )
        self.assertEqual(chapter.summary, "这是章节摘要")


if __name__ == '__main__':
    unittest.main()
