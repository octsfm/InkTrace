"""
Novel聚合根模块

作者：孔利群
"""

# 文件路径：domain/entities/novel.py


from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

from domain.types import NovelId, ChapterId, CharacterId, OutlineId
from domain.entities.chapter import Chapter
from domain.entities.character import Character
from domain.entities.outline import Outline


@dataclass
class Novel:
    """
    小说聚合根
    
    表示一部小说，整合章节、人物、大纲等。
    """
# 文件：模块：novel

    id: NovelId
    title: str
    author: str
    genre: str
    target_word_count: int
    created_at: datetime
    updated_at: datetime
    current_word_count: int = 0
    chapters: List[Chapter] = field(default_factory=list)
    characters: List[Character] = field(default_factory=list)
    outline: Optional[Outline] = None

    @property
    def chapter_count(self) -> int:
        """获取章节数量"""
        return len(self.chapters)

    def add_chapter(self, chapter: Chapter, updated_at: datetime) -> None:
        """
# 文件：模块：novel

        添加章节
        
        Args:
            chapter: 章节实体
            updated_at: 更新时间
        """
        existing = self.get_chapter(chapter.id)
        if existing:
            self.chapters.remove(existing)
        self.chapters.append(chapter)
        self.chapters.sort(key=lambda c: c.number)
        self._recalculate_word_count()
        self.updated_at = updated_at

    def get_chapter(self, chapter_id: ChapterId) -> Optional[Chapter]:
        """
# 文件：模块：novel

        获取指定ID的章节
        
        Args:
            chapter_id: 章节ID
            
        Returns:
            章节实体，不存在则返回None
        """
        for chapter in self.chapters:
            if chapter.id == chapter_id:
                return chapter
        return None

    def get_chapter_by_number(self, number: int) -> Optional[Chapter]:
        """
# 文件：模块：novel

        根据章节号获取章节
        
        Args:
            number: 章节号
            
        Returns:
            章节实体，不存在则返回None
        """
        for chapter in self.chapters:
            if chapter.number == number:
                return chapter
        return None

    def get_latest_chapters(self, count: int) -> List[Chapter]:
        """
# 文件：模块：novel

        获取最新的N个章节
        
        Args:
            count: 数量
            
        Returns:
            章节列表，按章节号倒序排列
        """
        sorted_chapters = sorted(self.chapters, key=lambda c: c.number, reverse=True)
        return sorted_chapters[:count]

    def add_character(self, character: Character, updated_at: datetime) -> None:
        """
# 文件：模块：novel

        添加人物
        
        Args:
            character: 人物实体
            updated_at: 更新时间
        """
        existing = self.get_character(character.id)
        if existing:
            self.characters.remove(existing)
        self.characters.append(character)
        self.updated_at = updated_at

    def get_character(self, character_id: CharacterId) -> Optional[Character]:
        """
# 文件：模块：novel

        获取指定ID的人物
        
        Args:
            character_id: 人物ID
            
        Returns:
            人物实体，不存在则返回None
        """
        for character in self.characters:
            if character.id == character_id:
                return character
        return None

    def get_protagonist(self) -> Optional[Character]:
        """
# 文件：模块：novel

        获取主角
        
        Returns:
            主角实体，不存在则返回None
        """
        for character in self.characters:
            if character.is_protagonist:
                return character
        return None

    def set_outline(self, outline: Outline, updated_at: datetime) -> None:
        """
# 文件：模块：novel

        设置大纲
        
        Args:
            outline: 大纲实体
            updated_at: 更新时间
        """
        self.outline = outline
        self.updated_at = updated_at

    def _recalculate_word_count(self) -> None:
        """重新计算总字数"""
# 文件：模块：novel

        self.current_word_count = sum(chapter.word_count for chapter in self.chapters)
