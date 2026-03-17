"""
Markdown导出器单元测试

作者：孔利群
"""

# 文件路径：tests/unit/test_markdown_exporter.py


import unittest
import os
import tempfile
from datetime import datetime

from domain.types import ChapterId, NovelId, ChapterStatus
from domain.entities.chapter import Chapter
from domain.entities.novel import Novel
from infrastructure.file.markdown_exporter import MarkdownExporter


class TestMarkdownExporter(unittest.TestCase):
    """测试MarkdownExporter"""

    def setUp(self):
        """测试前置设置"""
# 文件：模块：test_markdown_exporter

        self.exporter = MarkdownExporter()
        self.temp_dir = tempfile.mkdtemp()
        self.now = datetime.now()

    def tearDown(self):
        """测试后清理"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_export_chapter(self):
        """测试导出章节"""
# 文件：模块：test_markdown_exporter

        chapter = Chapter(
            id=ChapterId("chapter-001"),
            novel_id=NovelId("novel-001"),
            number=1,
            title="第一章 开端",
            content="这是第一章的内容。\n\n孔凡圣在丛林中奔跑。",
            status=ChapterStatus.DRAFT,
            created_at=self.now,
            updated_at=self.now
        )
        
        output_path = os.path.join(self.temp_dir, "chapter_001.md")
        self.exporter.export_chapter(chapter, output_path)
        
        self.assertTrue(os.path.exists(output_path))
        
        with open(output_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        self.assertIn("第1章 第一章 开端", content)
        self.assertIn("孔凡圣", content)

    def test_export_chapter_content(self):
        """测试导出章节内容"""
        chapter = Chapter(
            id=ChapterId("chapter-001"),
            novel_id=NovelId("novel-001"),
            number=1,
            title="测试章节",
            content="测试内容",
            status=ChapterStatus.DRAFT,
            created_at=self.now,
            updated_at=self.now
        )
        
        content = self.exporter.export_chapter_content(chapter)
        
        self.assertIn("第1章 测试章节", content)
        self.assertIn("测试内容", content)

    def test_export_novel(self):
        """测试导出小说"""
# 文件：模块：test_markdown_exporter

        novel = Novel(
            id=NovelId("novel-001"),
            title="修仙从逃出生天开始",
            author="孔利群",
            genre="现代修真",
            target_word_count=8000000,
            current_word_count=100,
            created_at=self.now,
            updated_at=self.now
        )
        
        chapters = [
            Chapter(
                id=ChapterId("chapter-001"),
                novel_id=NovelId("novel-001"),
                number=1,
                title="第一章 跑",
                content="孔凡圣在丛林中奔跑。",
                status=ChapterStatus.DRAFT,
                created_at=self.now,
                updated_at=self.now
            ),
            Chapter(
                id=ChapterId("chapter-002"),
                novel_id=NovelId("novel-001"),
                number=2,
                title="第二章 逃出生天",
                content="他跳入河中逃脱。",
                status=ChapterStatus.DRAFT,
                created_at=self.now,
                updated_at=self.now
            )
        ]
        
        output_path = os.path.join(self.temp_dir, "novel.md")
        self.exporter.export_novel(novel, chapters, output_path)
        
        self.assertTrue(os.path.exists(output_path))
        
        with open(output_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        self.assertIn("# 修仙从逃出生天开始", content)
        self.assertIn("孔利群", content)
        self.assertIn("第一章 跑", content)
        self.assertIn("第二章 逃出生天", content)

    def test_format_metadata(self):
        """测试格式化元数据"""
        novel = Novel(
            id=NovelId("novel-001"),
            title="测试小说",
            author="测试作者",
            genre="玄幻",
            target_word_count=100000,
            current_word_count=50000,
            created_at=self.now,
            updated_at=self.now
        )
        
        metadata = self.exporter.format_metadata(novel)
        
        self.assertIn("测试小说", metadata)
        self.assertIn("测试作者", metadata)
        self.assertIn("玄幻", metadata)


if __name__ == '__main__':
    unittest.main()
