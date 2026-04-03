from abc import ABC, abstractmethod
from typing import Optional

from domain.entities.style_requirements import StyleRequirements


class IStyleRequirementsRepository(ABC):
    @abstractmethod
    def find_by_project_id(self, project_id: str) -> Optional[StyleRequirements]:
        pass

    @abstractmethod
    def save(self, item: StyleRequirements) -> None:
        pass
