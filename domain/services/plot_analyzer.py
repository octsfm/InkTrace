"""
剧情分析领域服务模块

作者：孔利群
"""

# 文件路径：domain/services/plot_analyzer.py


import re
from typing import List, Dict, Optional
from dataclasses import dataclass
from collections import Counter

from domain.entities.chapter import Chapter
from domain.types import PlotType, PlotStatus


@dataclass
class CharacterInfo:
    """人物信息"""
    name: str
    aliases: List[str]
    appearance_count: int
    first_appearance_chapter: int


@dataclass
class TimelineEvent:
    """时间线事件"""
# 文件：模块：plot_analyzer

    chapter_number: int
    event_description: str
    characters_involved: List[str]


@dataclass
class ForeshadowingInfo:
    """伏笔信息"""
    description: str
    chapter_number: int
    status: str


class PlotAnalyzer:
    """
# 文件：模块：plot_analyzer

    剧情分析领域服务
    
    分析小说的剧情结构，提取人物、时间线、伏笔等。
    """

    def analyze(self, chapters: List[Chapter]) -> Dict:
        """
# 文件：模块：plot_analyzer

        分析小说剧情结构
        
        Args:
            chapters: 章节列表
            
        Returns:
            分析结果字典
        """
        characters = self.extract_characters(chapters)
        timeline = self.build_timeline(chapters)
        foreshadowings = self.extract_foreshadowings(chapters)
        
        return {
            'characters': characters,
            'timeline': timeline,
            'foreshadowings': foreshadowings
        }

    def extract_characters(self, chapters: List[Chapter]) -> List[Dict]:
        """
# 文件：模块：plot_analyzer

        提取人物信息
        
        Args:
            chapters: 章节列表
            
        Returns:
            人物信息列表
        """
        character_mentions: Dict[str, Dict] = {}
        
        name_patterns = [
            r'[\u4e00-\u9fa5]{2,4}(?=说|道|想|看|听|笑|哭|喊|叫)',
            r'[\u4e00-\u9fa5]{2,4}(?=在|是|有|被|把|让|给|向|对)',
            r'"([^"]+)"[^"]*?([^\s"]{2,4})[^"]*?"',
        ]
        
        for chapter in chapters:
            content = chapter.content
            
            for pattern in name_patterns:
                matches = re.findall(pattern, content)
                for match in matches:
                    name = match if isinstance(match, str) else match[-1]
                    name = name.strip()
                    
                    if len(name) >= 2 and len(name) <= 4:
                        if name not in character_mentions:
                            character_mentions[name] = {
                                'name': name,
                                'aliases': [],
                                'appearance_count': 0,
                                'first_appearance_chapter': chapter.number
                            }
                        character_mentions[name]['appearance_count'] += 1
        
        characters = list(character_mentions.values())
        characters.sort(key=lambda x: x['appearance_count'], reverse=True)
        
        return characters[:20]

    def build_timeline(self, chapters: List[Chapter]) -> List[Dict]:
        """
# 文件：模块：plot_analyzer

        构建时间线
        
        Args:
            chapters: 章节列表
            
        Returns:
            时间线事件列表
        """
        timeline = []
        
        time_patterns = [
            r'第[一二三四五六七八九十\d]+[天日年月]',
            r'[一二三四五六七八九十\d]+[天日年月][前后]',
            r'[今明后昨前][天日年]',
            r'\d+年后',
            r'\d+天后',
        ]
        
        for chapter in chapters:
            events = []
            sentences = re.split(r'[。！？\n]', chapter.content)
            
            for sentence in sentences:
                sentence = sentence.strip()
                if len(sentence) < 5:
                    continue
                
                has_time = False
                for pattern in time_patterns:
                    if re.search(pattern, sentence):
                        has_time = True
                        break
                
                if has_time or len(events) == 0:
                    events.append({
                        'chapter_number': chapter.number,
                        'event_description': sentence[:100],
                        'characters_involved': self._extract_names_from_text(sentence)
                    })
            
            if events:
                timeline.extend(events[:3])
        
        return timeline

    def extract_foreshadowings(self, chapters: List[Chapter]) -> List[Dict]:
        """
# 文件：模块：plot_analyzer

        提取伏笔
        
        Args:
            chapters: 章节列表
            
        Returns:
            伏笔信息列表
        """
        foreshadowings = []
        
        foreshadow_patterns = [
            r'[^。！？]*(?:神秘|奇怪|未知|隐约|仿佛|似乎|好像)[^。！？]*',
            r'[^。！？]*(?:等待|时机|觉醒|秘密|真相)[^。！？]*',
            r'[^。！？]*(?:伏笔|埋下|暗示)[^。！？]*',
        ]
        
        for chapter in chapters:
            for pattern in foreshadow_patterns:
                matches = re.findall(pattern, chapter.content)
                for match in matches:
                    match = match.strip()
                    if len(match) > 10:
                        foreshadowings.append({
                            'description': match[:200],
                            'chapter_number': chapter.number,
                            'status': '未回收'
                        })
        
        return foreshadowings[:10]

    def _extract_names_from_text(self, text: str) -> List[str]:
        """
# 文件：模块：plot_analyzer

        从文本中提取人名
        
        Args:
            text: 文本内容
            
        Returns:
            人名列表
        """
        names = []
        pattern = r'[\u4e00-\u9fa5]{2,4}(?=说|道|想|看|听|笑|哭|喊|叫|的)'
        matches = re.findall(pattern, text)
        
        for match in matches:
            if len(match) >= 2 and len(match) <= 4:
                names.append(match)
        
        return list(set(names))
