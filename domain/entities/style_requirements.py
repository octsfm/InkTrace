from dataclasses import dataclass, field
from datetime import datetime
from typing import List

from domain.constants.story_constants import (
    DEFAULT_DIALOGUE_DENSITY,
    DEFAULT_NARRATIVE_DISTANCE,
    DEFAULT_PREFERRED_RHYTHM,
)
from domain.constants.story_enums import STYLE_SOURCE_MANUAL


@dataclass
class StyleRequirements:
    id: str
    project_id: str
    author_voice_keywords: List[str] = field(default_factory=list)
    avoid_patterns: List[str] = field(default_factory=list)
    preferred_rhythm: str = DEFAULT_PREFERRED_RHYTHM
    narrative_distance: str = DEFAULT_NARRATIVE_DISTANCE
    dialogue_density: str = DEFAULT_DIALOGUE_DENSITY
    source_type: str = STYLE_SOURCE_MANUAL
    version: int = 1
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
