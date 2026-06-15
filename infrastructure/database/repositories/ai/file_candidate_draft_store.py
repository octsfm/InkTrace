from __future__ import annotations

import json
from pathlib import Path

from domain.entities.ai.models import CandidateDraft, CandidateDraftVersion, RewriteInstruction, RewriteRequest, RevisionRound
from domain.repositories.ai.candidate_draft_repository import CandidateDraftRepository
from infrastructure.database.models import initialize_schema
from infrastructure.database.session import get_database_path
from infrastructure.database.v1 import connect


class FileCandidateDraftStore(CandidateDraftRepository):
    def __init__(
        self,
        file_path: Path | str | None = None,
        *,
        database_path: Path | str | None = None,
    ) -> None:
        self._file_path = Path(file_path) if file_path else get_database_path().with_name("candidate_drafts.json")
        self._database_path = Path(database_path).resolve() if database_path else get_database_path()

    def save(self, draft: CandidateDraft) -> CandidateDraft:
        payload = self._load_payload()
        payload["drafts"][draft.candidate_draft_id] = draft.model_dump(mode="json")
        self._save_payload(payload)
        self._project_draft_to_sqlite(draft)
        return draft

    def get(self, candidate_draft_id: str) -> CandidateDraft:
        payload = self._load_payload()
        raw = payload["drafts"].get(candidate_draft_id)
        if raw is None:
            raise ValueError("candidate_draft_not_found")
        return CandidateDraft.model_validate(raw)

    def list_by_work(self, work_id: str, chapter_id: str = "") -> list[CandidateDraft]:
        payload = self._load_payload()
        items = [CandidateDraft.model_validate(item) for item in payload["drafts"].values() if item.get("work_id") == work_id]
        if chapter_id:
            items = [item for item in items if item.chapter_id == chapter_id]
        return sorted(items, key=lambda item: item.created_at, reverse=True)

    def save_version(self, version: CandidateDraftVersion) -> CandidateDraftVersion:
        payload = self._load_payload()
        payload["versions"][version.candidate_version_id] = version.model_dump(mode="json")
        self._save_payload(payload)
        return version

    def get_version(self, candidate_version_id: str) -> CandidateDraftVersion:
        payload = self._load_payload()
        raw = payload["versions"].get(candidate_version_id)
        if raw is None:
            raise ValueError("candidate_version_not_found")
        return CandidateDraftVersion.model_validate(raw)

    def list_versions(self, candidate_draft_id: str) -> list[CandidateDraftVersion]:
        payload = self._load_payload()
        items = [
            CandidateDraftVersion.model_validate(item)
            for item in payload["versions"].values()
            if item.get("candidate_draft_id") == candidate_draft_id
        ]
        return sorted(items, key=lambda item: (item.version_no, item.created_at))

    def save_rewrite_request(self, request: RewriteRequest) -> RewriteRequest:
        payload = self._load_payload()
        payload["rewrite_requests"][request.rewrite_request_id] = request.model_dump(mode="json")
        self._save_payload(payload)
        return request

    def get_rewrite_request(self, rewrite_request_id: str) -> RewriteRequest:
        payload = self._load_payload()
        raw = payload["rewrite_requests"].get(rewrite_request_id)
        if raw is None:
            raise ValueError("rewrite_request_not_found")
        return RewriteRequest.model_validate(raw)

    def list_rewrite_requests(self, candidate_draft_id: str) -> list[RewriteRequest]:
        payload = self._load_payload()
        items = [
            RewriteRequest.model_validate(item)
            for item in payload["rewrite_requests"].values()
            if item.get("candidate_draft_id") == candidate_draft_id
        ]
        return sorted(items, key=lambda item: item.created_at)

    def save_rewrite_instruction(self, instruction: RewriteInstruction) -> RewriteInstruction:
        payload = self._load_payload()
        payload["rewrite_instructions"][instruction.rewrite_instruction_id] = instruction.model_dump(mode="json")
        self._save_payload(payload)
        return instruction

    def list_rewrite_instructions(self, rewrite_request_id: str) -> list[RewriteInstruction]:
        payload = self._load_payload()
        items = [
            RewriteInstruction.model_validate(item)
            for item in payload["rewrite_instructions"].values()
            if item.get("rewrite_request_id") == rewrite_request_id
        ]
        return sorted(items, key=lambda item: item.created_at)

    def save_revision_round(self, revision_round: RevisionRound) -> RevisionRound:
        payload = self._load_payload()
        payload["revision_rounds"][revision_round.revision_round_id] = revision_round.model_dump(mode="json")
        self._save_payload(payload)
        return revision_round

    def get_revision_round(self, revision_round_id: str) -> RevisionRound:
        payload = self._load_payload()
        raw = payload["revision_rounds"].get(revision_round_id)
        if raw is None:
            raise ValueError("revision_round_not_found")
        return RevisionRound.model_validate(raw)

    def list_revision_rounds(self, candidate_draft_id: str) -> list[RevisionRound]:
        payload = self._load_payload()
        items = [
            RevisionRound.model_validate(item)
            for item in payload["revision_rounds"].values()
            if item.get("candidate_draft_id") == candidate_draft_id
        ]
        return sorted(items, key=lambda item: (item.round_no, item.created_at))

    def _load_payload(self) -> dict[str, dict[str, dict[str, object]]]:
        if not self._file_path.exists():
            return {
                "drafts": {},
                "versions": {},
                "rewrite_requests": {},
                "rewrite_instructions": {},
                "revision_rounds": {},
            }
        raw = json.loads(self._file_path.read_text(encoding="utf-8"))
        if "drafts" in raw or "versions" in raw or "rewrite_requests" in raw or "rewrite_instructions" in raw or "revision_rounds" in raw:
            return {
                "drafts": dict(raw.get("drafts", {})),
                "versions": dict(raw.get("versions", {})),
                "rewrite_requests": dict(raw.get("rewrite_requests", {})),
                "rewrite_instructions": dict(raw.get("rewrite_instructions", {})),
                "revision_rounds": dict(raw.get("revision_rounds", {})),
            }
        return {
            "drafts": dict(raw),
            "versions": {},
            "rewrite_requests": {},
            "rewrite_instructions": {},
            "revision_rounds": {},
        }

    def _save_payload(self, payload: dict[str, dict[str, dict[str, object]]]) -> None:
        self._file_path.parent.mkdir(parents=True, exist_ok=True)
        self._file_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def _project_draft_to_sqlite(self, draft: CandidateDraft) -> None:
        conn = connect(self._database_path)
        try:
            initialize_schema(conn)
            conn.execute(
                """
                INSERT INTO candidate_drafts (
                    candidate_draft_id, work_id, chapter_id, status,
                    applied_at, revision_count, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(candidate_draft_id) DO UPDATE SET
                    work_id = excluded.work_id,
                    chapter_id = excluded.chapter_id,
                    status = excluded.status,
                    applied_at = excluded.applied_at,
                    revision_count = excluded.revision_count,
                    created_at = excluded.created_at,
                    updated_at = excluded.updated_at
                """,
                (
                    draft.candidate_draft_id,
                    draft.work_id,
                    draft.chapter_id,
                    draft.status.value,
                    draft.applied_at or None,
                    draft.revision_count,
                    draft.created_at,
                    draft.updated_at,
                ),
            )
            conn.commit()
        finally:
            conn.close()
