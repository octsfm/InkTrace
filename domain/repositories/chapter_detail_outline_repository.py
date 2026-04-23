from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from domain.entities.chapter_detail_outline import ChapterDetailOutline
from domain.types import ChapterId


class IChapterDetailOutlineRepository(ABC):
    @abstractmethod
    def find_by_chapter_id(self, chapter_id: ChapterId) -> Optional[ChapterDetailOutline]:
        pass

    @abstractmethod
    def save(self, outline: ChapterDetailOutline) -> None:
        pass
