"""
导出服务模块

作者：孔利群
"""

# 文件路径：application/services/export_service.py


import os
from typing import List

from domain.entities.novel import Novel
from domain.entities.chapter import Chapter
from domain.types import NovelId
from domain.repositories.novel_repository import INovelRepository
from domain.repositories.chapter_repository import IChapterRepository
from infrastructure.file.markdown_exporter import MarkdownExporter
from application.dto.request_dto import ExportNovelRequest
from application.dto.response_dto import ExportResponse


class ExportService:
    """
    导出服务
    
    负责小说和章节的导出。
    """

    def __init__(
        self,
        novel_repo: INovelRepository,
        chapter_repo: IChapterRepository
    ):
        self.novel_repo = novel_repo
        self.chapter_repo = chapter_repo
        self.markdown_exporter = MarkdownExporter()

    def export_novel(self, request: ExportNovelRequest) -> ExportResponse:
        """
        导出小说
        
        Args:
            request: 导出请求
            
        Returns:
            导出响应
        """
# 文件：模块：export_service

        novel = self.novel_repo.find_by_id(NovelId(request.novel_id))
        if not novel:
            raise ValueError(f"小说不存在: {request.novel_id}")
        
        chapters = self.chapter_repo.find_by_novel(novel.id)
        
        os.makedirs(os.path.dirname(request.output_path), exist_ok=True)
        
        if request.format == "markdown":
            self.markdown_exporter.export_novel(novel, chapters, request.output_path)
        else:
            raise ValueError(f"不支持的导出格式: {request.format}")
        
        return ExportResponse(
            file_path=request.output_path,
            format=request.format,
            word_count=novel.current_word_count,
            chapter_count=len(chapters)
        )
