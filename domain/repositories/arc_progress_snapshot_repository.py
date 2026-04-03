from abc import ABC, abstractmethod
from typing import List

from domain.entities.arc_progress_snapshot import ArcProgressSnapshot


class IArcProgressSnapshotRepository(ABC):
    @abstractmethod
    def save(self, snapshot: ArcProgressSnapshot) -> None:
        pass

    @abstractmethod
    def list_by_arc(self, arc_id: str) -> List[ArcProgressSnapshot]:
        pass
