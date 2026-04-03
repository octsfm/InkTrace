from datetime import datetime

from application.prompts.prompt_input_builder import PromptInputBuilder
from domain.entities.continuation_context import ContinuationContext


def test_prompt_input_builder_structural_input_matches_schema():
    context = ContinuationContext(
        project_id="p1",
        chapter_id="c9",
        chapter_number=10,
        recent_chapter_memories=[{"scene_summary": "前情"}],
        last_chapter_tail="上一章尾部",
        relevant_characters=[{"name": "主角"}],
        relevant_foreshadowing=["伏笔A"],
        global_constraints={"must_keep_threads": ["主线"]},
        chapter_outline={},
        chapter_task_seed={},
        style_requirements={},
        created_at=datetime.now(),
    )
    result = PromptInputBuilder.build_structural_draft_input(
        chapter_task={"chapter_function": "continue_crisis"},
        global_constraints={"must_keep_threads": ["主线"]},
        continuation_context=context,
        relevant_characters=context.relevant_characters,
        relevant_foreshadowing=context.relevant_foreshadowing,
    )
    assert result["chapter_task"]["chapter_function"] == "continue_crisis"
    assert result["global_constraints"]["must_keep_threads"] == ["主线"]
    assert result["last_chapter_tail"] == "上一章尾部"
    assert result["relevant_foreshadowing"] == ["伏笔A"]


def test_prompt_input_builder_title_backfill_input_matches_schema():
    result = PromptInputBuilder.build_title_backfill_input({"chapter_function": "continue_crisis"}, "正文内容", {"project_id": "p1"})
    assert result["chapter_task"]["chapter_function"] == "continue_crisis"
    assert result["content"] == "正文内容"
    assert result["recent_context"]["project_id"] == "p1"
