from __future__ import annotations

from datetime import datetime
from typing import Any, Callable

from domain.entities.ai.models import LLMCallLog, LLMCallStatus, LLMUsage
from domain.repositories.ai.llm_call_log_repository import LLMCallLogRepository


class LLMCallLogger:
    def __init__(
        self,
        repository: LLMCallLogRepository,
        trace_service=None,
        pricing_resolver: Callable[..., dict[str, Any] | None] | None = None,
        strict_trace: bool = False,
    ) -> None:
        self._repository = repository
        self._trace_service = trace_service
        self._pricing_resolver = pricing_resolver
        self._strict_trace = strict_trace

    def record(
        self,
        *,
        prompt_key: str,
        prompt_version: str,
        work_id: str = "",
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
        job_id: str = "",
        run_id: str = "",
        content_hash: str = "",
        price_snapshot_override: dict[str, Any] | None = None,
    ) -> None:
        price_snapshot = dict(price_snapshot_override) if price_snapshot_override is not None else self._resolve_price_snapshot(
            provider_name=provider_name,
            model_name=model_name,
            model_role=model_role,
            work_id=work_id,
        )
        estimated_cost = self._calculate_estimated_cost(usage=usage, price_snapshot=price_snapshot)
        usage_payload = usage
        if usage is not None:
            usage_payload = usage.model_copy(
                update={
                    "estimated_cost": estimated_cost,
                    "price_snapshot_json": dict(price_snapshot),
                }
            )
        entry = LLMCallLog(
            prompt_key=prompt_key,
            prompt_version=prompt_version,
            work_id=work_id,
            model_role=model_role,
            provider_name=provider_name,
            model_name=model_name,
            request_id=request_id,
            trace_id=trace_id,
            session_id=session_id,
            step_id=step_id,
            job_id=job_id,
            run_id=run_id,
            status=status,
            error_code=error_code,
            error_message=error_message,
            attempt_no=attempt_no,
            started_at=started_at,
            finished_at=finished_at,
            usage=usage_payload,
            estimated_cost=estimated_cost,
            price_snapshot_json=dict(price_snapshot),
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
                if str(exc) != "trace_not_found" or self._strict_trace:
                    raise

    def _resolve_price_snapshot(self, *, provider_name: str, model_name: str, model_role: str, work_id: str = "") -> dict[str, Any]:
        if self._pricing_resolver is None:
            return {}
        try: resolved = self._pricing_resolver(provider_name, model_name, model_role, work_id) or {}
        except TypeError: resolved = self._pricing_resolver(provider_name, model_name, model_role) or {}
        return dict(resolved)

    def _calculate_estimated_cost(self, *, usage: LLMUsage | None, price_snapshot: dict[str, Any]) -> float:
        if usage is None:
            return 0.0
        input_tokens = max(int(usage.input_tokens or 0), 0)
        output_tokens = max(int(usage.output_tokens or 0), 0)
        input_price = float(price_snapshot.get("input_price_per_1k", 0.0) or 0.0)
        output_price = float(price_snapshot.get("output_price_per_1k", 0.0) or 0.0)
        estimated_cost = (input_tokens * input_price / 1000.0) + (output_tokens * output_price / 1000.0)
        return round(estimated_cost, 6)
