"""
向量存储值对象

作者：孔利群
"""

# 文件路径：domain/value_objects/embedding.py


from dataclasses import dataclass, field
from typing import Optional, Dict, Any


@dataclass(frozen=True)
class EmbeddingMetadata:
    """嵌入元数据值对象"""
    source_type: str
    source_id: str
    novel_id: str
    chunk_index: int = 0
    content_preview: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_type": self.source_type,
            "source_id": self.source_id,
            "novel_id": self.novel_id,
            "chunk_index": self.chunk_index,
            "content_preview": self.content_preview
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EmbeddingMetadata":
        return cls(
            source_type=data["source_type"],
            source_id=data["source_id"],
            novel_id=data["novel_id"],
            chunk_index=data.get("chunk_index", 0),
            content_preview=data.get("content_preview", "")
        )


@dataclass(frozen=True)
class SearchResult:
    """搜索结果值对象"""
# 文件：模块：embedding

    id: str
    content: str
    score: float
    metadata: EmbeddingMetadata
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "content": self.content,
            "score": self.score,
            "metadata": self.metadata.to_dict()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SearchResult":
        return cls(
            id=data["id"],
            content=data["content"],
            score=data["score"],
            metadata=EmbeddingMetadata.from_dict(data["metadata"])
        )


@dataclass(frozen=True)
class VectorStoreConfig:
    """向量存储配置值对象"""
    collection_name: str = "novel_embeddings"
    embedding_model: str = "text2vec-chinese"
    chunk_size: int = 500
    chunk_overlap: int = 50
    distance_metric: str = "cosine"
