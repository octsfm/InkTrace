"""
剧情分析领域服务单元测试

作者：孔利群
"""

import unittest
from datetime import datetime

from domain.entities.chapter import Chapter
from domain.entities.novel import Novel
from domain.types import ChapterId, NovelId, ChapterStatus
from domain.services.plot_analyzer import PlotAnalyzer


class TestPlotAnalyzer(unittest.TestCase):
    """测试PlotAnalyzer"""

    def setUp(self):
        """测试前置设置"""
        self.analyzer = PlotAnalyzer()
        self.now = datetime.now()

    def _create_chapter(self, content: str, number: int = 1) -> Chapter:
        """创建测试章节"""
        return Chapter(
            id=ChapterId(f"chapter-{number:03d}"),
            novel_id=NovelId("novel-001"),
            number=number,
            title=f"第{number}章",
            content=content,
            status=ChapterStatus.DRAFT,
            created_at=self.now,
            updated_at=self.now
        )

    def test_extract_characters(self):
        """测试提取人物"""
        content = """
        孔凡圣在丛林中奔跑。
        菩提老祖看着他远去的背影。
        "孔凡圣，你跑不掉的！"菩提老祖喊道。
        """
        chapter = self._create_chapter(content)
        characters = self.analyzer.extract_characters([chapter])
        
        self.assertIsInstance(characters, list)
        self.assertTrue(len(characters) > 0)

    def test_build_timeline(self):
        """测试构建时间线"""
        chapters = [
            self._create_chapter("第一天，孔凡圣开始逃跑。", 1),
            self._create_chapter("第二天，他遇到了菩提老祖。", 2),
            self._create_chapter("第三天，他开始了修炼。", 3)
        ]
        timeline = self.analyzer.build_timeline(chapters)
        
        self.assertIsInstance(timeline, list)
        self.assertEqual(len(timeline), 3)

    def test_extract_foreshadowings(self):
        """测试提取伏笔"""
        content = """
        孔凡圣感觉到体内有一股神秘的力量在涌动，但他不知道那是什么。
        这股力量仿佛在等待某个时机觉醒。
        """
        chapter = self._create_chapter(content)
        foreshadowings = self.analyzer.extract_foreshadowings([chapter])
        
        self.assertIsInstance(foreshadowings, list)

    def test_analyze_empty_chapters(self):
        """测试分析空章节列表"""
        result = self.analyzer.analyze([])
        
        self.assertIn('characters', result)
        self.assertIn('timeline', result)
        self.assertIn('foreshadowings', result)

    def test_analyze_with_chapters(self):
        """测试分析有内容的章节"""
        chapters = [
            self._create_chapter("孔凡圣在丛林中奔跑，菩提老祖在后面追赶。", 1),
            self._create_chapter("他跳入河中，成功逃脱。", 2)
        ]
        result = self.analyzer.analyze(chapters)
        
        self.assertIn('characters', result)
        self.assertIn('timeline', result)
        self.assertTrue(len(result['characters']) > 0)


class TestCharacterExtraction(unittest.TestCase):
    """测试人物提取"""

    def setUp(self):
        self.analyzer = PlotAnalyzer()
        self.now = datetime.now()

    def test_extract_protagonist(self):
        """测试提取主角"""
        content = "孔凡圣是这本书的主角，他拥有特殊的能力。"
        chapter = Chapter(
            id=ChapterId("chapter-001"),
            novel_id=NovelId("novel-001"),
            number=1,
            title="第一章",
            content=content,
            status=ChapterStatus.DRAFT,
            created_at=self.now,
            updated_at=self.now
        )
        characters = self.analyzer.extract_characters([chapter])
        
        names = [c['name'] for c in characters]
        self.assertIn('孔凡圣', names)

    def test_extract_multiple_characters(self):
        """测试提取多个人物"""
        content = """
        孔凡圣看着菩提老祖。
        "徒儿，你来了。"菩提老祖说道。
        这时，女娲娘娘也出现了。
        """
        chapter = Chapter(
            id=ChapterId("chapter-001"),
            novel_id=NovelId("novel-001"),
            number=1,
            title="第一章",
            content=content,
            status=ChapterStatus.DRAFT,
            created_at=self.now,
            updated_at=self.now
        )
        characters = self.analyzer.extract_characters([chapter])
        
        self.assertTrue(len(characters) >= 2)


if __name__ == '__main__':
    unittest.main()
