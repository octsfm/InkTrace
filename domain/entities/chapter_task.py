from dataclasses import dataclass, field
from datetime import datetime
from typing import List

from domain.constants.story_constants import (
    DEFAULT_FORESHADOWING_ACTION,
    DEFAULT_HOOK_STRENGTH,
    DEFAULT_PACE_TARGET,
)
from domain.constants.story_enums import WRITING_STATUS_READY


@dataclass
class ChapterTask:
    id: str
    chapter_id: str
    project_id: str
    branch_id: str
    chapter_number: int
    chapter_function: str = "continue_crisis"
    goals: List[str] = field(default_factory=list)
    must_continue_points: List[str] = field(default_factory=list)
    forbidden_jumps: List[str] = field(default_factory=list)
    required_foreshadowing_action: str = DEFAULT_FORESHADOWING_ACTION
    required_hook_strength: str = DEFAULT_HOOK_STRENGTH
    pace_target: str = DEFAULT_PACE_TARGET
    opening_continuation: str = ""
    chapter_payoff: str = ""
    style_bias: str = ""
    target_arc_id: str = ""
    secondary_arc_ids: List[str] = field(default_factory=list)
    arc_stage_before: str = ""
    arc_stage_after_expected: str = ""
    arc_push_goal: str = ""
    arc_conflict_focus: str = ""
    arc_payoff_expectation: str = ""
    planning_mode: str = "light_planning"
    status: str = WRITING_STATUS_READY
    version: int = 1
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
