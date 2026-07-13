from __future__ import annotations

import math
import re
from collections import Counter


_DIALOGUE_PATTERN = re.compile(r"[“「『](.*?)[”」』]", re.DOTALL)
_SENTENCE_PATTERN = re.compile(r"[^。！？!?]+[。！？!?]?")


class NovelTextAnalyzer:
    @staticmethod
    def sentences(text: str) -> list[str]:
        return [item.strip() for item in _SENTENCE_PATTERN.findall(str(text or "")) if item.strip()]

    @staticmethod
    def paragraphs(text: str) -> list[str]:
        return [item.strip() for item in re.split(r"\n\s*\n|\r\n\s*\r\n", str(text or "")) if item.strip()]

    @staticmethod
    def dialogue_segments(text: str) -> list[str]:
        return [item.strip() for item in _DIALOGUE_PATTERN.findall(str(text or "")) if item.strip()]

    @staticmethod
    def effective_length(text: str) -> int:
        return len(re.sub(r"\s+", "", str(text or "")))

    @classmethod
    def features(cls, text: str) -> dict[str, float]:
        sentences = cls.sentences(text)
        paragraphs = cls.paragraphs(text)
        dialogue = cls.dialogue_segments(text)
        total = max(cls.effective_length(text), 1)
        sentence_lengths = [cls.effective_length(item) for item in sentences]
        paragraph_lengths = [cls.effective_length(item) for item in paragraphs]
        return {
            "avg_sentence_length": cls._mean(sentence_lengths),
            "short_sentence_ratio": cls._ratio(sum(1 for value in sentence_lengths if value <= 15), len(sentence_lengths)),
            "long_sentence_ratio": cls._ratio(sum(1 for value in sentence_lengths if value >= 35), len(sentence_lengths)),
            "avg_paragraph_length": cls._mean(paragraph_lengths),
            "paragraph_length_std": cls._std(paragraph_lengths),
            "dialogue_ratio": min(1.0, sum(cls.effective_length(item) for item in dialogue) / total),
        }

    @staticmethod
    def _mean(values: list[int | float]) -> float:
        return round(sum(values) / len(values), 4) if values else 0.0

    @classmethod
    def _std(cls, values: list[int | float]) -> float:
        if not values:
            return 0.0
        mean = cls._mean(values)
        return round(math.sqrt(sum((value - mean) ** 2 for value in values) / len(values)), 4)

    @staticmethod
    def _ratio(part: int, total: int) -> float:
        return round(part / total, 4) if total else 0.0

    @staticmethod
    def word_tokens(text: str) -> list[str]:
        try:
            import jieba  # type: ignore

            values = jieba.lcut(str(text or ""), cut_all=False)
        except ImportError:
            values = re.findall(r"[\u4e00-\u9fff]{2,}|[A-Za-z]{2,}", str(text or ""))
        return [re.sub(r"[^\u4e00-\u9fffA-Za-z]", "", item).strip() for item in values]

    @staticmethod
    def top_words(tokens: list[str], stop_words: set[str], top_n: int) -> list[tuple[str, int]]:
        safe = [item for item in tokens if len(item) >= 2 and item not in stop_words and not item.lower().startswith("sk")]
        return Counter(safe).most_common(top_n)
