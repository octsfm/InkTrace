"""
内容管理服务模块

作者：孔利群
"""

import os
from datetime import datetime
from typing import List, Optional
import uuid

from domain.entities.novel import Novel
from domain.entities.chapter import Chapter
from domain.types import NovelId, ChapterId, ChapterStatus
from domain.repositories.novel_repository import INovelRepository
from domain.repositories.chapter_repository import IChapterRepository
from domain.repositories.character_repository import ICharacterRepository
from domain.repositories.outline_repository import IOutlineRepository
from domain.services.style_analyzer import StyleAnalyzer
from domain.services.plot_analyzer import PlotAnalyzer
from infrastructure.file.txt_parser import TxtParser
from application.dto.request_dto import ImportNovelRequest
from application.dto.response_dto import NovelResponse, StyleAnalysisResponse, PlotAnalysisResponse


class ContentService:
    """
    内容管理服务
    
    负责内容导入、解析、分析。
    """

    def __init__(
        self,
        novel_repo: INovelRepository,
        chapter_repo: IChapterRepository,
        character_repo: ICharacterRepository,
        outline_repo: IOutlineRepository,
        txt_parser: TxtParser
    ):
        self.novel_repo = novel_repo
        self.chapter_repo = chapter_repo
        self.character_repo = character_repo
        self.outline_repo = outline_repo
        self.txt_parser = txt_parser
        self.style_analyzer = StyleAnalyzer()
        self.plot_analyzer = PlotAnalyzer()

    def import_novel(self, request: ImportNovelRequest) -> NovelResponse:
        """
        导入小说
        
        Args:
            request: 导入请求
            
        Returns:
            小说响应
        """
        novel = self.novel_repo.find_by_id(NovelId(request.novel_id))
        if not novel:
            raise ValueError(f"小说不存在: {request.novel_id}")
        
        if not os.path.exists(request.file_path):
            raise FileNotFoundError(f"文件不存在: {request.file_path}")
        
        parsed = self.txt_parser.parse_novel_file(request.file_path)
        
        now = datetime.now()
        
        for chapter_data in parsed.get('chapters', []):
            chapter = Chapter(
                id=ChapterId(str(uuid.uuid4())),
                novel_id=novel.id,
                number=chapter_data['number'],
                title=chapter_data['title'],
                content=chapter_data['content'],
                status=ChapterStatus.DRAFT,
                created_at=now,
                updated_at=now
            )
            self.chapter_repo.save(chapter)
            novel.add_chapter(chapter, now)
        
        self.novel_repo.save(novel)
        
        return self._nov_to_response(novel)

    def analyze_style(self, novel_id: str) -> StyleAnalysisResponse:
        """
        分析文风
        
        Args:
            novel_id: 小说ID
            
        Returns:
            文风分析响应
        """
        novel = self.novel_repo.find_by_id(NovelId(novel_id))
        if not novel:
            raise ValueError(f"小说不存在: {novel_id}")
        
        chapters = self.chapter_repo.find_by_novel(novel.id)
        
        profile = self.style_analyzer.analyze(chapters)
        
        return StyleAnalysisResponse(
            vocabulary_stats=profile.vocabulary_stats,
            sentence_patterns=profile.sentence_patterns,
            rhetoric_stats=profile.rhetoric_stats,
            dialogue_style=profile.dialogue_style,
            narrative_voice=profile.narrative_voice,
            pacing=profile.pacing,
            sample_sentences=profile.sample_sentences
        )

    def analyze_plot(self, novel_id: str) -> PlotAnalysisResponse:
        """
        分析剧情
        
        Args:
            novel_id: 小说ID
            
        Returns:
            剧情分析响应
        """
        novel = self.novel_repo.find_by_id(NovelId(novel_id))
        if not novel:
            raise ValueError(f"小说不存在: {novel_id}")
        
        chapters = self.chapter_repo.find_by_novel(novel.id)
        
        analysis = self.plot_analyzer.analyze(chapters)
        
        return PlotAnalysisResponse(
            characters=analysis['characters'],
            timeline=analysis['timeline'],
            foreshadowings=analysis['foreshadowings']
        )

    def _nov_to_response(self, novel: Novel) -> NovelResponse:
        """将小说实体转换为响应"""
        return NovelResponse(
            id=novel.id.value,
            title=novel.title,
            author=novel.author,
            genre=novel.genre,
            target_word_count=novel.target_word_count,
            current_word_count=novel.current_word_count,
            chapter_count=novel.chapter_count,
            created_at=novel.created_at.isoformat(),
            updated_at=novel.updated_at.isoformat()
        )
