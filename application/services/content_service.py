"""
内容管理服务模块

作者：孔利群
"""

# 文件路径：application/services/content_service.py


import os
import hashlib
from datetime import datetime
from typing import List, Optional
import uuid

from application.services.logging_service import build_log_context, get_logger
from domain.entities.novel import Novel
from domain.entities.chapter import Chapter
from domain.entities.outline import Outline
from domain.types import NovelId, ChapterId, ChapterStatus, OutlineId
from domain.repositories.novel_repository import INovelRepository
from domain.repositories.chapter_repository import IChapterRepository
from domain.repositories.character_repository import ICharacterRepository
from domain.repositories.outline_repository import IOutlineRepository
from domain.repositories.outline_document_repository import IOutlineDocumentRepository
from domain.services.style_analyzer import StyleAnalyzer
from domain.services.plot_analyzer import PlotAnalyzer
from infrastructure.file.txt_parser import TxtParser
from application.dto.request_dto import ImportNovelRequest
from application.dto.response_dto import NovelResponse, StyleAnalysisResponse, PlotAnalysisResponse
from application.services.outline_digest_service import OutlineDigestService


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
        txt_parser: TxtParser,
        outline_document_repo: Optional[IOutlineDocumentRepository] = None,
        outline_digest_service: Optional[OutlineDigestService] = None,
    ):
        self.novel_repo = novel_repo
        self.chapter_repo = chapter_repo
        self.character_repo = character_repo
        self.outline_repo = outline_repo
        self.txt_parser = txt_parser
        self.outline_document_repo = outline_document_repo
        self.outline_digest_service = outline_digest_service or OutlineDigestService()
        self.style_analyzer = StyleAnalyzer()
        self.plot_analyzer = PlotAnalyzer()
        self.logger = get_logger(__name__)

    def import_novel(self, request: ImportNovelRequest) -> NovelResponse:
        """
        导入小说
        
        Args:
            request: 导入请求
            
        Returns:
            小说响应
        """
# 文件：模块：content_service

        novel = self.novel_repo.find_by_id(NovelId(request.novel_id))
        if not novel:
            self.logger.error(
                "import failed: novel not found",
                extra=build_log_context(event="import_failed", novel_id=request.novel_id, error="novel_not_found"),
            )
            raise ValueError(f"小说不存在: {request.novel_id}")
        incoming_author = str(getattr(request, "author", "") or "").strip()
        if incoming_author and (not str(novel.author or "").strip() or str(novel.author).strip() == "未知"):
            novel.author = incoming_author
        
        import_mode = str(getattr(request, "import_mode", "full") or "full")
        if import_mode not in {"full", "empty", "chapter_items"}:
            import_mode = "full"
        self.logger.info(
            "import started",
            extra=build_log_context(
                event="import_started",
                novel_id=request.novel_id,
                author=incoming_author,
                import_mode=import_mode,
                file_path=request.file_path,
                outline_present=bool(request.outline_path),
            ),
        )
        chapter_items = getattr(request, "chapter_items", None) or []
        parsed = {"chapters": []}
        if import_mode == "chapter_items" and chapter_items:
            rebuilt = self.txt_parser.rebuild_chapters_from_preview(chapter_items)
            if isinstance(rebuilt, dict):
                chapters = rebuilt.get("chapters")
                parsed = rebuilt if isinstance(chapters, list) else {"chapters": []}
            elif isinstance(rebuilt, list):
                parsed = {"chapters": rebuilt}
            else:
                parsed = {"chapters": []}
            if not parsed.get("chapters"):
                parsed["chapters"] = [
                    {
                        "number": int(item.get("number") or index),
                        "title": str(item.get("title") or f"第{index}章"),
                        "content": str(item.get("content") or "").strip(),
                        "word_count": len(str(item.get("content") or "").strip()),
                    }
                    for index, item in enumerate(chapter_items, 1)
                    if isinstance(item, dict) and str(item.get("content") or "").strip()
                ]
        elif import_mode == "empty":
            parsed["chapters"] = []
        else:
            if not os.path.exists(request.file_path):
                self.logger.error(
                    "import failed: source file not found",
                    extra=build_log_context(event="import_failed", novel_id=request.novel_id, file_path=request.file_path, error="file_not_found"),
                )
                raise FileNotFoundError(f"文件不存在: {request.file_path}")
            parsed = self.txt_parser.parse_novel_file(request.file_path)
        self.logger.info(
            "import parse finished",
            extra=build_log_context(
                event="import_parsed",
                novel_id=request.novel_id,
                import_mode=import_mode,
                chapter_count=len(parsed.get("chapters") or []),
                outline_present=bool(request.outline_path),
                file_path=request.file_path,
            ),
        )
        
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
        if request.outline_path and os.path.exists(request.outline_path):
            try:
                outline_text = self.txt_parser.parse_outline_file(request.outline_path)
            except Exception as exc:
                self.logger.error(
                    "import failed: outline parse error",
                    extra=build_log_context(
                        event="import_failed",
                        novel_id=request.novel_id,
                        file_path=request.outline_path,
                        error=str(exc),
                    ),
                )
                raise
            self.logger.info(
                "import outline loaded",
                extra=build_log_context(
                    event="import_outline_loaded",
                    novel_id=request.novel_id,
                    outline_present=True,
                    file_path=request.outline_path,
                ),
            )
            raw_outline_text = str(outline_text.get("raw_content") or "") if isinstance(outline_text, dict) else str(outline_text or "")
            digest = self.outline_digest_service.build_digest(raw_outline_text)
            if isinstance(outline_text, dict):
                premise = str(digest.get("premise") or outline_text.get("raw_content") or "")[:1200]
                story_background = str(digest.get("summary") or outline_text.get("story_background") or outline_text.get("raw_content") or "")[:2400]
                world_setting = str(digest.get("style_guidance") or outline_text.get("world_setting") or outline_text.get("story_background") or "")[:2400]
            else:
                premise = str(digest.get("premise") or raw_outline_text)[:1200]
                story_background = str(digest.get("summary") or raw_outline_text)[:2400]
                world_setting = str(digest.get("style_guidance") or raw_outline_text)[:2400]
            outline = Outline(
                id=OutlineId(str(uuid.uuid4())),
                novel_id=novel.id,
                premise=premise,
                story_background=story_background,
                world_setting=world_setting,
                created_at=now,
                updated_at=now
            )
            self.outline_repo.save(outline)
            if self.outline_document_repo is not None:
                self.outline_document_repo.save_document(
                    novel_id=str(novel.id.value),
                    raw_content=raw_outline_text,
                    digest_json=digest,
                    raw_hash=hashlib.sha256(raw_outline_text.encode("utf-8")).hexdigest(),
                    digest_version=getattr(self.outline_digest_service, "digest_version", "v1"),
                )
            novel.set_outline(outline, now)
            self.novel_repo.save(novel)
        self.logger.info(
            "import save finished",
            extra=build_log_context(
                event="import_saved",
                novel_id=request.novel_id,
                chapter_count=len(parsed.get("chapters") or []),
                import_mode=import_mode,
                outline_present=bool(request.outline_path and os.path.exists(request.outline_path)),
            ),
        )
        
        return self._nov_to_response(novel)

    def analyze_style(self, novel_id: str) -> StyleAnalysisResponse:
        """
        分析文风
        
        Args:
            novel_id: 小说ID
            
        Returns:
            文风分析响应
        """
# 文件：模块：content_service

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
# 文件：模块：content_service

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

    def get_novel_text(self, novel_id: str) -> str:
        novel = self.novel_repo.find_by_id(NovelId(novel_id))
        if not novel:
            raise ValueError(f"小说不存在: {novel_id}")
        chapters = self.chapter_repo.find_by_novel(novel.id)
        text = "\n\n".join([chapter.content for chapter in chapters if chapter.content])
        self.logger.info(
            "[ContentService] novel text loaded novel_id=%s chapters=%d text_length=%d",
            novel_id,
            len(chapters),
            len(text)
        )
        return text

    def get_outline_context(self, novel_id: str) -> dict:
        novel = self.novel_repo.find_by_id(NovelId(novel_id))
        if not novel:
            raise ValueError(f"小说不存在: {novel_id}")
        if self.outline_document_repo is not None:
            stored = self.outline_document_repo.find_by_novel_id(str(novel.id.value))
            if isinstance(stored, dict):
                digest = stored.get("digest_json") if isinstance(stored.get("digest_json"), dict) else {}
                if digest:
                    return {
                        "premise": str(digest.get("premise") or ""),
                        "story_background": str(digest.get("summary") or ""),
                        "world_setting": str(digest.get("style_guidance") or ""),
                        "summary": [str(x).strip() for x in (digest.get("main_plot_lines") or []) if str(x).strip()][:8],
                        "outline_digest": digest,
                    }
        outline = self.outline_repo.find_by_novel(novel.id)
        if not outline:
            return {}
        if self.outline_document_repo is not None:
            raw_fallback = "\n".join([str(outline.premise or ""), str(outline.story_background or ""), str(outline.world_setting or "")]).strip()
            if raw_fallback:
                digest = self.outline_digest_service.build_digest(raw_fallback)
                self.outline_document_repo.save_document(
                    novel_id=str(novel.id.value),
                    raw_content=raw_fallback,
                    digest_json=digest,
                    raw_hash=hashlib.sha256(raw_fallback.encode("utf-8")).hexdigest(),
                    digest_version=getattr(self.outline_digest_service, "digest_version", "v1"),
                )
                return {
                    "premise": str(digest.get("premise") or outline.premise or ""),
                    "story_background": str(digest.get("summary") or outline.story_background or ""),
                    "world_setting": str(digest.get("style_guidance") or outline.world_setting or ""),
                    "summary": [str(x).strip() for x in (digest.get("main_plot_lines") or []) if str(x).strip()][:8],
                    "outline_digest": digest,
                }
        summary = [outline.premise, outline.story_background, outline.world_setting]
        summary = [str(x) for x in summary if str(x).strip()]
        return {
            "premise": outline.premise or "",
            "story_background": outline.story_background or "",
            "world_setting": outline.world_setting or "",
            "summary": summary[:5],
        }

    def _nov_to_response(self, novel: Novel) -> NovelResponse:
        """将小说实体转换为响应"""
        return NovelResponse(
            id=novel.id.value,
            title=novel.title,
            author=novel.author,
            genre=novel.genre,
            word_count=novel.current_word_count,
            target_word_count=novel.target_word_count,
            current_word_count=novel.current_word_count,
            chapter_count=novel.chapter_count,
            status="active",
            created_at=novel.created_at.isoformat(),
            updated_at=novel.updated_at.isoformat()
        )
