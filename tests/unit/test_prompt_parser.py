from application.prompts.prompt_parser import parse_json_array, parse_json_object


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
