"""
向量仓储接口

作者：孔利群
"""

# 文件路径：domain/repositories/vector_repository.py


from abc import ABC, abstractmethod
from typing import Optional, List

from domain.value_objects.embedding import EmbeddingMetadata, SearchResult, VectorStoreConfig
from domain.types import NovelId


class IVectorRepository(ABC):
    """向量仓储接口"""
    
    @abstractmethod
    def add_vectors(
        self,
        contents: List[str],
        metadata_list: List[EmbeddingMetadata],
        ids: Optional[List[str]] = None
    ) -> List[str]:
        """添加向量"""
# 文件：模块：vector_repository

        pass
    
    @abstractmethod
    def search(
        self,
        query: str,
        novel_id: Optional[NovelId] = None,
        source_type: Optional[str] = None,
        n_results: int = 5
    ) -> List[SearchResult]:
        """语义搜索"""
        pass
    
    @abstractmethod
    def search_similar(
        self,
        content: str,
        novel_id: Optional[NovelId] = None,
        n_results: int = 5
    ) -> List[SearchResult]:
        """相似内容搜索"""
# 文件：模块：vector_repository

        pass
    
    @abstractmethod
    def get_by_id(self, vector_id: str) -> Optional[SearchResult]:
        """根据ID获取向量"""
        pass
    
    @abstractmethod
    def delete(self, vector_id: str) -> bool:
        """删除向量"""
# 文件：模块：vector_repository

        pass
    
    @abstractmethod
    def delete_by_source(self, source_type: str, source_id: str) -> int:
        """根据来源删除向量"""
        pass
    
    @abstractmethod
    def delete_by_novel(self, novel_id: NovelId) -> int:
        """删除小说的所有向量"""
# 文件：模块：vector_repository

        pass
    
    @abstractmethod
    def count(self, novel_id: Optional[NovelId] = None) -> int:
        """统计向量数量"""
        pass
    
    @abstractmethod
    def update_vector(
        self,
        vector_id: str,
        content: str,
        metadata: EmbeddingMetadata
    ) -> bool:
        """更新向量"""
# 文件：模块：vector_repository

        pass
