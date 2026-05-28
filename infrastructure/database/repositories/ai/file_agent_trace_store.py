from __future__ import annotations

import json
from pathlib import Path

from domain.entities.ai.models import (
    AgentStepTrace,
    AgentTrace,
    AgentTraceEvent,
    LLMCallTraceView,
    ObservationTrace,
    ToolCallTrace,
    TraceAlertRecord,
    TraceMetricPoint,
    UserDecisionTrace,
)
from domain.repositories.ai.agent_trace_repository import AgentTraceRepository
from infrastructure.database.session import get_database_path


class FileAgentTraceStore(AgentTraceRepository):
    def __init__(self, file_path: Path | str | None = None) -> None:
        self._file_path = Path(file_path) if file_path else get_database_path().with_name("agent_traces.json")

    def save_trace(self, trace: AgentTrace) -> AgentTrace:
        payload = self._load_payload()
        payload["traces"][trace.trace_id] = trace.model_dump(mode="json")
        self._save_payload(payload)
        return trace

    def get_trace(self, trace_id: str) -> AgentTrace:
        payload = self._load_payload()
        raw = payload["traces"].get(trace_id)
        if raw is None:
            raise ValueError("trace_not_found")
        return AgentTrace.model_validate(raw)

    def get_trace_by_session(self, session_id: str) -> AgentTrace:
        payload = self._load_payload()
        for item in payload["traces"].values():
            if item.get("session_id") == session_id:
                return AgentTrace.model_validate(item)
        raise ValueError("trace_not_found")

    def list_traces(self, *, work_id: str = "", chapter_id: str = "", session_id: str = "", status: str = "") -> list[AgentTrace]:
        payload = self._load_payload()
        items = [AgentTrace.model_validate(item) for item in payload["traces"].values()]
        if work_id:
            items = [item for item in items if item.work_id == work_id]
        if chapter_id:
            items = [item for item in items if item.chapter_id == chapter_id]
        if session_id:
            items = [item for item in items if item.session_id == session_id]
        if status:
            items = [item for item in items if item.status.value == status]
        return sorted(items, key=lambda item: item.started_at or item.created_at, reverse=True)

    def save_event(self, event: AgentTraceEvent) -> AgentTraceEvent:
        return self._save_model("events", event.event_id, event)

    def list_events(
        self,
        trace_id: str,
        *,
        step_id: str = "",
        event_type: str = "",
        time_range_start: str = "",
        time_range_end: str = "",
        event_stage: str = "",
    ) -> list[AgentTraceEvent]:
        items = self._list_models("events", AgentTraceEvent, trace_id=trace_id, step_id=step_id, event_type=event_type, sort_key="event_time")
        if event_stage:
            items = [item for item in items if item.event_stage.value == event_stage]
        if time_range_start:
            items = [item for item in items if item.event_time >= time_range_start]
        if time_range_end:
            items = [item for item in items if item.event_time <= time_range_end]
        return items

    def save_step_trace(self, step_trace: AgentStepTrace) -> AgentStepTrace:
        return self._save_model("step_traces", step_trace.step_trace_id, step_trace)

    def get_step_trace_by_step(self, step_id: str) -> AgentStepTrace:
        payload = self._load_payload()
        for item in payload["step_traces"].values():
            if item.get("step_id") == step_id:
                return AgentStepTrace.model_validate(item)
        raise ValueError("trace_step_not_found")

    def list_step_traces(self, trace_id: str) -> list[AgentStepTrace]:
        return self._list_models("step_traces", AgentStepTrace, trace_id=trace_id, sort_key="started_at")

    def save_tool_call(self, tool_trace: ToolCallTrace) -> ToolCallTrace:
        return self._save_model("tool_calls", tool_trace.tool_trace_id, tool_trace)

    def list_tool_calls(self, trace_id: str, *, step_id: str = "") -> list[ToolCallTrace]:
        return self._list_models("tool_calls", ToolCallTrace, trace_id=trace_id, step_id=step_id, sort_key="tool_trace_id")

    def save_observation_trace(self, observation_trace: ObservationTrace) -> ObservationTrace:
        return self._save_model("observation_traces", observation_trace.observation_trace_id, observation_trace)

    def list_observation_traces(self, trace_id: str, *, step_id: str = "") -> list[ObservationTrace]:
        return self._list_models(
            "observation_traces",
            ObservationTrace,
            trace_id=trace_id,
            step_id=step_id,
            sort_key="observation_trace_id",
        )

    def save_llm_call_view(self, llm_call_view: LLMCallTraceView) -> LLMCallTraceView:
        return self._save_model("llm_call_views", llm_call_view.llm_call_log_ref, llm_call_view)

    def list_llm_call_views(self, trace_id: str, *, step_id: str = "") -> list[LLMCallTraceView]:
        return self._list_models("llm_call_views", LLMCallTraceView, trace_id=trace_id, step_id=step_id, sort_key="llm_call_log_ref")

    def save_user_decision(self, decision_trace: UserDecisionTrace) -> UserDecisionTrace:
        return self._save_model("user_decisions", decision_trace.decision_trace_id, decision_trace)

    def list_user_decisions(self, trace_id: str) -> list[UserDecisionTrace]:
        return self._list_models("user_decisions", UserDecisionTrace, trace_id=trace_id, sort_key="decided_at")

    def save_metric(self, metric: TraceMetricPoint) -> TraceMetricPoint:
        return self._save_model("metrics", metric.metric_id, metric)

    def list_metrics(self, trace_id: str) -> list[TraceMetricPoint]:
        return self._list_models("metrics", TraceMetricPoint, trace_id=trace_id, sort_key="timestamp")

    def save_alert(self, alert: TraceAlertRecord) -> TraceAlertRecord:
        return self._save_model("alerts", alert.alert_id, alert)

    def get_alert(self, alert_id: str) -> TraceAlertRecord:
        payload = self._load_payload()
        raw = payload["alerts"].get(alert_id)
        if raw is None:
            raise ValueError("trace_alert_not_found")
        return TraceAlertRecord.model_validate(raw)

    def list_alerts(self, trace_id: str = "") -> list[TraceAlertRecord]:
        return self._list_models("alerts", TraceAlertRecord, trace_id=trace_id, sort_key="triggered_at")

    def cleanup_expired_details(self, *, trace_ids: list[str]) -> dict[str, int]:
        payload = self._load_payload()
        removed = {"events": 0, "tool_calls": 0, "observation_traces": 0, "llm_call_views": 0}
        expired = set(trace_ids)
        if not expired:
            return removed
        for bucket in ("tool_calls", "observation_traces", "llm_call_views"):
            for item_id, item in list(payload[bucket].items()):
                if item.get("trace_id") in expired:
                    del payload[bucket][item_id]
                    removed[bucket] += 1
        for item_id, item in list(payload["events"].items()):
            if item.get("trace_id") not in expired:
                continue
            if item.get("event_stage") == "audit":
                continue
            del payload["events"][item_id]
            removed["events"] += 1
        self._save_payload(payload)
        return removed

    def _save_model(self, bucket: str, item_id: str, model):
        payload = self._load_payload()
        payload[bucket][item_id] = model.model_dump(mode="json")
        self._save_payload(payload)
        return model

    def _list_models(self, bucket: str, model_type, **filters):
        payload = self._load_payload()
        items = [model_type.model_validate(item) for item in payload[bucket].values()]
        sort_key = str(filters.pop("sort_key", ""))
        for key, value in filters.items():
            if not value:
                continue
            items = [item for item in items if getattr(item, key, "") == value]
        if sort_key:
            items = sorted(items, key=lambda item: getattr(item, sort_key, ""))
        return items

    def _load_payload(self) -> dict[str, dict[str, object]]:
        if not self._file_path.exists():
            return self._empty_payload()
        payload = json.loads(self._file_path.read_text(encoding="utf-8"))
        for key, value in self._empty_payload().items():
            payload.setdefault(key, value)
        return payload

    def _save_payload(self, payload: dict[str, dict[str, object]]) -> None:
        self._file_path.parent.mkdir(parents=True, exist_ok=True)
        self._file_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    @staticmethod
    def _empty_payload() -> dict[str, dict[str, object]]:
        return {
            "traces": {},
            "events": {},
            "step_traces": {},
            "tool_calls": {},
            "observation_traces": {},
            "llm_call_views": {},
            "user_decisions": {},
            "metrics": {},
            "alerts": {},
        }
