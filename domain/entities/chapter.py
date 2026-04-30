from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import List

from domain.exceptions import InvalidOperationError
from domain.types import ChapterId, ChapterStatus, NovelId


@dataclass(init=False)
class Chapter:
    id: ChapterId
    work_id: NovelId
    title: str
    content: str
    status: ChapterStatus
    created_at: datetime
    updated_at: datetime
    order_index: int = 0
    version: int = 1
    summary: str = ""
    characters_involved: List[str] = field(default_factory=list)

    def __init__(
        self,
        id: ChapterId,
        work_id: NovelId | None = None,
        title: str = "",
        content: str = "",
        status: ChapterStatus = ChapterStatus.DRAFT,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
        order_index: int = 0,
        version: int = 1,
        summary: str = "",
        characters_involved: List[str] | None = None,
        novel_id: NovelId | None = None,
        number: int | None = None,
    ) -> None:
        if work_id is None:
            work_id = novel_id
        if work_id is None:
            raise ValueError("work_id is required")
        if number is not None and not order_index:
            order_index = int(number)
        if created_at is None or updated_at is None:
            raise ValueError("created_at and updated_at are required")

        self.id = id
        self.work_id = work_id
        self.title = str(title or "")
        self.content = str(content or "")
        self.status = status
        self.created_at = created_at
        self.updated_at = updated_at
        self.order_index = int(order_index or 0)
        self.version = int(version or 1)
        self.summary = str(summary or "")
        self.characters_involved = list(characters_involved or [])

    @property
    def novel_id(self) -> NovelId:
        return self.work_id

    @novel_id.setter
    def novel_id(self, value: NovelId) -> None:
        self.work_id = value

    @property
    def number(self) -> int:
        return self.order_index

    @number.setter
    def number(self, value: int) -> None:
        self.order_index = int(value or 0)

    @property
    def word_count(self) -> int:
        from application.services.v1.text_metrics import count_effective_characters

        return count_effective_characters(self.content)

    @property
    def is_published(self) -> bool:
        return self.status == ChapterStatus.PUBLISHED

    def update_content(self, new_content: str, updated_at: datetime) -> None:
        self.content = str(new_content or "")
        self.updated_at = updated_at
        self.version += 1

    def update_title(self, new_title: str, updated_at: datetime) -> None:
        self.title = str(new_title or "")
        self.updated_at = updated_at
        self.version += 1

    def move_to(self, order_index: int, updated_at: datetime) -> None:
        self.order_index = max(0, int(order_index))
        self.updated_at = updated_at

    def publish(self, published_at: datetime) -> None:
        if self.status == ChapterStatus.PUBLISHED:
            raise InvalidOperationError("chapter already published")
        self.status = ChapterStatus.PUBLISHED
        self.updated_at = published_at

    def unpublish(self, unpublished_at: datetime) -> None:
        if self.status == ChapterStatus.DRAFT:
            raise InvalidOperationError("chapter is not published")
        self.status = ChapterStatus.DRAFT
        self.updated_at = unpublished_at
