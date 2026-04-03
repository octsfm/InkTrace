import asyncio

from application.services.validation_service_v2 import ValidationServiceV2


class _FakeDraftIntegrityChecker:
    def __init__(self):
        self.calls = 0

    async def check(self, _structural_draft, detemplated_draft, _chapter_task):
        self.calls += 1
        content = str(detemplated_draft.get("content") or "")
        revised = "修订后" in content
        return {
            "id": f"check_{self.calls}",
            "event_integrity_ok": revised,
            "motivation_integrity_ok": revised,
            "foreshadowing_integrity_ok": revised,
            "hook_integrity_ok": revised,
            "continuity_ok": revised,
            "arc_consistency_ok": revised,
            "title_alignment_ok": True,
            "progression_integrity_ok": revised,
            "risk_notes": [] if revised else ["连续性不足"],
        }


class _FakePromptAIService:
    def __init__(self):
        self.calls = 0

    async def revise_detemplated_draft(self, **kwargs):
        self.calls += 1
        original = str((kwargs.get("detemplated_draft") or {}).get("content") or "")
        return {
            "content": f"{original}\n修订后补强了承接与剧情弧推进。",
            "used_fallback": False,
            "integrity_failed": False,
            "display_fallback_to_structural": False,
            "revision_applied": True,
        }


class _FakeWorkflow:
    def __init__(self):
        self.draft_integrity_checker = _FakeDraftIntegrityChecker()
        self.prompt_ai_service = _FakePromptAIService()

    def _is_integrity_ok(self, check):
        return bool(
            check.get("event_integrity_ok")
            and check.get("motivation_integrity_ok")
            and check.get("foreshadowing_integrity_ok")
            and check.get("hook_integrity_ok")
            and check.get("continuity_ok")
            and check.get("arc_consistency_ok", True)
        )


def test_validation_service_revises_failed_draft_once():
    workflow = _FakeWorkflow()
    service = ValidationServiceV2(workflow)
    result = asyncio.run(
        service.validate_and_revise(
            structural_draft={"project_id": "p1", "chapter_id": "c1", "chapter_number": 3, "content": "结构稿"},
            detemplated_draft={"content": "初稿内容"},
            chapter_task={"id": "t1"},
            global_constraints={},
            style_requirements={},
        )
    )

    assert workflow.prompt_ai_service.calls == 1
    assert workflow.draft_integrity_checker.calls == 2
    assert "修订后" in result["detemplated_draft"]["content"]
    assert result["integrity_check"]["revision_attempted"] is True
    assert result["integrity_check"]["revision_succeeded"] is True
    assert result["revision_attempts"][0]["revision_applied"] is True
