from __future__ import annotations

import json
from pathlib import Path

from domain.entities.ai.models import LLMCallLog
from domain.repositories.ai.llm_call_log_repository import LLMCallLogRepository
from infrastructure.database.models import initialize_schema
from infrastructure.database.session import get_database_path
from infrastructure.database.v1 import connect


class FileLLMCallLogStore(LLMCallLogRepository):
    def __init__(
        self,
        file_path: Path | str | None = None,
        *,
        database_path: Path | str | None = None,
    ) -> None:
        self._file_path = Path(file_path) if file_path else get_database_path().with_name("llm_call_logs.jsonl")
        self._database_path = Path(database_path).resolve() if database_path else get_database_path()

    def append(self, entry: LLMCallLog) -> None:
        self._file_path.parent.mkdir(parents=True, exist_ok=True)
        with self._file_path.open("a", encoding="utf-8") as handle:
            handle.write(entry.model_dump_json())
            handle.write("\n")
        self._project_to_sqlite(entry)

    def _project_to_sqlite(self, entry: LLMCallLog) -> None:
        conn = connect(self._database_path)
        try:
            initialize_schema(conn)
            usage = entry.usage
            conn.execute(
                """
                INSERT INTO llm_call_logs (
                    request_id, work_id, trace_id, session_id, step_id,
                    prompt_key, prompt_version, model_role, provider_name, model_name,
                    status, error_code, error_message, attempt_no,
                    input_tokens, output_tokens, total_tokens,
                    estimated_cost, price_snapshot_json,
                    context_pack_snapshot_id, output_schema_key,
                    started_at, finished_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(request_id) DO UPDATE SET
                    work_id = excluded.work_id,
                    trace_id = excluded.trace_id,
                    session_id = excluded.session_id,
                    step_id = excluded.step_id,
                    prompt_key = excluded.prompt_key,
                    prompt_version = excluded.prompt_version,
                    model_role = excluded.model_role,
                    provider_name = excluded.provider_name,
                    model_name = excluded.model_name,
                    status = excluded.status,
                    error_code = excluded.error_code,
                    error_message = excluded.error_message,
                    attempt_no = excluded.attempt_no,
                    input_tokens = excluded.input_tokens,
                    output_tokens = excluded.output_tokens,
                    total_tokens = excluded.total_tokens,
                    estimated_cost = excluded.estimated_cost,
                    price_snapshot_json = excluded.price_snapshot_json,
                    context_pack_snapshot_id = excluded.context_pack_snapshot_id,
                    output_schema_key = excluded.output_schema_key,
                    started_at = excluded.started_at,
                    finished_at = excluded.finished_at
                """,
                (
                    entry.request_id,
                    entry.work_id,
                    entry.trace_id,
                    entry.session_id,
                    entry.step_id,
                    entry.prompt_key,
                    entry.prompt_version,
                    entry.model_role,
                    entry.provider_name,
                    entry.model_name,
                    entry.status.value,
                    entry.error_code,
                    entry.error_message,
                    entry.attempt_no,
                    usage.input_tokens if usage else None,
                    usage.output_tokens if usage else None,
                    usage.total_tokens if usage else None,
                    entry.estimated_cost,
                    json.dumps(entry.price_snapshot_json, ensure_ascii=False),
                    entry.context_pack_snapshot_id,
                    entry.output_schema_key,
                    entry.started_at.isoformat(),
                    entry.finished_at.isoformat(),
                ),
            )
            conn.commit()
        finally:
            conn.close()
