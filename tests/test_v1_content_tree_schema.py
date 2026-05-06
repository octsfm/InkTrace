from uuid import uuid4

import pytest

from application.services.v1.content_tree_schema import validate_content_tree_json


def _node(**overrides):
    payload = {
        "node_id": str(uuid4()),
        "text": "主线目标",
        "children": [],
        "chapter_ref": None,
    }
    payload.update(overrides)
    return payload


def test_content_tree_schema_accepts_empty_tree_values():
    assert validate_content_tree_json(None) is None
    assert validate_content_tree_json("") is None
    assert validate_content_tree_json([]) == []
    assert validate_content_tree_json({}) == {}


def test_content_tree_schema_accepts_nested_tree_and_optional_collapsed():
    child = _node(text="子节点", chapter_ref="chapter-1", collapsed=True)
    root = _node(children=[child])

    normalized = validate_content_tree_json([root])

    assert normalized[0]["children"][0]["chapter_ref"] == "chapter-1"
    assert normalized[0]["children"][0]["collapsed"] is True


def test_content_tree_schema_rejects_non_whitelist_fields():
    tree = _node(ai_summary="禁止写入")

    with pytest.raises(ValueError, match="invalid_input"):
        validate_content_tree_json(tree)


@pytest.mark.parametrize(
    "payload",
    [
        _node(children={}),
        _node(chapter_ref=123),
        _node(collapsed="false"),
        _node(node_id="not-a-uuid"),
        _node(text=None),
    ],
)
def test_content_tree_schema_rejects_invalid_node_shape(payload):
    with pytest.raises(ValueError, match="invalid_input"):
        validate_content_tree_json(payload)
