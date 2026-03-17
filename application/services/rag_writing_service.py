"""
RAG续写服务

作者：孔利群
"""

# 文件路径：application/services/rag_writing_service.py


from typing import Optional

from domain.repositories.vector_repository import IVectorRepository
from domain.repositories.chapter_repository import IChapterRepository
from domain.repositories.novel_repository import INovelRepository
from domain.services.rag_context_builder import RAGContextBuilder
from application.services.rag_retrieval_service import RAGRetrievalService
from infrastructure.llm.llm_factory import LLMFactory
from domain.types import NovelId, ChapterId
from domain.entities.chapter import Chapter, ChapterStatus

from datetime import datetime
import uuid


class RAGWritingService:
    """RAG续写服务"""
    
    def __init__(
        self,
        vector_repo: IVectorRepository,
        chapter_repo: IChapterRepository,
        novel_repo: INovelRepository,
        rag_retrieval: RAGRetrievalService,
        llm_factory: LLMFactory
    ):
        self.vector_repo = vector_repo
        self.chapter_repo = chapter_repo
        self.novel_repo = novel_repo
        self.rag_retrieval = rag_retrieval
        self.llm_factory = llm_factory
    
    def write_chapter(
        self,
        novel_id: NovelId,
        prompt: str,
        target_words: int = 2100
    ) -> Chapter:
        """使用RAG增强续写章节"""
# 文件：模块：rag_writing_service

        novel = self.novel_repo.find_by_id(novel_id)
        if not novel:
            raise ValueError(f"小说不存在: {novel_id}")
        
        last_chapter = self._get_last_chapter(novel_id)
        
        rag_context = self.rag_retrieval.get_context_for_writing(
            novel_id=novel_id,
            writing_prompt=prompt
        )
        
        full_prompt = self._build_writing_prompt(
            novel=novel,
            last_chapter=last_chapter,
            rag_context=rag_context,
            user_prompt=prompt,
            target_words=target_words
        )
        
        llm_client = self.llm_factory.get_primary_client()
        new_content = llm_client.generate(full_prompt, max_tokens=target_words * 2)
        
        now = datetime.now()
        chapter = Chapter(
            id=ChapterId(str(uuid.uuid4())),
            novel_id=novel_id,
            number=(last_chapter.number + 1) if last_chapter else 1,
            title=f"第{(last_chapter.number + 1) if last_chapter else 1}章",
            content=new_content,
            word_count=len(new_content),
            status=ChapterStatus.DRAFT,
            created_at=now,
            updated_at=now
        )
        
        self.chapter_repo.save(chapter)
        
        return chapter
    
    def _get_last_chapter(self, novel_id: NovelId) -> Optional[Chapter]:
        """获取最后一章"""
        chapters = self.chapter_repo.find_by_novel(novel_id)
        if not chapters:
            return None
        return max(chapters, key=lambda c: c.number)
    
    def _build_writing_prompt(
        self,
        novel,
        last_chapter: Optional[Chapter],
        rag_context: dict,
        user_prompt: str,
        target_words: int
    ) -> str:
        """构建续写Prompt"""
# 文件：模块：rag_writing_service

        parts = []
        
        parts.append(f"你是一位专业的小说作家，请根据以下信息续写小说章节。\n")
        parts.append(f"小说标题：{novel.title}\n")
        
        if last_chapter:
            parts.append(f"\n上一章内容（第{last_chapter.number}章）：\n{last_chapter.content[:1000]}...\n")
        
        if rag_context:
            context_str = self._format_context(rag_context)
            if context_str:
                parts.append(f"\n相关背景信息：\n{context_str}\n")
        
        parts.append(f"\n续写要求：\n{user_prompt}\n")
        parts.append(f"\n请续写约{target_words}字的新章节内容：\n")
        
        return "\n".join(parts)
    
    def _format_context(self, rag_context: dict) -> str:
        """格式化RAG上下文"""
        parts = []
        
        if rag_context.get("chapters"):
            parts.append("【相关章节】")
            for result in rag_context["chapters"][:3]:
                parts.append(f"- {result.content[:200]}...")
        
        if rag_context.get("characters"):
            parts.append("\n【相关人物】")
            for result in rag_context["characters"][:2]:
                parts.append(f"- {result.content[:150]}")
        
        if rag_context.get("worldview"):
            parts.append("\n【相关世界观】")
            for result in rag_context["worldview"][:2]:
                parts.append(f"- {result.content[:100]}")
        
        return "\n".join(parts)
