from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class OutlineSuggestionPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    target_kind: Literal["work_outline", "chapter_outline", "selection"]
    target_id: str | None = None
    target_revision: int | None = None
    target_content_hash: str = ""
    target_content_text: str = ""
    target_content_tree_json: Any = Field(default_factory=list)
    proposed_content_text: str = ""
    proposed_content_tree_json: Any = Field(default_factory=list)
    diff_summary: list[str] = Field(default_factory=list)

    @field_validator("proposed_content_text")
    @classmethod
    def proposed_text_must_not_be_empty(cls, value: str) -> str:
        normalized = str(value or "").strip()
        if not normalized:
            raise ValueError("proposed_content_text_empty")
        return normalized

    @model_validator(mode="after")
    def validate_target(self):
        if self.target_kind == "selection":
            if self.target_id is not None or self.target_revision is not None:
                raise ValueError("selection_target_must_be_empty")
            return self
        if not str(self.target_id or "").strip() or self.target_revision is None or not self.target_content_hash:
            raise ValueError("formal_target_incomplete")
        return self


class OutlinePolishPayload(OutlineSuggestionPayload):
    polish_notes: list[str] = Field(default_factory=list)


class OutlineExpandPayload(OutlineSuggestionPayload):
    expansion_points: list[str] = Field(default_factory=list)
    expand_focus: str | None = None


class SceneBeatPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    beat_no: int
    description: str
    characters_involved: list[str] = Field(default_factory=list)
    estimated_words: int = 0


class ChapterOutlineDetailPayload(OutlineSuggestionPayload):
    chapter_goal: str
    scene_beats: list[SceneBeatPayload] = Field(default_factory=list)
    conflict_points: list[str] = Field(default_factory=list)
    ending_hook: str = ""


class WritingTaskSuggestionPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    chapter_id: str = Field(min_length=1, max_length=200)
    target_revision: int
    target_content_hash: str = Field(min_length=64, max_length=64)
    chapter_plan_id: str = Field(min_length=1, max_length=200)
    task_title: str = Field(min_length=1, max_length=200)
    writing_goal: str = Field(min_length=1, max_length=1000)
    must_include: list[Annotated[str, Field(max_length=300)]] = Field(default_factory=list, max_length=20)
    must_not_include: list[Annotated[str, Field(max_length=300)]] = Field(default_factory=list, max_length=20)
    target_word_count: int = Field(default=0, ge=0, le=100000)
    tone_guidance: str = Field(default="", max_length=500)
    required_beats: list[Annotated[str, Field(max_length=300)]] = Field(default_factory=list, max_length=30)
    context_summary: str = Field(default="", max_length=1000)


class SuggestionLaunchResult(BaseModel):
    suggestion_id: str
    job_id: str
    status: Literal["pending"] = "pending"
    polling_hint: str = "请稍候，结果准备好后会自动显示。"
