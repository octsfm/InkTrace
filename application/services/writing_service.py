"""
续写服务模块

作者：孔利群
"""

# 文件路径：application/services/writing_service.py


from datetime import datetime
from typing import List, Optional
import uuid
import re

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
        print(">>> writing_service: start writing")

        novel = self.novel_repo.find_by_id(NovelId(request.novel_id))
        if not novel:
            raise ValueError(f"小说不存在: {request.novel_id}")
        
        if not novel.outline:
            raise ValueError("小说没有大纲")
        
        llm_client = self.llm_factory.primary_client
        print(">>> client type:", type(llm_client))
        
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
        print(">>> writing_service: start writing")

        novel = self.novel_repo.find_by_id(NovelId(request.novel_id))
        if not novel:
            raise ValueError(f"小说不存在: {request.novel_id}")
        
        llm_client = self.llm_factory.primary_client
        print(">>> client type:", type(llm_client))
        
        style_profile = self._get_style_profile(novel.id.value)
        
        engine = WritingEngine(llm_client, style_profile)
        
        chapters = self.chapter_repo.find_by_novel(novel.id)
        previous_contents = [ch.content for ch in chapters[-5:]]
        
        context = WritingContext(
            novel_title=novel.title,
            outline_summary=novel.outline.premise if novel.outline else "",
            previous_chapters=previous_contents,
            plot_direction=self._normalize_direction(request.plot_direction)
        )
        
        config = WritingConfig(
            target_word_count=request.target_word_count,
            enable_style_mimicry=request.enable_style_mimicry,
            enable_consistency_check=request.enable_consistency_check
        )
        
        content = engine.generate_chapter(context, config)
        if self._is_bad_chapter(content, previous_contents):
            retry_context = WritingContext(
                novel_title=novel.title,
                outline_summary=novel.outline.premise if novel.outline else "",
                previous_chapters=previous_contents,
                plot_direction=self._normalize_direction(request.plot_direction, strict=True)
            )
            content = engine.generate_chapter(retry_context, config)
        
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

    def generate_chapter_with_direction(
        self,
        novel_id: str,
        memory: dict,
        chapters: List[str],
        direction: str,
        chapter_count: int,
        target_word_count: int
    ) -> dict:
        print(">>> writing_service: start writing")

        novel = self.novel_repo.find_by_id(NovelId(novel_id))
        if not novel:
            raise ValueError(f"小说不存在: {novel_id}")
        llm_client = self.llm_factory.primary_client
        print(">>> client type:", type(llm_client))
        style_profile = self._get_style_profile(novel.id.value)
        engine = WritingEngine(llm_client, style_profile)
        recent = [str(item or "") for item in chapters[-8:]]
        print(">>> MEMORY RAW:", memory)
        memory_text = self._memory_to_text(memory)
        print(">>> MEMORY TEXT:", memory_text)
        context = WritingContext(
            novel_title=novel.title,
            outline_summary=memory_text,
            previous_chapters=recent,
            plot_direction=self._normalize_direction(direction)
        )
        config = WritingConfig(
            target_word_count=target_word_count,
            enable_style_mimicry=True,
            enable_consistency_check=True
        )
        chapter_text = engine.generate_chapter(context, config)
        if self._is_bad_chapter(chapter_text, recent):
            chapter_text = engine.generate_chapter(
                WritingContext(
                    novel_title=novel.title,
                    outline_summary=memory_text,
                    previous_chapters=recent,
                    plot_direction=self._normalize_direction(direction, strict=True)
                ),
                config
            )
        events = self._extract_new_events(chapter_text, memory)
        return {"chapter_text": chapter_text, "new_events": events, "chapter_count": chapter_count}

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

    def _normalize_direction(self, direction: str, strict: bool = False) -> str:
        base = str(direction or "").strip()
        if strict:
            return f"{base}\n必须推进至少一个新事件，不得复述前文，不得偏离人物设定。"
        return base

    def _is_bad_chapter(self, text: str, previous_contents: List[str]) -> bool:
        content = str(text or "").strip()
        if len(content) < 120:
            return True
        filler = ["不知道为什么", "一时间", "似乎", "总之", "然后", "接着", "忽然之间"]
        filler_hits = sum(content.count(k) for k in filler)
        if filler_hits >= 8:
            return True
        history = "\n".join(previous_contents)[-1200:]
        if history:
            overlap = 0
            for i in range(0, max(len(content) - 40, 1), 40):
                seg = content[i:i + 80]
                if len(seg) >= 40 and seg in history:
                    overlap += 1
            if overlap >= 2:
                return True
        return False

    def _memory_to_text(self, memory: dict) -> str:
        characters = memory.get("characters") or []
        names = [str(item.get("name") or "").strip() for item in characters if isinstance(item, dict)]
        world_settings = str(memory.get("world_settings") or "")
        plot_outline = str(memory.get("plot_outline") or "")
        writing_style = str(memory.get("writing_style") or "")
        current_progress = str(memory.get("current_progress") or "")
        events = memory.get("events") or []
        event_text = "；".join([str(ev.get("event") or "") for ev in events if isinstance(ev, dict)])
        parts = [",".join([n for n in names if n]), world_settings, plot_outline, writing_style, current_progress, event_text]
        return "；".join([p for p in parts if p])

    def _extract_new_events(self, chapter_text: str, memory: dict) -> List[dict]:
        lead = "主角"
        characters = memory.get("characters") or []
        if characters and isinstance(characters[0], dict):
            lead = str(characters[0].get("name") or lead)
        summary = re.sub(r"\s+", " ", str(chapter_text or ""))[:120]
        return [
            {
                "event": f"{lead}在本章推进主线并触发新冲突：{summary}",
                "actors": [lead],
                "action": "推进",
                "result": "局势升级",
                "impact": "下一章必须处理升级后的冲突"
            }
        ]
