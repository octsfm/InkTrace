from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class ChapterArcBinding:
    binding_id: str
    project_id: str
    chapter_id: str
    arc_id: str
    binding_role: str = "background"
    push_type: str = "advance"
    confidence: float = 0.6
    created_at: datetime = field(default_factory=datetime.now)
