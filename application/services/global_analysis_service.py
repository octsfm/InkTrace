from __future__ import annotations

from typing import Any, Dict, List

from application.prompts.prompt_input_builder import PromptInputBuilder
from application.services.chapter_ai_service import ChapterAIService


class GlobalAnalysisService:
    def __init__(self, chapter_ai_service: ChapterAIService, memory_provider: Any = None):
        self.chapter_ai_service = chapter_ai_service
        self.memory_provider = memory_provider

    async def analyze_story(
        self,
        project_id: str,
        project_name: str,
        outline_context: Dict[str, Any],
        chapters: List[Dict[str, Any]],
        require_model_success: bool = False,
        chapter_artifacts: List[Dict[str, Any]] | None = None,
    ) -> Dict[str, object]:
        payload = PromptInputBuilder.build_global_analysis_input(
            project_name,
            outline_context or {},
            chapters or [],
            chapter_artifacts=chapter_artifacts or [],
        )
        payload["project_id"] = project_id
        payload["require_model_success"] = bool(require_model_success)
        if hasattr(self.chapter_ai_service, "analyze_global_story"):
            return await self.chapter_ai_service.analyze_global_story(payload)
        if require_model_success:
            raise RuntimeError("kimi 全书分析失败，已停止整理，请检查模型配置后重试")
        summaries = []
        source_items = chapter_artifacts or chapters or []
        for item in source_items:
            if not isinstance(item, dict):
                continue
            title = str(item.get("chapter_title") or item.get("title") or "").strip()
            content = str(
                item.get("analysis_summary")
                or item.get("scene_summary")
                or item.get("content_preview")
                or item.get("content")
                or ""
            ).strip().replace("\n", " ")
            summaries.append(f"{title}:{content[:80]}".strip(":"))
        premise = str((outline_context or {}).get("premise") or "").strip()
        background = str((outline_context or {}).get("story_background") or "").strip()
        world = str((outline_context or {}).get("world_setting") or "").strip()
        return {
            "characters": [],
            "world_facts": {"background": [world] if world else [], "power_system": [], "organizations": [], "locations": [], "rules": [], "artifacts": []},
            "style_profile": {"narrative_pov": "third_person_limited", "tone_tags": [], "rhythm_tags": []},
            "global_constraints": {
                "main_plot": premise,
                "hidden_plot": background,
                "core_selling_points": [],
                "protagonist_core_traits": [],
                "must_keep_threads": [x for x in [premise, background] if x],
                "genre_guardrails": [],
            },
            "chapter_summaries": summaries,
            "main_plot_lines": [x for x in [premise, background] if x],
        }

    async def analyze_project(self, project_id: str) -> Dict[str, object]:
        memory = self.memory_provider(project_id) if callable(self.memory_provider) else {}
        if not isinstance(memory, dict):
            return {}
        return {
            "main_plot_lines": list(memory.get("main_plot_lines", []) or []),
            "world_summary": list(memory.get("world_summary", []) or []),
            "main_characters": list(memory.get("main_characters", []) or []),
            "next_writing_focus": memory.get("next_writing_focus", "") or "",
        }
