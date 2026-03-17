"""
RAG检索服务单元测试

作者：孔利群
"""

# 文件路径：tests/unit/test_rag_retrieval_service.py


import pytest
from unittest.mock import Mock, MagicMock
from application.services.rag_retrieval_service import RAGRetrievalService
from domain.value_objects.embedding import SearchResult, EmbeddingMetadata
from domain.types import NovelId


class TestRAGRetrievalService:
    """RAG检索服务测试"""

    @pytest.fixture
    def mock_vector_repo(self):
        """模拟向量仓储"""
# 文件：模块：test_rag_retrieval_service

        return Mock()

    @pytest.fixture
    def mock_chapter_repo(self):
        """模拟章节仓储"""
        return Mock()

    @pytest.fixture
    def mock_character_repo(self):
        """模拟人物仓储"""
# 文件：模块：test_rag_retrieval_service

        return Mock()

    @pytest.fixture
    def service(self, mock_vector_repo, mock_chapter_repo, mock_character_repo):
        """创建服务实例"""
        return RAGRetrievalService(
            vector_repo=mock_vector_repo,
            chapter_repo=mock_chapter_repo,
            character_repo=mock_character_repo
        )

    def test_create_service(self, service):
        """测试创建服务"""
# 文件：模块：test_rag_retrieval_service

        assert service.vector_repo is not None
        assert service.chapter_repo is not None
        assert service.character_repo is not None

    def test_search_relevant_content(self, service, mock_vector_repo):
        """测试搜索相关内容"""
        metadata = EmbeddingMetadata("chapter", "ch1", "novel1")
        expected_results = [
            SearchResult("vec-001", "相关内容1", 0.95, metadata),
            SearchResult("vec-002", "相关内容2", 0.85, metadata)
        ]
        mock_vector_repo.search.return_value = expected_results

        novel_id = NovelId("test-novel-001")
        results = service.search_relevant_content(novel_id, "查询内容", 5)

        assert len(results) == 2
        assert results[0].score == 0.95
        mock_vector_repo.search.assert_called_once()

    def test_search_relevant_chapters(self, service, mock_vector_repo):
        """测试搜索相关章节"""
# 文件：模块：test_rag_retrieval_service

        metadata = EmbeddingMetadata("chapter", "ch1", "novel1")
        expected_results = [
            SearchResult("vec-001", "章节内容", 0.90, metadata)
        ]
        mock_vector_repo.search.return_value = expected_results

        novel_id = NovelId("test-novel-001")
        results = service.search_relevant_chapters(novel_id, "战斗场景", 3)

        assert len(results) == 1
        call_args = mock_vector_repo.search.call_args
        assert call_args[1]["source_type"] == "chapter"

    def test_search_relevant_characters(self, service, mock_vector_repo):
        """测试搜索相关人物"""
        metadata = EmbeddingMetadata("character", "char1", "novel1")
        expected_results = [
            SearchResult("vec-001", "人物信息", 0.88, metadata)
        ]
        mock_vector_repo.search.return_value = expected_results

        novel_id = NovelId("test-novel-001")
        results = service.search_relevant_characters(novel_id, "主角", 3)

        assert len(results) == 1
        call_args = mock_vector_repo.search.call_args
        assert call_args[1]["source_type"] == "character"

    def test_search_relevant_worldview(self, service, mock_vector_repo):
        """测试搜索相关世界观"""
# 文件：模块：test_rag_retrieval_service

        metadata = EmbeddingMetadata("worldview", "world1", "novel1")
        expected_results = [
            SearchResult("vec-001", "世界观信息", 0.92, metadata)
        ]
        mock_vector_repo.search.return_value = expected_results

        novel_id = NovelId("test-novel-001")
        results = service.search_relevant_worldview(novel_id, "功法", 3)

        assert len(results) == 1
        call_args = mock_vector_repo.search.call_args
        assert call_args[1]["source_type"] == "worldview"

    def test_get_context_for_writing(self, service, mock_vector_repo):
        """测试获取续写上下文"""
        chapter_metadata = EmbeddingMetadata("chapter", "ch1", "novel1")
        character_metadata = EmbeddingMetadata("character", "char1", "novel1")
        worldview_metadata = EmbeddingMetadata("worldview", "world1", "novel1")

        def mock_search(**kwargs):
            source_type = kwargs.get("source_type")
            if source_type == "chapter":
                return [SearchResult("vec-1", "章节内容", 0.9, chapter_metadata)]
            elif source_type == "character":
                return [SearchResult("vec-2", "人物信息", 0.85, character_metadata)]
            elif source_type == "worldview":
                return [SearchResult("vec-3", "世界观", 0.8, worldview_metadata)]
            return []

        mock_vector_repo.search.side_effect = mock_search

        novel_id = NovelId("test-novel-001")
        context = service.get_context_for_writing(novel_id, "主角修炼")

        assert len(context["chapters"]) == 1
        assert len(context["characters"]) == 1
        assert len(context["worldview"]) == 1

    def test_get_context_for_writing_empty(self, service, mock_vector_repo):
        """测试获取空续写上下文"""
# 文件：模块：test_rag_retrieval_service

        mock_vector_repo.search.return_value = []

        novel_id = NovelId("test-novel-001")
        context = service.get_context_for_writing(novel_id, "无相关内容")

        assert context["chapters"] == []
        assert context["characters"] == []
        assert context["worldview"] == []

    def test_build_rag_prompt(self, service, mock_vector_repo):
        """测试构建RAG Prompt"""
        chapter_metadata = EmbeddingMetadata("chapter", "ch1", "novel1")
        character_metadata = EmbeddingMetadata("character", "char1", "novel1")
        worldview_metadata = EmbeddingMetadata("worldview", "world1", "novel1")

        def mock_search(**kwargs):
            source_type = kwargs.get("source_type")
            if source_type == "chapter":
                return [SearchResult("vec-1", "章节内容测试", 0.9, chapter_metadata)]
            elif source_type == "character":
                return [SearchResult("vec-2", "人物信息测试", 0.85, character_metadata)]
            elif source_type == "worldview":
                return [SearchResult("vec-3", "世界观测试", 0.8, worldview_metadata)]
            return []

        mock_vector_repo.search.side_effect = mock_search

        novel_id = NovelId("test-novel-001")
        prompt = service.build_rag_prompt(novel_id, "请续写主角修炼的场景")

        assert "相关上下文信息" in prompt
        assert "相关章节" in prompt
        assert "相关人物" in prompt
        assert "相关世界观" in prompt
        assert "创作要求" in prompt
        assert "请续写主角修炼的场景" in prompt

    def test_build_rag_prompt_with_long_content(self, service, mock_vector_repo):
        """测试构建RAG Prompt处理长内容"""
# 文件：模块：test_rag_retrieval_service

        chapter_metadata = EmbeddingMetadata("chapter", "ch1", "novel1")
        long_content = "测试内容" * 200
        mock_vector_repo.search.return_value = [
            SearchResult("vec-1", long_content, 0.9, chapter_metadata)
        ]

        novel_id = NovelId("test-novel-001")
        prompt = service.build_rag_prompt(novel_id, "测试请求")

        assert len(prompt) < len(long_content) + 1000

    def test_build_rag_prompt_empty_context(self, service, mock_vector_repo):
        """测试构建空上下文RAG Prompt"""
        mock_vector_repo.search.return_value = []

        novel_id = NovelId("test-novel-001")
        prompt = service.build_rag_prompt(novel_id, "测试请求")

        assert "创作要求" in prompt
        assert "测试请求" in prompt


class TestRAGRetrievalServiceEdgeCases:
    """RAG检索服务边界情况测试"""

    @pytest.fixture
    def service(self):
        """创建服务实例"""
        return RAGRetrievalService(
            vector_repo=Mock(),
            chapter_repo=Mock(),
            character_repo=Mock()
        )

    def test_search_with_empty_query(self, service):
        """测试空查询"""
# 文件：模块：test_rag_retrieval_service

        service.vector_repo.search.return_value = []

        novel_id = NovelId("test-novel-001")
        results = service.search_relevant_content(novel_id, "", 5)

        assert results == []

    def test_search_with_zero_results(self, service):
        """测试零结果请求"""
        service.vector_repo.search.return_value = []

        novel_id = NovelId("test-novel-001")
        results = service.search_relevant_content(novel_id, "查询", 0)

        service.vector_repo.search.assert_called_once()

    def test_get_context_with_custom_limits(self, service):
        """测试自定义限制获取上下文"""
# 文件：模块：test_rag_retrieval_service

        service.vector_repo.search.return_value = []

        novel_id = NovelId("test-novel-001")
        context = service.get_context_for_writing(
            novel_id,
            "测试",
            max_chapters=5,
            max_characters=3,
            max_worldview=4
        )

        assert context["chapters"] == []
        assert context["characters"] == []
        assert context["worldview"] == []

    def test_multiple_search_calls(self, service):
        """测试多次搜索调用"""
        metadata = EmbeddingMetadata("chapter", "ch1", "novel1")
        service.vector_repo.search.return_value = [
            SearchResult("vec-1", "内容", 0.9, metadata)
        ]

        novel_id = NovelId("test-novel-001")
        
        service.search_relevant_content(novel_id, "查询1")
        service.search_relevant_content(novel_id, "查询2")
        service.search_relevant_content(novel_id, "查询3")

        assert service.vector_repo.search.call_count == 3
