from domain.utils import looks_garbled_text, sanitize_display_text


def test_sanitize_display_text_removes_intermediate_noise():
    raw = " chunk=2 分析完成 ？？？ 角色A|角色B "
    cleaned = sanitize_display_text(raw)
    assert "chunk=" not in cleaned
    assert "分析完成" not in cleaned
    assert "？" not in cleaned
    assert "角色A" in cleaned


def test_looks_garbled_text_detects_mojibake_tokens():
    assert looks_garbled_text("瑙掕壊锛缁")
    assert looks_garbled_text("??????")
    assert not looks_garbled_text("与当前大纲方向基本一致")
