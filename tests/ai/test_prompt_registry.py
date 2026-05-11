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
