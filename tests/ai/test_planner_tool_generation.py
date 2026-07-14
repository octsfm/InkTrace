from __future__ import annotations

from application.services.ai.tool_facade import CoreToolFacade, ToolExecutionContext


class _StubContextPackService:
    pass


class _StubCandidateDraftRepository:
    pass


class _StubWriter:
    pass


class _RecordingPlanningGenerationService:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def build_chapter_plan_payload(self, **kwargs) -> dict[str, object]:
        self.calls.append(dict(kwargs))
        return {
            "chapter_plan_id": "plan_model_1",
            "work_id": kwargs["work_id"],
            "chapter_id": kwargs["chapter_id"],
            "direction_proposal_id": kwargs["direction_proposal_id"],
            "plan_items": [{"item_id": "item_model_1", "plan_order": 1, "chapter_goal": "model goal"}],
        }


def test_create_chapter_plan_tool_uses_generation_service_for_minimal_agent_payload() -> None:
    generator = _RecordingPlanningGenerationService()
    facade = CoreToolFacade(
        context_pack_service=_StubContextPackService(),
        candidate_draft_repository=_StubCandidateDraftRepository(),
        writer=_StubWriter(),
        planning_generation_service=generator,
    )
    context = ToolExecutionContext(
        caller_type="agent",
        work_id="work-1",
        chapter_id="chapter-1",
        request_id="req-1",
        trace_id="trace-1",
        agent_session_id="session-1",
        agent_step_id="step-1",
        agent_type="planner",
        session_status="running",
        step_status="waiting_observation",
        resource_scope_refs=["work:work-1", "chapter:chapter-1"],
        side_effect_level="plan_write",
    )

    result = facade.call(
        "create_chapter_plan",
        context=context,
        payload={"work_id": "work-1", "chapter_id": "chapter-1", "direction_proposal_id": "dir-1"},
    )

    assert result.ok is True
    assert result.payload["result_ref"] == "chapter_plan:plan_model_1"
    assert generator.calls == [
        {
            "work_id": "work-1",
            "chapter_id": "chapter-1",
            "direction_proposal_id": "dir-1",
            "request_id": "req-1",
            "trace_id": "trace-1",
            "agent_session_id": "session-1",
        }
    ]
