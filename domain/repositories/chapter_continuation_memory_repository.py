from abc import ABC, abstractmethod
from typing import List, Optional

from domain.entities.chapter_continuation_memory import ChapterContinuationMemory


class IChapterContinuationMemoryRepository(ABC):
    @abstractmethod
    def find_by_id(self, item_id: str) -> Optional[ChapterContinuationMemory]:
        pass

    @abstractmethod
    def find_by_chapter_id(self, chapter_id: str) -> List[ChapterContinuationMemory]:
        pass

    @abstractmethod
    def save(self, item: ChapterContinuationMemory) -> None:
        pass
