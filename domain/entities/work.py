from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(init=False)
class Work:
    id: str
    title: str
    author: str
    created_at: datetime
    updated_at: datetime
    word_count: int = 0

    def __init__(
        self,
        id: str,
        title: str,
        author: str,
        created_at: datetime,
        updated_at: datetime,
        word_count: int = 0,
        current_word_count: int | None = None,
    ) -> None:
        self.id = str(id)
        self.title = str(title or "")
        self.author = str(author or "")
        self.created_at = created_at
        self.updated_at = updated_at
        count = word_count if current_word_count is None else current_word_count
        self.word_count = max(0, int(count or 0))

    @property
    def current_word_count(self) -> int:
        return self.word_count

    @current_word_count.setter
    def current_word_count(self, value: int) -> None:
        self.word_count = max(0, int(value or 0))

    def rename(self, title: str, updated_at: datetime) -> None:
        self.title = str(title or "").strip()
        self.updated_at = updated_at

    def update_word_count(self, value: int, updated_at: datetime) -> None:
        self.word_count = max(0, int(value or 0))
        self.updated_at = updated_at
