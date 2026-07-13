from __future__ import annotations

import os
from dataclasses import dataclass

from domain.repositories.ai.feature_preference_repository import FeaturePreferenceRepository


class FeatureCapabilityError(RuntimeError):
    def __init__(self, error_code: str) -> None:
        self.error_code = error_code
        super().__init__(error_code)


@dataclass(frozen=True)
class FeatureDefinition:
    feature_key: str
    env_name: str
    label: str
    description: str
    release_level: str
    system_default: bool
    user_default: bool
    configurable: bool = True


FEATURE_DEFINITIONS: tuple[FeatureDefinition, ...] = (
    FeatureDefinition("enable_auto_queue", "INKTRACE_P2_ENABLE_AUTO_QUEUE", "接着写", "写一章独立新稿，看过以后再决定。", "available", True, True),
    FeatureDefinition("enable_style_dna", "INKTRACE_P2_ENABLE_STYLE_DNA", "风格画像", "整理你的写作特点，帮助新稿保持风格。", "available", True, False),
    FeatureDefinition("enable_mentions", "INKTRACE_P2_ENABLE_MENTIONS", "@引用", "在正文中快速引用人物、事件和伏笔。", "available", True, False),
    FeatureDefinition("enable_opening_agent", "INKTRACE_P2_ENABLE_OPENING_AGENT", "开篇助手", "从故事想法出发，准备原创开篇候选稿。", "available", True, False),
    FeatureDefinition("enable_outline_assist", "INKTRACE_P2_ENABLE_OUTLINE_ASSIST", "大纲辅助", "润色、扩写或整理故事大纲。", "available", True, False),
    FeatureDefinition("enable_selection_rewrite", "INKTRACE_P2_ENABLE_SELECTION_REWRITE", "选区改写", "选中一段文字后扩写、缩写或润色。", "available", True, False),
    FeatureDefinition("enable_multi_chapter", "INKTRACE_P2_ENABLE_MULTI_CHAPTER", "多章续写", "逐章准备多份候选稿，每章都由你确认。", "available", True, False),
    FeatureDefinition("enable_citation_link", "INKTRACE_P2_ENABLE_CITATION_LINK", "引用来源", "查看新稿参考了哪些前文和资料。", "available", True, False),
    FeatureDefinition("enable_cost_dashboard", "INKTRACE_P2_ENABLE_COST_DASHBOARD", "AI 用量与预算", "查看预计费用，并设置使用保护。", "available", True, False),
    FeatureDefinition("enable_analysis_dashboard", "INKTRACE_P2_ENABLE_ANALYSIS_DASHBOARD", "创作分析", "查看篇幅、节奏、对白和用词变化。", "available", True, False),
)


def _read_bool(value: str | None, default: bool) -> bool:
    if value is None or not str(value).strip():
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def is_system_feature_available_by_env(env_name: str) -> bool:
    definition = next((item for item in FEATURE_DEFINITIONS if item.env_name == env_name), None)
    return _read_bool(os.getenv(env_name), definition.system_default if definition else False)


class FeatureCapabilityService:
    def __init__(self, repository: FeaturePreferenceRepository) -> None:
        self._repository = repository

    def list_capabilities(self) -> dict[str, object]:
        preferences = self._repository.load()
        return {"capabilities": [self._serialize(item, preferences) for item in FEATURE_DEFINITIONS]}

    def is_effectively_enabled_by_env(self, env_name: str) -> bool:
        definition = next((item for item in FEATURE_DEFINITIONS if item.env_name == env_name), None)
        if definition is None:
            return False
        item = self._serialize(definition, self._repository.load())
        return bool(item["effective_enabled"])

    def update_preference(
        self,
        *,
        feature_key: str,
        enabled: bool,
        idempotency_key: str,
    ) -> dict[str, object]:
        definition = self._find(feature_key)
        system_available = self._system_available(definition)
        if enabled and (not system_available or definition.release_level == "unavailable"):
            raise FeatureCapabilityError("P2_FEATURE_DISABLED")
        preferences = self._repository.save_preference(
            feature_key=feature_key,
            enabled=enabled,
            idempotency_key=idempotency_key,
        )
        return {"capability": self._serialize(definition, preferences)}

    def _find(self, feature_key: str) -> FeatureDefinition:
        for item in FEATURE_DEFINITIONS:
            if item.feature_key == feature_key:
                return item
        raise FeatureCapabilityError("P2_FEATURE_DISABLED")

    def _system_available(self, definition: FeatureDefinition) -> bool:
        return is_system_feature_available_by_env(definition.env_name)

    def _serialize(self, definition: FeatureDefinition, preferences: dict[str, bool]) -> dict[str, object]:
        system_available = self._system_available(definition)
        user_enabled = bool(preferences.get(definition.feature_key, definition.user_default))
        effective_enabled = system_available and user_enabled and definition.release_level != "unavailable"
        if not system_available or definition.release_level == "unavailable":
            reason = "这个功能正在完善，暂时还不能使用。"
        elif not user_enabled:
            reason = "你可以在这里开启这个写作助手。"
        else:
            reason = "这个写作助手已经开启。"
        return {
            "feature_key": definition.feature_key,
            "label": definition.label,
            "description": definition.description,
            "release_level": definition.release_level,
            "system_available": system_available,
            "user_enabled": user_enabled,
            "effective_enabled": effective_enabled,
            "configurable": definition.configurable and system_available and definition.release_level != "unavailable",
            "reason": reason,
        }
