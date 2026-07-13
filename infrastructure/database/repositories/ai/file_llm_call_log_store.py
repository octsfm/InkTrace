from __future__ import annotations

import hashlib
import json
import logging
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

from domain.entities.ai.models import LLMCallLog
from domain.repositories.ai.llm_call_log_repository import LLMCallLogRepository
from infrastructure.database.models import initialize_schema
from infrastructure.database.session import get_database_path
from infrastructure.database.v1 import connect


logger = logging.getLogger(__name__)


class FileLLMCallLogStore(LLMCallLogRepository):
    """SQLite-authoritative append-only call facts with optional JSONL replica."""

    def __init__(self, file_path: Path | str | None = None, *, database_path: Path | str | None = None) -> None:
        self._file_path = Path(file_path) if file_path else get_database_path().with_name("llm_call_logs.jsonl")
        self._database_path = Path(database_path).resolve() if database_path else get_database_path()

    def append(self, entry: LLMCallLog) -> None:
        inserted = self._insert_sqlite_fact(entry)
        if not inserted:
            return
        try:
            self._file_path.parent.mkdir(parents=True, exist_ok=True)
            with self._file_path.open("a", encoding="utf-8") as handle:
                handle.write(entry.model_dump_json())
                handle.write("\n")
        except OSError:
            logger.warning("optional llm usage replica write failed", extra={"request_id": entry.request_id})

    def _insert_sqlite_fact(self, entry: LLMCallLog) -> bool:
        fact = self._canonical_fact(entry)
        digest = hashlib.sha256(json.dumps(fact, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
        usage = entry.usage
        snapshot = dict(entry.price_snapshot_json or {})
        usage_status = "known" if usage and usage.input_tokens is not None and usage.output_tokens is not None and usage.total_tokens is not None else "unknown"
        cost_status = "known" if usage_status == "known" and bool(snapshot) else "unknown"
        currency = str(snapshot.get("currency") or "").upper() if cost_status == "known" else ""
        cost_text = str(Decimal(str(entry.estimated_cost or 0)).quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)) if cost_status == "known" else None
        conn = connect(self._database_path)
        try:
            initialize_schema(conn)
            existing = conn.execute("SELECT canonical_digest FROM llm_call_logs WHERE request_id=?", (entry.request_id,)).fetchone()
            if existing:
                if str(existing[0] or "") == digest:
                    return False
                raise ValueError("llm_call_log_conflict")
            conn.execute(
                """INSERT INTO llm_call_logs (
                    request_id,work_id,trace_id,session_id,step_id,job_id,run_id,prompt_key,prompt_version,model_role,provider_name,model_name,
                    status,error_code,error_message,attempt_no,input_tokens,output_tokens,total_tokens,estimated_cost,price_snapshot_json,
                    context_pack_snapshot_id,output_schema_key,started_at,finished_at,canonical_digest,usage_status,cost_status,cost_currency,estimated_cost_text
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (entry.request_id,entry.work_id,entry.trace_id,entry.session_id,entry.step_id,entry.job_id,entry.run_id,entry.prompt_key,entry.prompt_version,entry.model_role,
                 entry.provider_name,entry.model_name,entry.status.value,entry.error_code,entry.error_message,entry.attempt_no,
                 usage.input_tokens if usage else None,usage.output_tokens if usage else None,usage.total_tokens if usage else None,float(entry.estimated_cost or 0),
                 json.dumps(snapshot, ensure_ascii=False),entry.context_pack_snapshot_id,entry.output_schema_key,entry.started_at.isoformat(),entry.finished_at.isoformat(),
                 digest,usage_status,cost_status,currency,cost_text),
            )
            conn.commit()
            return True
        finally:
            conn.close()

    @staticmethod
    def _canonical_fact(entry: LLMCallLog) -> dict[str, object]:
        payload = entry.model_dump(mode="json")
        payload.pop("error_message", None)
        return payload
