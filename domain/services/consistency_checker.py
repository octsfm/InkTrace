"""
连贯性检查领域服务模块

作者：孔利群
"""

import re
from typing import List, Dict, Optional
from dataclasses import dataclass, field

from domain.entities.chapter import Chapter
from domain.entities.character import Character


@dataclass
class Inconsistency:
    """不一致项"""
    type: str
    description: str
    severity: str = "低"
    suggestion: str = ""


@dataclass
class ConsistencyReport:
    """连贯性检查报告"""
    is_valid: bool
    inconsistencies: List[Inconsistency]
    warnings: List[str] = field(default_factory=list)


class ConsistencyChecker:
    """
    连贯性检查领域服务
    
    检查章节内容与已有内容的一致性。
    """

    def check(
        self, 
        new_chapter: Chapter, 
        existing_chapters: List[Chapter],
        characters: List[Character] = None,
        timeline: List[Dict] = None
    ) -> ConsistencyReport:
        """
        检查新章节与已有内容的连贯性
        
        Args:
            new_chapter: 新章节
            existing_chapters: 已有章节列表
            characters: 人物列表
            timeline: 时间线
            
        Returns:
            连贯性检查报告
        """
        inconsistencies = []
        warnings = []
        
        if characters:
            for character in characters:
                char_issues = self.check_character_state(character, new_chapter)
                inconsistencies.extend(char_issues)
        
        if timeline:
            timeline_issues = self.check_timeline(timeline, new_chapter)
            inconsistencies.extend(timeline_issues)
        
        if existing_chapters:
            plot_issues = self.check_plot_continuity(new_chapter, existing_chapters)
            inconsistencies.extend(plot_issues)
        
        is_valid = len(inconsistencies) == 0
        
        return ConsistencyReport(
            is_valid=is_valid,
            inconsistencies=inconsistencies,
            warnings=warnings
        )

    def check_character_state(
        self, 
        character: Character, 
        chapter: Chapter
    ) -> List[Inconsistency]:
        """
        检查人物状态一致性
        
        Args:
            character: 人物实体
            chapter: 章节实体
            
        Returns:
            不一致项列表
        """
        inconsistencies = []
        
        cultivation_keywords = {
            "凡人": 0,
            "练气": 1,
            "筑基": 2,
            "金丹": 3,
            "元婴": 4,
            "化神": 5,
            "合体": 6,
            "大乘": 7,
            "渡劫": 8,
            "仙人": 9
        }
        
        current_level = 0
        for keyword, level in cultivation_keywords.items():
            if keyword in character.current_state:
                current_level = level
                break
        
        for keyword, level in cultivation_keywords.items():
            pattern = rf'{keyword}[期境]?'
            if re.search(pattern, chapter.content):
                if level < current_level:
                    inconsistencies.append(Inconsistency(
                        type="人物状态",
                        description=f"人物{character.name}的修为境界可能出现倒退：从{character.current_state}变为{keyword}",
                        severity="高",
                        suggestion=f"请检查{character.name}的修为状态是否正确"
                    ))
                elif level > current_level + 1:
                    warnings_msg = f"人物{character.name}的修为境界可能跳级：从{character.current_state}变为{keyword}"
        
        return inconsistencies

    def check_timeline(
        self, 
        timeline: List[Dict], 
        chapter: Chapter
    ) -> List[Inconsistency]:
        """
        检查时间线一致性
        
        Args:
            timeline: 时间线事件列表
            chapter: 章节实体
            
        Returns:
            不一致项列表
        """
        inconsistencies = []
        
        if not timeline:
            return inconsistencies
        
        last_event = timeline[-1]
        last_chapter = last_event.get('chapter_number', 0)
        
        if chapter.number <= last_chapter:
            return inconsistencies
        
        return inconsistencies

    def check_plot_continuity(
        self, 
        new_chapter: Chapter, 
        existing_chapters: List[Chapter]
    ) -> List[Inconsistency]:
        """
        检查剧情连贯性
        
        Args:
            new_chapter: 新章节
            existing_chapters: 已有章节列表
            
        Returns:
            不一致项列表
        """
        inconsistencies = []
        
        if not existing_chapters:
            return inconsistencies
        
        last_chapter = max(existing_chapters, key=lambda c: c.number)
        
        return inconsistencies

    def check_foreshadowing(
        self, 
        foreshadowings: List[Dict], 
        chapter: Chapter
    ) -> List[Inconsistency]:
        """
        检查伏笔回收
        
        Args:
            foreshadowings: 伏笔列表
            chapter: 章节实体
            
        Returns:
            不一致项列表
        """
        inconsistencies = []
        
        return inconsistencies
