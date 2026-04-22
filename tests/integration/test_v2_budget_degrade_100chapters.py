from __future__ import annotations

import asyncio
from types import SimpleNamespace

from application.services.v2_workflow_service import V2WorkflowService
from domain.types import NovelId


class _ProjectService:
    def get_project(self, project_id):
        return SimpleNamespace(id=SimpleNamespace(value=project_id), novel_id=NovelId("novel_long"), name="LongProject")

    def bind_memory_to_novel(self, novel_id, memory):
        return None

    def get_memory_by_novel(self, novel_id):
        return {}


class _ContentService:
    def get_outline_context(self, novel_id: str):
        return {
            "premise": "主线",
            "story_background": "背景",
            "world_setting": "设定",
            "outline_digest": {"premise": "主线", "summary": "背景", "style_guidance": "设定"},
        }

    def get_novel_text(self, novel_id: str):
        return ""


class _ChapterRepo:
    def find_by_novel(self, novel_id: NovelId):
        return [
            SimpleNamespace(
                id=SimpleNamespace(value=f"c{i}"),
                number=i,
                title=f"第{i}章",
                content=f"第{i}章正文",
            )
            for i in range(1, 121)
        ]


class _OutlineRepo:
    def find_by_novel(self, novel_id: NovelId):
        return None


class _NullRepo:
    def find_by_project_id(self, *_args, **_kwargs):
        return []

    def find_by_id(self, *_args, **_kwargs):
        return None

    def find_by_chapter_id(self, *_args, **_kwargs):
        return []

    def save(self, *_args, **_kwargs):
        return None

    def replace_by_project(self, *_args, **_kwargs):
        return None


class _ChapterOutlineRepo:
    def find_by_chapter_id(self, *_args, **_kwargs):
        return None

    def save(self, *_args, **_kwargs):
        return None


class _V2Repo:
    def __init__(self):
        self.stage_metrics = []
        self.batch_digests = []

    def find_active_project_memory(self, project_id: str):
        return None

    def start_workflow_job(self, *args, **kwargs):
        return "job_1"

    def finish_workflow_job(self, *args, **kwargs):
        return None

    def save_project_memory(self, payload):
        return None

    def save_memory_view(self, payload):
        return None

    def save_organize_stage_metric(self, **kwargs):
        self.stage_metrics.append(kwargs)

    def save_organize_batch_digest(self, **kwargs):
        self.batch_digests.append(kwargs)

    def list_organize_batch_digests(self, project_id: str):
        return []

    def delete_organize_batch_digests(self, project_id: str):
        return None

    def mark_structured_story_migrated(self, project_id: str):
        return None


class _PromptAI:
    def __init__(self):
        self.global_batch_sizes = []

    async def analyze_to_outline(self, **kwargs):
        return {
            "outline_draft": {
                "goal": "推进主线",
                "conflict": "冲突升级",
                "events": ["事件A"],
                "character_progress": "角色推进",
                "ending_hook": "悬念",
                "opening_continuation": "承接",
                "notes": "",
            },
            "used_fallback": False,
        }

    async def extract_continuation_memory(self, **kwargs):
        return {
            "scene_summary": "本章摘要",
            "scene_state": {},
            "protagonist_state": {},
            "active_characters": [],
            "active_conflicts": [],
            "immediate_threads": [],
            "long_term_threads": [],
            "recent_reveals": [],
            "must_continue_points": ["推进主线"],
            "forbidden_jumps": [],
            "tone_and_pacing": {},
            "last_hook": "悬念",
            "used_fallback": False,
        }

    async def analyze_global_story(self, payload):
        self.global_batch_sizes.append(len(payload.get("batch_digests") or []))
        return {
            "characters": [],
            "world_facts": {"background": [], "power_system": [], "organizations": [], "locations": [], "rules": [], "artifacts": []},
            "style_profile": {"narrative_pov": "", "tone_tags": [], "rhythm_tags": []},
            "global_constraints": {"main_plot": "主线", "hidden_plot": "", "core_selling_points": [], "protagonist_core_traits": [], "must_keep_threads": ["主线"], "genre_guardrails": []},
            "chapter_summaries": ["摘要"],
            "main_plot_lines": ["主线"],
            "used_fallback": False,
        }

    async def extract_plot_arcs(self, payload):
        return {"plot_arcs": [], "chapter_arc_bindings": [], "active_arc_ids": []}


class _LLMFactory:
    deepseek_client = object()
    kimi_client = object()


def test_v2_organize_8k_budget_degrades_instead_of_failing_on_100_plus_chapters():
    repo = _V2Repo()
    service = V2WorkflowService(
        project_service=_ProjectService(),
        content_service=_ContentService(),
        chapter_repo=_ChapterRepo(),
        novel_repo=object(),
        outline_repo=_OutlineRepo(),
        llm_factory=_LLMFactory(),
        v2_repo=repo,
        global_constraints_repo=_NullRepo(),
        chapter_analysis_memory_repo=_NullRepo(),
        chapter_continuation_memory_repo=_NullRepo(),
        chapter_outline_repo=_ChapterOutlineRepo(),
        chapter_task_repo=_NullRepo(),
        structural_draft_repo=_NullRepo(),
        detemplated_draft_repo=_NullRepo(),
        draft_integrity_check_repo=_NullRepo(),
        style_requirements_repo=_NullRepo(),
    )
    prompt_ai = _PromptAI()
    service.prompt_ai_service = prompt_ai

    result = asyncio.run(
        service.organize_project(
            "proj_long",
            mode="full_reanalyze",
            rebuild_memory=True,
            capacity_plan={
                "model_name": "moonshot-v1-8k",
                "stage_cap_tokens": {"global_analysis": 32},
                "batch_size_chapters": 4,
                "enable_chunking": False,
                "strategy": "batch_digest_first",
            },
        )
    )

    assert result["organized_chapter_count"] == 120
    assert prompt_ai.global_batch_sizes[-1] == 1
    assert any(item.get("stage") == "global_analysis" and item.get("status") == "budget_block" for item in repo.stage_metrics)
    assert any(item.get("stage") == "global_analysis" and item.get("degrade_path") == "force_minimal" and item.get("status") == "ok" for item in repo.stage_metrics)
