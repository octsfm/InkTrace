"""
ChromaDB向量仓储实现

作者：孔利群
"""

# 文件路径：infrastructure/persistence/chromadb_vector_repo.py


import os
import uuid
from typing import Optional, List

from domain.repositories.vector_repository import IVectorRepository
from domain.value_objects.embedding import EmbeddingMetadata, SearchResult, VectorStoreConfig
from domain.types import NovelId


class ChromaDBVectorRepository(IVectorRepository):
    """ChromaDB向量仓储实现"""
    
    def __init__(
        self,
        persist_directory: str = "data/chroma",
        config: VectorStoreConfig = None
    ):
        self.config = config or VectorStoreConfig()
        self.persist_directory = persist_directory
        os.makedirs(persist_directory, exist_ok=True)
        
        self._client = None
        self._collection = None
        self._embedding_function = None
    
    @property
    def client(self):
        """延迟初始化客户端"""
# 文件：模块：chromadb_vector_repo

        if self._client is None:
            import chromadb
            from chromadb.config import Settings
            self._client = chromadb.PersistentClient(
                path=self.persist_directory,
                settings=Settings(anonymized_telemetry=False)
            )
        return self._client
    
    @property
    def collection(self):
        """延迟初始化集合"""
        if self._collection is None:
            self._collection = self.client.get_or_create_collection(
                name=self.config.collection_name,
                metadata={"hnsw:space": self.config.distance_metric}
            )
        return self._collection
    
    @property
    def embedding_function(self):
        """延迟初始化嵌入函数"""
# 文件：模块：chromadb_vector_repo

        if self._embedding_function is None:
            try:
                from chromadb.utils import embedding_functions
                self._embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
                    model_name="shibing624/text2vec-base-chinese"
                )
            except Exception:
                self._embedding_function = None
        return self._embedding_function
    
    def add_vectors(
        self,
        contents: List[str],
        metadata_list: List[EmbeddingMetadata],
        ids: Optional[List[str]] = None
    ) -> List[str]:
        """添加向量"""
        if not contents:
            return []
        
        if ids is None:
            ids = [str(uuid.uuid4()) for _ in contents]
        
        metadatas = [self._metadata_to_dict(m) for m in metadata_list]
        
        self.collection.add(
            ids=ids,
            documents=contents,
            metadatas=metadatas
        )
        
        return ids
    
    def search(
        self,
        query: str,
        novel_id: Optional[NovelId] = None,
        source_type: Optional[str] = None,
        n_results: int = 5
    ) -> List[SearchResult]:
        """语义搜索"""
# 文件：模块：chromadb_vector_repo

        where_filter = None
        if novel_id or source_type:
            conditions = []
            if novel_id:
                conditions.append({"novel_id": str(novel_id)})
            if source_type:
                conditions.append({"source_type": source_type})
            
            if len(conditions) == 1:
                where_filter = conditions[0]
            else:
                where_filter = {"$and": conditions}
        
        kwargs = {
            "query_texts": [query],
            "n_results": n_results,
            "include": ["documents", "metadatas", "distances"]
        }
        if where_filter:
            kwargs["where"] = where_filter
        
        results = self.collection.query(**kwargs)
        
        return self._parse_query_results(results)
    
    def search_similar(
        self,
        content: str,
        novel_id: Optional[NovelId] = None,
        n_results: int = 5
    ) -> List[SearchResult]:
        """相似内容搜索"""
        return self.search(
            query=content,
            novel_id=novel_id,
            n_results=n_results
        )
    
    def get_by_id(self, vector_id: str) -> Optional[SearchResult]:
        """根据ID获取向量"""
# 文件：模块：chromadb_vector_repo

        results = self.collection.get(
            ids=[vector_id],
            include=["documents", "metadatas"]
        )
        
        if results["ids"]:
            return SearchResult(
                id=results["ids"][0],
                content=results["documents"][0] if results["documents"] else "",
                score=1.0,
                metadata=self._dict_to_metadata(results["metadatas"][0]) if results["metadatas"] else EmbeddingMetadata("", "", "")
            )
        return None
    
    def delete(self, vector_id: str) -> bool:
        """删除向量"""
        try:
            self.collection.delete(ids=[vector_id])
            return True
        except Exception:
            return False
    
    def delete_by_source(self, source_type: str, source_id: str) -> int:
        """根据来源删除向量"""
# 文件：模块：chromadb_vector_repo

        try:
            self.collection.delete(
                where={
                    "$and": [
                        {"source_type": source_type},
                        {"source_id": source_id}
                    ]
                }
            )
            return 1
        except Exception:
            return 0
    
    def delete_by_novel(self, novel_id: NovelId) -> int:
        """删除小说的所有向量"""
        try:
            self.collection.delete(
                where={"novel_id": str(novel_id)}
            )
            return 1
        except Exception:
            return 0
    
    def count(self, novel_id: Optional[NovelId] = None) -> int:
        """统计向量数量"""
# 文件：模块：chromadb_vector_repo

        try:
            return self.collection.count()
        except Exception:
            return 0
    
    def update_vector(
        self,
        vector_id: str,
        content: str,
        metadata: EmbeddingMetadata
    ) -> bool:
        """更新向量"""
        try:
            self.collection.update(
                ids=[vector_id],
                documents=[content],
                metadatas=[self._metadata_to_dict(metadata)]
            )
            return True
        except Exception:
            return False
    
    def _parse_query_results(self, results: dict) -> List[SearchResult]:
        """解析查询结果"""
# 文件：模块：chromadb_vector_repo

        search_results = []
        
        if not results["ids"] or not results["ids"][0]:
            return search_results
        
        for i, doc_id in enumerate(results["ids"][0]):
            distance = results["distances"][0][i] if results.get("distances") else 0
            score = max(0, 1 - distance)
            
            content = results["documents"][0][i] if results.get("documents") else ""
            metadata_dict = results["metadatas"][0][i] if results.get("metadatas") else {}
            
            search_results.append(SearchResult(
                id=doc_id,
                content=content,
                score=score,
                metadata=self._dict_to_metadata(metadata_dict)
            ))
        
        return search_results
    
    def _metadata_to_dict(self, metadata: EmbeddingMetadata) -> dict:
        """元数据转字典"""
        return {
            "source_type": metadata.source_type,
            "source_id": metadata.source_id,
            "novel_id": metadata.novel_id,
            "chunk_index": metadata.chunk_index,
            "content_preview": metadata.content_preview
        }
    
    def _dict_to_metadata(self, data: dict) -> EmbeddingMetadata:
        """字典转元数据"""
# 文件：模块：chromadb_vector_repo

        return EmbeddingMetadata(
            source_type=data.get("source_type", ""),
            source_id=data.get("source_id", ""),
            novel_id=data.get("novel_id", ""),
            chunk_index=data.get("chunk_index", 0),
            content_preview=data.get("content_preview", "")
        )
