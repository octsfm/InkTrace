"""
领域层工具函数模块

作者：孔利群
"""

# 文件路径：domain/utils.py



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
