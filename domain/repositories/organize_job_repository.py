from abc import ABC, abstractmethod
from typing import Optional

from domain.entities.organize_job import OrganizeJob
from domain.types import NovelId


class IOrganizeJobRepository(ABC):
    @abstractmethod
    def find_by_novel_id(self, novel_id: NovelId) -> Optional[OrganizeJob]:
        pass

    @abstractmethod
    def save(self, job: OrganizeJob) -> None:
        pass

    @abstractmethod
    def delete(self, novel_id: NovelId) -> None:
        pass

