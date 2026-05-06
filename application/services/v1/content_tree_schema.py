"""content_tree_json schema validation for V1.1 outlines."""

from __future__ import annotations

import json
from copy import deepcopy
from typing import Any
from uuid import UUID

ALLOWED_NODE_FIELDS = {"node_id", "text", "children", "chapter_ref", "collapsed"}


def _raise_invalid() -> None:
    raise ValueError("invalid_input")


def _ensure_uuid(value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        _raise_invalid()
    try:
        UUID(value.strip())
    except (TypeError, ValueError):
        _raise_invalid()
    return value.strip()


def _validate_node(node: Any) -> dict[str, Any]:
    if not isinstance(node, dict):
        _raise_invalid()
    if not node:
        _raise_invalid()
    if not set(node).issubset(ALLOWED_NODE_FIELDS):
        _raise_invalid()

    if "node_id" not in node or "text" not in node or "children" not in node:
        _raise_invalid()

    node_id = _ensure_uuid(node.get("node_id"))
    text = node.get("text")
    children = node.get("children")
    chapter_ref = node.get("chapter_ref", None)
    collapsed = node.get("collapsed", False)

    if not isinstance(text, str):
        _raise_invalid()
    if not isinstance(children, list):
        _raise_invalid()
    if chapter_ref is not None and not isinstance(chapter_ref, str):
        _raise_invalid()
    if not isinstance(collapsed, bool):
        _raise_invalid()

    normalized: dict[str, Any] = {
        "node_id": node_id,
        "text": text,
        "children": [_validate_node(child) for child in children],
        "chapter_ref": chapter_ref,
    }
    if "collapsed" in node:
        normalized["collapsed"] = collapsed
    return normalized


def validate_content_tree_json(tree: Any) -> Any:
    """Validate and normalize outline tree cache data.

    Empty tree values are represented by ``None``, ``[]`` or ``{}``. Non-empty
    nodes must only contain the V1.1 whitelist fields.
    """
    if tree is None:
        return None
    payload = tree
    if isinstance(tree, str):
        if not tree.strip():
            return None
        try:
            payload = json.loads(tree)
        except json.JSONDecodeError:
            _raise_invalid()

    payload = deepcopy(payload)
    if payload == [] or payload == {}:
        return payload
    if isinstance(payload, list):
        return [_validate_node(node) for node in payload]
    if isinstance(payload, dict):
        return _validate_node(payload)
    _raise_invalid()
