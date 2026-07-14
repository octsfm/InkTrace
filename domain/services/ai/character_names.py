from __future__ import annotations

from collections.abc import Iterable


def normalize_character_names(
    values: Iterable[object],
) -> list[str]:
    """Trim and de-duplicate model output without guessing character semantics."""

    normalized: list[str] = []
    for value in values:
        clean = str(value or "").strip(" \t\r\n，。！？；：、,.!?;:")
        if clean and clean not in normalized:
            normalized.append(clean)
    return normalized
