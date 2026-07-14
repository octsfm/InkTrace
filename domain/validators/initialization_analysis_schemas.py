from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class OutlineAnalysisOutputModel(_StrictModel):
    global_summary: str = Field(min_length=1)
    genre: str = ""
    tone: str = ""
    issues: list[str] = Field(default_factory=list)
    outline_empty: bool = False
    story_phase_map: list[str] = Field(default_factory=list)
    main_conflict: str = ""
    important_characters: list[str] = Field(default_factory=list)
    setting_facts: list[str] = Field(default_factory=list)
    foreshadow_map: list[str] = Field(default_factory=list)
    expected_story_direction: str = ""
    analysis_confidence: float = Field(default=0.0, ge=0.0, le=1.0)


class ChapterSceneOutputModel(_StrictModel):
    scene_order: int = Field(ge=1)
    location: str = Field(min_length=1)
    time_of_day: str = ""
    atmosphere: str = ""
    characters_present: list[str] = Field(default_factory=list)
    emotional_tone: str = ""
    pov_hint: str = ""
    reveal_points: list[str] = Field(default_factory=list)


class CharacterStateDeltaOutputModel(_StrictModel):
    character_name: str = Field(min_length=1)
    current_location: str = ""
    current_status: str = ""
    recent_actions: list[str] = Field(default_factory=list)
    relationships: list[str] = Field(default_factory=list)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)


class SettingFactDeltaOutputModel(_StrictModel):
    fact_type: str = ""
    description: str = Field(min_length=1)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)


class ForeshadowCandidateDeltaOutputModel(_StrictModel):
    description: str = Field(min_length=1)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)


class ManuscriptChapterAnalysisOutputModel(_StrictModel):
    summary: str = Field(min_length=1)
    characters: list[str] = Field(default_factory=list)
    locations: list[str] = Field(default_factory=list)
    plot_points: list[str] = Field(default_factory=list)
    unresolved_threads: list[str] = Field(default_factory=list)
    scene_details: list[ChapterSceneOutputModel] = Field(default_factory=list)
    chapter_position: str = ""
    plot_progress: str = ""
    character_state_delta: list[CharacterStateDeltaOutputModel] = Field(default_factory=list)
    setting_fact_delta: list[SettingFactDeltaOutputModel] = Field(default_factory=list)
    foreshadow_candidate_delta: list[ForeshadowCandidateDeltaOutputModel] = Field(default_factory=list)
    deviations_from_outline: list[str] = Field(default_factory=list)
    timeline_info: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    analysis_confidence: float = Field(default=0.0, ge=0.0, le=1.0)


class StoryMemoryLayerSummaryOutputModel(_StrictModel):
    title: str = Field(min_length=1)
    chapter_ids: list[str] = Field(min_length=1)
    summary: str = Field(min_length=1)
    main_conflict: str = ""
    plot_progress: str = ""
    open_loops: list[str] = Field(default_factory=list)


class StoryMemoryStructureOutputModel(_StrictModel):
    stage_summaries: list[StoryMemoryLayerSummaryOutputModel] = Field(min_length=1)
    volume_summaries: list[StoryMemoryLayerSummaryOutputModel] = Field(min_length=1)
    warnings: list[str] = Field(default_factory=list)
    analysis_confidence: float = Field(default=0.0, ge=0.0, le=1.0)


class StoryMemoryGlobalOutputModel(_StrictModel):
    global_summary: str = Field(min_length=1)
    current_story_phase: str = ""
    main_plot_threads: list[str] = Field(default_factory=list)
    unresolved_questions: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    analysis_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
