from __future__ import annotations

import json
from pathlib import Path

from domain.entities.ai.models import AutoQueueRun, AutoQueueStopRecord
from domain.repositories.ai.auto_queue_run_repository import AutoQueueRunRepository
from infrastructure.database.models import initialize_schema
from infrastructure.database.session import get_database_path
from infrastructure.database.v1 import connect


class SQLiteAutoQueueRunRepository(AutoQueueRunRepository):
    TERMINAL_STATUSES = {"stopped", "completed", "failed", "cancelled"}

    def __init__(self, database_path: Path | str | None = None) -> None:
        self._database_path = Path(database_path).resolve() if database_path else get_database_path()

    def save(self, run: AutoQueueRun) -> AutoQueueRun:
        conn = connect(self._database_path)
        try:
            initialize_schema(conn)
            conn.execute(
                """
                INSERT INTO auto_queue_runs (
                    run_id, job_id, config_id, work_id, multi_chapter_session_id, status,
                    generated_count, total_word_count, consumed_tokens, current_stop_evaluation_json,
                    stop_record_json, current_candidate_story_state_json, queue_state_snapshots_json,
                    consecutive_blocking_count, consecutive_revision_failure_count,
                    error_code, error_message, request_id, trace_id,
                    created_at, updated_at, started_at, stopped_at, finished_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(run_id) DO UPDATE SET
                    job_id = excluded.job_id,
                    config_id = excluded.config_id,
                    work_id = excluded.work_id,
                    multi_chapter_session_id = excluded.multi_chapter_session_id,
                    status = excluded.status,
                    generated_count = excluded.generated_count,
                    total_word_count = excluded.total_word_count,
                    consumed_tokens = excluded.consumed_tokens,
                    current_stop_evaluation_json = excluded.current_stop_evaluation_json,
                    stop_record_json = excluded.stop_record_json,
                    current_candidate_story_state_json = excluded.current_candidate_story_state_json,
                    queue_state_snapshots_json = excluded.queue_state_snapshots_json,
                    consecutive_blocking_count = excluded.consecutive_blocking_count,
                    consecutive_revision_failure_count = excluded.consecutive_revision_failure_count,
                    error_code = excluded.error_code,
                    error_message = excluded.error_message,
                    request_id = excluded.request_id,
                    trace_id = excluded.trace_id,
                    created_at = excluded.created_at,
                    updated_at = excluded.updated_at,
                    started_at = excluded.started_at,
                    stopped_at = excluded.stopped_at,
                    finished_at = excluded.finished_at
                """,
                self._params(run),
            )
            conn.commit()
            return run
        finally:
            conn.close()

    def get_by_id(self, run_id: str) -> AutoQueueRun | None:
        items = self._query("SELECT * FROM auto_queue_runs WHERE run_id = ?", (run_id,))
        return items[0] if items else None

    def get_active(self, work_id: str) -> AutoQueueRun | None:
        placeholders = ", ".join(["?"] * len(self.TERMINAL_STATUSES))
        items = self._query(
            f"""
            SELECT * FROM auto_queue_runs
            WHERE work_id = ? AND status NOT IN ({placeholders})
            ORDER BY updated_at DESC, created_at DESC
            LIMIT 1
            """,
            (work_id, *sorted(self.TERMINAL_STATUSES)),
        )
        return items[0] if items else None

    def get_history(self, work_id: str, limit: int = 20) -> list[AutoQueueRun]:
        return self._query(
            "SELECT * FROM auto_queue_runs WHERE work_id = ? ORDER BY updated_at DESC, created_at DESC LIMIT ?",
            (work_id, max(int(limit or 20), 1)),
        )

    def update(self, run: AutoQueueRun) -> AutoQueueRun:
        return self.save(run)

    def _query(self, sql: str, params: tuple[object, ...]) -> list[AutoQueueRun]:
        conn = connect(self._database_path)
        try:
            initialize_schema(conn)
            rows = conn.execute(sql, params).fetchall()
            return [self._row_to_run(row) for row in rows]
        finally:
            conn.close()

    def _row_to_run(self, row) -> AutoQueueRun:
        stop_record_payload = json.loads(str(row["stop_record_json"] or "{}"))
        return AutoQueueRun(
            run_id=row["run_id"],
            job_id=row["job_id"],
            config_id=row["config_id"],
            work_id=row["work_id"],
            multi_chapter_session_id=row["multi_chapter_session_id"],
            status=row["status"],
            generated_count=int(row["generated_count"] or 0),
            total_word_count=int(row["total_word_count"] or 0),
            consumed_tokens=int(row["consumed_tokens"] or 0),
            current_stop_evaluation=json.loads(str(row["current_stop_evaluation_json"] or "{}")),
            stop_record=AutoQueueStopRecord.model_validate(stop_record_payload) if stop_record_payload else None,
            current_candidate_story_state=json.loads(str(row["current_candidate_story_state_json"] or "{}")),
            queue_state_snapshots=json.loads(str(row["queue_state_snapshots_json"] or "[]")),
            consecutive_blocking_count=int(row["consecutive_blocking_count"] or 0),
            consecutive_revision_failure_count=int(row["consecutive_revision_failure_count"] or 0),
            error_code=row["error_code"],
            error_message=row["error_message"],
            request_id=row["request_id"],
            trace_id=row["trace_id"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            started_at=row["started_at"],
            stopped_at=row["stopped_at"],
            finished_at=row["finished_at"],
        )

    def _params(self, run: AutoQueueRun) -> tuple[object, ...]:
        return (
            run.run_id,
            run.job_id,
            run.config_id,
            run.work_id,
            run.multi_chapter_session_id,
            run.status.value,
            run.generated_count,
            run.total_word_count,
            run.consumed_tokens,
            json.dumps(run.current_stop_evaluation, ensure_ascii=False),
            json.dumps(run.stop_record.model_dump(mode="json") if run.stop_record else {}, ensure_ascii=False),
            json.dumps(run.current_candidate_story_state, ensure_ascii=False),
            json.dumps(run.queue_state_snapshots, ensure_ascii=False),
            run.consecutive_blocking_count,
            run.consecutive_revision_failure_count,
            run.error_code,
            run.error_message,
            run.request_id,
            run.trace_id,
            run.created_at,
            run.updated_at,
            run.started_at,
            run.stopped_at,
            run.finished_at,
        )
