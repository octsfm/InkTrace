"""
导出服务单元测试

作者：孔利群
"""

import pytest
import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime

from application.services.export_service import ExportService
from application.dto.request_dto import ExportNovelRequest
from domain.entities.novel import Novel
from domain.entities.chapter import Chapter
from domain.types import NovelId, ChapterId, ChapterStatus


class TestExportService:
    """导出服务测试"""
    
    def setup_method(self):
        """测试前准备"""
        self.mock_novel_repo = Mock()
        self.mock_chapter_repo = Mock()
        self.service = ExportService(self.mock_novel_repo, self.mock_chapter_repo)
    
    def create_test_novel(self):
        """创建测试用小说"""
        return Novel(
            id=NovelId("novel_001"),
            title="测试小说",
            author="测试作者",
            genre="玄幻",
            target_word_count=100000,
            current_word_count=5000,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
    
    def create_test_chapters(self, novel_id):
        """创建测试用章节"""
        chapters = []
        for i in range(1, 4):
            chapter = Chapter(
                id=ChapterId(f"chapter_{i:03d}"),
                novel_id=novel_id,
                number=i,
                title=f"第{i}章 测试章节",
                content=f"这是第{i}章的内容。" * 100,
                status=ChapterStatus.PUBLISHED,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            chapters.append(chapter)
        return chapters
    
    def test_export_novel_markdown(self):
        """测试导出小说为Markdown"""
        novel = self.create_test_novel()
        chapters = self.create_test_chapters(novel.id)
        
        self.mock_novel_repo.find_by_id.return_value = novel
        self.mock_chapter_repo.find_by_novel.return_value = chapters
        
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "test_export.md")
            request = ExportNovelRequest(
                novel_id="novel_001",
                output_path=output_path,
                format="markdown"
            )
            
            result = self.service.export_novel(request)
            
            assert result.file_path == output_path
            assert result.format == "markdown"
            assert result.mode == "file"
            assert result.scope == "full"
            assert result.chapter_count == 3
            self.mock_novel_repo.find_by_id.assert_called_once()
            self.mock_chapter_repo.find_by_novel.assert_called_once()
    
    def test_export_novel_not_found(self):
        """测试导出不存在的小说"""
        self.mock_novel_repo.find_by_id.return_value = None
        
        request = ExportNovelRequest(
            novel_id="novel_999",
            output_path="/tmp/test.md",
            format="markdown"
        )
        
        with pytest.raises(ValueError, match="小说不存在"):
            self.service.export_novel(request)
    
    def test_export_novel_unsupported_format(self):
        """测试导出不支持的格式"""
        novel = self.create_test_novel()
        chapters = self.create_test_chapters(novel.id)
        
        self.mock_novel_repo.find_by_id.return_value = novel
        self.mock_chapter_repo.find_by_novel.return_value = chapters
        
        request = ExportNovelRequest.model_construct(
            novel_id="novel_001",
            output_path="/tmp/test.pdf",
            format="pdf",
            scope="full",
        )
        
        with pytest.raises(ValueError, match="不支持的导出格式"):
            self.service.export_novel(request)
    
    def test_export_novel_empty_chapters(self):
        """测试导出没有章节的小说"""
        novel = self.create_test_novel()
        
        self.mock_novel_repo.find_by_id.return_value = novel
        self.mock_chapter_repo.find_by_novel.return_value = []
        
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "test_empty.md")
            request = ExportNovelRequest(
                novel_id="novel_001",
                output_path=output_path,
                format="markdown"
            )
            
            result = self.service.export_novel(request)
            
            assert result.chapter_count == 0
            assert result.mode == "file"
    
    def test_export_novel_creates_directory(self):
        """测试导出时创建目录"""
        novel = self.create_test_novel()
        chapters = self.create_test_chapters(novel.id)
        
        self.mock_novel_repo.find_by_id.return_value = novel
        self.mock_chapter_repo.find_by_novel.return_value = chapters
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建一个不存在的子目录路径
            output_dir = os.path.join(tmpdir, "subdir1", "subdir2")
            output_path = os.path.join(output_dir, "test_export.md")
            
            request = ExportNovelRequest(
                novel_id="novel_001",
                output_path=output_path,
                format="markdown"
            )
            
            result = self.service.export_novel(request)
            
            assert os.path.exists(output_dir)

    def test_export_relative_path_always_under_exports(self):
        novel = self.create_test_novel()
        chapters = self.create_test_chapters(novel.id)
        self.mock_novel_repo.find_by_id.return_value = novel
        self.mock_chapter_repo.find_by_novel.return_value = chapters
        request = ExportNovelRequest(
            novel_id="novel_001",
            output_path="nested/章节:一?.md",
            format="markdown"
        )
        result = self.service.export_novel(request)
        assert result.file_path.startswith("nested/")
        assert ":" not in result.file_path
        assert "?" not in result.file_path
        assert result.mode == "file"

    def test_export_word_count_uses_chapters(self):
        novel = self.create_test_novel()
        novel.current_word_count = 1
        chapters = self.create_test_chapters(novel.id)
        self.mock_novel_repo.find_by_id.return_value = novel
        self.mock_chapter_repo.find_by_novel.return_value = chapters
        request = ExportNovelRequest(
            novel_id="novel_001",
            output_path="word_count_test.md",
            format="markdown"
        )
        result = self.service.export_novel(request)
        expected = sum(chapter.word_count for chapter in chapters)
        assert result.word_count == expected

    def test_export_full_txt(self):
        novel = self.create_test_novel()
        chapters = self.create_test_chapters(novel.id)
        self.mock_novel_repo.find_by_id.return_value = novel
        self.mock_chapter_repo.find_by_novel.return_value = chapters
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "full.txt")
            request = ExportNovelRequest(
                novel_id="novel_001",
                output_path=output_path,
                format="txt",
                scope="full",
            )
            result = self.service.export_novel(request)
            assert result.mode == "file"
            assert result.format == "txt"
            assert result.file_path == output_path

    def test_export_by_chapter_markdown(self):
        novel = self.create_test_novel()
        chapters = self.create_test_chapters(novel.id)
        self.mock_novel_repo.find_by_id.return_value = novel
        self.mock_chapter_repo.find_by_novel.return_value = chapters
        request = ExportNovelRequest(
            novel_id="novel_001",
            output_path="chapter_exports",
            format="markdown",
            scope="by_chapter",
        )
        result = self.service.export_novel(request)
        assert result.mode == "directory"
        assert result.scope == "by_chapter"
        assert result.file_count == 3
        assert result.directory_path == "chapter_exports"

    def test_export_by_chapter_txt(self):
        novel = self.create_test_novel()
        chapters = self.create_test_chapters(novel.id)
        self.mock_novel_repo.find_by_id.return_value = novel
        self.mock_chapter_repo.find_by_novel.return_value = chapters
        request = ExportNovelRequest(
            novel_id="novel_001",
            output_path="chapter_txt_exports",
            format="txt",
            scope="by_chapter",
        )
        result = self.service.export_novel(request)
        assert result.mode == "directory"
        assert result.format == "txt"
        assert result.file_count == 3

    def test_export_author_fallback_unknown(self):
        novel = self.create_test_novel()
        novel.author = ""
        chapters = self.create_test_chapters(novel.id)
        self.mock_novel_repo.find_by_id.return_value = novel
        self.mock_chapter_repo.find_by_novel.return_value = chapters
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "author_fallback.txt")
            request = ExportNovelRequest(
                novel_id="novel_001",
                output_path=output_path,
                format="txt",
                scope="full",
            )
            self.service.export_novel(request)
            content = Path(output_path).read_text(encoding="utf-8")
            assert "作者：未知" in content

    def test_export_markdown_contains_author(self):
        novel = self.create_test_novel()
        novel.author = "孔利群"
        chapters = self.create_test_chapters(novel.id)
        self.mock_novel_repo.find_by_id.return_value = novel
        self.mock_chapter_repo.find_by_novel.return_value = chapters
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "author_markdown.md")
            request = ExportNovelRequest(
                novel_id="novel_001",
                output_path=output_path,
                format="markdown",
                scope="full",
            )
            self.service.export_novel(request)
            content = Path(output_path).read_text(encoding="utf-8")
            assert "**作者**: 孔利群" in content


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
