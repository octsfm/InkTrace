from application.prompts.prompt_parser import (
    parse_json_array,
    parse_json_object,
    parse_json_object_with_diagnostics,
)


def test_parse_json_object_handles_code_fence_and_trailing_comma():
    text = """```json
    {"title": "章节标题", "content": "正文",}
    ```"""
    result = parse_json_object(text)
    assert result["title"] == "章节标题"
    assert result["content"] == "正文"


def test_parse_json_array_handles_plain_array():
    text = '[{"name": "甲"}, {"name": "乙"}]'
    result = parse_json_array(text)
    assert len(result) == 2
    assert result[0]["name"] == "甲"


def test_parse_json_object_handles_prefixed_text_and_balanced_object():
    text = """模型分析如下：
    先给结论，再给JSON。
    {"title":"第三章 夜雨","content":"正文内容","new_events":[],"possible_continuity_flags":[]}
    说明结束。"""
    result = parse_json_object(text)
    assert result["title"] == "第三章 夜雨"
    assert result["content"] == "正文内容"


def test_parse_json_object_repairs_fullwidth_punctuation_and_chinese_quotes():
    text = '｛“scene_summary”：“雨夜追逐”，“must_continue_points”：["门后的脚步声"]｝'
    result = parse_json_object(text)
    assert result["scene_summary"] == "雨夜追逐"
    assert result["must_continue_points"] == ["门后的脚步声"]


def test_parse_json_object_with_diagnostics_marks_noncompliant_output():
    result, meta = parse_json_object_with_diagnostics("这是一段解释文本，不是JSON。")
    assert result is None
    assert meta["reason"] == "model_output_noncompliant"
