from __future__ import annotations

from datetime import datetime

from domain.entities.ai.models import LLMCallLog, LLMCallStatus, LLMUsage
from domain.repositories.ai.llm_call_log_repository import LLMCallLogRepository


class LLMCallLogger:
    def __init__(self, repository: LLMCallLogRepository, trace_service=None) -> None:
        self._repository = repository
        self._trace_service = trace_service

    def record(
        self,
        *,
        prompt_key: str,
        prompt_version: str,
        model_role: str,
        provider_name: str,
        model_name: str,
        request_id: str,
        trace_id: str,
        status: LLMCallStatus,
        started_at: datetime,
        finished_at: datetime,
        usage: LLMUsage | None = None,
        error_code: str = "",
        error_message: str = "",
        attempt_no: int = 1,
        context_pack_snapshot_id: str = "",
        output_schema_key: str = "",
        session_id: str = "",
        step_id: str = "",
        content_hash: str = "",
    ) -> None:
        entry = LLMCallLog(
            prompt_key=prompt_key,
            prompt_version=prompt_version,
            model_role=model_role,
            provider_name=provider_name,
            model_name=model_name,
            request_id=request_id,
            trace_id=trace_id,
            status=status,
            error_code=error_code,
            error_message=error_message,
            attempt_no=attempt_no,
            started_at=started_at,
            finished_at=finished_at,
            usage=usage,
            context_pack_snapshot_id=context_pack_snapshot_id,
            output_schema_key=output_schema_key,
        )
        self._repository.append(entry)
        if self._trace_service is not None and trace_id:
            try:
                self._trace_service.record_llm_call(
                    entry,
                    session_id=session_id,
                    step_id=step_id,
                    content_hash=content_hash,
                )
            except ValueError as exc:
                if str(exc) != "trace_not_found":
                    raise
