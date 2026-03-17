"""
续写服务模块

作者：孔利群
"""

# 文件路径：application/services/writing_service.py


from datetime import datetime
from typing import List, Optional
import uuid

from domain.entities.novel import Novel
from domain.entities.chapter import Chapter
from domain.types import NovelId, ChapterId, ChapterStatus
from domain.repositories.novel_repository import INovelRepository
from domain.repositories.chapter_repository import IChapterRepository
from domain.services.writing_engine import WritingEngine, WritingContext
from domain.services.consistency_checker import ConsistencyChecker
from domain.value_objects.style_profile import StyleProfile
from domain.value_objects.writing_config import WritingConfig
from application.dto.request_dto import GenerateChapterRequest, PlanPlotRequest
from application.dto.response_dto import GenerateChapterResponse, ConsistencyCheckResponse


from infrastructure.llm.llm_factory import LLMFactory, LLMConfig


class WritingService:
    """
    续写服务
    
    负责剧情规划、章节生成、连贯性检查。
    """

    def __init__(
        self,
        novel_repo: INovelRepository,
        chapter_repo: IChapterRepository,
        llm_factory: LLMFactory
    ):
        self.novel_repo = novel_repo
        self.chapter_repo = chapter_repo
        self.llm_factory = llm_factory
        self.consistency_checker = ConsistencyChecker()

        self._style_profiles: dict = {}

    def plan_plot(self, request: PlanPlotRequest) -> List[dict]:
        """
        规划剧情
        
        Args:
            request: 规划请求
            
        Returns:
            剧情节点列表
        """
# 文件：模块：writing_service

        novel = self.novel_repo.find_by_id(NovelId(request.novel_id))
        if not novel:
            raise ValueError(f"小说不存在: {request.novel_id}")
        
        if not novel.outline:
            raise ValueError("小说没有大纲")
        
        llm_client = self.llm_factory.primary_client
        
        
        engine = WritingEngine(llm_client, self._get_style_profile(novel.id.value))
        
        plot_nodes = engine.plan_plot(
            novel.outline,
            request.chapter_count,
            request.direction
        )
        
        return [
            {
                'id': node.id,
                'title': node.title,
                'description': node.description,
                'type': node.type.value,
                'status': node.status.value
            }
            for node in plot_nodes
        ]

    def generate_chapter(self, request: GenerateChapterRequest) -> GenerateChapterResponse:
        """
        生成章节
        
        Args:
            request: 生成请求
            
        Returns:
            生成响应
        """
# 文件：模块：writing_service

        novel = self.novel_repo.find_by_id(NovelId(request.novel_id))
        if not novel:
            raise ValueError(f"小说不存在: {request.novel_id}")
        
        llm_client = self.llm_factory.primary_client
        
        
        style_profile = self._get_style_profile(novel.id.value)
        
        engine = WritingEngine(llm_client, style_profile)
        
        chapters = self.chapter_repo.find_by_novel(novel.id)
        previous_contents = [ch.content for ch in chapters[-5:]]
        
        context = WritingContext(
            novel_title=novel.title,
            outline_summary=novel.outline.premise if novel.outline else "",
            previous_chapters=previous_contents,
            plot_direction=request.plot_direction
        )
        
        config = WritingConfig(
            target_word_count=request.target_word_count,
            enable_style_mimicry=request.enable_style_mimicry,
            enable_consistency_check=request.enable_consistency_check
        )
        
        content = engine.generate_chapter(context, config)
        
        now = datetime.now()
        chapter = Chapter(
            id=ChapterId(str(uuid.uuid4())),
            novel_id=novel.id,
            number=novel.chapter_count + 1,
            title=f"第{novel.chapter_count + 1}章",
            content=content,
            status=ChapterStatus.DRAFT,
            created_at=now,
            updated_at=now
        )
        
        consistency_report = None
        if request.enable_consistency_check:
            report = self.consistency_checker.check(chapter, chapters)
            consistency_report = ConsistencyCheckResponse(
                is_valid=report.is_valid,
                inconsistencies=[
                    {
                        'type': inc.type,
                        'description': inc.description,
                        'severity': inc.severity
                    }
                    for inc in report.inconsistencies
                ],
                warnings=report.warnings
            )
        
        return GenerateChapterResponse(
            chapter_id=chapter.id.value,
            content=content,
            word_count=chapter.word_count,
            consistency_report=consistency_report
        )

    def _get_style_profile(self, novel_id: str) -> StyleProfile:
        """获取或创建文风特征"""
        if novel_id not in self._style_profiles:
            self._style_profiles[novel_id] = StyleProfile(
                vocabulary_stats={},
                sentence_patterns=[],
                rhetoric_stats={},
                dialogue_style="",
                narrative_voice="",
                pacing="",
                sample_sentences=[]
            )
        return self._style_profiles[novel_id]
