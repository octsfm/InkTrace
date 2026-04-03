from dataclasses import dataclass, field
from datetime import datetime

from domain.constants.story_enums import GENERATION_STAGE_STRUCTURAL


@dataclass
class StructuralDraft:
    id: str
    chapter_id: str
    project_id: str
    chapter_number: int
    title: str = ""
    content: str = ""
    source_task_id: str = ""
    model_name: str = ""
    used_fallback: bool = False
    generation_stage: str = GENERATION_STAGE_STRUCTURAL
    version: int = 1
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
