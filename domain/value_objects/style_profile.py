"""
StyleProfile值对象模块

作者：孔利群
"""

from dataclasses import dataclass
from typing import Dict, List


@dataclass(frozen=True)
class StyleProfile:
    """
    文风特征值对象
    
    表示小说的文风特征，包含词汇、句式、修辞等统计信息。
    """
    vocabulary_stats: Dict[str, float]
    sentence_patterns: List[str]
    rhetoric_stats: Dict[str, int]
    dialogue_style: str
    narrative_voice: str
    pacing: str
    sample_sentences: List[str]
