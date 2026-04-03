from abc import ABC, abstractmethod
from typing import List

from domain.entities.chapter_arc_binding import ChapterArcBinding


class IChapterArcBindingRepository(ABC):
    @abstractmethod
    def save(self, binding: ChapterArcBinding) -> None:
        pass

    @abstractmethod
    def list_by_project(self, project_id: str) -> List[ChapterArcBinding]:
        pass

    @abstractmethod
    def list_by_chapter(self, chapter_id: str) -> List[ChapterArcBinding]:
        pass

    @abstractmethod
    def delete_by_project(self, project_id: str) -> None:
        pass
