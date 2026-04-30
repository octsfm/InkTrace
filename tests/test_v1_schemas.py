import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from presentation.api.app import app
from presentation.api.routers.v1.schemas import (
    ChapterUpdateRequest,
    ExportTxtResponse,
    ImportTxtResponse,
    SessionSaveRequest,
    WorkCreateRequest,
    build_conflict_response,
    validate_snake_case_fields,
)


def test_v1_schema_rejects_unknown_or_camel_case_fields():
    with pytest.raises(ValidationError):
        ChapterUpdateRequest.model_validate({"content": "正文", "expectedVersion": 1})

    with pytest.raises(ValidationError):
        WorkCreateRequest.model_validate({"title": "作品", "author": "作者", "legacy_field": "x"})


def test_v1_session_schema_accepts_snake_case_chapter_alias_only():
    request = SessionSaveRequest.model_validate(
        {"chapter_id": "chapter-1", "cursor_position": 12, "scroll_top": 34}
    )

    assert request.last_open_chapter_id == "chapter-1"
    assert request.cursor_position == 12
    assert request.scroll_top == 34

    with pytest.raises(ValidationError):
        SessionSaveRequest.model_validate({"chapterId": "chapter-1"})


def test_v1_conflict_response_template_is_stable_and_snake_case():
    payload = build_conflict_response(
        "version_conflict",
        server_version=7,
        resource_type="chapter",
        resource_id="chapter-1",
    )

    assert payload == {
        "detail": "version_conflict",
        "server_version": 7,
        "resource_type": "chapter",
        "resource_id": "chapter-1",
    }
    validate_snake_case_fields(payload)


def test_v1_io_response_schemas_are_reusable():
    import_payload = ImportTxtResponse.model_validate(
        {
            "id": "work-1",
            "title": "作品",
            "author": "作者",
            "current_word_count": 3,
            "created_at": "2026-04-30T00:00:00Z",
            "updated_at": "2026-04-30T00:00:00Z",
            "chapters": [],
        }
    )
    export_payload = ExportTxtResponse.model_validate({"filename": "作品-20260430.txt"})

    assert import_payload.current_word_count == 3
    assert export_payload.media_type == "text/plain; charset=utf-8"


def test_v1_schema_validation_error_returns_invalid_input():
    client = TestClient(app)

    invalid = client.post("/api/v1/works", json={"title": "作品", "authorName": "作者"})

    assert invalid.status_code == 400
    assert invalid.json() == {"detail": "invalid_input"}
