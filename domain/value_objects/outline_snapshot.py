from __future__ import annotations

import hashlib
import json
from typing import Any


def outline_content_hash(content_text: str, content_tree_json: Any) -> str:
    """Stable hash of the complete formal outline baseline."""
    canonical = json.dumps(
        {
            "content_text": str(content_text or ""),
            "content_tree_json": content_tree_json,
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _outline_node_contract(tree: Any) -> list[tuple[str, str | None]]:
    contract: list[tuple[str, str | None]] = []

    def visit(value: Any) -> None:
        if isinstance(value, list):
            for item in value:
                visit(item)
            return
        if not isinstance(value, dict) or not value:
            return
        node_id = value.get("node_id")
        if isinstance(node_id, str) and node_id:
            contract.append((node_id, value.get("chapter_ref")))
        visit(value.get("children", []))

    visit(tree)
    return contract


def preserves_outline_node_contract(target_tree: Any, proposed_tree: Any) -> bool:
    """Preserve existing refs; model-added nodes may not introduce chapter refs."""
    target_items = _outline_node_contract(target_tree)
    proposed_items = _outline_node_contract(proposed_tree)
    target_contract = dict(target_items)
    proposed_contract = dict(proposed_items)
    if len(proposed_contract) != len(proposed_items):
        return False
    if any(
        node_id not in proposed_contract or proposed_contract.get(node_id) != chapter_ref
        for node_id, chapter_ref in target_items
    ):
        return False
    return all(
        node_id in target_contract or chapter_ref is None
        for node_id, chapter_ref in proposed_items
    )
