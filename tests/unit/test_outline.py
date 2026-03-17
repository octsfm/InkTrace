"""
Outline聚合根单元测试

作者：孔利群
"""

# 文件路径：tests/unit/test_outline.py


import unittest
from datetime import datetime

from domain.entities.outline import Outline, VolumeOutline, PlotNode
from domain.types import OutlineId, NovelId, PlotType, PlotStatus


class TestOutline(unittest.TestCase):
    """测试Outline聚合根"""

    def setUp(self):
        """测试前置设置"""
# 文件：模块：test_outline

        self.outline_id = OutlineId("outline-001")
        self.novel_id = NovelId("novel-001")
        self.now = datetime.now()

    def test_create_outline(self):
        """测试创建大纲"""
        outline = Outline(
            id=self.outline_id,
            novel_id=self.novel_id,
            premise="当现代科学与古老修仙碰撞",
            story_background="科技与修仙共存的现代都市",
            world_setting="蓝星、龙国、修仙宗门",
            created_at=self.now,
            updated_at=self.now
        )
        self.assertEqual(outline.id, self.outline_id)
        self.assertEqual(outline.novel_id, self.novel_id)
        self.assertEqual(outline.premise, "当现代科学与古老修仙碰撞")

    def test_update_premise(self):
        """测试更新核心设定"""
# 文件：模块：test_outline

        outline = Outline(
            id=self.outline_id,
            novel_id=self.novel_id,
            premise="原设定",
            story_background="",
            world_setting="",
            created_at=self.now,
            updated_at=self.now
        )
        outline.update_premise("新设定", self.now)
        self.assertEqual(outline.premise, "新设定")

    def test_add_volume(self):
        """测试添加分卷"""
        outline = Outline(
            id=self.outline_id,
            novel_id=self.novel_id,
            premise="",
            story_background="",
            world_setting="",
            created_at=self.now,
            updated_at=self.now
        )
        volume = VolumeOutline(
            number=1,
            title="蓝星篇",
            summary="主角在蓝星的成长",
            target_word_count=300000
        )
        outline.add_volume(volume, self.now)
        self.assertEqual(len(outline.volumes), 1)
        self.assertEqual(outline.volumes[0].title, "蓝星篇")

    def test_get_volume(self):
        """测试获取分卷"""
# 文件：模块：test_outline

        outline = Outline(
            id=self.outline_id,
            novel_id=self.novel_id,
            premise="",
            story_background="",
            world_setting="",
            volumes=[
                VolumeOutline(
                    number=1,
                    title="蓝星篇",
                    summary="主角在蓝星的成长",
                    target_word_count=300000
                )
            ],
            created_at=self.now,
            updated_at=self.now
        )
        volume = outline.get_volume(1)
        self.assertIsNotNone(volume)
        self.assertEqual(volume.title, "蓝星篇")

    def test_add_main_plot(self):
        """测试添加主线剧情"""
        outline = Outline(
            id=self.outline_id,
            novel_id=self.novel_id,
            premise="",
            story_background="",
            world_setting="",
            created_at=self.now,
            updated_at=self.now
        )
        plot_node = PlotNode(
            id="plot-001",
            title="主角踏上修仙路",
            description="主角因意外进入修仙世界",
            type=PlotType.MAIN,
            status=PlotStatus.PLANNED
        )
        outline.add_main_plot(plot_node, self.now)
        self.assertEqual(len(outline.main_plots), 1)

    def test_add_sub_plot(self):
        """测试添加支线剧情"""
# 文件：模块：test_outline

        outline = Outline(
            id=self.outline_id,
            novel_id=self.novel_id,
            premise="",
            story_background="",
            world_setting="",
            created_at=self.now,
            updated_at=self.now
        )
        plot_node = PlotNode(
            id="plot-002",
            title="主角结识红颜",
            description="主角在都市认识女主角",
            type=PlotType.SUB,
            status=PlotStatus.PLANNED
        )
        outline.add_sub_plot(plot_node, self.now)
        self.assertEqual(len(outline.sub_plots), 1)

    def test_update_plot_status(self):
        """测试更新剧情状态"""
        outline = Outline(
            id=self.outline_id,
            novel_id=self.novel_id,
            premise="",
            story_background="",
            world_setting="",
            main_plots=[
                PlotNode(
                    id="plot-001",
                    title="主角踏上修仙路",
                    description="",
                    type=PlotType.MAIN,
                    status=PlotStatus.PLANNED
                )
            ],
            created_at=self.now,
            updated_at=self.now
        )
        outline.update_plot_status("plot-001", PlotStatus.ONGOING, self.now)
        self.assertEqual(outline.main_plots[0].status, PlotStatus.ONGOING)

    def test_get_plot_by_id(self):
        """测试根据ID获取剧情"""
# 文件：模块：test_outline

        outline = Outline(
            id=self.outline_id,
            novel_id=self.novel_id,
            premise="",
            story_background="",
            world_setting="",
            main_plots=[
                PlotNode(
                    id="plot-001",
                    title="主角踏上修仙路",
                    description="",
                    type=PlotType.MAIN,
                    status=PlotStatus.PLANNED
                )
            ],
            sub_plots=[
                PlotNode(
                    id="plot-002",
                    title="主角结识红颜",
                    description="",
                    type=PlotType.SUB,
                    status=PlotStatus.PLANNED
                )
            ],
            created_at=self.now,
            updated_at=self.now
        )
        plot = outline.get_plot_by_id("plot-002")
        self.assertIsNotNone(plot)
        self.assertEqual(plot.title, "主角结识红颜")


class TestVolumeOutline(unittest.TestCase):
    """测试VolumeOutline"""

    def test_create_volume(self):
        """测试创建分卷"""
# 文件：模块：test_outline

        volume = VolumeOutline(
            number=1,
            title="蓝星篇",
            summary="主角在蓝星的成长",
            target_word_count=300000
        )
        self.assertEqual(volume.number, 1)
        self.assertEqual(volume.title, "蓝星篇")
        self.assertEqual(volume.target_word_count, 300000)


class TestPlotNode(unittest.TestCase):
    """测试PlotNode"""

    def test_create_plot_node(self):
        """测试创建剧情节点"""
# 文件：模块：test_outline

        plot_node = PlotNode(
            id="plot-001",
            title="主角踏上修仙路",
            description="主角因意外进入修仙世界",
            type=PlotType.MAIN,
            status=PlotStatus.PLANNED
        )
        self.assertEqual(plot_node.id, "plot-001")
        self.assertEqual(plot_node.type, PlotType.MAIN)
        self.assertEqual(plot_node.status, PlotStatus.PLANNED)

    def test_is_main_plot(self):
        """测试是否主线剧情"""
        main_plot = PlotNode(
            id="plot-001",
            title="主线",
            description="",
            type=PlotType.MAIN,
            status=PlotStatus.PLANNED
        )
        sub_plot = PlotNode(
            id="plot-002",
            title="支线",
            description="",
            type=PlotType.SUB,
            status=PlotStatus.PLANNED
        )
        self.assertTrue(main_plot.is_main)
        self.assertFalse(sub_plot.is_main)

    def test_is_completed(self):
        """测试是否完成"""
# 文件：模块：test_outline

        planned = PlotNode(
            id="plot-001",
            title="测试",
            description="",
            type=PlotType.MAIN,
            status=PlotStatus.PLANNED
        )
        completed = PlotNode(
            id="plot-002",
            title="测试",
            description="",
            type=PlotType.MAIN,
            status=PlotStatus.COMPLETED
        )
        self.assertFalse(planned.is_completed)
        self.assertTrue(completed.is_completed)


if __name__ == '__main__':
    unittest.main()
