from __future__ import annotations

from abc import ABC, abstractmethod

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


class AgentTraceRepository(ABC):
    @abstractmethod
    def save_trace(self, trace: AgentTrace) -> AgentTrace:
        raise NotImplementedError

    @abstractmethod
    def get_trace(self, trace_id: str) -> AgentTrace:
        raise NotImplementedError

    @abstractmethod
    def get_trace_by_session(self, session_id: str) -> AgentTrace:
        raise NotImplementedError

    @abstractmethod
    def list_traces(
        self,
        *,
        work_id: str = "",
        chapter_id: str = "",
        session_id: str = "",
        status: str = "",
    ) -> list[AgentTrace]:
        raise NotImplementedError

    @abstractmethod
    def save_event(self, event: AgentTraceEvent) -> AgentTraceEvent:
        raise NotImplementedError

    @abstractmethod
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
        raise NotImplementedError

    @abstractmethod
    def save_step_trace(self, step_trace: AgentStepTrace) -> AgentStepTrace:
        raise NotImplementedError

    @abstractmethod
    def get_step_trace_by_step(self, step_id: str) -> AgentStepTrace:
        raise NotImplementedError

    @abstractmethod
    def list_step_traces(self, trace_id: str) -> list[AgentStepTrace]:
        raise NotImplementedError

    @abstractmethod
    def save_tool_call(self, tool_trace: ToolCallTrace) -> ToolCallTrace:
        raise NotImplementedError

    @abstractmethod
    def list_tool_calls(self, trace_id: str, *, step_id: str = "") -> list[ToolCallTrace]:
        raise NotImplementedError

    @abstractmethod
    def save_observation_trace(self, observation_trace: ObservationTrace) -> ObservationTrace:
        raise NotImplementedError

    @abstractmethod
    def list_observation_traces(self, trace_id: str, *, step_id: str = "") -> list[ObservationTrace]:
        raise NotImplementedError

    @abstractmethod
    def save_llm_call_view(self, llm_call_view: LLMCallTraceView) -> LLMCallTraceView:
        raise NotImplementedError

    @abstractmethod
    def list_llm_call_views(self, trace_id: str, *, step_id: str = "") -> list[LLMCallTraceView]:
        raise NotImplementedError

    @abstractmethod
    def save_user_decision(self, decision_trace: UserDecisionTrace) -> UserDecisionTrace:
        raise NotImplementedError

    @abstractmethod
    def list_user_decisions(self, trace_id: str) -> list[UserDecisionTrace]:
        raise NotImplementedError

    @abstractmethod
    def save_metric(self, metric: TraceMetricPoint) -> TraceMetricPoint:
        raise NotImplementedError

    @abstractmethod
    def list_metrics(self, trace_id: str) -> list[TraceMetricPoint]:
        raise NotImplementedError

    @abstractmethod
    def save_alert(self, alert: TraceAlertRecord) -> TraceAlertRecord:
        raise NotImplementedError

    @abstractmethod
    def get_alert(self, alert_id: str) -> TraceAlertRecord:
        raise NotImplementedError

    @abstractmethod
    def list_alerts(self, trace_id: str = "") -> list[TraceAlertRecord]:
        raise NotImplementedError

    @abstractmethod
    def cleanup_expired_details(self, *, trace_ids: list[str]) -> dict[str, int]:
        raise NotImplementedError
