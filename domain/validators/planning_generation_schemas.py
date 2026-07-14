from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class DirectionConflictOutput(_StrictModel):
    conflict_name: str
    conflict_description: str
    conflict_type: str
    intensity: str = ""


class DirectionForeshadowOutput(_StrictModel):
    foreshadow_id: str = ""
    foreshadow_description: str
    usage_plan: str
    is_new: bool = False


class DirectionRiskOutput(_StrictModel):
    risk_description: str
    risk_severity: str
    mitigation: str = ""


class DirectionScoreOutput(_StrictModel):
    total_score: int = Field(ge=0, le=100)
    consistency_score: int = Field(ge=0, le=100)
    conflict_density_score: int = Field(ge=0, le=100)
    satisfaction_rhythm_score: int = Field(ge=0, le=100)
    foreshadow_progress_score: int = Field(ge=0, le=100)
    risk_controllability_score: int = Field(ge=0, le=100)
    score_rationale: str = ""


class DirectionOptionOutput(_StrictModel):
    label: str
    title: str
    plot_summary: str
    narrative_premise: str
    narrative_benefits: list[str] = Field(default_factory=list)
    main_conflicts: list[DirectionConflictOutput] = Field(default_factory=list)
    foreshadow_usage: list[DirectionForeshadowOutput] = Field(default_factory=list)
    risk_points: list[DirectionRiskOutput] = Field(default_factory=list)
    estimated_chapters: int = Field(ge=1, le=20)
    chapter_preview: list[str] = Field(default_factory=list)
    score: DirectionScoreOutput
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    tone_direction: str = ""
    key_characters_involved: list[str] = Field(default_factory=list)


class DirectionGenerationOutput(_StrictModel):
    options: list[DirectionOptionOutput] = Field(min_length=3, max_length=3)


class ChapterBeatOutput(_StrictModel):
    beat_order: int = Field(ge=1)
    beat_name: str
    beat_description: str
    beat_type: str
    emotional_tone: str = ""
    involved_characters: list[str] = Field(default_factory=list)


class ForeshadowArrangementOutput(_StrictModel):
    foreshadow_id: str = ""
    foreshadow_description: str
    arrangement: str
    arrangement_detail: str = ""


class ChapterPlanItemOutput(_StrictModel):
    plan_order: int = Field(ge=1)
    chapter_goal: str
    key_events: list[ChapterBeatOutput] = Field(default_factory=list)
    conflict_progression: str
    foreshadow_arrangement: list[ForeshadowArrangementOutput] = Field(default_factory=list)
    forbidden_items: list[str] = Field(default_factory=list)
    required_beats: list[str] = Field(default_factory=list)
    estimated_word_count: int = Field(default=0, ge=0)
    estimated_word_count_max: int = Field(default=0, ge=0)
    tone_hint: str = ""
    pov_hint: str = ""


class ChapterPlanGenerationOutput(_StrictModel):
    plan_items: list[ChapterPlanItemOutput] = Field(min_length=1)
    plan_summary: str
    constraints: list[str] = Field(default_factory=list)

