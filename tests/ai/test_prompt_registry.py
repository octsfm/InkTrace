from __future__ import annotations

from pathlib import Path

import pytest

from application.services.ai.prompt_registry import PromptRegistry


def test_prompt_registry_loads_template_and_renders_variables() -> None:
    prompt_dir = Path(__file__).resolve().parents[2] / "application" / "prompts" / "ai"
    registry = PromptRegistry(prompt_directory=prompt_dir)

    template = registry.get_template("provider_connection_test_p0")
    rendered = registry.render(
        "provider_connection_test_p0",
        {"provider_name": "fake", "model_name": "fake-chat"},
    )

    assert template.prompt_key == "provider_connection_test_p0"
    assert "fake" in rendered
    assert "fake-chat" in rendered


def test_prompt_registry_raises_when_variable_missing() -> None:
    prompt_dir = Path(__file__).resolve().parents[2] / "application" / "prompts" / "ai"
    registry = PromptRegistry(prompt_directory=prompt_dir)

    with pytest.raises(ValueError, match="prompt_variable_missing"):
        registry.render("provider_connection_test_p0", {"provider_name": "fake"})


def test_prompt_registry_loads_selection_rewrite_template_and_renders_variables() -> None:
    prompt_dir = Path(__file__).resolve().parents[2] / "application" / "prompts" / "ai"
    registry = PromptRegistry(prompt_directory=prompt_dir)

    template = registry.get_template("selection_expand_v1")
    rendered = registry.render(
        "selection_expand_v1",
        {
            "source_text": "月光落在窗台上",
            "context_before": "夜里很安静。",
            "context_after": "窗外传来风声。"
        },
    )

    assert template.prompt_key == "selection_expand_v1"
    assert template.model_role == "writer"
    assert template.output_schema_key == "selection_rewrite_schema"
    assert "月光落在窗台上" in rendered
    assert "夜里很安静。" in rendered
