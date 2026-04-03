from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict

from domain.constants.story_enums import GENERATION_STAGE_DETEMPLATED


@dataclass
class DetemplatedDraft:
    id: str
    chapter_id: str
    project_id: str
    chapter_number: int
    title: str = ""
    content: str = ""
    based_on_structural_draft_id: str = ""
    style_requirements_snapshot: Dict[str, Any] = field(default_factory=dict)
    model_name: str = ""
    used_fallback: bool = False
    integrity_failed: bool = False
    display_fallback_to_structural: bool = False
    generation_stage: str = GENERATION_STAGE_DETEMPLATED
    version: int = 1
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
