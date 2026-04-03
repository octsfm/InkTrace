from dataclasses import dataclass, field
from datetime import datetime
from typing import List


@dataclass
class GlobalConstraints:
    id: str
    project_id: str
    main_plot: str = ""
    hidden_plot: str = ""
    core_selling_points: List[str] = field(default_factory=list)
    protagonist_core_traits: List[str] = field(default_factory=list)
    must_keep_threads: List[str] = field(default_factory=list)
    genre_guardrails: List[str] = field(default_factory=list)
    source_type: str = "system"
    version: int = 1
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
