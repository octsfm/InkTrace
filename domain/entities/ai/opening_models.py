from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class OpeningBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class OpeningBriefStatus(StrEnum):
    COLLECTING = "collecting_brief"
    READY = "ready"


class OpeningDirectionStatus(StrEnum):
    PROPOSED = "proposed"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"


class OpeningBatchStatus(StrEnum):
    PREPARING = "preparing"
    WAITING_DIRECTION_CHOICE = "waiting_direction_choice"
    GENERATING = "generating_drafts"
    PARTIAL_SUCCESS = "partial_success"
    WAITING_DRAFT_REVIEW = "waiting_draft_review"
    COMPLETED = "completed"
    FAILED = "failed"
    STOPPED = "stopped"


class OpeningRiskLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class OpeningBrief(OpeningBaseModel):
    brief_id: str
    work_id: str
    story_premise: str
    protagonist_desire: str
    third_chapter_expectation: str
    source_outline_version: str = ""
    source_asset_versions: dict[str, str] = Field(default_factory=dict)
    status: OpeningBriefStatus = OpeningBriefStatus.READY
    idempotency_key: str = ""
    created_at: str
    updated_at: str


class OpeningReferenceSummary(OpeningBaseModel):
    reference_id: str
    title: str
    chapter_count: int
    word_count: int
    source_text_hash: str
    analysis_summary: str


class OpeningReferenceSession(OpeningBaseModel):
    reference_session_id: str
    brief_id: str
    work_id: str
    reference_summaries: list[OpeningReferenceSummary] = Field(default_factory=list)
    copyright_confirmed_at: str
    rights_text_version: str
    status: str = "analyzed"
    expires_at: str = ""
    idempotency_key: str = ""
    created_at: str
    updated_at: str


class OpeningDirection(OpeningBaseModel):
    direction_id: str
    batch_id: str
    brief_id: str
    work_id: str
    name: str
    summary: str
    chapter_goals: list[str] = Field(default_factory=list)
    advantages: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    revision_no: int = 1
    parent_direction_id: str = ""
    status: OpeningDirectionStatus = OpeningDirectionStatus.PROPOSED
    confirmed_by: str = ""
    confirmed_at: str = ""
    created_at: str
    updated_at: str


class OpeningDirectionBatch(OpeningBaseModel):
    batch_id: str
    brief_id: str
    work_id: str
    directions: list[OpeningDirection] = Field(default_factory=list)
    confirmed_direction_id: str = ""
    status: OpeningBatchStatus = OpeningBatchStatus.WAITING_DIRECTION_CHOICE
    idempotency_key: str = ""
    created_at: str
    updated_at: str


class OpeningChapterResult(OpeningBaseModel):
    chapter_no: int
    status: str
    candidate_draft_id: str = ""
    review_id: str = ""
    originality_report_id: str = ""
    error_code: str = ""


class OpeningDraftBatch(OpeningBaseModel):
    draft_batch_id: str
    work_id: str
    brief_id: str
    direction_id: str
    status: OpeningBatchStatus
    chapter_results: list[OpeningChapterResult] = Field(default_factory=list)
    result_refs: list[str] = Field(default_factory=list)
    idempotency_key: str = ""
    created_at: str
    updated_at: str


class OpeningOriginalityReport(OpeningBaseModel):
    report_id: str
    work_id: str
    brief_id: str
    direction_id: str
    draft_batch_id: str = ""
    candidate_draft_id: str = ""
    candidate_version_id: str = ""
    check_stage: str
    risk_level: OpeningRiskLevel
    evidence_summary: str = ""
    revision_suggestions: list[str] = Field(default_factory=list)
    status: str = "completed"
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: str

