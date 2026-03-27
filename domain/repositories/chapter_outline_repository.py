from abc import ABC, abstractmethod
from typing import Optional

from domain.entities.chapter_outline import ChapterOutline
from domain.types import ChapterId


class IChapterOutlineRepository(ABC):
    @abstractmethod
    def find_by_chapter_id(self, chapter_id: ChapterId) -> Optional[ChapterOutline]:
        pass

    @abstractmethod
    def save(self, outline: ChapterOutline) -> None:
        pass
