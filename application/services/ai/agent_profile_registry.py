from __future__ import annotations

from domain.entities.ai.models import (
    AgentCapability,
    AgentExecutionProfile,
    AgentToolPermission,
    AgentToolPermissionMode,
    AgentType,
)


class AgentProfileRegistry:
    def __init__(
        self,
        *,
        profiles: list[AgentExecutionProfile] | None = None,
        permissions: list[AgentToolPermission] | None = None,
    ) -> None:
        self._profiles = {profile.agent_type.value: profile for profile in profiles or []}
        self._permissions = {
            (permission.agent_type.value, permission.tool_name): permission for permission in permissions or []
        }

    def get_profile(self, agent_type: str) -> AgentExecutionProfile | None:
        return self._profiles.get(agent_type)

    def require_profile(self, agent_type: str) -> AgentExecutionProfile:
        profile = self.get_profile(agent_type)
        if profile is None:
            raise ValueError("unsupported_agent_type")
        return profile

    def get_permission(self, agent_type: str, tool_name: str) -> AgentToolPermission:
        permission = self._permissions.get((agent_type, tool_name))
        if permission is not None:
            return permission
        profile = self.get_profile(agent_type)
        denied_tool_names = set(profile.denied_tool_names) if profile is not None else set()
        if tool_name in denied_tool_names or tool_name in _USER_ACTION_ONLY_TOOLS or tool_name in _FORMAL_WRITE_TOOLS:
            return AgentToolPermission(
                tool_name=tool_name,
                agent_type=AgentType(agent_type),
                permission=AgentToolPermissionMode.DENY,
                side_effect_level="formal_write_forbidden",
                requires_user_action=tool_name in _USER_ACTION_ONLY_TOOLS,
                allow_degraded=False,
                retryable=False,
                notes="agent_tool_denied_by_policy",
            )
        return AgentToolPermission(
            tool_name=tool_name,
            agent_type=AgentType(agent_type),
            permission=AgentToolPermissionMode.DENY,
            side_effect_level="formal_write_forbidden",
            requires_user_action=False,
            allow_degraded=False,
            retryable=False,
            notes="agent_tool_not_registered",
        )


_USER_ACTION_ONLY_TOOLS = {
    "accept_candidate_draft",
    "reject_candidate_draft",
    "apply_candidate_to_draft",
}
_FORMAL_WRITE_TOOLS = {"formal_chapter_write"}


def build_default_agent_profile_registry() -> AgentProfileRegistry:
    profiles = [
        AgentExecutionProfile(
            agent_type=AgentType.MEMORY,
            capabilities=[
                AgentCapability.STORY_CONTEXT_READ.value,
                AgentCapability.MEMORY_GAP_DETECTION.value,
                AgentCapability.MEMORY_UPDATE_SUGGESTION.value,
            ],
            model_role="analysis",
            allowed_tool_names=[
                "get_story_memory_snapshot",
                "get_story_state_baseline",
                "create_memory_update_suggestion",
                "request_conflict_check",
                "create_agent_observation",
                "create_agent_trace_event",
            ],
            denied_tool_names=sorted(_USER_ACTION_ONLY_TOOLS | _FORMAL_WRITE_TOOLS),
            output_schema_key="memory_context",
            metadata={"formal_write_forbidden": True},
        ),
        AgentExecutionProfile(
            agent_type=AgentType.PLANNER,
            capabilities=[
                AgentCapability.DIRECTION_PROPOSAL.value,
                AgentCapability.CHAPTER_PLANNING.value,
                AgentCapability.WRITING_TASK_PREPARATION.value,
            ],
            model_role="planning",
            allowed_tool_names=[
                "build_context_pack",
                "create_direction_proposal",
                "create_chapter_plan",
                "create_writing_task",
                "request_conflict_check",
                "create_agent_observation",
                "create_agent_trace_event",
            ],
            denied_tool_names=sorted(_USER_ACTION_ONLY_TOOLS | _FORMAL_WRITE_TOOLS | {"run_writer_step"}),
            output_schema_key="chapter_plan",
            metadata={"formal_write_forbidden": True},
        ),
        AgentExecutionProfile(
            agent_type=AgentType.WRITER,
            capabilities=[
                AgentCapability.CANDIDATE_GENERATION.value,
                AgentCapability.CANDIDATE_VALIDATION.value,
            ],
            model_role="writer",
            allowed_tool_names=[
                "build_context_pack",
                "run_writer_step",
                "validate_writer_output",
                "save_candidate_draft",
                "request_conflict_check",
                "create_agent_observation",
                "create_agent_trace_event",
            ],
            denied_tool_names=sorted(_USER_ACTION_ONLY_TOOLS | _FORMAL_WRITE_TOOLS | {"create_review_report"}),
            output_schema_key="candidate_draft",
            metadata={"formal_write_forbidden": True},
        ),
        AgentExecutionProfile(
            agent_type=AgentType.REVIEWER,
            capabilities=[
                AgentCapability.CONSISTENCY_REVIEW.value,
                AgentCapability.STYLE_REVIEW.value,
                AgentCapability.PLOT_REVIEW.value,
                AgentCapability.ISSUE_REPORTING.value,
            ],
            model_role="reviewer",
            allowed_tool_names=[
                "create_review_report",
                "create_review_issue",
                "request_conflict_check",
                "create_ai_suggestion",
                "create_agent_observation",
                "create_agent_trace_event",
            ],
            denied_tool_names=sorted(_USER_ACTION_ONLY_TOOLS | _FORMAL_WRITE_TOOLS | {"run_writer_step"}),
            output_schema_key="review_report",
            metadata={"formal_write_forbidden": True},
        ),
        AgentExecutionProfile(
            agent_type=AgentType.REWRITER,
            capabilities=[
                AgentCapability.CANDIDATE_REVISION.value,
                AgentCapability.REVISION_VALIDATION.value,
            ],
            model_role="rewriter",
            allowed_tool_names=[
                "create_candidate_version",
                "validate_writer_output",
                "request_conflict_check",
                "create_agent_observation",
                "create_agent_trace_event",
            ],
            denied_tool_names=sorted(_USER_ACTION_ONLY_TOOLS | _FORMAL_WRITE_TOOLS),
            output_schema_key="candidate_version",
            metadata={"formal_write_forbidden": True},
        ),
    ]
    permissions = [
        AgentToolPermission(
            tool_name="get_story_memory_snapshot",
            agent_type=AgentType.MEMORY,
            permission=AgentToolPermissionMode.ALLOW,
            side_effect_level="read_only",
            allow_degraded=True,
            retryable=True,
            notes="memory_snapshot_read",
        ),
        AgentToolPermission(
            tool_name="get_story_state_baseline",
            agent_type=AgentType.MEMORY,
            permission=AgentToolPermissionMode.ALLOW,
            side_effect_level="read_only",
            allow_degraded=True,
            retryable=True,
            notes="story_state_read",
        ),
        AgentToolPermission(
            tool_name="create_memory_update_suggestion",
            agent_type=AgentType.MEMORY,
            permission=AgentToolPermissionMode.ALLOW,
            side_effect_level="safe_write_suggestion",
            allow_degraded=True,
            retryable=True,
            notes="memory_agent_only",
        ),
        AgentToolPermission(
            tool_name="build_context_pack",
            agent_type=AgentType.PLANNER,
            permission=AgentToolPermissionMode.ALLOW,
            side_effect_level="read_only",
            allow_degraded=True,
            retryable=True,
            notes="planner_context_prepare",
        ),
        AgentToolPermission(
            tool_name="create_direction_proposal",
            agent_type=AgentType.PLANNER,
            permission=AgentToolPermissionMode.ALLOW,
            side_effect_level="plan_write",
            allow_degraded=True,
            retryable=True,
            notes="planner_direction_proposal",
        ),
        AgentToolPermission(
            tool_name="create_chapter_plan",
            agent_type=AgentType.PLANNER,
            permission=AgentToolPermissionMode.ALLOW,
            side_effect_level="plan_write",
            allow_degraded=True,
            retryable=True,
            notes="planner_chapter_plan",
        ),
        AgentToolPermission(
            tool_name="create_writing_task",
            agent_type=AgentType.PLANNER,
            permission=AgentToolPermissionMode.ALLOW,
            side_effect_level="plan_write",
            allow_degraded=True,
            retryable=True,
            notes="planner_writing_task",
        ),
        AgentToolPermission(
            tool_name="run_writer_step",
            agent_type=AgentType.WRITER,
            permission=AgentToolPermissionMode.ALLOW,
            side_effect_level="safe_write_candidate",
            allow_degraded=True,
            retryable=True,
            notes="writer_only",
        ),
        AgentToolPermission(
            tool_name="validate_writer_output",
            agent_type=AgentType.WRITER,
            permission=AgentToolPermissionMode.ALLOW,
            side_effect_level="safe_write_candidate",
            allow_degraded=True,
            retryable=True,
            notes="writer_validation",
        ),
        AgentToolPermission(
            tool_name="save_candidate_draft",
            agent_type=AgentType.WRITER,
            permission=AgentToolPermissionMode.ALLOW,
            side_effect_level="safe_write_candidate",
            allow_degraded=True,
            retryable=True,
            notes="writer_candidate_persist",
        ),
        AgentToolPermission(
            tool_name="create_review_report",
            agent_type=AgentType.REVIEWER,
            permission=AgentToolPermissionMode.ALLOW,
            side_effect_level="safe_write_review",
            allow_degraded=True,
            retryable=True,
            notes="reviewer_only",
        ),
        AgentToolPermission(
            tool_name="create_review_issue",
            agent_type=AgentType.REVIEWER,
            permission=AgentToolPermissionMode.ALLOW,
            side_effect_level="safe_write_review",
            allow_degraded=True,
            retryable=True,
            notes="reviewer_issue_reporting",
        ),
        AgentToolPermission(
            tool_name="create_ai_suggestion",
            agent_type=AgentType.REVIEWER,
            permission=AgentToolPermissionMode.CONDITIONAL,
            side_effect_level="safe_write_suggestion",
            allow_degraded=True,
            retryable=True,
            notes="reviewer_ai_suggestion",
        ),
        AgentToolPermission(
            tool_name="create_candidate_version",
            agent_type=AgentType.REWRITER,
            permission=AgentToolPermissionMode.ALLOW,
            side_effect_level="safe_write_candidate",
            allow_degraded=True,
            retryable=True,
            notes="rewriter_only",
        ),
        AgentToolPermission(
            tool_name="create_agent_observation",
            agent_type=AgentType.MEMORY,
            permission=AgentToolPermissionMode.ALLOW,
            side_effect_level="trace_only",
            allow_degraded=True,
            retryable=True,
            notes="shared_trace",
        ),
        AgentToolPermission(
            tool_name="create_agent_observation",
            agent_type=AgentType.PLANNER,
            permission=AgentToolPermissionMode.ALLOW,
            side_effect_level="trace_only",
            allow_degraded=True,
            retryable=True,
            notes="shared_trace",
        ),
        AgentToolPermission(
            tool_name="create_agent_observation",
            agent_type=AgentType.WRITER,
            permission=AgentToolPermissionMode.ALLOW,
            side_effect_level="trace_only",
            allow_degraded=True,
            retryable=True,
            notes="shared_trace",
        ),
        AgentToolPermission(
            tool_name="create_agent_observation",
            agent_type=AgentType.REVIEWER,
            permission=AgentToolPermissionMode.ALLOW,
            side_effect_level="trace_only",
            allow_degraded=True,
            retryable=True,
            notes="shared_trace",
        ),
        AgentToolPermission(
            tool_name="create_agent_observation",
            agent_type=AgentType.REWRITER,
            permission=AgentToolPermissionMode.ALLOW,
            side_effect_level="trace_only",
            allow_degraded=True,
            retryable=True,
            notes="shared_trace",
        ),
        AgentToolPermission(
            tool_name="create_agent_trace_event",
            agent_type=AgentType.MEMORY,
            permission=AgentToolPermissionMode.ALLOW,
            side_effect_level="trace_only",
            allow_degraded=True,
            retryable=True,
            notes="shared_trace",
        ),
        AgentToolPermission(
            tool_name="create_agent_trace_event",
            agent_type=AgentType.PLANNER,
            permission=AgentToolPermissionMode.ALLOW,
            side_effect_level="trace_only",
            allow_degraded=True,
            retryable=True,
            notes="shared_trace",
        ),
        AgentToolPermission(
            tool_name="create_agent_trace_event",
            agent_type=AgentType.WRITER,
            permission=AgentToolPermissionMode.ALLOW,
            side_effect_level="trace_only",
            allow_degraded=True,
            retryable=True,
            notes="shared_trace",
        ),
        AgentToolPermission(
            tool_name="create_agent_trace_event",
            agent_type=AgentType.REVIEWER,
            permission=AgentToolPermissionMode.ALLOW,
            side_effect_level="trace_only",
            allow_degraded=True,
            retryable=True,
            notes="shared_trace",
        ),
        AgentToolPermission(
            tool_name="create_agent_trace_event",
            agent_type=AgentType.REWRITER,
            permission=AgentToolPermissionMode.ALLOW,
            side_effect_level="trace_only",
            allow_degraded=True,
            retryable=True,
            notes="shared_trace",
        ),
        AgentToolPermission(
            tool_name="request_conflict_check",
            agent_type=AgentType.MEMORY,
            permission=AgentToolPermissionMode.CONDITIONAL,
            side_effect_level="read_only",
            allow_degraded=True,
            retryable=True,
            notes="conditional_guard_check",
        ),
        AgentToolPermission(
            tool_name="request_conflict_check",
            agent_type=AgentType.PLANNER,
            permission=AgentToolPermissionMode.CONDITIONAL,
            side_effect_level="read_only",
            allow_degraded=True,
            retryable=True,
            notes="conditional_guard_check",
        ),
        AgentToolPermission(
            tool_name="request_conflict_check",
            agent_type=AgentType.WRITER,
            permission=AgentToolPermissionMode.CONDITIONAL,
            side_effect_level="read_only",
            allow_degraded=True,
            retryable=True,
            notes="conditional_guard_check",
        ),
        AgentToolPermission(
            tool_name="request_conflict_check",
            agent_type=AgentType.REVIEWER,
            permission=AgentToolPermissionMode.CONDITIONAL,
            side_effect_level="read_only",
            allow_degraded=True,
            retryable=True,
            notes="conditional_guard_check",
        ),
        AgentToolPermission(
            tool_name="request_conflict_check",
            agent_type=AgentType.REWRITER,
            permission=AgentToolPermissionMode.CONDITIONAL,
            side_effect_level="read_only",
            allow_degraded=True,
            retryable=True,
            notes="conditional_guard_check",
        ),
    ]
    return AgentProfileRegistry(profiles=profiles, permissions=permissions)
