"""
RAG上下文组装器

作者：孔利群
"""

# 文件路径：domain/services/rag_context_builder.py


from dataclasses import dataclass, field
from typing import List, Optional

from domain.value_objects.embedding import SearchResult


@dataclass
class RAGContext:
    """RAG上下文值对象"""
    query: str
    related_chapters: List[SearchResult] = field(default_factory=list)
    related_characters: List[SearchResult] = field(default_factory=list)
    related_worldview: List[SearchResult] = field(default_factory=list)
    foreshadows: List[SearchResult] = field(default_factory=list)
    total_tokens: int = 0
    max_context_tokens: int = 8000
    
    def to_prompt(self) -> str:
        """将上下文转换为Prompt格式"""
# 文件：模块：rag_context_builder

        sections = []
        
        if self.related_chapters:
            chapter_texts = "\n".join([
                f"【相关章节】{r.content[:500]}..."
                for r in self.related_chapters[:3]
            ])
            sections.append(f"相关章节内容：\n{chapter_texts}")
        
        if self.related_characters:
            char_texts = "\n".join([
                f"- {r.metadata.source_id}: {r.content[:200]}"
                for r in self.related_characters[:3]
            ])
            sections.append(f"人物设定：\n{char_texts}")
        
        if self.related_worldview:
            world_texts = "\n".join([
                f"- {r.metadata.source_id}: {r.content[:200]}"
                for r in self.related_worldview[:3]
            ])
            sections.append(f"世界观设定：\n{world_texts}")
        
        if self.foreshadows:
            foreshadow_texts = "\n".join([
                f"- {r.content}"
                for r in self.foreshadows
            ])
            sections.append(f"待回收伏笔：\n{foreshadow_texts}")
        
        context = "\n\n".join(sections)
        return context
    
    def estimate_tokens(self, text: str) -> int:
        """估算文本Token数（中文约1.5字/token）"""
        return int(len(text) * 1.5)


class RAGContextBuilder:
    """RAG上下文构建器"""
    
    def __init__(self, max_context_tokens: int = 8000):
        self.max_context_tokens = max_context_tokens
    
    def build(
        self,
        query: str,
        chapter_results: List[SearchResult],
        character_results: List[SearchResult],
        worldview_results: List[SearchResult],
        foreshadow_results: List[SearchResult] = None
    ) -> RAGContext:
        """构建RAG上下文"""
        context = RAGContext(
            query=query,
            related_chapters=chapter_results,
            related_characters=character_results,
            related_worldview=worldview_results,
            foreshadows=foreshadow_results,
            max_context_tokens=self.max_context_tokens
        )
        
        while context.total_tokens > self.max_context_tokens:
            context = self._trim_context(context)
        
        return context
    
    def _trim_context(self, context: RAGContext) -> RAGContext:
        """裁剪上下文以适应Token限制"""
# 文件：模块：rag_context_builder

        while context.total_tokens > self.max_context_tokens:
            if context.foreshadows:
                context.foreshadows = context.foreshadows[:-1]
            elif context.related_worldview:
                context.related_worldview = context.related_worldview[:-1]
            elif context.related_characters:
                context.related_characters = context.related_characters[:-1]
            elif context.related_chapters:
                context.related_chapters = context.related_chapters[:-1]
            else:
                break
            
            context.total_tokens = self._calculate_total_tokens(context)
        
        return context
    
    def _calculate_total_tokens(self, context: RAGContext) -> int:
        """计算总Token数"""
        total = 0
        total += sum(context.estimate_tokens(r.content) for r in context.related_chapters)
        total += sum(context.estimate_tokens(r.content) for r in context.related_characters)
        total += sum(context.estimate_tokens(r.content) for r in context.related_worldview)
        total += sum(context.estimate_tokens(r.content) for r in context.foreshadows)
        return int(total)
