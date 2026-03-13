"""
向量索引服务

作者：孔利群
"""

from typing import List, Optional
import uuid

from domain.repositories.vector_repository import IVectorRepository
from domain.repositories.chapter_repository import IChapterRepository
from domain.repositories.character_repository import ICharacterRepository
from domain.repositories.worldview_repository import IWorldviewRepository
from domain.value_objects.embedding import EmbeddingMetadata, VectorStoreConfig
from domain.types import NovelId, ChapterId, CharacterId


class VectorIndexService:
    """向量索引服务"""
    
    def __init__(
        self,
        vector_repo: IVectorRepository,
        chapter_repo: IChapterRepository,
        character_repo: ICharacterRepository,
        worldview_repo: IWorldviewRepository,
        config: VectorStoreConfig = None
    ):
        self.vector_repo = vector_repo
        self.chapter_repo = chapter_repo
        self.character_repo = character_repo
        self.worldview_repo = worldview_repo
        self.config = config or VectorStoreConfig()
    
    def index_novel(self, novel_id: NovelId) -> dict:
        """索引小说内容"""
        stats = {
            "chapters_indexed": 0,
            "characters_indexed": 0,
            "worldview_indexed": 0,
            "errors": []
        }
        
        stats["chapters_indexed"] = self._index_chapters(novel_id)
        stats["characters_indexed"] = self._index_characters(novel_id)
        stats["worldview_indexed"] = self._index_worldview(novel_id)
        
        return stats
    
    def _index_chapters(self, novel_id: NovelId) -> int:
        """索引章节"""
        chapters = self.chapter_repo.find_by_novel(novel_id)
        if not chapters:
            return 0
        
        contents = []
        metadatas = []
        
        for chapter in chapters:
            content_chunks = self._chunk_content(chapter.content)
            for i, chunk in enumerate(content_chunks):
                contents.append(chunk)
                metadatas.append(EmbeddingMetadata(
                    source_type="chapter",
                    source_id=str(chapter.id),
                    novel_id=str(novel_id),
                    chunk_index=i,
                    content_preview=chunk[:100]
                ))
        
        if contents:
            self.vector_repo.add_vectors(contents, metadatas)
        
        return len(contents)
    
    def _index_characters(self, novel_id: NovelId) -> int:
        """索引人物"""
        characters = self.character_repo.find_by_novel(novel_id)
        if not characters:
            return 0
        
        contents = []
        metadatas = []
        
        for character in characters:
            content = self._build_character_content(character)
            contents.append(content)
            metadatas.append(EmbeddingMetadata(
                source_type="character",
                source_id=str(character.id),
                novel_id=str(novel_id),
                content_preview=content[:100]
            ))
        
        if contents:
            self.vector_repo.add_vectors(contents, metadatas)
        
        return len(contents)
    
    def _index_worldview(self, novel_id: NovelId) -> int:
        """索引世界观"""
        count = 0
        
        techniques = self.worldview_repo.find_techniques_by_novel(novel_id)
        for tech in techniques:
            content = f"功法：{tech.name}\\n描述：{tech.description}\\n效果：{tech.effect}"
            self.vector_repo.add_vectors(
                [content],
                [EmbeddingMetadata(
                    source_type="worldview",
                    source_id=str(tech.id),
                    novel_id=str(novel_id),
                    content_preview=content[:100]
                )]
            )
            count += 1
        
        factions = self.worldview_repo.find_factions_by_novel(novel_id)
        for faction in factions:
            content = f"势力：{faction.name}\\n描述：{faction.description}\\n地盘：{faction.territory}"
            self.vector_repo.add_vectors(
                [content],
                [EmbeddingMetadata(
                    source_type="worldview",
                    source_id=str(faction.id),
                    novel_id=str(novel_id),
                    content_preview=content[:100]
                )]
            )
            count += 1
        
        locations = self.worldview_repo.find_locations_by_novel(novel_id)
        for location in locations:
            content = f"地点：{location.name}\\n描述：{location.description}"
            self.vector_repo.add_vectors(
                [content],
                [EmbeddingMetadata(
                    source_type="worldview",
                    source_id=str(location.id),
                    novel_id=str(novel_id),
                    content_preview=content[:100]
                )]
            )
            count += 1
        
        return count
    
    def _chunk_content(self, content: str) -> List[str]:
        """内容分块"""
        if not content:
            return []
        
        chunk_size = self.config.chunk_size
        overlap = self.config.chunk_overlap
        
        if len(content) <= chunk_size:
            return [content]
        
        chunks = []
        start = 0
        
        while start < len(content):
            end = start + chunk_size
            chunks.append(content[start:end])
            start = end - overlap
        
        return chunks
    
    def _build_character_content(self, character) -> str:
        """构建人物内容"""
        parts = [f"人物：{character.name}"]
        
        if character.background:
            parts.append(f"背景：{character.background}")
        if character.personality:
            parts.append(f"性格：{character.personality}")
        if character.appearance:
            parts.append(f"外貌：{character.appearance}")
        if character.abilities:
            parts.append(f"能力：{', '.join(character.abilities)}")
        
        return "\\n".join(parts)
    
    def delete_novel_index(self, novel_id: NovelId) -> int:
        """删除小说索引"""
        return self.vector_repo.delete_by_novel(novel_id)
    
    def get_index_status(self, novel_id: NovelId) -> dict:
        """获取索引状态"""
        return {
            "total_vectors": self.vector_repo.count(novel_id),
            "chapters_count": self.vector_repo.count(novel_id),
            "is_indexed": self.vector_repo.count(novel_id) > 0
        }
