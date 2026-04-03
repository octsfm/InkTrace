from abc import ABC, abstractmethod
from typing import List, Optional

from domain.entities.chapter_analysis_memory import ChapterAnalysisMemory


class IChapterAnalysisMemoryRepository(ABC):
    @abstractmethod
    def find_by_id(self, item_id: str) -> Optional[ChapterAnalysisMemory]:
        pass

    @abstractmethod
    def find_by_chapter_id(self, chapter_id: str) -> List[ChapterAnalysisMemory]:
        pass

    @abstractmethod
    def save(self, item: ChapterAnalysisMemory) -> None:
        pass
