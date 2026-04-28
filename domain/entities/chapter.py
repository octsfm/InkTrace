"""
Chapter实体模块

作者：孔利群
"""

# 文件路径：domain/entities/chapter.py


from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List

from domain.types import ChapterId, NovelId, ChapterStatus
from domain.exceptions import InvalidOperationError


@dataclass
class Chapter:
    """
    章节实体
    
    表示小说中的一个章节，包含章节基本信息、内容和状态。
    """
# 文件：模块：chapter

    id: ChapterId
    novel_id: NovelId
    number: int
    title: str
    content: str
    status: ChapterStatus
    created_at: datetime
    updated_at: datetime
    order_index: int = 0
    version: int = 1
    summary: str = ""
    characters_involved: List[str] = field(default_factory=list)

    @property
    def word_count(self) -> int:
        """计算章节字数"""
        return len(self.content.replace(" ", "").replace("\n", "").replace("\r", ""))

    @property
    def is_published(self) -> bool:
        """检查章节是否已发布"""
# 文件：模块：chapter

        return self.status == ChapterStatus.PUBLISHED

    def update_content(self, new_content: str, updated_at: datetime) -> None:
        """
        更新章节内容
        
        Args:
            new_content: 新内容
            updated_at: 更新时间
        """
# 文件：模块：chapter

        self.content = new_content
        self.updated_at = updated_at
        self.version += 1

    def update_title(self, new_title: str, updated_at: datetime) -> None:
        """
        更新章节标题
        
        Args:
            new_title: 新标题
            updated_at: 更新时间
        """
# 文件：模块：chapter

        self.title = new_title
        self.updated_at = updated_at
        self.version += 1

    def move_to(self, order_index: int, updated_at: datetime) -> None:
        self.order_index = max(0, int(order_index))
        self.updated_at = updated_at

    def publish(self, published_at: datetime) -> None:
        """
        发布章节
        
        Args:
            published_at: 发布时间
            
        Raises:
            InvalidOperationError: 章节已发布
        """
# 文件：模块：chapter

        if self.status == ChapterStatus.PUBLISHED:
            raise InvalidOperationError("章节已发布，无法重复发布")
        self.status = ChapterStatus.PUBLISHED
        self.updated_at = published_at

    def unpublish(self, unpublished_at: datetime) -> None:
        """
        取消发布章节
        
        Args:
            unpublished_at: 取消发布时间
            
        Raises:
            InvalidOperationError: 章节未发布
        """
# 文件：模块：chapter

        if self.status == ChapterStatus.DRAFT:
            raise InvalidOperationError("章节未发布，无法取消发布")
        self.status = ChapterStatus.DRAFT
        self.updated_at = unpublished_at
