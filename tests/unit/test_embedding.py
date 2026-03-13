"""
向量存储值对象单元测试

作者：孔利群
"""

import unittest

from domain.value_objects.embedding import EmbeddingMetadata, SearchResult, VectorStoreConfig


class TestEmbeddingMetadata(unittest.TestCase):
    """嵌入元数据值对象测试"""
    
    def test_create_embedding_metadata(self):
        """测试创建嵌入元数据"""
        metadata = EmbeddingMetadata(
            source_type="chapter",
            source_id="chapter_001",
            novel_id="novel_001",
            chunk_index=0,
            content_preview="测试内容预览"
        )
        self.assertEqual(metadata.source_type, "chapter")
        self.assertEqual(metadata.source_id, "chapter_001")
        self.assertEqual(metadata.chunk_index, 0)
    
    def test_metadata_to_dict(self):
        """测试元数据转字典"""
        metadata = EmbeddingMetadata(
            source_type="character",
            source_id="char_001",
            novel_id="novel_001"
        )
        data = metadata.to_dict()
        self.assertEqual(data["source_type"], "character")
        self.assertEqual(data["source_id"], "char_001")
    
    def test_metadata_from_dict(self):
        """测试从字典创建元数据"""
        data = {
            "source_type": "worldview",
            "source_id": "wv_001",
            "novel_id": "novel_001",
            "chunk_index": 2,
            "content_preview": "预览"
        }
        metadata = EmbeddingMetadata.from_dict(data)
        self.assertEqual(metadata.source_type, "worldview")
        self.assertEqual(metadata.chunk_index, 2)


class TestSearchResult(unittest.TestCase):
    """搜索结果值对象测试"""
    
    def test_create_search_result(self):
        """测试创建搜索结果"""
        result = SearchResult(
            id="emb_001",
            content="匹配的内容",
            score=0.95,
            metadata=EmbeddingMetadata(
                source_type="chapter",
                source_id="chapter_001",
                novel_id="novel_001"
            )
        )
        self.assertEqual(result.id, "emb_001")
        self.assertEqual(result.score, 0.95)
        self.assertEqual(result.metadata.source_type, "chapter")
    
    def test_search_result_to_dict(self):
        """测试搜索结果转字典"""
        result = SearchResult(
            id="emb_002",
            content="内容",
            score=0.88,
            metadata=EmbeddingMetadata(
                source_type="character",
                source_id="char_001",
                novel_id="novel_001"
            )
        )
        data = result.to_dict()
        self.assertEqual(data["id"], "emb_002")
        self.assertEqual(data["score"], 0.88)


class TestVectorStoreConfig(unittest.TestCase):
    """向量存储配置值对象测试"""
    
    def test_create_default_config(self):
        """测试创建默认配置"""
        config = VectorStoreConfig()
        self.assertEqual(config.collection_name, "novel_embeddings")
        self.assertEqual(config.embedding_model, "text2vec-chinese")
        self.assertEqual(config.chunk_size, 500)
        self.assertEqual(config.chunk_overlap, 50)
    
    def test_create_custom_config(self):
        """测试创建自定义配置"""
        config = VectorStoreConfig(
            collection_name="custom_collection",
            embedding_model="bge-large",
            chunk_size=1000,
            chunk_overlap=100
        )
        self.assertEqual(config.collection_name, "custom_collection")
        self.assertEqual(config.chunk_size, 1000)


if __name__ == "__main__":
    unittest.main()
