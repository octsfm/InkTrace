from __future__ import annotations

import json
from pathlib import Path

from domain.entities.ai.models import ConflictDetectionResult, ConflictGuardDecision, ConflictGuardRecord
from domain.repositories.ai.conflict_guard_repository import ConflictGuardRepository
from infrastructure.database.session import get_database_path


class FileConflictGuardStore(ConflictGuardRepository):
    def __init__(self, file_path: Path | str | None = None) -> None:
        self._file_path = Path(file_path) if file_path else get_database_path().with_name("conflict_guard.json")

    def save_record(self, record: ConflictGuardRecord) -> ConflictGuardRecord:
        payload = self._load_payload()
        payload["records"][record.record_id] = record.model_dump(mode="json")
        self._save_payload(payload)
        return record

    def get_record(self, record_id: str) -> ConflictGuardRecord:
        payload = self._load_payload()
        raw = payload["records"].get(record_id)
        if raw is None:
            raise ValueError("conflict_record_not_found")
        return ConflictGuardRecord.model_validate(raw)

    def list_records(
        self,
        *,
        work_id: str = "",
        chapter_id: str = "",
        candidate_draft_id: str = "",
        candidate_version_id: str = "",
    ) -> list[ConflictGuardRecord]:
        payload = self._load_payload()
        items = [ConflictGuardRecord.model_validate(item) for item in payload["records"].values()]
        if work_id:
            items = [item for item in items if item.work_id == work_id]
        if chapter_id:
            items = [item for item in items if item.chapter_id == chapter_id]
        if candidate_draft_id:
            items = [item for item in items if item.candidate_draft_id == candidate_draft_id]
        if candidate_version_id:
            items = [item for item in items if item.candidate_version_id == candidate_version_id]
        return sorted(items, key=lambda item: item.created_at, reverse=True)

    def save_result(self, result: ConflictDetectionResult) -> ConflictDetectionResult:
        payload = self._load_payload()
        payload["results"][result.result_id] = result.model_dump(mode="json")
        self._save_payload(payload)
        return result

    def get_result(self, result_id: str) -> ConflictDetectionResult:
        payload = self._load_payload()
        raw = payload["results"].get(result_id)
        if raw is None:
            raise ValueError("conflict_result_not_found")
        return ConflictDetectionResult.model_validate(raw)

    def save_decision(self, decision: ConflictGuardDecision) -> ConflictGuardDecision:
        payload = self._load_payload()
        payload["decisions"][decision.decision_id] = decision.model_dump(mode="json")
        self._save_payload(payload)
        return decision

    def _load_payload(self) -> dict[str, dict[str, dict[str, object]]]:
        if not self._file_path.exists():
            return {"records": {}, "results": {}, "decisions": {}}
        raw = json.loads(self._file_path.read_text(encoding="utf-8"))
        return {
            "records": dict(raw.get("records", {})),
            "results": dict(raw.get("results", {})),
            "decisions": dict(raw.get("decisions", {})),
        }

    def _save_payload(self, payload: dict[str, dict[str, dict[str, object]]]) -> None:
        self._file_path.parent.mkdir(parents=True, exist_ok=True)
        self._file_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
