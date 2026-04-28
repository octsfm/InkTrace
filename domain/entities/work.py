from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass
class Work:
    id: str
    title: str
    author: str
    created_at: datetime
    updated_at: datetime
    current_word_count: int = 0

    def rename(self, title: str, updated_at: datetime) -> None:
        self.title = str(title or "").strip()
        self.updated_at = updated_at

    def update_word_count(self, value: int, updated_at: datetime) -> None:
        count = int(value)
        self.current_word_count = count if count >= 0 else 0
        self.updated_at = updated_at
