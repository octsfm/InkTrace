from abc import ABC, abstractmethod
from typing import List, Optional

from domain.entities.draft_integrity_check import DraftIntegrityCheck


class IDraftIntegrityCheckRepository(ABC):
    @abstractmethod
    def find_by_id(self, item_id: str) -> Optional[DraftIntegrityCheck]:
        pass

    @abstractmethod
    def find_by_project_id(self, project_id: str) -> List[DraftIntegrityCheck]:
        pass

    @abstractmethod
    def save(self, item: DraftIntegrityCheck) -> None:
        pass
