"""
向量索引服务单元测试

作者：孔利群
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from application.services.vector_index_service import VectorIndexService
from domain.value_objects.embedding import EmbeddingMetadata, VectorStoreConfig
from domain.types import NovelId, ChapterId, CharacterId
import uuid


class TestVectorIndexService:
    """向量索引服务测试"""

    @pytest.fixture
    def mock_vector_repo(self):
        """模拟向量仓储"""
        return Mock()

    @pytest.fixture
    def mock_chapter_repo(self):
        """模拟章节仓储"""
        repo = Mock()
        repo.find_by_novel.return_value = []
        return repo

    @pytest.fixture
    def mock_character_repo(self):
        """模拟人物仓储"""
        repo = Mock()
        repo.find_by_novel.return_value = []
        return repo

    @pytest.fixture
    def mock_worldview_repo(self):
        """模拟世界观仓储"""
        repo = Mock()
        repo.find_techniques_by_novel.return_value = []
        repo.find_factions_by_novel.return_value = []
        repo.find_locations_by_novel.return_value = []
        return repo

    @pytest.fixture
    def service(self, mock_vector_repo, mock_chapter_repo, mock_character_repo, mock_worldview_repo):
        """创建服务实例"""
        return VectorIndexService(
            vector_repo=mock_vector_repo,
            chapter_repo=mock_chapter_repo,
            character_repo=mock_character_repo,
            worldview_repo=mock_worldview_repo
        )

    def test_create_service(self, service):
        """测试创建服务"""
        assert service.vector_repo is not None
        assert service.chapter_repo is not None
        assert service.character_repo is not None
        assert service.worldview_repo is not None

    def test_create_service_with_custom_config(self, mock_vector_repo, mock_chapter_repo, mock_character_repo, mock_worldview_repo):
        """测试使用自定义配置创建服务"""
        config = VectorStoreConfig(chunk_size=1000, chunk_overlap=100)
        service = VectorIndexService(
            vector_repo=mock_vector_repo,
            chapter_repo=mock_chapter_repo,
            character_repo=mock_character_repo,
            worldview_repo=mock_worldview_repo,
            config=config
        )
        assert service.config.chunk_size == 1000
        assert service.config.chunk_overlap == 100

    def test_index_novel_empty(self, service):
        """测试索引空小说"""
        novel_id = NovelId("test-novel-001")
        stats = service.index_novel(novel_id)

        assert stats["chapters_indexed"] == 0
        assert stats["characters_indexed"] == 0
        assert stats["worldview_indexed"] == 0
        assert stats["errors"] == []

    def test_index_chapters(self, mock_vector_repo, mock_character_repo, mock_worldview_repo):
        """测试索引章节"""
        mock_chapter = Mock()
        mock_chapter.id = ChapterId("chapter-001")
        mock_chapter.content = "这是一段测试内容，用于测试章节索引功能。这段内容需要足够长才能测试分块功能。"
        
        mock_chapter_repo = Mock()
        mock_chapter_repo.find_by_novel.return_value = [mock_chapter]
        mock_vector_repo.add_vectors.return_value = ["vec-001"]

        service = VectorIndexService(
            vector_repo=mock_vector_repo,
            chapter_repo=mock_chapter_repo,
            character_repo=mock_character_repo,
            worldview_repo=mock_worldview_repo
        )

        novel_id = NovelId("test-novel-001")
        count = service._index_chapters(novel_id)

        assert count >= 1
        mock_vector_repo.add_vectors.assert_called()

    def test_index_characters(self, mock_vector_repo, mock_chapter_repo, mock_worldview_repo):
        """测试索引人物"""
        mock_character = Mock()
        mock_character.id = CharacterId("char-001")
        mock_character.name = "张三"
        mock_character.background = "出身名门"
        mock_character.personality = "性格豪爽"
        mock_character.appearance = "身材高大"
        mock_character.abilities = ["剑法", "内功"]
        
        mock_character_repo = Mock()
        mock_character_repo.find_by_novel.return_value = [mock_character]
        mock_vector_repo.add_vectors.return_value = ["vec-001"]

        service = VectorIndexService(
            vector_repo=mock_vector_repo,
            chapter_repo=mock_chapter_repo,
            character_repo=mock_character_repo,
            worldview_repo=mock_worldview_repo
        )

        novel_id = NovelId("test-novel-001")
        count = service._index_characters(novel_id)

        assert count == 1
        mock_vector_repo.add_vectors.assert_called_once()

    def test_index_worldview(self, service, mock_worldview_repo, mock_vector_repo):
        """测试索引世界观"""
        mock_technique = Mock()
        mock_technique.id = "tech-001"
        mock_technique.name = "九阳神功"
        mock_technique.description = "至阳至刚的内功心法"
        mock_technique.effect = "增强内力"

        mock_faction = Mock()
        mock_faction.id = "faction-001"
        mock_faction.name = "明教"
        mock_faction.description = "江湖第一大教"
        mock_faction.territory = "光明顶"

        mock_location = Mock()
        mock_location.id = "loc-001"
        mock_location.name = "光明顶"
        mock_location.description = "明教总坛所在地"

        mock_worldview_repo.find_techniques_by_novel.return_value = [mock_technique]
        mock_worldview_repo.find_factions_by_novel.return_value = [mock_faction]
        mock_worldview_repo.find_locations_by_novel.return_value = [mock_location]
        mock_vector_repo.add_vectors.return_value = ["vec-001"]

        novel_id = NovelId("test-novel-001")
        count = service._index_worldview(novel_id)

        assert count == 3
        assert mock_vector_repo.add_vectors.call_count == 3

    def test_chunk_content_short(self, service):
        """测试短内容分块"""
        content = "短内容"
        chunks = service._chunk_content(content)
        assert len(chunks) == 1
        assert chunks[0] == "短内容"

    def test_chunk_content_long(self, service):
        """测试长内容分块"""
        content = "a" * 1000
        chunks = service._chunk_content(content)
        assert len(chunks) > 1

    def test_chunk_content_empty(self, service):
        """测试空内容分块"""
        chunks = service._chunk_content("")
        assert chunks == []

    def test_chunk_content_none(self, service):
        """测试None内容分块"""
        chunks = service._chunk_content(None)
        assert chunks == []

    def test_build_character_content_full(self, service):
        """测试构建完整人物内容"""
        character = Mock()
        character.name = "李四"
        character.background = "武林世家"
        character.personality = "沉稳内敛"
        character.appearance = "英俊潇洒"
        character.abilities = ["轻功", "暗器"]

        content = service._build_character_content(character)

        assert "李四" in content
        assert "武林世家" in content
        assert "沉稳内敛" in content
        assert "英俊潇洒" in content
        assert "轻功" in content
        assert "暗器" in content

    def test_build_character_content_minimal(self, service):
        """测试构建最小人物内容"""
        character = Mock()
        character.name = "王五"
        character.background = None
        character.personality = None
        character.appearance = None
        character.abilities = []

        content = service._build_character_content(character)

        assert "王五" in content

    def test_delete_novel_index(self, service, mock_vector_repo):
        """测试删除小说索引"""
        mock_vector_repo.delete_by_novel.return_value = 10

        novel_id = NovelId("test-novel-001")
        count = service.delete_novel_index(novel_id)

        assert count == 10
        mock_vector_repo.delete_by_novel.assert_called_once_with(novel_id)

    def test_get_index_status(self, service, mock_vector_repo):
        """测试获取索引状态"""
        mock_vector_repo.count.return_value = 50

        novel_id = NovelId("test-novel-001")
        status = service.get_index_status(novel_id)

        assert status["total_vectors"] == 50
        assert status["is_indexed"] is True

    def test_get_index_status_empty(self, service, mock_vector_repo):
        """测试获取空索引状态"""
        mock_vector_repo.count.return_value = 0

        novel_id = NovelId("test-novel-001")
        status = service.get_index_status(novel_id)

        assert status["total_vectors"] == 0
        assert status["is_indexed"] is False


class TestVectorIndexServiceIntegration:
    """向量索引服务集成测试"""

    def test_full_index_workflow(self):
        """测试完整索引流程"""
        mock_vector_repo = Mock()
        mock_chapter_repo = Mock()
        mock_character_repo = Mock()
        mock_worldview_repo = Mock()

        mock_chapter = Mock()
        mock_chapter.id = ChapterId("chapter-001")
        mock_chapter.content = "测试章节内容"
        mock_chapter_repo.find_by_novel.return_value = [mock_chapter]

        mock_character = Mock()
        mock_character.id = CharacterId("char-001")
        mock_character.name = "测试人物"
        mock_character.background = None
        mock_character.personality = None
        mock_character.appearance = None
        mock_character.abilities = []
        mock_character_repo.find_by_novel.return_value = [mock_character]

        mock_worldview_repo.find_techniques_by_novel.return_value = []
        mock_worldview_repo.find_factions_by_novel.return_value = []
        mock_worldview_repo.find_locations_by_novel.return_value = []

        mock_vector_repo.add_vectors.return_value = ["vec-001"]
        mock_vector_repo.count.return_value = 2

        service = VectorIndexService(
            vector_repo=mock_vector_repo,
            chapter_repo=mock_chapter_repo,
            character_repo=mock_character_repo,
            worldview_repo=mock_worldview_repo
        )

        novel_id = NovelId("test-novel-001")
        stats = service.index_novel(novel_id)

        assert stats["chapters_indexed"] >= 1
        assert stats["characters_indexed"] == 1
        assert stats["worldview_indexed"] == 0
