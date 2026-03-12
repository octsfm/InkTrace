"""
写作引擎领域服务单元测试

作者：孔利群
"""

import unittest
from unittest.mock import MagicMock, AsyncMock
from datetime import datetime

from domain.entities.chapter import Chapter
from domain.entities.novel import Novel
from domain.entities.outline import Outline, PlotNode
from domain.types import ChapterId, NovelId, OutlineId, ChapterStatus, PlotType, PlotStatus
from domain.value_objects.style_profile import StyleProfile
from domain.value_objects.writing_config import WritingConfig
from domain.services.writing_engine import WritingEngine, WritingContext


class TestWritingEngine(unittest.TestCase):
    """测试WritingEngine"""

    def setUp(self):
        """测试前置设置"""
        self.mock_llm_client = MagicMock()
        self.mock_llm_client.generate = AsyncMock(return_value="生成的章节内容")
        self.mock_llm_client.chat = AsyncMock(return_value="生成的对话内容")
        
        self.style_profile = StyleProfile(
            vocabulary_stats={"高频词": [("孔凡圣", 100)]},
            sentence_patterns=["主谓宾结构"],
            rhetoric_stats={"比喻": 10},
            dialogue_style="简洁",
            narrative_voice="第三人称",
            pacing="快节奏",
            sample_sentences=["孔凡圣在丛林中奔跑。"]
        )
        
        self.engine = WritingEngine(self.mock_llm_client, self.style_profile)

    def test_create_context(self):
        """测试创建写作上下文"""
        context = WritingContext(
            novel_title="测试小说",
            outline_summary="修仙故事",
            previous_chapters=[],
            plot_direction="主角突破境界"
        )
        
        self.assertEqual(context.novel_title, "测试小说")
        self.assertEqual(context.plot_direction, "主角突破境界")

    def test_generate_chapter(self):
        """测试生成章节"""
        context = WritingContext(
            novel_title="修仙从逃出生天开始",
            outline_summary="现代修仙故事",
            previous_chapters=[],
            plot_direction="孔凡圣突破筑基期"
        )
        
        config = WritingConfig(target_word_count=2100)
        
        content = self.engine.generate_chapter(context, config)
        
        self.assertIsNotNone(content)
        self.mock_llm_client.generate.assert_called()

    def test_plan_plot(self):
        """测试规划剧情"""
        outline = Outline(
            id=OutlineId("outline-001"),
            novel_id=NovelId("novel-001"),
            premise="修仙故事",
            story_background="现代都市",
            world_setting="蓝星",
            main_plots=[
                PlotNode(
                    id="plot-001",
                    title="主角成长",
                    description="孔凡圣从凡人成长为强者",
                    type=PlotType.MAIN,
                    status=PlotStatus.ONGOING
                )
            ],
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        plot_nodes = self.engine.plan_plot(outline, 10, "主角突破境界")
        
        self.assertIsInstance(plot_nodes, list)

        self.assertTrue(len(plot_nodes) > 0)

    def test_apply_style(self):
        """测试应用文风"""
        content = "孔凡圣在丛林中奔跑。他回头看了一眼。 眼中闪过一丝金光。"
        styled_content = self.engine.apply_style(content, self.style_profile)
        
        self.assertIsNotNone(styled_content)


class TestWritingContext(unittest.TestCase):
    """测试写作上下文"""

    def test_context_creation(self):
        """测试上下文创建"""
        context = WritingContext(
            novel_title="测试小说",
            outline_summary="测试大纲",
            previous_chapters=["第一章内容"],
            plot_direction="测试方向"
        )
        
        self.assertEqual(context.novel_title, "测试小说")
        self.assertEqual(len(context.previous_chapters), 1)


if __name__ == '__main__':
    unittest.main()
