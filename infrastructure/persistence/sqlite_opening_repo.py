from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import TypeVar

from domain.entities.ai.opening_models import (
    OpeningBrief,
    OpeningDirection,
    OpeningDirectionBatch,
    OpeningDraftBatch,
    OpeningOriginalityReport,
    OpeningReferenceSession,
)
from domain.repositories.ai.opening_repository import OpeningRepository
from infrastructure.database.session import get_database_path

T = TypeVar("T")


class SQLiteOpeningRepository(OpeningRepository):
    _MODELS = {
        "brief": OpeningBrief,
        "reference_session": OpeningReferenceSession,
        "direction_batch": OpeningDirectionBatch,
        "draft_batch": OpeningDraftBatch,
        "originality_report": OpeningOriginalityReport,
    }

    def __init__(self, database_path: Path | str | None = None) -> None:
        self._database_path = Path(database_path).resolve() if database_path else get_database_path()
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        self._database_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self._database_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _initialize(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS opening_entities (
                    entity_type TEXT NOT NULL,
                    entity_id TEXT NOT NULL,
                    work_id TEXT NOT NULL,
                    parent_id TEXT NOT NULL DEFAULT '',
                    idempotency_key TEXT NOT NULL DEFAULT '',
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY(entity_type, entity_id)
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_opening_work ON opening_entities(work_id, entity_type, created_at)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_opening_parent ON opening_entities(parent_id, entity_type)")
            conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_opening_idempotency ON opening_entities(entity_type, idempotency_key) WHERE idempotency_key <> ''")

    def _save(self, entity_type: str, entity_id: str, value, *, parent_id: str = ""):
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO opening_entities(entity_type, entity_id, work_id, parent_id, idempotency_key, payload_json, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(entity_type, entity_id) DO UPDATE SET
                    work_id=excluded.work_id, parent_id=excluded.parent_id,
                    idempotency_key=excluded.idempotency_key, payload_json=excluded.payload_json,
                    updated_at=excluded.updated_at
                """,
                (entity_type, entity_id, value.work_id, parent_id, getattr(value, "idempotency_key", ""), json.dumps(value.model_dump(mode="json"), ensure_ascii=False), value.created_at, getattr(value, "updated_at", value.created_at)),
            )
        return value

    def _get(self, entity_type: str, entity_id: str):
        with self._connect() as conn:
            row = conn.execute("SELECT payload_json FROM opening_entities WHERE entity_type=? AND entity_id=?", (entity_type, entity_id)).fetchone()
        if row is None:
            return None
        return self._MODELS[entity_type].model_validate_json(row["payload_json"])

    def save_brief(self, value: OpeningBrief) -> OpeningBrief:
        return self._save("brief", value.brief_id, value)

    def get_brief(self, brief_id: str) -> OpeningBrief | None:
        return self._get("brief", brief_id)

    def save_reference_session(self, value: OpeningReferenceSession) -> OpeningReferenceSession:
        return self._save("reference_session", value.reference_session_id, value, parent_id=value.brief_id)

    def get_reference_session(self, session_id: str) -> OpeningReferenceSession | None:
        return self._get("reference_session", session_id)

    def list_reference_sessions(self, brief_id: str) -> list[OpeningReferenceSession]:
        return self._list("reference_session", parent_id=brief_id)

    def save_direction_batch(self, value: OpeningDirectionBatch) -> OpeningDirectionBatch:
        return self._save("direction_batch", value.batch_id, value, parent_id=value.brief_id)

    def get_direction_batch(self, batch_id: str) -> OpeningDirectionBatch | None:
        return self._get("direction_batch", batch_id)

    def get_direction(self, direction_id: str) -> OpeningDirection | None:
        for batch in self._list("direction_batch"):
            for direction in batch.directions:
                if direction.direction_id == direction_id:
                    return direction
        return None

    def save_draft_batch(self, value: OpeningDraftBatch) -> OpeningDraftBatch:
        return self._save("draft_batch", value.draft_batch_id, value, parent_id=value.direction_id)

    def get_draft_batch(self, batch_id: str) -> OpeningDraftBatch | None:
        return self._get("draft_batch", batch_id)

    def save_originality_report(self, value: OpeningOriginalityReport) -> OpeningOriginalityReport:
        return self._save("originality_report", value.report_id, value, parent_id=value.direction_id)

    def find_by_idempotency(self, entity_type: str, idempotency_key: str):
        if not idempotency_key:
            return None
        with self._connect() as conn:
            row = conn.execute("SELECT payload_json FROM opening_entities WHERE entity_type=? AND idempotency_key=?", (entity_type, idempotency_key)).fetchone()
        return self._MODELS[entity_type].model_validate_json(row["payload_json"]) if row else None

    def get_latest(self, work_id: str) -> dict[str, object]:
        result = {}
        for entity_type in ("brief", "reference_session", "direction_batch", "draft_batch"):
            items = self._list(entity_type, work_id=work_id)
            result[entity_type] = items[-1] if items else None
        return result

    def _list(self, entity_type: str, *, parent_id: str = "", work_id: str = ""):
        clauses = ["entity_type=?"]
        params: list[object] = [entity_type]
        if parent_id:
            clauses.append("parent_id=?")
            params.append(parent_id)
        if work_id:
            clauses.append("work_id=?")
            params.append(work_id)
        with self._connect() as conn:
            rows = conn.execute(f"SELECT payload_json FROM opening_entities WHERE {' AND '.join(clauses)} ORDER BY created_at", tuple(params)).fetchall()
        return [self._MODELS[entity_type].model_validate_json(row["payload_json"]) for row in rows]

