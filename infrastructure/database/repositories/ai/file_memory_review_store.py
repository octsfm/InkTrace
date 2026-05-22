from __future__ import annotations

import json
from pathlib import Path

from domain.entities.ai.models import (
    MemoryReviewGate,
    MemoryRevisionApplyResult,
    MemoryRevisionDecision,
    MemoryUpdateSuggestion,
    StoryMemoryRevision,
    StoryStateRevision,
)
from domain.repositories.ai.memory_review_repository import MemoryReviewRepository
from infrastructure.database.session import get_database_path


class FileMemoryReviewStore(MemoryReviewRepository):
    def __init__(self, file_path: Path | str | None = None) -> None:
        self._file_path = Path(file_path) if file_path else get_database_path().with_name("memory_review.json")

    def claim_idempotency_key(self, *, idempotency_key: str, operation_name: str) -> None:
        normalized = str(idempotency_key or "").strip()
        if not normalized:
            raise ValueError("idempotency_key_required")
        payload = self._load_payload()
        existing = payload["idempotency_keys"].get(normalized)
        if existing is not None:
            raise ValueError("idempotency_key_conflict")
        payload["idempotency_keys"][normalized] = {"operation_name": operation_name}
        self._save_payload(payload)

    def save_suggestion(self, suggestion: MemoryUpdateSuggestion) -> MemoryUpdateSuggestion:
        payload = self._load_payload()
        payload["suggestions"][suggestion.id] = suggestion.model_dump(mode="json")
        self._save_payload(payload)
        return suggestion

    def get_suggestion(self, suggestion_id: str) -> MemoryUpdateSuggestion:
        payload = self._load_payload()
        raw = payload["suggestions"].get(suggestion_id)
        if raw is None:
            raise ValueError("memory_suggestion_not_found")
        return MemoryUpdateSuggestion.model_validate(raw)

    def list_suggestions(self, *, work_id: str, chapter_id: str = "", gate_id: str = "") -> list[MemoryUpdateSuggestion]:
        payload = self._load_payload()
        items = [MemoryUpdateSuggestion.model_validate(item) for item in payload["suggestions"].values() if item.get("work_id") == work_id]
        if chapter_id:
            items = [item for item in items if item.chapter_id == chapter_id]
        if gate_id:
            gate = self.get_gate(gate_id)
            items = [item for item in items if item.id in gate.suggestion_ids]
        return sorted(items, key=lambda item: item.created_at, reverse=True)

    def save_gate(self, gate: MemoryReviewGate) -> MemoryReviewGate:
        payload = self._load_payload()
        payload["gates"][gate.gate_id] = gate.model_dump(mode="json")
        self._save_payload(payload)
        return gate

    def get_gate(self, gate_id: str) -> MemoryReviewGate:
        payload = self._load_payload()
        raw = payload["gates"].get(gate_id)
        if raw is None:
            raise ValueError("memory_gate_not_found")
        return MemoryReviewGate.model_validate(raw)

    def list_gates(self, *, work_id: str, chapter_id: str = "") -> list[MemoryReviewGate]:
        payload = self._load_payload()
        items = [MemoryReviewGate.model_validate(item) for item in payload["gates"].values() if item.get("work_id") == work_id]
        if chapter_id:
            items = [item for item in items if item.chapter_id == chapter_id]
        return sorted(items, key=lambda item: item.open_at, reverse=True)

    def save_story_memory_revision(self, revision: StoryMemoryRevision) -> StoryMemoryRevision:
        payload = self._load_payload()
        payload["story_memory_revisions"][revision.id] = revision.model_dump(mode="json")
        self._save_payload(payload)
        return revision

    def save_story_state_revision(self, revision: StoryStateRevision) -> StoryStateRevision:
        payload = self._load_payload()
        payload["story_state_revisions"][revision.id] = revision.model_dump(mode="json")
        self._save_payload(payload)
        return revision

    def get_story_memory_revision(self, revision_id: str) -> StoryMemoryRevision:
        payload = self._load_payload()
        raw = payload["story_memory_revisions"].get(revision_id)
        if raw is None:
            raise ValueError("memory_revision_not_found")
        return StoryMemoryRevision.model_validate(raw)

    def get_story_state_revision(self, revision_id: str) -> StoryStateRevision:
        payload = self._load_payload()
        raw = payload["story_state_revisions"].get(revision_id)
        if raw is None:
            raise ValueError("memory_revision_not_found")
        return StoryStateRevision.model_validate(raw)

    def list_story_memory_revisions(self, *, work_id: str, chapter_id: str = "", source_suggestion_id: str = "") -> list[StoryMemoryRevision]:
        payload = self._load_payload()
        items = [StoryMemoryRevision.model_validate(item) for item in payload["story_memory_revisions"].values() if item.get("work_id") == work_id]
        if chapter_id:
            items = [item for item in items if item.chapter_id == chapter_id]
        if source_suggestion_id:
            items = [item for item in items if item.source_suggestion_id == source_suggestion_id]
        return sorted(items, key=lambda item: item.created_at, reverse=True)

    def list_story_state_revisions(self, *, work_id: str, chapter_id: str = "", source_suggestion_id: str = "") -> list[StoryStateRevision]:
        payload = self._load_payload()
        items = [StoryStateRevision.model_validate(item) for item in payload["story_state_revisions"].values() if item.get("work_id") == work_id]
        if chapter_id:
            items = [item for item in items if item.chapter_id == chapter_id]
        if source_suggestion_id:
            items = [item for item in items if item.source_suggestion_id == source_suggestion_id]
        return sorted(items, key=lambda item: item.created_at, reverse=True)

    def save_decision(self, decision: MemoryRevisionDecision) -> MemoryRevisionDecision:
        payload = self._load_payload()
        payload["decisions"][decision.id] = decision.model_dump(mode="json")
        self._save_payload(payload)
        return decision

    def list_decisions(self, revision_id: str) -> list[MemoryRevisionDecision]:
        payload = self._load_payload()
        items = [
            MemoryRevisionDecision.model_validate(item)
            for item in payload["decisions"].values()
            if item.get("revision_id") == revision_id
        ]
        return sorted(items, key=lambda item: item.decided_at, reverse=True)

    def save_apply_result(self, result: MemoryRevisionApplyResult) -> MemoryRevisionApplyResult:
        payload = self._load_payload()
        payload["apply_results"][result.id] = result.model_dump(mode="json")
        self._save_payload(payload)
        return result

    def get_apply_result(self, result_id: str) -> MemoryRevisionApplyResult:
        payload = self._load_payload()
        raw = payload["apply_results"].get(result_id)
        if raw is None:
            raise ValueError("memory_apply_result_not_found")
        return MemoryRevisionApplyResult.model_validate(raw)

    def _load_payload(self) -> dict[str, dict[str, object]]:
        if not self._file_path.exists():
            return self._empty_payload()
        payload = json.loads(self._file_path.read_text(encoding="utf-8"))
        for key in self._empty_payload():
            payload.setdefault(key, {})
        return payload

    def _save_payload(self, payload: dict[str, dict[str, object]]) -> None:
        self._file_path.parent.mkdir(parents=True, exist_ok=True)
        self._file_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    @staticmethod
    def _empty_payload() -> dict[str, dict[str, object]]:
        return {
            "idempotency_keys": {},
            "suggestions": {},
            "gates": {},
            "story_memory_revisions": {},
            "story_state_revisions": {},
            "decisions": {},
            "apply_results": {},
        }
