from __future__ import annotations

import json

from application.services.ai.initialization_analysis_service import (
    ManuscriptAnalysisService,
    OutlineAnalysisService,
)
from application.services.ai.output_validation_service import OutputValidationService
from application.services.ai.prompt_registry import PromptRegistry
from domain.entities.ai.models import ChapterAnalysisResult, ChapterAnalysisStatus, LLMResponse, LLMUsage, OutlineAnalysisResult


class _RecordingModelRouter:
    def __init__(self, outputs: list[dict[str, object]]) -> None:
        self._outputs = list(outputs)
        self.requests = []

    def generate(self, request):  # noqa: ANN001
        self.requests.append(request)
        return LLMResponse(
            provider_name="fake",
            model_name="fake-chat",
            content=json.dumps(self._outputs.pop(0), ensure_ascii=False),
            request_id=request.request_id,
            trace_id=request.trace_id,
            token_usage=LLMUsage(input_tokens=10, output_tokens=20, total_tokens=30),
        )


def test_outline_analysis_reads_formal_content_text_and_calls_outline_model() -> None:
    router = _RecordingModelRouter(
        [
            {
                "global_summary": "孔凡圣从现代跌入修仙界，主线是查明穿越与梦境的真相。",
                "genre": "现代修仙",
                "tone": "悬疑成长",
                "issues": [],
                "outline_empty": False,
                "story_phase_map": ["逃离都市", "进入宗门"],
                "main_conflict": "现代认知与修仙秩序冲突",
                "important_characters": ["孔凡圣", "宋成"],
                "setting_facts": ["梦境可以连接两界"],
                "foreshadow_map": ["反复出现的钟声"],
                "expected_story_direction": "查清梦境来源",
                "analysis_confidence": 0.91,
            }
        ]
    )
    service = OutlineAnalysisService(
        model_router=router,
        prompt_registry=PromptRegistry(),
        output_validator=OutputValidationService(),
    )

    result = service.analyze(
        work_id="work-1",
        work_title="修仙从逃出生天开始",
        user_outline="第一卷：孔凡圣醒来后发现梦境正在侵入现实。",
        existing_chapters=[{"chapter_id": "chapter-1", "title": "前言"}],
        job_id="job-1",
    )

    assert result.important_characters == ["孔凡圣", "宋成"]
    assert router.requests[0].model_role == "outline_analyzer"
    assert router.requests[0].output_schema_key == "outline_analysis_result_p0"
    assert "孔凡圣醒来后发现梦境正在侵入现实" in router.requests[0].messages[0]["content"]


def test_manuscript_analysis_sends_one_chapter_and_outline_result_to_model() -> None:
    router = _RecordingModelRouter(
        [
            {
                "summary": "孔凡圣在丛林中逃亡，并确认有人追踪自己。",
                "characters": ["孔凡圣"],
                "locations": ["东南亚丛林"],
                "plot_points": ["孔凡圣躲避追兵"],
                "unresolved_threads": ["追兵身份未知"],
                "scene_details": [
                    {
                        "scene_order": 1,
                        "location": "东南亚丛林",
                        "time_of_day": "清晨",
                        "atmosphere": "紧张",
                        "characters_present": ["孔凡圣"],
                        "emotional_tone": "警觉",
                        "pov_hint": "孔凡圣",
                        "reveal_points": ["追兵正在接近"],
                    }
                ],
                "chapter_position": "第一卷开端",
                "plot_progress": "主角开始逃亡",
                "character_state_delta": [
                    {
                        "character_name": "孔凡圣",
                        "current_location": "东南亚丛林",
                        "current_status": "逃亡中",
                        "recent_actions": ["躲避追兵"],
                        "relationships": [],
                        "confidence": 0.95,
                    }
                ],
                "setting_fact_delta": [],
                "foreshadow_candidate_delta": [],
                "deviations_from_outline": [],
                "timeline_info": ["故事开端的清晨"],
                "warnings": [],
                "analysis_confidence": 0.93,
            }
        ]
    )
    service = ManuscriptAnalysisService(
        model_router=router,
        prompt_registry=PromptRegistry(),
        output_validator=OutputValidationService(),
    )
    outline = OutlineAnalysisResult(
        work_id="work-1",
        global_summary="孔凡圣需要逃出追捕并寻找穿越原因。",
        important_characters=["孔凡圣"],
        outline_empty=False,
    )

    result = service.analyze_chapter(
        work_id="work-1",
        chapter_id="chapter-1",
        chapter_title="跑",
        chapter_content="孔凡圣在东南亚丛林中拼命奔跑，身后的脚步越来越近。",
        chapter_version=2,
        chapter_order=1,
        outline_analysis=outline,
        previous_chapter_summaries=[],
        job_id="job-1",
    )

    assert result.characters == ["孔凡圣"]
    assert result.scene_details[0].chapter_id == "chapter-1"
    assert router.requests[0].model_role == "manuscript_analyzer"
    prompt = router.requests[0].messages[0]["content"]
    assert "孔凡圣在东南亚丛林中拼命奔跑" in prompt
    assert "寻找穿越原因" in prompt


def test_manuscript_analysis_builds_hierarchical_memory_with_two_real_model_calls() -> None:
    router = _RecordingModelRouter(
        [
            {
                "stage_summaries": [
                    {
                        "title": "逃亡阶段",
                        "chapter_ids": ["chapter-1", "chapter-2"],
                        "summary": "孔凡圣逃离追捕，并发现梦境与修仙界相连。",
                        "main_conflict": "逃亡与追查真相",
                        "plot_progress": "确认两界存在联系",
                        "open_loops": ["追兵身份未知"],
                    }
                ],
                "volume_summaries": [
                    {
                        "title": "第一卷",
                        "chapter_ids": ["chapter-1", "chapter-2"],
                        "summary": "孔凡圣从现实逃亡进入两界谜局。",
                        "main_conflict": "现实追杀与两界谜团",
                        "plot_progress": "主角开始主动调查",
                        "open_loops": ["梦境来源未知"],
                    }
                ],
                "warnings": [],
                "analysis_confidence": 0.91,
            },
            {
                "global_summary": "孔凡圣在逃亡中发现现实与修仙界通过梦境相连，目前正在追查两界谜团。",
                "current_story_phase": "第一卷·主动调查两界联系",
                "main_plot_threads": ["追查梦境来源", "确认追兵身份"],
                "unresolved_questions": ["谁在操控梦境"],
                "warnings": [],
                "analysis_confidence": 0.93,
            },
        ]
    )
    service = ManuscriptAnalysisService(
        model_router=router,
        prompt_registry=PromptRegistry(),
        output_validator=OutputValidationService(),
    )
    outline = OutlineAnalysisResult(
        work_id="work-1",
        global_summary="孔凡圣需要逃出追捕并寻找穿越原因。",
        story_phase_map=["逃亡阶段", "进入宗门"],
        outline_empty=False,
    )
    chapter_results = [
        ChapterAnalysisResult(
            chapter_id="chapter-1",
            chapter_title="前言",
            status=ChapterAnalysisStatus.SUCCEEDED,
            summary="孔凡圣遭遇追捕。",
            chapter_position="逃亡阶段",
            plot_progress="开始逃亡",
        ),
        ChapterAnalysisResult(
            chapter_id="chapter-2",
            chapter_title="梦境",
            status=ChapterAnalysisStatus.SUCCEEDED,
            summary="孔凡圣发现梦境通往修仙界。",
            chapter_position="逃亡阶段",
            plot_progress="发现两界联系",
        ),
    ]

    result = service.analyze_story_hierarchy(
        work_id="work-1",
        outline_analysis=outline,
        chapter_results=chapter_results,
        job_id="job-1",
    )

    assert len(router.requests) == 2
    assert router.requests[0].model_role == "memory_extractor"
    assert router.requests[0].prompt_key == "story_memory_structure_p1"
    assert "孔凡圣遭遇追捕" in router.requests[0].messages[0]["content"]
    assert router.requests[1].model_role == "memory_extractor"
    assert router.requests[1].prompt_key == "story_memory_global_p1"
    assert "孔凡圣从现实逃亡进入两界谜局" in router.requests[1].messages[0]["content"]
    assert result.global_summary.startswith("孔凡圣在逃亡中")
    assert result.stage_summaries[0]["chapter_ids"] == ["chapter-1", "chapter-2"]
    assert result.volume_summaries[0]["title"] == "第一卷"


def test_story_hierarchy_retries_when_a_layer_does_not_cover_all_chapters() -> None:
    incomplete = {
        "stage_summaries": [
            {
                "title": "开端",
                "chapter_ids": ["chapter-1"],
                "summary": "只覆盖第一章。",
                "main_conflict": "",
                "plot_progress": "",
                "open_loops": [],
            }
        ],
        "volume_summaries": [
            {
                "title": "第一卷",
                "chapter_ids": ["chapter-1"],
                "summary": "只覆盖第一章。",
                "main_conflict": "",
                "plot_progress": "",
                "open_loops": [],
            }
        ],
        "warnings": [],
        "analysis_confidence": 0.5,
    }
    complete = {
        "stage_summaries": [{**incomplete["stage_summaries"][0], "chapter_ids": ["chapter-1", "chapter-2"]}],
        "volume_summaries": [{**incomplete["volume_summaries"][0], "chapter_ids": ["chapter-1", "chapter-2"]}],
        "warnings": [],
        "analysis_confidence": 0.9,
    }
    router = _RecordingModelRouter(
        [
            incomplete,
            complete,
            {
                "global_summary": "两章共同构成故事开端。",
                "current_story_phase": "开端",
                "main_plot_threads": [],
                "unresolved_questions": [],
                "warnings": [],
                "analysis_confidence": 0.9,
            },
        ]
    )
    service = ManuscriptAnalysisService(
        model_router=router,
        prompt_registry=PromptRegistry(),
        output_validator=OutputValidationService(),
    )
    chapters = [
        ChapterAnalysisResult(chapter_id=f"chapter-{index}", status=ChapterAnalysisStatus.SUCCEEDED, summary=f"第{index}章摘要")
        for index in (1, 2)
    ]

    result = service.analyze_story_hierarchy(
        work_id="work-1",
        outline_analysis=OutlineAnalysisResult(work_id="work-1", global_summary="故事开端", outline_empty=False),
        chapter_results=chapters,
        job_id="job-1",
    )

    assert len(router.requests) == 3
    assert result.global_summary == "两章共同构成故事开端。"
