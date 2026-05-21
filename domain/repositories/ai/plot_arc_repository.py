from __future__ import annotations

from abc import ABC, abstractmethod

from domain.entities.ai.models import MasterArc, SequenceArc, VolumeArc


class PlotArcRepository(ABC):
    @abstractmethod
    def save_master_arc(self, arc: MasterArc) -> MasterArc:
        raise NotImplementedError

    @abstractmethod
    def get_master_arc(self, work_id: str) -> MasterArc | None:
        raise NotImplementedError

    @abstractmethod
    def save_volume_arc(self, arc: VolumeArc) -> VolumeArc:
        raise NotImplementedError

    @abstractmethod
    def get_active_volume_arc(self, work_id: str, chapter_no: int = 0) -> VolumeArc | None:
        raise NotImplementedError

    @abstractmethod
    def list_volume_arcs(self, work_id: str) -> list[VolumeArc]:
        raise NotImplementedError

    @abstractmethod
    def save_sequence_arc(self, arc: SequenceArc) -> SequenceArc:
        raise NotImplementedError

    @abstractmethod
    def get_active_sequence_arc(self, work_id: str, chapter_no: int = 0) -> SequenceArc | None:
        raise NotImplementedError

    @abstractmethod
    def list_sequence_arcs(self, work_id: str) -> list[SequenceArc]:
        raise NotImplementedError
