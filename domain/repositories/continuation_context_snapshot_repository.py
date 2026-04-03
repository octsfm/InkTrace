from abc import ABC, abstractmethod
from typing import List, Optional

from domain.entities.continuation_context_snapshot import ContinuationContextSnapshot


class IContinuationContextSnapshotRepository(ABC):
    @abstractmethod
    def find_latest(self, project_id: str, chapter_id: str = "") -> Optional[ContinuationContextSnapshot]:
        pass

    @abstractmethod
    def list_by_project_id(self, project_id: str, limit: int = 20) -> List[ContinuationContextSnapshot]:
        pass

    @abstractmethod
    def save(self, item: ContinuationContextSnapshot) -> None:
        pass
