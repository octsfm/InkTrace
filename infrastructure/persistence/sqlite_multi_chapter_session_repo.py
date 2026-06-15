from __future__ import annotations

import json
from pathlib import Path

from domain.entities.ai.models import MultiChapterSession, MultiChapterStatus
from domain.repositories.ai.multi_chapter_session_repository import MultiChapterSessionRepository
from infrastructure.database.models import initialize_schema
from infrastructure.database.session import get_database_path
from infrastructure.database.v1 import connect

ACTIVE_MULTI_CHAPTER_STATUSES = {
    MultiChapterStatus.PENDING.value,
    MultiChapterStatus.RUNNING.value,
    MultiChapterStatus.PAUSED.value,
    MultiChapterStatus.WAITING_USER_DECISION.value,
    MultiChapterStatus.BLOCKED.value,
}


class SQLiteMultiChapterSessionRepository(MultiChapterSessionRepository):
    def __init__(self, database_path: Path | str | None = None) -> None:
        self._database_path = Path(database_path).resolve() if database_path else get_database_path()

    def save(self, session: MultiChapterSession) -> MultiChapterSession:
        conn = connect(self._database_path)
        try:
            initialize_schema(conn)
            conn.execute(
                """
                INSERT INTO multi_chapter_sessions (
                    session_id, work_id, start_chapter_id, target_chapters, current_index, status,
                    per_chapter_status_json, agent_session_ids_json, candidate_draft_ids_json,
                    candidate_story_state_json, queue_state_snapshots_json, warning_codes_json,
                    error_code, error_message, paused_reason, blocked_source, blocked_reason_code,
                    request_id, trace_id, created_by, created_at, updated_at, started_at, finished_at,
                    auto_mode, pending_pause, metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(session_id) DO UPDATE SET
                    work_id = excluded.work_id,
                    start_chapter_id = excluded.start_chapter_id,
                    target_chapters = excluded.target_chapters,
                    current_index = excluded.current_index,
                    status = excluded.status,
                    per_chapter_status_json = excluded.per_chapter_status_json,
                    agent_session_ids_json = excluded.agent_session_ids_json,
                    candidate_draft_ids_json = excluded.candidate_draft_ids_json,
                    candidate_story_state_json = excluded.candidate_story_state_json,
                    queue_state_snapshots_json = excluded.queue_state_snapshots_json,
                    warning_codes_json = excluded.warning_codes_json,
                    error_code = excluded.error_code,
                    error_message = excluded.error_message,
                    paused_reason = excluded.paused_reason,
                    blocked_source = excluded.blocked_source,
                    blocked_reason_code = excluded.blocked_reason_code,
                    request_id = excluded.request_id,
                    trace_id = excluded.trace_id,
                    created_by = excluded.created_by,
                    created_at = excluded.created_at,
                    updated_at = excluded.updated_at,
                    started_at = excluded.started_at,
                    finished_at = excluded.finished_at,
                    auto_mode = excluded.auto_mode,
                    pending_pause = excluded.pending_pause,
                    metadata_json = excluded.metadata_json
                """,
                (
                    session.session_id,
                    session.work_id,
                    session.start_chapter_id,
                    session.target_chapters,
                    session.current_index,
                    session.status.value,
                    json.dumps([item.model_dump(mode="json") for item in session.per_chapter_status], ensure_ascii=False),
                    json.dumps(session.agent_session_ids, ensure_ascii=False),
                    json.dumps(session.candidate_draft_ids, ensure_ascii=False),
                    json.dumps(session.candidate_story_state, ensure_ascii=False),
                    json.dumps(session.queue_state_snapshots, ensure_ascii=False),
                    json.dumps(session.warning_codes, ensure_ascii=False),
                    session.error_code,
                    session.error_message,
                    session.paused_reason,
                    session.blocked_source,
                    session.blocked_reason_code,
                    session.request_id,
                    session.trace_id,
                    session.created_by,
                    session.created_at,
                    session.updated_at,
                    session.started_at,
                    session.finished_at,
                    session.auto_mode,
                    1 if session.pending_pause else 0,
                    json.dumps(session.metadata, ensure_ascii=False),
                ),
            )
            conn.commit()
        finally:
            conn.close()
        return session

    def get_by_id(self, session_id: str) -> MultiChapterSession | None:
        conn = connect(self._database_path)
        try:
            initialize_schema(conn)
            row = conn.execute("SELECT * FROM multi_chapter_sessions WHERE session_id = ?", (session_id,)).fetchone()
            return self._row_to_session(row) if row is not None else None
        finally:
            conn.close()

    def get_by_work_id(self, work_id: str) -> list[MultiChapterSession]:
        conn = connect(self._database_path)
        try:
            initialize_schema(conn)
            rows = conn.execute(
                "SELECT * FROM multi_chapter_sessions WHERE work_id = ? ORDER BY created_at DESC",
                (work_id,),
            ).fetchall()
            return [self._row_to_session(row) for row in rows]
        finally:
            conn.close()

    def list_active(self, work_id: str) -> list[MultiChapterSession]:
        sessions = self.get_by_work_id(work_id)
        return [item for item in sessions if item.status.value in ACTIVE_MULTI_CHAPTER_STATUSES]

    def _row_to_session(self, row) -> MultiChapterSession:
        return MultiChapterSession.model_validate(
            {
                "session_id": row["session_id"],
                "work_id": row["work_id"],
                "start_chapter_id": row["start_chapter_id"],
                "target_chapters": int(row["target_chapters"]),
                "current_index": int(row["current_index"]),
                "status": row["status"],
                "per_chapter_status": json.loads(str(row["per_chapter_status_json"] or "[]")),
                "agent_session_ids": json.loads(str(row["agent_session_ids_json"] or "[]")),
                "candidate_draft_ids": json.loads(str(row["candidate_draft_ids_json"] or "[]")),
                "candidate_story_state": json.loads(str(row["candidate_story_state_json"] or "{}")),
                "queue_state_snapshots": json.loads(str(row["queue_state_snapshots_json"] or "[]")),
                "warning_codes": json.loads(str(row["warning_codes_json"] or "[]")),
                "error_code": row["error_code"],
                "error_message": row["error_message"],
                "paused_reason": row["paused_reason"],
                "blocked_source": row["blocked_source"],
                "blocked_reason_code": row["blocked_reason_code"],
                "request_id": row["request_id"],
                "trace_id": row["trace_id"],
                "created_by": row["created_by"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
                "started_at": row["started_at"],
                "finished_at": row["finished_at"],
                "auto_mode": row["auto_mode"],
                "pending_pause": bool(row["pending_pause"]),
                "metadata": json.loads(str(row["metadata_json"] or "{}")),
            }
        )
