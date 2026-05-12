from __future__ import annotations

from domain.services.ai.reviewer import ReviewerPort


class FakeReviewer(ReviewerPort):
    def __init__(self) -> None:
        self.calls = 0

    def review(self, *, review_context: dict[str, object], review_mode: str, user_instruction: str = "") -> dict[str, object]:
        self.calls += 1
        preview = str(review_context.get("candidate_draft_content", ""))[:120]
        return {
            "summary": f"已完成 {review_mode}，重点检查候选稿的一致性与表达清晰度。",
            "issues": [
                {
                    "issue_id": "issue_1",
                    "severity": "medium",
                    "category": "logic",
                    "message": "部分转场略快，建议补足动作连接。",
                    "suggestion": "在场景切换前增加一小句过渡。",
                    "source_ref": preview,
                }
            ],
            "suggestions": ["增强段落之间的衔接。"],
            "risk_level": "medium",
            "consistency_notes": ["人物情绪基本连贯。"],
            "style_notes": ["语言风格较统一。"],
            "logic_notes": ["情节推进清晰，但可增加因果承接。"],
            "provider_name": "fake",
            "model_name": "fake-reviewer",
            "reviewer_model_role": "reviewer",
        }


class FailingReviewer(ReviewerPort):
    def review(self, *, review_context: dict[str, object], review_mode: str, user_instruction: str = "") -> dict[str, object]:
        raise ValueError("review_failed")
