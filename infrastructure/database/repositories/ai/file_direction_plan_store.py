from __future__ import annotations

import json
from pathlib import Path
from threading import RLock

from domain.entities.ai.models import (
    DirectionPlanSnapshot,
    DirectionProposal,
    DirectionSelection,
    PlanConfirmation,
    WritingTask,
    WritingTaskStatus,
)
from domain.repositories.ai.direction_plan_repository import DirectionPlanRepository
from infrastructure.database.session import get_database_path


_DIRECTION_PLAN_FILE_LOCK = RLock()


class FileDirectionPlanStore(DirectionPlanRepository):
    def __init__(self, file_path: Path | str | None = None) -> None:
        self._file_path = Path(file_path) if file_path else get_database_path().with_name("direction_plan.json")

    def save_direction_proposal(self, proposal: DirectionProposal) -> DirectionProposal:
        with _DIRECTION_PLAN_FILE_LOCK:
            payload = self._load_payload()
            payload["direction_proposals"][proposal.direction_proposal_id] = proposal.model_dump(mode="json")
            self._save_payload(payload)
        return proposal

    def get_direction_proposal(self, direction_proposal_id: str) -> DirectionProposal:
        raw = self._load_payload()["direction_proposals"].get(direction_proposal_id)
        if raw is None:
            raise ValueError("direction_proposal_not_found")
        return DirectionProposal.model_validate(raw)

    def list_direction_proposals(self, work_id: str, chapter_id: str = "") -> list[DirectionProposal]:
        items = [
            DirectionProposal.model_validate(item)
            for item in self._load_payload()["direction_proposals"].values()
            if item.get("work_id") == work_id
        ]
        if chapter_id:
            items = [item for item in items if item.chapter_id == chapter_id]
        return sorted(items, key=lambda item: (item.created_at, item.direction_proposal_id), reverse=True)

    def save_direction_selection(self, selection: DirectionSelection) -> DirectionSelection:
        with _DIRECTION_PLAN_FILE_LOCK:
            payload = self._load_payload()
            payload["direction_selections"][selection.selection_id] = selection.model_dump(mode="json")
            self._save_payload(payload)
        return selection

    def get_direction_selection(self, selection_id: str) -> DirectionSelection:
        raw = self._load_payload()["direction_selections"].get(selection_id)
        if raw is None:
            raise ValueError("direction_selection_not_found")
        return DirectionSelection.model_validate(raw)

    def save_plan_confirmation(self, confirmation: PlanConfirmation) -> PlanConfirmation:
        with _DIRECTION_PLAN_FILE_LOCK:
            payload = self._load_payload()
            payload["plan_confirmations"][confirmation.confirmation_id] = confirmation.model_dump(mode="json")
            self._save_payload(payload)
        return confirmation

    def get_plan_confirmation(self, confirmation_id: str) -> PlanConfirmation:
        raw = self._load_payload()["plan_confirmations"].get(confirmation_id)
        if raw is None:
            raise ValueError("plan_confirmation_not_found")
        return PlanConfirmation.model_validate(raw)

    def save_writing_task(self, task: WritingTask) -> WritingTask:
        with _DIRECTION_PLAN_FILE_LOCK:
            payload = self._load_payload()
            payload["writing_tasks"][task.writing_task_id] = task.model_dump(mode="json")
            self._save_payload(payload)
        return task

    def get_writing_task(self, writing_task_id: str) -> WritingTask:
        raw = self._load_payload()["writing_tasks"].get(writing_task_id)
        if raw is None:
            raise ValueError("writing_task_not_found")
        return WritingTask.model_validate(raw)

    def list_writing_tasks(self, work_id: str, chapter_id: str = "") -> list[WritingTask]:
        items = [
            WritingTask.model_validate(item)
            for item in self._load_payload()["writing_tasks"].values()
            if item.get("work_id") == work_id
        ]
        if chapter_id:
            items = [item for item in items if item.chapter_id == chapter_id or item.target_chapter_id == chapter_id]
        return sorted(items, key=lambda item: (item.created_at, item.writing_task_id), reverse=True)

    def get_active_writing_task(self, work_id: str, chapter_id: str = "") -> WritingTask | None:
        items = [
            item
            for item in self.list_writing_tasks(work_id, chapter_id=chapter_id)
            if item.status == WritingTaskStatus.READY and item.stale_status == "fresh"
        ]
        return items[0] if items else None

    def save_direction_plan_snapshot(self, snapshot: DirectionPlanSnapshot) -> DirectionPlanSnapshot:
        with _DIRECTION_PLAN_FILE_LOCK:
            payload = self._load_payload()
            payload["direction_plan_snapshots"][snapshot.snapshot_id] = snapshot.model_dump(mode="json")
            self._save_payload(payload)
        return snapshot

    def get_direction_plan_snapshot(self, snapshot_id: str) -> DirectionPlanSnapshot:
        raw = self._load_payload()["direction_plan_snapshots"].get(snapshot_id)
        if raw is None:
            raise ValueError("direction_plan_snapshot_not_found")
        return DirectionPlanSnapshot.model_validate(raw)

    def _load_payload(self) -> dict[str, dict[str, object]]:
        with _DIRECTION_PLAN_FILE_LOCK:
            if not self._file_path.exists():
                return self._empty_payload()
            payload = json.loads(self._file_path.read_text(encoding="utf-8"))
            for key, value in self._empty_payload().items():
                payload.setdefault(key, value)
            return payload

    def _save_payload(self, payload: dict[str, dict[str, object]]) -> None:
        with _DIRECTION_PLAN_FILE_LOCK:
            self._file_path.parent.mkdir(parents=True, exist_ok=True)
            self._file_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def _empty_payload(self) -> dict[str, dict[str, object]]:
        return {
            "direction_proposals": {},
            "direction_selections": {},
            "plan_confirmations": {},
            "writing_tasks": {},
            "direction_plan_snapshots": {},
        }
