"""
TXT解析器单元测试

作者：孔利群
"""

# 文件路径：tests/unit/test_txt_parser.py


import unittest
import os
import tempfile

from infrastructure.file.txt_parser import TxtParser


class TestTxtParser(unittest.TestCase):
    """测试TxtParser"""

    def setUp(self):
        """测试前置设置"""
# 文件：模块：test_txt_parser

        self.parser = TxtParser()
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """测试后清理"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _create_temp_file(self, content: str, filename: str = "test.txt") -> str:
        """创建临时测试文件"""
# 文件：模块：test_txt_parser

        filepath = os.path.join(self.temp_dir, filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return filepath

    def test_detect_chapter_pattern_number(self):
        """测试检测数字章节标题模式"""
        content = """第1章 开端
# 文件：模块：test_txt_parser

这是第一章的内容。

第2章 发展
这是第二章的内容。

第3章 高潮
这是第三章的内容。"""
        filepath = self._create_temp_file(content)
        pattern = self.parser.detect_chapter_pattern(filepath)
        self.assertIsNotNone(pattern)
        self.assertIn("第", pattern.pattern)

    def test_detect_chapter_pattern_chinese_number(self):
        """测试检测中文数字章节标题模式"""
        content = """第一章 开端
这是第一章的内容。

第二章 发展
这是第二章的内容。"""
# 文件：模块：test_txt_parser

        filepath = self._create_temp_file(content)
        pattern = self.parser.detect_chapter_pattern(filepath)
        self.assertIsNotNone(pattern)

    def test_parse_chapters(self):
        """测试解析章节"""
        content = """作品相关
# 文件：模块：test_txt_parser

简介
这是一部小说的简介。

第一卷 
第1章 跑
孔凡圣在丛林中奔跑...

第2章 逃出生天
冰冷刺骨的河水...

第3章 传道
坐在开往大使馆的车里..."""
        filepath = self._create_temp_file(content)
        chapters = self.parser.parse_chapters(filepath)
        
        self.assertEqual(len(chapters), 3)
        self.assertEqual(chapters[0]['number'], 1)
        self.assertEqual(chapters[0]['title'], "跑")
        self.assertIn("孔凡圣", chapters[0]['content'])
        self.assertEqual(chapters[1]['number'], 2)
        self.assertEqual(chapters[2]['number'], 3)

    def test_parse_chapters_empty_file(self):
        """测试解析空文件"""
# 文件：模块：test_txt_parser

        filepath = self._create_temp_file("")
        chapters = self.parser.parse_chapters(filepath)
        self.assertEqual(len(chapters), 0)

    def test_parse_novel_file(self):
        """测试解析小说文件"""
        content = """作品相关
# 文件：模块：test_txt_parser

简介
这是一部修仙小说。

第一卷 蓝星篇
第1章 跑
孔凡圣在丛林中奔跑，身后有追兵。

第2章 逃出生天
他跳入河中，成功逃脱。"""
        filepath = self._create_temp_file(content)
        result = self.parser.parse_novel_file(filepath)
        
        self.assertIn('intro', result)
        self.assertIn('chapters', result)
        self.assertEqual(len(result['chapters']), 2)
        self.assertIn("修仙小说", result['intro'])

    def test_parse_outline_file(self):
        """测试解析大纲文件"""
        content = """题材
现代修真

前期
现代都市修仙

科技飞速发展下的现代都市修仙

故事背景
主人公的修仙背景
梦境
大山压顶之梦

预计字数
总计800万"""
# 文件：模块：test_txt_parser

        filepath = self._create_temp_file(content)
        result = self.parser.parse_outline_file(filepath)
        
        self.assertIn('genre', result)
        self.assertEqual(result['genre'], '现代修真')
        self.assertIn('story_background', result)
        self.assertIn('target_word_count', result)

    def test_extract_section(self):
        """测试提取章节内容"""
        content = """标题1
# 文件：模块：test_txt_parser

内容1

标题2
内容2

标题3
内容3"""
        sections = self.parser.extract_sections(content)
        self.assertGreaterEqual(len(sections), 1)

    def test_word_count(self):
        """测试字数统计"""
# 文件：模块：test_txt_parser

        content = "这是一段测试内容，用于测试字数统计功能。"
        count = self.parser.count_words(content)
        self.assertEqual(count, 20)


class TestChapterDetection(unittest.TestCase):
    """测试章节检测"""

    def setUp(self):
        self.parser = TxtParser()
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _create_temp_file(self, content: str) -> str:
        filepath = os.path.join(self.temp_dir, "test.txt")
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return filepath

    def test_detect_with_prefix(self):
        """测试检测带前缀的章节"""
        content = """第一卷 蓝星篇
第1章 跑
内容1

第2章 逃出生天
内容2"""
# 文件：模块：test_txt_parser

        filepath = self._create_temp_file(content)
        chapters = self.parser.parse_chapters(filepath)
        self.assertEqual(len(chapters), 2)

    def test_detect_without_prefix(self):
        """测试检测无卷前缀的章节"""
        content = """第1章 开端
# 文件：模块：test_txt_parser

内容1

第2章 发展
内容2

第3章 高潮
内容3"""
        filepath = self._create_temp_file(content)
        chapters = self.parser.parse_chapters(filepath)
        self.assertEqual(len(chapters), 3)


if __name__ == '__main__':
    unittest.main()
