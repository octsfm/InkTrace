from __future__ import annotations

import json
from pathlib import Path

from domain.entities.ai.models import PromptTemplate


class _StrictFormatDict(dict[str, object]):
    def __missing__(self, key: str) -> object:
        raise ValueError(f"prompt_variable_missing:{key}")


class PromptRegistry:
    def __init__(self, prompt_directory: Path | str | None = None) -> None:
        base_directory = Path(prompt_directory) if prompt_directory else Path(__file__).resolve().parents[2] / "prompts" / "ai"
        self._prompt_directory = base_directory
        self._templates: dict[tuple[str, str], PromptTemplate] = {}
        self._default_versions: dict[str, str] = {}
        self._loaded = False

    def get_template(self, prompt_key: str, version: str | None = None) -> PromptTemplate:
        self._load_templates()
        resolved_version = version or self._default_versions.get(prompt_key, "")
        template = self._templates.get((prompt_key, resolved_version))
        if template is None or not template.enabled:
            raise ValueError("prompt_template_missing")
        return template

    def render(self, prompt_key: str, variables: dict[str, object], version: str | None = None) -> str:
        template = self.get_template(prompt_key, version=version)
        return template.template_text.format_map(_StrictFormatDict(variables))

    def _load_templates(self) -> None:
        if self._loaded:
            return
        self._loaded = True
        if not self._prompt_directory.exists():
            return
        for file_path in sorted(self._prompt_directory.glob("*.json")):
            payload = json.loads(file_path.read_text(encoding="utf-8"))
            template = PromptTemplate.model_validate(payload)
            self._templates[(template.prompt_key, template.prompt_version)] = template
            self._default_versions.setdefault(template.prompt_key, template.prompt_version)
