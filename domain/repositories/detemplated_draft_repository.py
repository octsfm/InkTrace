from abc import ABC, abstractmethod
from typing import List, Optional

from domain.entities.detemplated_draft import DetemplatedDraft


class IDetemplatedDraftRepository(ABC):
    @abstractmethod
    def find_by_id(self, item_id: str) -> Optional[DetemplatedDraft]:
        pass

    @abstractmethod
    def find_by_project_id(self, project_id: str) -> List[DetemplatedDraft]:
        pass

    @abstractmethod
    def save(self, item: DetemplatedDraft) -> None:
        pass
