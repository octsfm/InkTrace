"""
领域层工具函数模块

作者：孔利群
"""

# 文件路径：domain/utils.py

import re

def repair_mojibake(text: str) -> str:
    """
    尝试修复 UTF-8 文本被误按 Latin-1/Windows-1252 解码后的常见串码。
    """
    if not isinstance(text, str) or not text:
        return text

    suspicious_chars = ("Ã", "Â", "ä", "å", "æ", "ç", "é", "è", "ê", "ï", "î", "ð", "¿", "»", "¼")
    if not any(ch in text for ch in suspicious_chars):
        return text

    try:
        repaired = text.encode("latin1").decode("utf-8")
    except Exception:
        return text

    original_cjk = sum(1 for ch in text if "\u4e00" <= ch <= "\u9fff")
    repaired_cjk = sum(1 for ch in repaired if "\u4e00" <= ch <= "\u9fff")
    if repaired_cjk >= original_cjk:
        return repaired
    return text


def looks_garbled_text(text: str) -> bool:
    if not isinstance(text, str):
        return False
    value = text.strip()
    if not value:
        return False
    suspicious_tokens = ("瑙", "锛", "€", "缁", "閸", "绔", "妭", "鍒", "辫", "璇", "湇", "鍔")
    question_count = value.count("?") + value.count("？")
    if question_count >= max(3, len(value) // 6):
        return True
    if any(token in value for token in suspicious_tokens):
        return True
    cjk_count = sum(1 for ch in value if "\u4e00" <= ch <= "\u9fff")
    abnormal_count = sum(1 for ch in value if ch in {"�", "?", "？", "¤", "¢", "€"})
    punctuation_count = sum(1 for ch in value if ch in "，。！？；：、,.!?;:")
    if len(value) >= 6 and cjk_count <= 1 and (abnormal_count + punctuation_count) >= len(value) // 2:
        return True
    return False


def is_probably_garbled_message(text: str) -> bool:
    if not isinstance(text, str):
        return False
    value = text.strip()
    if not value:
        return False
    mojibake_markers = (
        "Ã",
        "Â",
        "â€",
        "�",
        "瑙",
        "锛",
        "缁",
        "閸",
        "绔",
        "妭",
        "鍒",
        "辫",
        "璇",
        "湇",
        "鍔",
    )
    if any(token in value for token in mojibake_markers):
        return True
    return looks_garbled_text(value)


def sanitize_display_text(text: str) -> str:
    if not isinstance(text, str):
        return ""
    value = repair_mojibake(text).strip()
    if not value:
        return ""
    value = value.replace("|", "；").replace("/", "；").replace("\\", "；")
    value = value.replace("，", "、")
    value = value.replace(";;", "；").replace("；；", "；")
    value = value.replace("???", "").replace("??", "").replace("？？？", "").replace("？？", "")
    value = value.replace("?1?", "").replace("?2?", "").replace("?3?", "")
    value = re.sub(r"chunk\s*=?\s*\d*", "", value, flags=re.IGNORECASE)
    value = value.replace("分析完成", "").replace("Organize complete", "")
    value = value.replace("？", "").replace("?", "")
    value = " ".join(value.split())
    value = value.strip("；、-:：")
    return value


def add_numbers(a: float, b: float) -> float:
    """
    计算两个数的和

    Args:
        a: 第一个数
        b: 第二个数

    Returns:
        两数之和
    """
# 文件：模块：utils

    return a + b
