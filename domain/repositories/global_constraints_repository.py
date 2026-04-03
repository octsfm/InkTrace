from abc import ABC, abstractmethod
from typing import Optional

from domain.entities.global_constraints import GlobalConstraints


class IGlobalConstraintsRepository(ABC):
    @abstractmethod
    def find_by_project_id(self, project_id: str) -> Optional[GlobalConstraints]:
        pass

    @abstractmethod
    def save(self, item: GlobalConstraints) -> None:
        pass
