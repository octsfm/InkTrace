"""V1.1 text metrics baseline."""

from __future__ import annotations

import re


SOFT_LIMIT_CHARACTER_COUNT = 200_000
INVISIBLE_CHARACTER_PATTERN = re.compile(r"[\s\u200b-\u200d\ufeff]+", re.UNICODE)


def count_effective_characters(text: object) -> int:
    """Count visible body characters after removing invisible whitespace."""
    return len(INVISIBLE_CHARACTER_PATTERN.sub("", str(text or "")))


def exceeds_soft_limit(text: object, limit: int = SOFT_LIMIT_CHARACTER_COUNT) -> bool:
    resolved_limit = int(limit or SOFT_LIMIT_CHARACTER_COUNT)
    return count_effective_characters(text) > resolved_limit
