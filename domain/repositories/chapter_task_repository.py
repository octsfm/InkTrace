from abc import ABC, abstractmethod
from typing import List, Optional

from domain.entities.chapter_task import ChapterTask


class IChapterTaskRepository(ABC):
    @abstractmethod
    def find_by_id(self, item_id: str) -> Optional[ChapterTask]:
        pass

    @abstractmethod
    def find_by_project_id(self, project_id: str) -> List[ChapterTask]:
        pass

    @abstractmethod
    def replace_by_project(self, project_id: str, items: List[ChapterTask]) -> None:
        pass

    @abstractmethod
    def save(self, item: ChapterTask) -> None:
        pass
