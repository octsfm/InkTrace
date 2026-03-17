"""
向量仓储单元测试

作者：孔利群
"""

# 文件路径：tests/unit/test_vector_repository.py


import pytest
from unittest.mock import Mock, patch, MagicMock
from domain.value_objects.embedding import EmbeddingMetadata, SearchResult, VectorStoreConfig
from domain.repositories.vector_repository import IVectorRepository


class TestEmbeddingMetadata:
    """嵌入元数据测试"""

    def test_create_embedding_metadata(self):
        """测试创建嵌入元数据"""
# 文件：模块：test_vector_repository

        metadata = EmbeddingMetadata(
            source_type="chapter",
            source_id="chapter-001",
            novel_id="novel-001",
            chunk_index=0,
            content_preview="这是内容预览..."
        )
        assert metadata.source_type == "chapter"
        assert metadata.source_id == "chapter-001"
        assert metadata.novel_id == "novel-001"
        assert metadata.chunk_index == 0
        assert metadata.content_preview == "这是内容预览..."

    def test_metadata_from_dict(self):
        """测试从字典创建元数据"""
        data = {
            "source_type": "character",
            "source_id": "char-001",
            "novel_id": "novel-001",
            "chunk_index": 1,
            "content_preview": "角色描述"
        }
        metadata = EmbeddingMetadata.from_dict(data)
        assert metadata.source_type == "character"
        assert metadata.source_id == "char-001"

    def test_metadata_to_dict(self):
        """测试元数据转字典"""
# 文件：模块：test_vector_repository

        metadata = EmbeddingMetadata(
            source_type="worldview",
            source_id="world-001",
            novel_id="novel-001"
        )
        data = metadata.to_dict()
        assert data["source_type"] == "worldview"
        assert data["source_id"] == "world-001"
        assert data["chunk_index"] == 0

    def test_metadata_default_values(self):
        """测试元数据默认值"""
        metadata = EmbeddingMetadata(
            source_type="chapter",
            source_id="chapter-001",
            novel_id="novel-001"
        )
        assert metadata.chunk_index == 0
        assert metadata.content_preview == ""


class TestSearchResult:
    """搜索结果测试"""

    def test_create_search_result(self):
        """测试创建搜索结果"""
        metadata = EmbeddingMetadata(
            source_type="chapter",
            source_id="chapter-001",
            novel_id="novel-001"
        )
        result = SearchResult(
            id="vec-001",
            content="搜索到的内容",
            score=0.95,
            metadata=metadata
        )
        assert result.id == "vec-001"
        assert result.content == "搜索到的内容"
        assert result.score == 0.95
        assert result.metadata == metadata

    def test_search_result_to_dict(self):
        """测试搜索结果转字典"""
# 文件：模块：test_vector_repository

        metadata = EmbeddingMetadata(
            source_type="chapter",
            source_id="chapter-001",
            novel_id="novel-001"
        )
        result = SearchResult(
            id="vec-001",
            content="内容",
            score=0.8,
            metadata=metadata
        )
        data = result.to_dict()
        assert data["id"] == "vec-001"
        assert data["content"] == "内容"
        assert data["score"] == 0.8
        assert "metadata" in data

    def test_search_result_from_dict(self):
        """测试从字典创建搜索结果"""
        data = {
            "id": "vec-002",
            "content": "测试内容",
            "score": 0.75,
            "metadata": {
                "source_type": "character",
                "source_id": "char-001",
                "novel_id": "novel-001",
                "chunk_index": 0,
                "content_preview": ""
            }
        }
        result = SearchResult.from_dict(data)
        assert result.id == "vec-002"
        assert result.score == 0.75
        assert result.metadata.source_type == "character"


class TestVectorStoreConfig:
    """向量存储配置测试"""

    def test_create_default_config(self):
        """测试创建默认配置"""
        config = VectorStoreConfig()
        assert config.collection_name == "novel_embeddings"
        assert config.embedding_model == "text2vec-chinese"
        assert config.chunk_size == 500
        assert config.chunk_overlap == 50

    def test_create_custom_config(self):
        """测试创建自定义配置"""
# 文件：模块：test_vector_repository

        config = VectorStoreConfig(
            collection_name="custom_collection",
            embedding_model="custom-model",
            chunk_size=1000,
            chunk_overlap=100
        )
        assert config.collection_name == "custom_collection"
        assert config.embedding_model == "custom-model"
        assert config.chunk_size == 1000
        assert config.chunk_overlap == 100


class TestIVectorRepository:
    """向量仓储接口测试"""

    def test_interface_methods(self):
        """测试接口方法定义"""
# 文件：模块：test_vector_repository

        repo = Mock(spec=IVectorRepository)
        
        repo.add_vectors.return_value = ["id1", "id2"]
        repo.search.return_value = []
        repo.delete.return_value = True
        repo.get_by_id.return_value = None
        repo.count.return_value = 0
        
        ids = repo.add_vectors(["content1", "content2"], [], None)
        assert ids == ["id1", "id2"]
        
        results = repo.search("query", None, None, 5)
        assert results == []


class TestMockVectorRepository:
    """模拟向量仓储测试"""

    def test_add_vectors(self):
        """测试添加向量"""
# 文件：模块：test_vector_repository

        mock_repo = Mock(spec=IVectorRepository)
        mock_repo.add_vectors.return_value = ["vec-001", "vec-002"]
        
        contents = ["第一段内容", "第二段内容"]
        metadata_list = [
            EmbeddingMetadata("chapter", "ch1", "novel1"),
            EmbeddingMetadata("chapter", "ch2", "novel1")
        ]
        
        ids = mock_repo.add_vectors(contents, metadata_list)
        assert len(ids) == 2
        assert ids == ["vec-001", "vec-002"]
        mock_repo.add_vectors.assert_called_once_with(contents, metadata_list)

    def test_search_vectors(self):
        """测试搜索向量"""
        mock_repo = Mock(spec=IVectorRepository)
        
        metadata = EmbeddingMetadata("chapter", "ch1", "novel1")
        expected_results = [
            SearchResult("vec-001", "相关内容1", 0.95, metadata),
            SearchResult("vec-002", "相关内容2", 0.85, metadata)
        ]
        mock_repo.search.return_value = expected_results
        
        results = mock_repo.search("查询内容", "novel1", "chapter", 2)
        assert len(results) == 2
        assert results[0].score == 0.95
        assert results[1].score == 0.85

    def test_delete_vectors(self):
        """测试删除向量"""
# 文件：模块：test_vector_repository

        mock_repo = Mock(spec=IVectorRepository)
        mock_repo.delete.return_value = True
        
        result = mock_repo.delete(["vec-001", "vec-002"])
        assert result is True
        mock_repo.delete.assert_called_once_with(["vec-001", "vec-002"])

    def test_get_by_id(self):
        """测试根据ID获取向量"""
        mock_repo = Mock(spec=IVectorRepository)
        
        metadata = EmbeddingMetadata("chapter", "ch1", "novel1")
        expected_result = SearchResult("vec-001", "内容", 1.0, metadata)
        mock_repo.get_by_id.return_value = expected_result
        
        result = mock_repo.get_by_id("vec-001")
        assert result is not None
        assert result.id == "vec-001"

    def test_get_by_id_not_found(self):
        """测试获取不存在的向量"""
# 文件：模块：test_vector_repository

        mock_repo = Mock(spec=IVectorRepository)
        mock_repo.get_by_id.return_value = None
        
        result = mock_repo.get_by_id("non-existent")
        assert result is None

    def test_count_vectors(self):
        """测试统计向量数量"""
        mock_repo = Mock(spec=IVectorRepository)
        mock_repo.count.return_value = 100
        
        result = mock_repo.count()
        assert result == 100
