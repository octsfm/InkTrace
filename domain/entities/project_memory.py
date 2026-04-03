from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List


@dataclass
class ProjectMemory:
    id: str
    project_id: str
    characters: List[Dict[str, Any]] = field(default_factory=list)
    world_facts: Dict[str, Any] = field(default_factory=dict)
    plot_arcs: List[Dict[str, Any]] = field(default_factory=list)
    events: List[Dict[str, Any]] = field(default_factory=list)
    style_profile: Dict[str, Any] = field(default_factory=dict)
    outline_context: Dict[str, Any] = field(default_factory=dict)
    current_state: Dict[str, Any] = field(default_factory=dict)
    chapter_summaries: List[str] = field(default_factory=list)
    continuity_flags: List[Dict[str, Any]] = field(default_factory=list)
    global_constraints: Dict[str, Any] = field(default_factory=dict)
    chapter_analysis_memory_refs: List[str] = field(default_factory=list)
    chapter_continuation_memory_refs: List[str] = field(default_factory=list)
    chapter_task_refs: List[str] = field(default_factory=list)
    style_requirements: Dict[str, Any] = field(default_factory=dict)
    version: int = 1
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
