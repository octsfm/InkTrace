from abc import ABC, abstractmethod
from typing import List, Optional

from domain.entities.structural_draft import StructuralDraft


class IStructuralDraftRepository(ABC):
    @abstractmethod
    def find_by_id(self, item_id: str) -> Optional[StructuralDraft]:
        pass

    @abstractmethod
    def find_by_project_id(self, project_id: str) -> List[StructuralDraft]:
        pass

    @abstractmethod
    def save(self, item: StructuralDraft) -> None:
        pass
