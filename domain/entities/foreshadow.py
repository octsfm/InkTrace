"""
伏笔实体

作者：孔利群
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List
from enum import Enum

from domain.types import ForeshadowId, NovelId, ChapterId


class ForeshadowStatus(Enum):
    """伏笔状态枚举"""
    PENDING = "pending"
    RESOLVED = "resolved"


@dataclass
class Foreshadow:
    """伏笔实体"""
    id: ForeshadowId
    novel_id: NovelId
    chapter_id: ChapterId
    content: str
    foreshadow_type: str = "plot"
    status: ForeshadowStatus = ForeshadowStatus.PENDING
    resolved_chapter_id: Optional[ChapterId] = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def is_pending(self) -> bool:
        return self.status == ForeshadowStatus.PENDING
    
    def is_resolved(self) -> bool:
        return self.status == ForeshadowStatus.RESOLVED
    
    def resolve(self, chapter_id: ChapterId) -> None:
        if self.status != ForeshadowStatus.PENDING:
            raise ValueError("只能解决待处理的伏笔")
        
        self.status = ForeshadowStatus.RESOLVED
        self.resolved_chapter_id = chapter_id
        self.updated_at = datetime.now()
    
    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "novel_id": str(self.novel_id),
            "chapter_id": str(self.chapter_id),
            "content": self.content,
            "foreshadow_type": self.foreshadow_type,
            "status": self.status.value,
            "resolved_chapter_id": str(self.resolved_chapter_id) if self.resolved_chapter_id else None,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Foreshadow":
        return cls(
            id=ForeshadowId(data["id"]),
            novel_id=NovelId(data["novel_id"]),
            chapter_id=ChapterId(data["chapter_id"]),
            content=data["content"],
            foreshadow_type=data.get("foreshadow_type", "plot"),
            status=ForeshadowStatus(data.get("status", "pending")),
            resolved_chapter_id=ChapterId(data["resolved_chapter_id"]) if data.get("resolved_chapter_id") else None,
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"])
        )
