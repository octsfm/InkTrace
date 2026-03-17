"""
TXT文件解析器模块

作者：孔利群
"""

# 文件路径：infrastructure/file/txt_parser.py


import re
import os
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass


@dataclass
class ChapterData:
    """章节数据"""
    number: int
    title: str
    content: str
    word_count: int


class TxtParser:
    """
# 文件：模块：txt_parser

    TXT文件解析器
    
    用于解析小说TXT文件，自动识别章节结构。
    """

    CHAPTER_PATTERNS = [
        r'第[一二三四五六七八九十百千万零\d]+章\s+[^\n]+',
        r'第[一二三四五六七八九十百千万零\d]+节\s+[^\n]+',
        r'Chapter\s*\d+[:\s]*[^\n]*',
        r'[一二三四五六七八九十]+[、.．]\s*[^\n]+',
    ]

    SECTION_PATTERNS = [
        r'^[^\n]{1,20}$',
    ]

    def detect_chapter_pattern(self, filepath: str) -> Optional[re.Pattern]:
        """
# 文件：模块：txt_parser

        检测章节标题模式
        
        Args:
            filepath: 文件路径
            
        Returns:
            匹配的正则表达式模式，未检测到则返回None
        """
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        for pattern_str in self.CHAPTER_PATTERNS:
            matches = re.findall(pattern_str, content, re.MULTILINE)
            if len(matches) >= 2:
                return re.compile(pattern_str, re.MULTILINE)
        
        return None

    def parse_chapters(self, filepath: str) -> List[Dict]:
        """
# 文件：模块：txt_parser

        解析章节
        
        Args:
            filepath: 文件路径
            
        Returns:
            章节列表，每个元素包含number, title, content, word_count
        """
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        pattern = self.detect_chapter_pattern(filepath)
        if not pattern:
            return []
        
        matches = list(pattern.finditer(content))
        chapters = []
        
        for i, match in enumerate(matches):
            start = match.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(content)
            
            title_line = match.group().strip()
            chapter_content = content[start:end].strip()
            
            number = self._extract_chapter_number(title_line)
            title = self._extract_chapter_title(title_line)
            
            chapters.append({
                'number': number,
                'title': title,
                'content': chapter_content,
                'word_count': self.count_words(chapter_content)
            })
        
        return chapters

    def parse_novel_file(self, filepath: str) -> Dict:
        """
# 文件：模块：txt_parser

        解析小说文件
        
        Args:
            filepath: 文件路径
            
        Returns:
            包含intro和chapters的字典
        """
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        pattern = self.detect_chapter_pattern(filepath)
        
        if pattern:
            first_match = pattern.search(content)
            if first_match:
                intro = content[:first_match.start()].strip()
            else:
                intro = ""
        else:
            intro = content
        
        chapters = self.parse_chapters(filepath)
        
        return {
            'intro': intro,
            'chapters': chapters
        }

    def parse_outline_file(self, filepath: str) -> Dict:
        """
# 文件：模块：txt_parser

        解析大纲文件
        
        Args:
            filepath: 文件路径
            
        Returns:
            大纲数据字典
        """
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        result = {
            'genre': '',
            'story_background': '',
            'world_setting': '',
            'target_word_count': '',
            'raw_content': content
        }
        
        lines = content.split('\n')
        
        section_map = {
            '题材': 'genre',
            '故事背景': 'story_background',
            '世界背景': 'world_setting',
            '世界观': 'world_setting',
            '预计字数': 'target_word_count',
            '字数': 'target_word_count'
        }
        
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
            for key, field in section_map.items():
                if key in line and len(line) < 20:
                    if field == 'target_word_count':
                        j = i + 1
                        while j < len(lines):
                            next_line = lines[j].strip()
                            if next_line:
                                numbers = re.findall(r'[\d万]+', next_line)
                                if numbers:
                                    result[field] = numbers[0]
                                break
                            j += 1
                    else:
                        j = i + 1
                        while j < len(lines):
                            next_line = lines[j].strip()
                            if next_line and len(next_line) < 50 and not any(k in next_line for k in section_map.keys()):
                                result[field] = next_line
                                break
                            j += 1
                    break
            
            i += 1
        
        return result

    def extract_sections(self, content: str) -> List[Dict]:
        """
# 文件：模块：txt_parser

        提取章节内容
        
        Args:
            content: 文本内容
            
        Returns:
            章节列表
        """
        lines = content.split('\n')
        sections = []
        current_title = ""
        current_content = []
        
        for line in lines:
            stripped = line.strip()
            if stripped and len(stripped) < 30 and not stripped.startswith('　'):
                if current_title:
                    sections.append({
                        'title': current_title,
                        'content': '\n'.join(current_content).strip()
                    })
                current_title = stripped
                current_content = []
            else:
                current_content.append(line)
        
        if current_title:
            sections.append({
                'title': current_title,
                'content': '\n'.join(current_content).strip()
            })
        
        return sections

    def count_words(self, text: str) -> int:
        """
# 文件：模块：txt_parser

        统计字数
        
        Args:
            text: 文本内容
            
        Returns:
            字数
        """
        cleaned = text.replace(' ', '').replace('\n', '').replace('\r', '')
        return len(cleaned)

    def _extract_chapter_number(self, title_line: str) -> int:
        """
# 文件：模块：txt_parser

        提取章节号
        
        Args:
            title_line: 章节标题行
            
        Returns:
            章节号
        """
        chinese_nums = {
            '零': 0, '一': 1, '二': 2, '三': 3, '四': 4,
            '五': 5, '六': 6, '七': 7, '八': 8, '九': 9,
            '十': 10, '百': 100, '千': 1000, '万': 10000
        }
        
        match = re.search(r'第([一二三四五六七八九十百千万零\d]+)', title_line)
        if not match:
            return 0
        
        num_str = match.group(1)
        
        if num_str.isdigit():
            return int(num_str)
        
        result = 0
        temp = 0
        for char in num_str:
            if char in chinese_nums:
                val = chinese_nums[char]
                if val >= 10:
                    if temp == 0:
                        temp = 1
                    result += temp * val
                    temp = 0
                else:
                    temp = temp * 10 + val if temp else val
        
        return result + temp

    def _extract_chapter_title(self, title_line: str) -> str:
        """
# 文件：模块：txt_parser

        提取章节标题
        
        Args:
            title_line: 章节标题行
            
        Returns:
            章节标题
        """
        match = re.search(r'第[一二三四五六七八九十百千万零\d]+[章节]\s*(.+)', title_line)
        if match:
            return match.group(1).strip()
        return title_line
