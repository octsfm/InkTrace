import asyncio

import pytest

from application.services.chapter_ai_service import ChapterAIService


class _FakeRouter:
    def __init__(self, responses):
        self.responses = list(responses)

    async def generate(self, *_args, **_kwargs):
        return self.responses.pop(0)


class _FakeFactory:
    primary_client = None
    backup_client = None


def _build_service(responses):
    service = ChapterAIService(_FakeFactory())
    service.model_router = _FakeRouter(responses)
    return service


def test_generate_structural_draft_parses_unified_json_contract():
    service = _build_service([{"ok": True, "text": '```json\n{"title":"门后追击","content":"正文","new_events":[],"possible_continuity_flags":[]}\n```'}])
    context = type("Context", (), {"project_id": "p1", "chapter_id": "c1", "chapter_number": 3, "recent_chapter_memories": [], "last_chapter_tail": "尾部", "relevant_characters": [], "relevant_foreshadowing": []})()
    result = asyncio.run(service.generate_structural_draft({"chapter_id": "c1", "chapter_number": 3}, context, {}, 1800))
    assert result["title"] == "门后追击"
    assert result["content"] == "正文"


def test_generate_structural_draft_falls_back_to_plain_text_when_json_parse_failed():
    service = _build_service(
        [
            {"ok": True, "text": "先说明一下：本章将从门后异响展开，不是JSON。"},
            {"ok": True, "text": "主角推门而入，黑暗中传来脚步声，他意识到自己被反向追踪。"},
        ]
    )
    context = type("Context", (), {"project_id": "p1", "chapter_id": "c1", "chapter_number": 3, "recent_chapter_memories": [], "last_chapter_tail": "尾部", "relevant_characters": [], "relevant_foreshadowing": []})()
    result = asyncio.run(service.generate_structural_draft({"chapter_id": "c1", "chapter_number": 3}, context, {}, 1800))
    assert result["used_fallback"] is True
    assert "主角推门而入" in result["content"]


def test_rewrite_detemplated_draft_falls_back_when_model_fails():
    service = _build_service([{"ok": False, "error": "model_failed"}])
    result = asyncio.run(service.rewrite_detemplated_draft({"content": "结构稿"}, {}, {}, {}))
    assert result["used_fallback"] is True
    assert result["content"] == "结构稿"


def test_backfill_title_returns_non_empty_title():
    service = _build_service([{"ok": True, "text": '{"title":"异响之后"}'}])
    title = asyncio.run(service.backfill_title({"chapter_id": "c1", "chapter_number": 4}, "正文", {"project_id": "p1"}))
    assert title == "异响之后"


def test_check_draft_integrity_parse_failure_is_not_fatal():
    service = _build_service([{"ok": True, "text": "not-json"}])
    result = asyncio.run(service.check_draft_integrity({"project_id": "p1", "chapter_id": "c1", "chapter_number": 4}, {"content": "改写稿"}, {}))
    assert result is None


def test_extract_continuation_memory_parses_chinese_quotes_payload():
    service = _build_service(
        [
            {
                "ok": True,
                "text": '｛“scene_summary”：“雨夜追逐”，“scene_state”：{}，“protagonist_state”：{}，“active_characters”：[]，“active_conflicts”：[]，“immediate_threads”：[]，“long_term_threads”：[]，“recent_reveals”：[]，“must_continue_points”：["门后的脚步声"]，“forbidden_jumps”：[]，“tone_and_pacing”：{}，“last_hook”：“门后有人”，“used_fallback”：false｝',
            }
        ]
    )
    result = asyncio.run(service.extract_continuation_memory("第三章", "正文", [], {}))
    assert result["used_fallback"] is False
    assert result["scene_summary"] == "雨夜追逐"
    assert result["must_continue_points"] == ["门后的脚步声"]


def test_extract_continuation_memory_logs_parser_fallback_failed(caplog: pytest.LogCaptureFixture):
    service = _build_service([{"ok": True, "text": '{"scene_summary":"x","scene_state":{bad},"must_continue_points":[]}' }])
    with caplog.at_level("WARNING"):
        result = asyncio.run(service.extract_continuation_memory("第三章", "正文", [], {}))
    assert result["used_fallback"] is True
    events = [getattr(record, "event", "") for record in caplog.records]
    assert "continuation_memory_extracted_parser_fallback_failed" in events


def test_extract_continuation_memory_logs_model_output_noncompliant(caplog: pytest.LogCaptureFixture):
    service = _build_service([{"ok": True, "text": "我先解释一下本章，不返回JSON。"}])
    with caplog.at_level("WARNING"):
        result = asyncio.run(service.extract_continuation_memory("第三章", "正文", [], {}))
    assert result["used_fallback"] is True
    events = [getattr(record, "event", "") for record in caplog.records]
    assert "continuation_memory_extracted_model_output_noncompliant" in events
