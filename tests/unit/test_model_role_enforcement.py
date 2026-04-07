import asyncio
import json
import os
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from application.agent_mvp.model_role_router import ModelRoleRouter
from application.services.chapter_ai_service import ChapterAIService
from domain.entities.model_role import ModelRole
from domain.exceptions import LLMClientError


class _RecordingClient:
    def __init__(self, model_name: str, responses=None):
        self._model_name = model_name
        self._responses = list(responses or [])
        self.calls = []

    @property
    def model_name(self) -> str:
        return self._model_name

    async def generate(self, prompt: str, max_tokens: int = 1600, temperature: float = 0.35) -> str:
        self.calls.append(
            {
                "prompt": prompt,
                "max_tokens": max_tokens,
                "temperature": temperature,
            }
        )
        response = self._responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response

    async def is_available(self) -> bool:
        return True


class _FakeFactory:
    def __init__(self, deepseek_responses=None, kimi_responses=None, deepseek_fallback_responses=None, kimi_fallback_responses=None):
        self.deepseek_client = _RecordingClient("deepseek", deepseek_responses)
        self.kimi_client = _RecordingClient("kimi", kimi_responses)
        self.deepseek_fallback_client = _RecordingClient("deepseek-fallback", deepseek_fallback_responses)
        self.kimi_fallback_client = _RecordingClient("kimi-fallback", kimi_fallback_responses)
        self.primary_client = self.deepseek_client
        self.backup_client = self.kimi_client

    def get_client_for_provider(self, provider: str):
        if provider == "deepseek":
            return self.deepseek_client
        if provider == "kimi":
            return self.kimi_client
        raise ValueError(provider)

    def get_fallback_client_for_provider(self, provider: str):
        if provider == "deepseek":
            return self.deepseek_fallback_client if self.deepseek_fallback_client._responses else None
        if provider == "kimi":
            return self.kimi_fallback_client if self.kimi_fallback_client._responses else None
        return None


def test_global_analysis_uses_kimi_only():
    factory = _FakeFactory(
        kimi_responses=[
            json.dumps(
                {
                    "characters": [],
                    "world_facts": {},
                    "style_profile": {},
                    "global_constraints": {"main_plot": "main", "hidden_plot": ""},
                    "chapter_summaries": ["c1"],
                    "main_plot_lines": ["main"],
                }
            )
        ]
    )
    service = ChapterAIService(factory)

    result = asyncio.run(
        service.analyze_global_story(
            {
                "project_id": "p1",
                "project_name": "Novel",
                "outline_context": {},
                "chapters": [{"title": "Chapter 1", "content_preview": "text"}],
            }
        )
    )

    assert result["main_plot_lines"] == ["main"]
    assert len(factory.kimi_client.calls) == 1
    assert factory.deepseek_client.calls == []


def test_plot_arc_extraction_uses_kimi_only():
    factory = _FakeFactory(
        kimi_responses=[
            json.dumps(
                {
                    "plot_arcs": [
                        {
                            "arc_id": "arc_1",
                            "title": "Main Arc",
                            "arc_type": "main_arc",
                            "priority": "core",
                            "status": "active",
                            "current_stage": "setup",
                        }
                    ],
                    "chapter_arc_bindings": [
                        {
                            "chapter_number": 1,
                            "chapter_id": "ch1",
                            "arc_id": "arc_1",
                            "binding_role": "primary",
                            "push_type": "advance",
                            "confidence": 0.8,
                        }
                    ],
                    "active_arc_ids": ["arc_1"],
                }
            )
        ]
    )
    service = ChapterAIService(factory)

    result = asyncio.run(
        service.extract_plot_arcs(
            {
                "project_id": "p1",
                "global_analysis": {"main_plot_lines": ["main"]},
                "chapter_artifacts": [{"chapter_id": "ch1", "chapter_number": 1}],
            }
        )
    )

    assert "arc_1" in result["active_arc_ids"]
    assert len(result["active_arc_ids"]) == 3
    assert len(result["plot_arcs"]) >= 3
    main_arc = next(item for item in result["plot_arcs"] if item["arc_id"] == "arc_1")
    assert main_arc["arc_type"] == "main_arc"
    assert main_arc["stage_reason"]
    assert main_arc["stage_confidence"] >= 0.55
    assert len(factory.kimi_client.calls) == 1
    assert factory.deepseek_client.calls == []


def test_outline_analysis_uses_kimi_only():
    factory = _FakeFactory(
        kimi_responses=[
            json.dumps(
                {
                    "goal": "push the arc",
                    "conflict": "conflict",
                    "events": ["event 1"],
                    "character_progress": "growth",
                    "ending_hook": "hook",
                }
            )
        ]
    )
    service = ChapterAIService(factory)

    result = asyncio.run(service.analyze_to_outline("Chapter 1", "Story text"))

    assert result["outline_draft"]["goal"] == "push the arc"
    assert len(factory.kimi_client.calls) == 1
    assert factory.deepseek_client.calls == []


def test_structural_writing_uses_deepseek_only():
    factory = _FakeFactory(
        deepseek_responses=[
            json.dumps(
                {
                    "title": "Draft",
                    "content": "Body",
                    "new_events": [],
                    "possible_continuity_flags": [],
                }
            )
        ]
    )
    service = ChapterAIService(factory)
    context = SimpleNamespace(
        project_id="p1",
        chapter_id="c1",
        chapter_number=3,
        recent_chapter_memories=[],
        last_chapter_tail="tail",
        relevant_characters=[],
        relevant_foreshadowing=[],
    )

    result = asyncio.run(service.generate_structural_draft({"chapter_id": "c1", "chapter_number": 3}, context, {}, 1800))

    assert result["content"] == "Body"
    assert len(factory.deepseek_client.calls) == 1
    assert factory.kimi_client.calls == []


def test_detemplating_rewrite_uses_deepseek_only():
    factory = _FakeFactory(deepseek_responses=["Refined draft"])
    service = ChapterAIService(factory)

    result = asyncio.run(service.rewrite_detemplated_draft({"project_id": "p1", "chapter_id": "c1", "chapter_number": 2, "content": "raw"}, {}, {}, {}))

    assert result["content"] == "Refined draft"
    assert len(factory.deepseek_client.calls) == 1
    assert factory.kimi_client.calls == []


def test_consistency_validation_uses_kimi_only():
    factory = _FakeFactory(
        kimi_responses=[
            json.dumps(
                {
                    "event_integrity_ok": True,
                    "motivation_integrity_ok": True,
                    "foreshadowing_integrity_ok": True,
                    "hook_integrity_ok": True,
                    "continuity_ok": True,
                    "risk_notes": [],
                }
            )
        ]
    )
    service = ChapterAIService(factory)

    result = asyncio.run(
        service.check_draft_integrity(
            {"project_id": "p1", "chapter_id": "c1", "chapter_number": 4, "content": "structural"},
            {"content": "detemplated"},
            {},
        )
    )

    assert result["continuity_ok"] is True
    assert len(factory.kimi_client.calls) == 1
    assert factory.deepseek_client.calls == []


def test_degraded_mode_does_not_cross_role_boundary():
    factory = _FakeFactory(
        deepseek_responses=["should-not-be-used"],
        kimi_responses=[RuntimeError("kimi failed")],
    )

    with patch.dict(os.environ, {"INKTRACE_MODEL_ROLE_MODE": "degraded"}):
        router = ModelRoleRouter(factory)
        result = asyncio.run(router.generate(ModelRole.GLOBAL_ANALYSIS, "prompt"))

    assert result["ok"] is False
    assert result["provider"] == "kimi"
    assert result["degraded_mode"] is True
    assert len(factory.kimi_client.calls) == 1
    assert factory.deepseek_client.calls == []


def test_global_analysis_requires_kimi_success_when_strict_requested():
    factory = _FakeFactory(kimi_responses=[RuntimeError("kimi failed")])
    service = ChapterAIService(factory)

    with pytest.raises(LLMClientError):
        asyncio.run(
            service.analyze_global_story(
                {
                    "project_id": "p1",
                    "project_name": "Novel",
                    "outline_context": {},
                    "chapters": [{"title": "Chapter 1", "content_preview": "text"}],
                    "require_model_success": True,
                }
            )
        )

    assert len(factory.kimi_client.calls) == 1
    assert factory.deepseek_client.calls == []


def test_plot_arc_extraction_requires_kimi_success_when_strict_requested():
    factory = _FakeFactory(kimi_responses=[RuntimeError("kimi failed")])
    service = ChapterAIService(factory)

    with pytest.raises(LLMClientError):
        asyncio.run(
            service.extract_plot_arcs(
                {
                    "project_id": "p1",
                    "global_analysis": {"main_plot_lines": ["main"]},
                    "chapter_artifacts": [{"chapter_id": "ch1", "chapter_number": 1}],
                    "require_model_success": True,
                }
            )
        )

    assert len(factory.kimi_client.calls) == 1
    assert factory.deepseek_client.calls == []


def test_degraded_mode_uses_same_provider_fallback():
    factory = _FakeFactory(
        kimi_responses=[RuntimeError("kimi failed")],
        kimi_fallback_responses=[json.dumps({"goal": "fallback worked", "conflict": "", "events": [], "character_progress": "", "ending_hook": ""})],
    )

    with patch.dict(os.environ, {"INKTRACE_MODEL_ROLE_MODE": "degraded"}):
        service = ChapterAIService(factory)
        result = asyncio.run(service.analyze_to_outline("Chapter 1", "Story text"))

    assert result["used_fallback"] is False
    assert result["outline_draft"]["goal"] == "fallback worked"
    assert len(factory.kimi_client.calls) == 1
    assert len(factory.kimi_fallback_client.calls) == 1
    assert factory.deepseek_client.calls == []
