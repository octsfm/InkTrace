from domain.services.ai.character_names import normalize_character_names


def test_normalize_character_names_preserves_model_semantics_without_guessing() -> None:
    assert normalize_character_names(["孔凡圣", "宋成这", "时候也", "宋成沉", "宋成"]) == [
        "孔凡圣",
        "宋成这",
        "时候也",
        "宋成沉",
        "宋成",
    ]


def test_normalize_character_names_preserves_distinct_three_character_name() -> None:
    assert normalize_character_names(["陆浮沉", "顾迟"]) == ["陆浮沉", "顾迟"]
