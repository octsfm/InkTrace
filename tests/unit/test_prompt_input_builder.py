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


def test_global_analysis_input_keeps_100_plus_chapters_and_digests():
    chapters = [{"id": f"c{i}", "index": i, "title": f"第{i}章", "content": "正文"} for i in range(1, 121)]
    artifacts = [{"chapter_id": f"c{i}", "chapter_number": i, "chapter_title": f"第{i}章", "analysis_summary": "摘要"} for i in range(1, 121)]
    digests = [{"batch_no": i, "chapter_start": i, "chapter_end": i, "digest": f"d{i}"} for i in range(1, 121)]
    payload = PromptInputBuilder.build_global_analysis_input(
        project_name="P",
        outline_context={"premise": "主线"},
        chapters=chapters,
        chapter_artifacts=artifacts,
        outline_digest={"premise": "主线"},
        batch_digests=digests,
    )
    assert len(payload["chapters"]) == 120
    assert len(payload["chapter_artifacts"]) == 120
    assert len(payload["batch_digests"]) == 120
    assert payload["input_counts"]["batch_digest_count"] == 120
