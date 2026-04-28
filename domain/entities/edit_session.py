from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass
class EditSession:
    work_id: str
    last_open_chapter_id: str
    cursor_position: int
    scroll_top: int
    updated_at: datetime

    def open_chapter(self, chapter_id: str, updated_at: datetime) -> None:
        self.last_open_chapter_id = str(chapter_id or "")
        self.updated_at = updated_at

    def update_viewport(self, cursor_position: int, scroll_top: int, updated_at: datetime) -> None:
        cursor = int(cursor_position)
        scroll = int(scroll_top)
        self.cursor_position = cursor if cursor >= 0 else 0
        self.scroll_top = scroll if scroll >= 0 else 0
        self.updated_at = updated_at
