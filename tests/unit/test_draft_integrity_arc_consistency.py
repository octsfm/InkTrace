import asyncio

from application.services.draft_integrity_checker import DraftIntegrityChecker


class _FakePromptAIService:
    async def check_draft_integrity(self, _structural_draft, _detemplated_draft, _chapter_task):
        return {
            "event_integrity_ok": True,
            "motivation_integrity_ok": True,
            "foreshadowing_integrity_ok": True,
            "hook_integrity_ok": True,
            "continuity_ok": True,
            "arc_consistency_ok": True,
            "risk_notes": [],
        }


class _FakeWorkflowService:
    def __init__(self, heuristic):
        self._heuristic = heuristic
        self.prompt_ai_service = _FakePromptAIService()

    def _check_draft_integrity(self, _structural_draft, _detemplated_draft, _chapter_task):
        return dict(self._heuristic)

    def _is_integrity_ok(self, check):
        required = [
            "event_integrity_ok",
            "motivation_integrity_ok",
            "foreshadowing_integrity_ok",
            "hook_integrity_ok",
            "continuity_ok",
            "arc_consistency_ok",
        ]
        return all(bool(check.get(key)) for key in required)


def test_arc_consistency_failed_adds_risk_note():
    checker = DraftIntegrityChecker(
        _FakeWorkflowService(
            {
                "event_integrity_ok": True,
                "motivation_integrity_ok": True,
                "foreshadowing_integrity_ok": True,
                "hook_integrity_ok": True,
                "continuity_ok": True,
                "arc_consistency_ok": False,
                "risk_notes": [],
            }
        )
    )
    result = asyncio.run(checker.check({}, {}, {}))
    assert result["arc_consistency_ok"] is False
    assert any("剧情弧推进一致性不足" in item for item in result["risk_notes"])


def test_arc_consistency_pass_keeps_integrity():
    checker = DraftIntegrityChecker(
        _FakeWorkflowService(
            {
                "event_integrity_ok": True,
                "motivation_integrity_ok": True,
                "foreshadowing_integrity_ok": True,
                "hook_integrity_ok": True,
                "continuity_ok": True,
                "arc_consistency_ok": True,
                "risk_notes": [],
            }
        )
    )
    result = asyncio.run(checker.check({}, {}, {}))
    assert result["arc_consistency_ok"] is True
