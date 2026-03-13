"""
RAG检索服务

作者：孔利群
"""

from typing import List, Optional
import uuid

from domain.repositories.vector_repository import IVectorRepository
from domain.repositories.chapter_repository import IChapterRepository
from domain.repositories.character_repository import ICharacterRepository
from domain.value_objects.embedding import SearchResult, EmbeddingMetadata
from domain.types import NovelId


class RAGRetrievalService:
    """RAG检索服务"""
    
    def __init__(
        self,
        vector_repo: IVectorRepository,
        chapter_repo: IChapterRepository,
        character_repo: ICharacterRepository
    ):
        self.vector_repo = vector_repo
        self.chapter_repo = chapter_repo
        self.character_repo = character_repo
    
    def search_relevant_content(
        self,
        novel_id: NovelId,
        query: str,
        n_results: int = 5
    ) -> List[SearchResult]:
        """搜索相关内容"""
        return self.vector_repo.search(
            query=query,
            novel_id=novel_id,
            n_results=n_results
        )
    
    def search_relevant_chapters(
        self,
        novel_id: NovelId,
        query: str,
        n_results: int = 3
    ) -> List[SearchResult]:
        """搜索相关章节"""
        return self.vector_repo.search(
            query=query,
            novel_id=novel_id,
            source_type="chapter",
            n_results=n_results
        )
    
    def search_relevant_characters(
        self,
        novel_id: NovelId,
        query: str,
        n_results: int = 3
    ) -> List[SearchResult]:
        """搜索相关人物"""
        return self.vector_repo.search(
            query=query,
            novel_id=novel_id,
            source_type="character",
            n_results=n_results
        )
    
    def search_relevant_worldview(
        self,
        novel_id: NovelId,
        query: str,
        n_results: int = 3
    ) -> List[SearchResult]:
        """搜索相关世界观"""
        return self.vector_repo.search(
            query=query,
            novel_id=novel_id,
            source_type="worldview",
            n_results=n_results
        )
    
    def get_context_for_writing(
        self,
        novel_id: NovelId,
        writing_prompt: str,
        max_chapters: int = 3,
        max_characters: int = 2,
        max_worldview: int = 2
    ) -> dict:
        """获取续写上下文"""
        context = {
            "chapters": [],
            "characters": [],
            "worldview": []
        }
        
        context["chapters"] = self.search_relevant_chapters(
            novel_id, writing_prompt, max_chapters
        )
        
        context["characters"] = self.search_relevant_characters(
            novel_id, writing_prompt, max_characters
        )
        
        context["worldview"] = self.search_relevant_worldview(
            novel_id, writing_prompt, max_worldview
        )
        
        return context
    
    def build_rag_prompt(
        self,
        novel_id: NovelId,
        user_request: str,
        max_tokens: int = 8000
    ) -> str:
        """构建RAG Prompt"""
        context = self.get_context_for_writing(novel_id, user_request)
        
        prompt_parts = []
        prompt_parts.append("以下是相关上下文信息，请参考这些信息进行创作：\\n")
        
        if context["chapters"]:
            prompt_parts.append("\\n【相关章节】")
            for i, result in enumerate(context["chapters"][:3]):
                preview = result.content[:500] if len(result.content) > 500 else result.content
                prompt_parts.append(f"\\n章节片段{i+1}（相似度: {result.score:.2f}）：\\n{preview}")
        
        if context["characters"]:
            prompt_parts.append("\\n【相关人物】")
            for result in context["characters"][:2]:
                prompt_parts.append(f"\\n{result.content[:300]}")
        
        if context["worldview"]:
            prompt_parts.append("\\n【相关世界观】")
            for result in context["worldview"][:2]:
                prompt_parts.append(f"\\n{result.content[:200]}")
        
        prompt_parts.append(f"\\n\\n【创作要求】\\n{user_request}")
        
        full_prompt = "\\n".join(prompt_parts)
        
        return full_prompt
