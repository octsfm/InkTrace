from __future__ import annotations

from pydantic import BaseModel, field_validator


class SelectionRewriteOutputModel(BaseModel):
    rewritten_text: str
    diff_summary: str
    risk_notes: list[str]

    @field_validator("rewritten_text")
    @classmethod
    def validate_rewritten_text(cls, value: str) -> str:
        normalized = str(value or "").strip()
        if not normalized:
            raise ValueError("rewritten_text_empty")
        return normalized
