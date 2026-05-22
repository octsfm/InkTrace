from __future__ import annotations

from abc import ABC, abstractmethod

from domain.entities.ai.models import (
    DirectionPlanSnapshot,
    DirectionProposal,
    DirectionSelection,
    PlanConfirmation,
    WritingTask,
)


class DirectionPlanRepository(ABC):
    @abstractmethod
    def save_direction_proposal(self, proposal: DirectionProposal) -> DirectionProposal:
        raise NotImplementedError

    @abstractmethod
    def get_direction_proposal(self, direction_proposal_id: str) -> DirectionProposal:
        raise NotImplementedError

    @abstractmethod
    def list_direction_proposals(self, work_id: str, chapter_id: str = "") -> list[DirectionProposal]:
        raise NotImplementedError

    @abstractmethod
    def save_direction_selection(self, selection: DirectionSelection) -> DirectionSelection:
        raise NotImplementedError

    @abstractmethod
    def get_direction_selection(self, selection_id: str) -> DirectionSelection:
        raise NotImplementedError

    @abstractmethod
    def save_plan_confirmation(self, confirmation: PlanConfirmation) -> PlanConfirmation:
        raise NotImplementedError

    @abstractmethod
    def get_plan_confirmation(self, confirmation_id: str) -> PlanConfirmation:
        raise NotImplementedError

    @abstractmethod
    def save_writing_task(self, task: WritingTask) -> WritingTask:
        raise NotImplementedError

    @abstractmethod
    def get_writing_task(self, writing_task_id: str) -> WritingTask:
        raise NotImplementedError

    @abstractmethod
    def list_writing_tasks(self, work_id: str, chapter_id: str = "") -> list[WritingTask]:
        raise NotImplementedError

    @abstractmethod
    def get_active_writing_task(self, work_id: str, chapter_id: str = "") -> WritingTask | None:
        raise NotImplementedError

    @abstractmethod
    def save_direction_plan_snapshot(self, snapshot: DirectionPlanSnapshot) -> DirectionPlanSnapshot:
        raise NotImplementedError

    @abstractmethod
    def get_direction_plan_snapshot(self, snapshot_id: str) -> DirectionPlanSnapshot:
        raise NotImplementedError
