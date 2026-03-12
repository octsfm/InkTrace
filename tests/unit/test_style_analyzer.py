"""
文风分析领域服务单元测试

作者：孔利群
"""

import unittest
from datetime import datetime

from domain.entities.chapter import Chapter
from domain.types import ChapterId, NovelId, ChapterStatus
from domain.services.style_analyzer import StyleAnalyzer
from domain.value_objects.style_profile import StyleProfile


class TestStyleAnalyzer(unittest.TestCase):
    """测试StyleAnalyzer"""

    def setUp(self):
        """测试前置设置"""
        self.analyzer = StyleAnalyzer()
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

    def test_analyze_empty_chapters(self):
        """测试分析空章节列表"""
        profile = self.analyzer.analyze([])
        self.assertIsInstance(profile, StyleProfile)

    def test_analyze_single_chapter(self):
        """测试分析单个章节"""
        content = """孔凡圣在丛林中奔跑，身后传来追兵的脚步声。
他回头看了一眼，眼中闪过一丝金光。
"绝对不能被抓住！"他心中暗想。
"""
        chapter = self._create_chapter(content)
        profile = self.analyzer.analyze([chapter])
        
        self.assertIsInstance(profile, StyleProfile)
        self.assertIsInstance(profile.dialogue_style, str)

    def test_analyze_vocabulary(self):
        """测试词汇分析"""
        content = "孔凡圣奔跑在丛林中。孔凡圣回头看了一眼。孔凡圣眼中闪过金光。"
        result = self.analyzer.analyze_vocabulary(content)
        
        self.assertIsInstance(result, dict)
        self.assertIn("高频词", result)

    def test_analyze_sentence_patterns(self):
        """测试句式分析"""
        content = "孔凡圣在丛林中奔跑。他回头看了一眼。眼中闪过一丝金光。"
        patterns = self.analyzer.analyze_sentence_patterns(content)
        
        self.assertIsInstance(patterns, list)

    def test_analyze_rhetoric(self):
        """测试修辞分析"""
        content = "他的眼神如同星辰般闪耀，仿佛能看穿一切。"
        result = self.analyzer.analyze_rhetoric(content)
        
        self.assertIsInstance(result, dict)

    def test_extract_dialogue_style(self):
        """测试对话风格提取"""
        content = '''
        "绝对不能被抓住！"他心中暗想。
        "快跑！"身后传来喊声。
        孔凡圣咬紧牙关，继续向前奔跑。
        '''
        style = self.analyzer.extract_dialogue_style(content)
        
        self.assertIsInstance(style, str)

    def test_analyze_multiple_chapters(self):
        """测试分析多个章节"""
        chapters = [
            self._create_chapter("孔凡圣在丛林中奔跑。他回头看了一眼。", 1),
            self._create_chapter("冰冷刺骨的河水包裹着他。他心中涌起庆幸。", 2),
            self._create_chapter("坐在车里，他回想着这两天的经历。", 3)
        ]
        profile = self.analyzer.analyze(chapters)
        
        self.assertIsInstance(profile, StyleProfile)
        self.assertTrue(len(profile.sample_sentences) > 0)


class TestStyleProfileGeneration(unittest.TestCase):
    """测试文风特征生成"""

    def setUp(self):
        self.analyzer = StyleAnalyzer()

    def test_generate_profile_with_content(self):
        """测试生成文风特征"""
        content = """
        孔凡圣在丛林中拼命奔跑，胸膛剧烈起伏。
        "呼......呼......"他大口喘着粗气。
        身后的追兵越来越近，他能听到恶犬的咆哮声。
        眼前出现了一道微弱的光线，如同希望之光。
        """
        profile = self.analyzer.analyze_vocabulary(content)
        
        self.assertIsInstance(profile, dict)


if __name__ == '__main__':
    unittest.main()
