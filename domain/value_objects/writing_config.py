"""
WritingConfig值对象模块

作者：孔利群
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class WritingConfig:
    """
    写作配置值对象
    
    表示续写时的配置参数。
    """
    target_word_count: int = 2100
    style_intensity: float = 0.8
    temperature: float = 0.7
    max_context_chapters: int = 5
    enable_consistency_check: bool = True
    enable_style_mimicry: bool = True
