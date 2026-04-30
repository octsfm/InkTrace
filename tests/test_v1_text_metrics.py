from application.services.v1.text_metrics import (
    SOFT_LIMIT_CHARACTER_COUNT,
    count_effective_characters,
    exceeds_soft_limit,
)


def test_count_effective_characters_removes_invisible_whitespace():
    assert count_effective_characters("你 好\nInk\tTrace") == 10


def test_count_effective_characters_handles_empty_values():
    assert count_effective_characters("") == 0
    assert count_effective_characters(None) == 0


def test_count_effective_characters_keeps_visible_punctuation():
    assert count_effective_characters("第1章：开始。") == 7


def test_exceeds_soft_limit_uses_body_text_only():
    assert exceeds_soft_limit("字" * (SOFT_LIMIT_CHARACTER_COUNT + 1))
    assert not exceeds_soft_limit("字" * SOFT_LIMIT_CHARACTER_COUNT)
