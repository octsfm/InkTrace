"""V1.1 Workbench logging helpers.

Logs must never include editor content, drafts, or structured asset payloads.
"""

from __future__ import annotations

from typing import Any

from application.services.logging_service import build_log_context, get_logger


V1_LOG_CATEGORIES = frozenset({"api", "db", "service", "error"})
SENSITIVE_LOG_KEYS = frozenset(
    {
        "content",
        "draft",
        "payload",
        "content_text",
        "content_tree_json",
        "description",
        "aliases",
    }
)


def get_v1_logger(name: str):
    return get_logger(f"inktrace.v1.{name}")


def build_v1_log_context(*, category: str, event: str, **kwargs: Any) -> dict[str, Any]:
    if category not in V1_LOG_CATEGORIES:
        raise ValueError(f"unsupported v1 log category: {category}")

    safe_kwargs = {
        key: value
        for key, value in kwargs.items()
        if str(key) not in SENSITIVE_LOG_KEYS
    }
    return build_log_context(
        event=f"v1_{category}_{event}",
        scope="workbench",
        api="v1",
        category=category,
        **safe_kwargs,
    )
