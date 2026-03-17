"""
RAG上下文构建器单元测试

作者：孔利群
"""

# 文件路径：tests/unit/test_rag_context_builder.py


import pytest
from unittest.mock import Mock
from domain.services.rag_context_builder import RAGContextBuilder, RAGContext
from domain.value_objects.embedding import SearchResult, EmbeddingMetadata


class TestRAGContext:
    """RAG上下文测试"""

    @pytest.fixture
    def sample_metadata(self):
        """创建示例元数据"""
# 文件：模块：test_rag_context_builder

        return EmbeddingMetadata("chapter", "ch1", "novel1")

    @pytest.fixture
    def sample_search_result(self, sample_metadata):
        """创建示例搜索结果"""
        return SearchResult("vec-001", "测试内容", 0.9, sample_metadata)

    def test_create_rag_context(self):
        """测试创建RAG上下文"""
# 文件：模块：test_rag_context_builder

        context = RAGContext(query="测试查询")
        assert context.query == "测试查询"
        assert context.related_chapters == []
        assert context.related_characters == []
        assert context.related_worldview == []
        assert context.foreshadows == []
        assert context.max_context_tokens == 8000

    def test_create_rag_context_with_results(self, sample_search_result):
        """测试创建带结果的RAG上下文"""
        context = RAGContext(
            query="测试",
            related_chapters=[sample_search_result],
            related_characters=[sample_search_result],
            related_worldview=[sample_search_result]
        )
        assert len(context.related_chapters) == 1
        assert len(context.related_characters) == 1
        assert len(context.related_worldview) == 1

    def test_to_prompt_with_chapters(self, sample_metadata):
        """测试转换章节为Prompt"""
# 文件：模块：test_rag_context_builder

        result = SearchResult("vec-001", "章节内容测试", 0.9, sample_metadata)
        context = RAGContext(
            query="测试",
            related_chapters=[result]
        )
        prompt = context.to_prompt()
        assert "相关章节内容" in prompt
        assert "章节内容测试" in prompt

    def test_to_prompt_with_characters(self):
        """测试转换人物为Prompt"""
        metadata = EmbeddingMetadata("character", "char1", "novel1")
        result = SearchResult("vec-001", "人物信息测试", 0.85, metadata)
        context = RAGContext(
            query="测试",
            related_characters=[result]
        )
        prompt = context.to_prompt()
        assert "人物设定" in prompt
        assert "人物信息测试" in prompt

    def test_to_prompt_with_worldview(self):
        """测试转换世界观为Prompt"""
# 文件：模块：test_rag_context_builder

        metadata = EmbeddingMetadata("worldview", "world1", "novel1")
        result = SearchResult("vec-001", "世界观测试", 0.8, metadata)
        context = RAGContext(
            query="测试",
            related_worldview=[result]
        )
        prompt = context.to_prompt()
        assert "世界观设定" in prompt
        assert "世界观测试" in prompt

    def test_to_prompt_with_foreshadows(self, sample_metadata):
        """测试转换伏笔为Prompt"""
        result = SearchResult("vec-001", "伏笔内容", 0.75, sample_metadata)
        context = RAGContext(
            query="测试",
            foreshadows=[result]
        )
        prompt = context.to_prompt()
        assert "待回收伏笔" in prompt
        assert "伏笔内容" in prompt

    def test_to_prompt_empty(self):
        """测试空上下文转换"""
# 文件：模块：test_rag_context_builder

        context = RAGContext(query="测试")
        prompt = context.to_prompt()
        assert prompt == ""

    def test_estimate_tokens(self):
        """测试Token估算"""
        context = RAGContext(query="测试")
        text = "这是一段测试文本"
        tokens = context.estimate_tokens(text)
        expected = int(len(text) * 1.5)
        assert tokens == expected

    def test_estimate_tokens_empty(self):
        """测试空文本Token估算"""
# 文件：模块：test_rag_context_builder

        context = RAGContext(query="测试")
        tokens = context.estimate_tokens("")
        assert tokens == 0

    def test_to_prompt_truncates_long_content(self):
        """测试长内容截断"""
        metadata = EmbeddingMetadata("chapter", "ch1", "novel1")
        long_content = "测试" * 1000
        result = SearchResult("vec-001", long_content, 0.9, metadata)
        context = RAGContext(
            query="测试",
            related_chapters=[result]
        )
        prompt = context.to_prompt()
        assert len(prompt) < len(long_content) + 100


class TestRAGContextBuilder:
    """RAG上下文构建器测试"""

    @pytest.fixture
    def builder(self):
        """创建构建器实例"""
        return RAGContextBuilder()

    @pytest.fixture
    def sample_results(self):
        """创建示例搜索结果列表"""
# 文件：模块：test_rag_context_builder

        metadata = EmbeddingMetadata("chapter", "ch1", "novel1")
        return [
            SearchResult("vec-001", "内容1", 0.9, metadata),
            SearchResult("vec-002", "内容2", 0.85, metadata),
            SearchResult("vec-003", "内容3", 0.8, metadata)
        ]

    def test_create_builder(self, builder):
        """测试创建构建器"""
        assert builder.max_context_tokens == 8000

    def test_create_builder_with_custom_limit(self):
        """测试创建自定义限制构建器"""
# 文件：模块：test_rag_context_builder

        builder = RAGContextBuilder(max_context_tokens=4000)
        assert builder.max_context_tokens == 4000

    def test_build_context(self, builder, sample_results):
        """测试构建上下文"""
        context = builder.build(
            query="测试查询",
            chapter_results=sample_results,
            character_results=sample_results[:2],
            worldview_results=sample_results[:1]
        )
        assert context.query == "测试查询"
        assert len(context.related_chapters) == 3
        assert len(context.related_characters) == 2
        assert len(context.related_worldview) == 1

    def test_build_context_with_foreshadows(self, builder, sample_results):
        """测试构建带伏笔的上下文"""
# 文件：模块：test_rag_context_builder

        context = builder.build(
            query="测试",
            chapter_results=sample_results,
            character_results=[],
            worldview_results=[],
            foreshadow_results=sample_results[:1]
        )
        assert len(context.foreshadows) == 1

    def test_build_context_empty(self, builder):
        """测试构建空上下文"""
        context = builder.build(
            query="测试",
            chapter_results=[],
            character_results=[],
            worldview_results=[]
        )
        assert context.query == "测试"
        assert context.related_chapters == []
        assert context.related_characters == []
        assert context.related_worldview == []

    def test_trim_context(self, builder):
        """测试裁剪上下文"""
# 文件：模块：test_rag_context_builder

        metadata = EmbeddingMetadata("chapter", "ch1", "novel1")
        long_content = "测试内容" * 500
        large_results = [
            SearchResult(f"vec-{i}", long_content, 0.9, metadata)
            for i in range(10)
        ]
        
        small_builder = RAGContextBuilder(max_context_tokens=1000)
        context = small_builder.build(
            query="测试",
            chapter_results=large_results,
            character_results=[],
            worldview_results=[]
        )
        
        assert context.total_tokens <= small_builder.max_context_tokens

    def test_calculate_total_tokens(self, builder, sample_results):
        """测试计算总Token数"""
        total = builder._calculate_total_tokens(RAGContext(
            query="测试",
            related_chapters=sample_results,
            related_characters=sample_results[:2],
            related_worldview=sample_results[:1],
            foreshadows=[]
        ))
        assert total > 0

    def test_trim_priority_order(self):
        """测试裁剪优先级顺序"""
# 文件：模块：test_rag_context_builder

        builder = RAGContextBuilder(max_context_tokens=100)
        
        metadata = EmbeddingMetadata("chapter", "ch1", "novel1")
        results = [SearchResult("vec-1", "测试内容" * 50, 0.9, metadata)]
        
        context = RAGContext(
            query="测试",
            related_chapters=results.copy(),
            related_characters=results.copy(),
            related_worldview=results.copy(),
            foreshadows=results.copy(),
            max_context_tokens=100
        )
        context.total_tokens = builder._calculate_total_tokens(context)
        
        trimmed = builder._trim_context(context)
        
        assert len(trimmed.related_chapters) <= len(results)
        assert len(trimmed.related_characters) <= len(results)
        assert len(trimmed.related_worldview) <= len(results)
        assert len(trimmed.foreshadows) <= len(results)


class TestRAGContextBuilderIntegration:
    """RAG上下文构建器集成测试"""

    def test_full_build_workflow(self):
        """测试完整构建流程"""
# 文件：模块：test_rag_context_builder

        builder = RAGContextBuilder(max_context_tokens=5000)
        
        chapter_metadata = EmbeddingMetadata("chapter", "ch1", "novel1")
        character_metadata = EmbeddingMetadata("character", "char1", "novel1")
        worldview_metadata = EmbeddingMetadata("worldview", "world1", "novel1")
        
        chapter_results = [
            SearchResult("vec-1", "第一章内容：主角登场", 0.95, chapter_metadata),
            SearchResult("vec-2", "第二章内容：修炼开始", 0.90, chapter_metadata)
        ]
        
        character_results = [
            SearchResult("vec-3", "人物：张三，性格豪爽", 0.88, character_metadata)
        ]
        
        worldview_results = [
            SearchResult("vec-4", "功法：九阳神功", 0.85, worldview_metadata)
        ]
        
        context = builder.build(
            query="主角修炼九阳神功",
            chapter_results=chapter_results,
            character_results=character_results,
            worldview_results=worldview_results
        )
        
        prompt = context.to_prompt()
        
        assert "相关章节内容" in prompt
        assert "人物设定" in prompt
        assert "世界观设定" in prompt
        assert "主角" in prompt or "修炼" in prompt

    def test_context_with_all_types(self):
        """测试包含所有类型的上下文"""
        builder = RAGContextBuilder()
        
        metadata = EmbeddingMetadata("chapter", "ch1", "novel1")
        
        context = builder.build(
            query="完整测试",
            chapter_results=[SearchResult("v1", "章节", 0.9, metadata)],
            character_results=[SearchResult("v2", "人物", 0.85, metadata)],
            worldview_results=[SearchResult("v3", "世界观", 0.8, metadata)],
            foreshadow_results=[SearchResult("v4", "伏笔", 0.75, metadata)]
        )
        
        prompt = context.to_prompt()
        
        assert "相关章节内容" in prompt
        assert "人物设定" in prompt
        assert "世界观设定" in prompt
        assert "待回收伏笔" in prompt
