from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List


@dataclass
class ContinuationContextSnapshot:
    id: str
    project_id: str
    chapter_id: str
    chapter_number: int
    recent_chapter_memories: List[Dict[str, Any]] = field(default_factory=list)
    last_chapter_tail: str = ""
    relevant_characters: List[Dict[str, Any]] = field(default_factory=list)
    relevant_foreshadowing: List[str] = field(default_factory=list)
    global_constraints: Dict[str, Any] = field(default_factory=dict)
    chapter_task_seed: Dict[str, Any] = field(default_factory=dict)
    style_requirements: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
