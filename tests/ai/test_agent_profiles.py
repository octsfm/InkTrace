from __future__ import annotations

from application.services.ai.agent_profile_registry import build_default_agent_profile_registry
from domain.entities.ai.models import (
    AgentCapability,
    AgentExecutionProfile,
    AgentInput,
    AgentOutput,
    AgentResultRef,
    AgentToolPermissionMode,
    AgentType,
)


def test_agent_profile_registry_returns_writer_execution_profile() -> None:
    registry = build_default_agent_profile_registry()

    profile = registry.require_profile(AgentType.WRITER.value)

    assert isinstance(profile, AgentExecutionProfile)
    assert profile.agent_type == AgentType.WRITER
    assert profile.model_role == "writer"
    assert profile.default_timeout == 300
    assert profile.max_retry == 1
    assert profile.allow_degraded is True
    assert "run_writer_step" in profile.allowed_tool_names
    assert "formal_chapter_write" in profile.denied_tool_names
    assert profile.metadata["formal_write_forbidden"] is True
    assert AgentCapability.CANDIDATE_GENERATION.value in profile.capabilities


def test_agent_profile_registry_returns_tool_permissions_for_writer_and_reviewer() -> None:
    registry = build_default_agent_profile_registry()

    writer_permission = registry.get_permission(AgentType.WRITER.value, "run_writer_step")
    reviewer_permission = registry.get_permission(AgentType.REVIEWER.value, "run_writer_step")
    memory_permission = registry.get_permission(AgentType.MEMORY.value, "create_memory_update_suggestion")

    assert writer_permission.permission == AgentToolPermissionMode.ALLOW
    assert writer_permission.side_effect_level == "safe_write_candidate"
    assert writer_permission.requires_user_action is False
    assert reviewer_permission.permission == AgentToolPermissionMode.DENY
    assert reviewer_permission.side_effect_level == "formal_write_forbidden"
    assert memory_permission.permission == AgentToolPermissionMode.ALLOW
    assert memory_permission.side_effect_level == "safe_write_suggestion"


def test_agent_profile_registry_returns_planner_reviewer_rewriter_profiles() -> None:
    registry = build_default_agent_profile_registry()

    planner = registry.require_profile(AgentType.PLANNER.value)
    reviewer = registry.require_profile(AgentType.REVIEWER.value)
    rewriter = registry.require_profile(AgentType.REWRITER.value)
    memory = registry.require_profile(AgentType.MEMORY.value)

    assert planner.model_role == "planning"
    assert "create_direction_proposal" in planner.allowed_tool_names
    assert reviewer.model_role == "reviewer"
    assert "create_review_report" in reviewer.allowed_tool_names
    assert rewriter.model_role == "rewriter"
    assert "create_candidate_version" in rewriter.allowed_tool_names
    assert memory.model_role == "analysis"
    assert "get_story_memory_snapshot" in memory.allowed_tool_names


def test_agent_profile_registry_exposes_explicit_shared_and_conditional_permissions() -> None:
    registry = build_default_agent_profile_registry()

    planner_task = registry.get_permission(AgentType.PLANNER.value, "create_writing_task")
    reviewer_ai_suggestion = registry.get_permission(AgentType.REVIEWER.value, "create_ai_suggestion")
    writer_conflict = registry.get_permission(AgentType.WRITER.value, "request_conflict_check")
    rewriter_trace = registry.get_permission(AgentType.REWRITER.value, "create_agent_trace_event")

    assert planner_task.permission == AgentToolPermissionMode.ALLOW
    assert planner_task.side_effect_level == "plan_write"
    assert reviewer_ai_suggestion.permission == AgentToolPermissionMode.CONDITIONAL
    assert reviewer_ai_suggestion.side_effect_level == "safe_write_suggestion"
    assert writer_conflict.permission == AgentToolPermissionMode.CONDITIONAL
    assert writer_conflict.side_effect_level == "read_only"
    assert rewriter_trace.permission == AgentToolPermissionMode.ALLOW
    assert rewriter_trace.side_effect_level == "trace_only"


def test_agent_input_and_output_use_structured_safe_refs() -> None:
    result_ref = AgentResultRef(
        ref_type="candidate_draft",
        ref_id="candidate_draft:cd_1",
        source_agent_type=AgentType.WRITER.value,
        source_step_id="agent_step_1",
        status="success",
        ref_scope="chapter",
        checksum="sha256:abc",
        summary="candidate draft summary",
        created_at="2026-05-20T00:00:00+00:00",
    )

    agent_input = AgentInput(
        session_id="agent_session_1",
        workflow_type="continuation",
        stage="drafting",
        agent_type=AgentType.WRITER,
        work_id="work-1",
        chapter_id="chapter-1",
        user_instruction="继续写这一章",
        context_refs=["context_pack:cp_1", "writing_task:wt_1"],
        selected_direction_id="dir_1",
        selected_chapter_plan_id="plan_1",
        current_candidate_draft_id="cd_1",
        allow_degraded=True,
        warning_codes=["context_degraded"],
        metadata={"model_role": "writer"},
    )
    agent_output = AgentOutput(
        agent_type=AgentType.WRITER,
        step_id="agent_step_1",
        status="succeeded",
        result_refs=[result_ref],
        warning_codes=["context_degraded"],
        decision_hint="candidate_ready",
        suggested_next_stage="candidate_ready",
        requires_user_action=False,
        metadata={"output_schema_key": "candidate_draft"},
    )

    assert agent_input.workflow_type == "continuation"
    assert agent_input.context_refs == ["context_pack:cp_1", "writing_task:wt_1"]
    assert agent_output.result_refs[0].ref_scope == "chapter"
    assert agent_output.result_refs[0].summary == "candidate draft summary"
    assert agent_output.result_refs[0].source_agent_type == AgentType.WRITER.value
