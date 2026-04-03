from abc import ABC, abstractmethod
from typing import List, Optional

from domain.entities.plot_arc import PlotArc


class IPlotArcRepository(ABC):
    @abstractmethod
    def save(self, arc: PlotArc) -> None:
        pass

    @abstractmethod
    def find_by_project(self, project_id: str) -> List[PlotArc]:
        pass

    @abstractmethod
    def find_by_id(self, arc_id: str) -> Optional[PlotArc]:
        pass

    @abstractmethod
    def delete_by_project(self, project_id: str) -> None:
        pass
