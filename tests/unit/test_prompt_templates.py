from application.prompts.prompt_templates import (
    build_detemplating_prompt,
    build_integrity_check_prompt,
    build_structural_draft_prompt,
)
from application.agent_mvp.prompts_v2 import build_chapter_writing_prompt


def test_structural_prompt_declares_fixed_output_contract():
    prompt = build_structural_draft_prompt({"chapter_task": {"goals": ["推进"]}})
    assert "title, content, new_events, possible_continuity_flags" in prompt
    assert "content不能为空" in prompt


def test_detemplating_prompt_contains_webnovel_rhythm_rules():
    prompt = build_detemplating_prompt({"structural_draft": {"content": "正文"}})
    assert "不得过度文学化" in prompt
    assert "不得削弱章节推进感" in prompt
    assert "不得把连载文本改成慢叙事散文" in prompt


def test_integrity_prompt_contains_title_and_progression_checks():
    prompt = build_integrity_check_prompt({"structural_draft": {}, "detemplated_draft": {}, "chapter_task": {}})
    assert "title_alignment_ok" in prompt
    assert "progression_integrity_ok" in prompt


def test_legacy_agent_prompt_wrapper_uses_unified_structural_contract():
    prompt = build_chapter_writing_prompt(
        memory={"global_constraints": {"must_keep_threads": ["主线"]}, "chapter_continuation_memories": []},
        direction="推进主线",
        chapters_text="上一章结尾",
        chapter_count=10,
        target_word_count=2500,
        ending_hook="新的危险逼近",
    )
    assert "title, content, new_events, possible_continuity_flags" in prompt
    assert "content" in prompt
