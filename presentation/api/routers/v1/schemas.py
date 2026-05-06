"""V1.1 Workbench API request/response schemas."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from http import HTTPStatus
import json
import re
from typing import Any, Mapping

from pydantic import AliasChoices, BaseModel, ConfigDict, Field


SNAKE_CASE_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")


class V1BaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


ERROR_HTTP_STATUS_MAP: dict[str, int] = {
    "version_conflict": HTTPStatus.CONFLICT,
    "asset_version_conflict": HTTPStatus.CONFLICT,
    "work_not_found": HTTPStatus.NOT_FOUND,
    "chapter_not_found": HTTPStatus.NOT_FOUND,
    "asset_not_found": HTTPStatus.NOT_FOUND,
    "invalid_input": HTTPStatus.BAD_REQUEST,
    "internal_error": HTTPStatus.INTERNAL_SERVER_ERROR,
}


@dataclass(frozen=True)
class ErrorResponse:
    detail: str

    def to_dict(self) -> dict[str, str]:
        return {"detail": self.detail}


@dataclass(frozen=True)
class ConflictErrorResponse:
    detail: str
    server_version: int
    resource_type: str
    resource_id: str

    def to_dict(self) -> dict[str, str | int]:
        return {
            "detail": self.detail,
            "server_version": self.server_version,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
        }


class V1APIError(Exception):
    """Reusable V1.1 API exception with stable snake_case fields."""

    def __init__(
        self,
        error_code: str,
        *,
        status_code: int | None = None,
        payload: Mapping[str, Any] | None = None,
    ) -> None:
        validate_error_code(error_code)
        if payload:
            validate_snake_case_fields(payload)
        self.error_code = error_code
        self.status_code = int(status_code or ERROR_HTTP_STATUS_MAP.get(error_code, HTTPStatus.BAD_REQUEST))
        self.payload = dict(payload or ErrorResponse(error_code).to_dict())
        super().__init__(error_code)


def validate_error_code(error_code: str) -> None:
    if not SNAKE_CASE_PATTERN.match(error_code):
        raise ValueError("error_code must use snake_case")


def validate_snake_case_fields(payload: Mapping[str, Any]) -> None:
    for field_name in payload.keys():
        if not SNAKE_CASE_PATTERN.match(str(field_name)):
            raise ValueError(f"error response field must use snake_case: {field_name}")


def build_error_response(error_code: str) -> dict[str, str]:
    return ErrorResponse(error_code).to_dict()


def build_conflict_response(
    error_code: str,
    *,
    server_version: int,
    resource_type: str,
    resource_id: str,
) -> dict[str, str | int]:
    if ERROR_HTTP_STATUS_MAP.get(error_code) != HTTPStatus.CONFLICT:
        raise ValueError("conflict response requires a 409 error code")
    payload = ConflictErrorResponse(
        detail=error_code,
        server_version=server_version,
        resource_type=resource_type,
        resource_id=resource_id,
    ).to_dict()
    validate_snake_case_fields(payload)
    return payload


class WorkCreateRequest(V1BaseModel):
    title: str
    author: str = ""


class WorkUpdateRequest(V1BaseModel):
    title: str | None = None
    author: str | None = None


class WorkResponse(V1BaseModel):
    id: str
    title: str
    author: str
    current_word_count: int
    created_at: datetime
    updated_at: datetime


class WorkListResponse(V1BaseModel):
    items: list[WorkResponse]
    total: int


class WorkDeleteResponse(V1BaseModel):
    ok: bool
    id: str


class ChapterCreateRequest(V1BaseModel):
    title: str = ""
    after_chapter_id: str = ""


class ChapterUpdateRequest(V1BaseModel):
    title: str | None = None
    content: str | None = None
    expected_version: int | None = None
    force_override: bool = False


class ChapterReorderItem(V1BaseModel):
    id: str
    order_index: int


class ChapterReorderRequest(V1BaseModel):
    items: list[ChapterReorderItem]


class ChapterResponse(V1BaseModel):
    id: str
    work_id: str
    title: str
    content: str
    chapter_number: int
    order_index: int
    version: int
    word_count: int
    created_at: datetime
    updated_at: datetime


class ChapterListResponse(V1BaseModel):
    work_id: str
    items: list[ChapterResponse]
    total: int


class ChapterDeleteResponse(V1BaseModel):
    ok: bool
    id: str
    next_chapter_id: str


class SessionSaveRequest(V1BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    last_open_chapter_id: str = Field(
        default="",
        validation_alias=AliasChoices("last_open_chapter_id", "active_chapter_id", "chapter_id"),
    )
    cursor_position: int = 0
    scroll_top: int = 0


class SessionResponse(V1BaseModel):
    work_id: str
    last_open_chapter_id: str
    cursor_position: int
    scroll_top: int
    updated_at: datetime


class ImportTxtResponse(V1BaseModel):
    id: str
    title: str
    author: str
    current_word_count: int
    created_at: datetime
    updated_at: datetime
    chapters: list[ChapterResponse] = []


class ExportTxtResponse(V1BaseModel):
    filename: str
    media_type: str = "text/plain; charset=utf-8"


class OutlineSaveRequest(V1BaseModel):
    content_text: str = ""
    content_tree_json: Any = None
    expected_version: int | None = None
    force_override: bool = False


class WorkOutlineResponse(V1BaseModel):
    id: str
    work_id: str
    content_text: str
    content_tree_json: Any
    version: int
    created_at: datetime
    updated_at: datetime


class ChapterOutlineResponse(V1BaseModel):
    id: str
    chapter_id: str
    content_text: str
    content_tree_json: Any
    version: int
    created_at: datetime
    updated_at: datetime


class TimelineEventCreateRequest(V1BaseModel):
    title: str = ""
    description: str = ""
    chapter_id: str | None = None


class TimelineEventUpdateRequest(V1BaseModel):
    title: str | None = None
    description: str | None = None
    chapter_id: str | None = None
    expected_version: int | None = None
    force_override: bool = False


class TimelineEventReorderItem(V1BaseModel):
    id: str
    order_index: int


class TimelineEventReorderRequest(V1BaseModel):
    items: list[TimelineEventReorderItem]


class TimelineEventResponse(V1BaseModel):
    id: str
    work_id: str
    order_index: int
    title: str
    description: str
    chapter_id: str | None
    version: int
    created_at: datetime
    updated_at: datetime


class TimelineEventListResponse(V1BaseModel):
    work_id: str
    items: list[TimelineEventResponse]
    total: int


class TimelineEventDeleteResponse(V1BaseModel):
    ok: bool
    id: str


class ForeshadowCreateRequest(V1BaseModel):
    title: str = ""
    description: str = ""
    status: str = "open"
    introduced_chapter_id: str | None = None
    resolved_chapter_id: str | None = None


class ForeshadowUpdateRequest(V1BaseModel):
    title: str | None = None
    description: str | None = None
    status: str | None = None
    introduced_chapter_id: str | None = None
    resolved_chapter_id: str | None = None
    expected_version: int | None = None
    force_override: bool = False


class ForeshadowResponse(V1BaseModel):
    id: str
    work_id: str
    status: str
    title: str
    description: str
    introduced_chapter_id: str | None
    resolved_chapter_id: str | None
    version: int
    created_at: datetime
    updated_at: datetime


class ForeshadowListResponse(V1BaseModel):
    work_id: str
    items: list[ForeshadowResponse]
    total: int


class ForeshadowDeleteResponse(V1BaseModel):
    ok: bool
    id: str


class CharacterCreateRequest(V1BaseModel):
    name: str
    description: str = ""
    aliases: list[str] = []


class CharacterUpdateRequest(V1BaseModel):
    name: str | None = None
    description: str | None = None
    aliases: list[str] | None = None
    expected_version: int | None = None
    force_override: bool = False


class CharacterResponse(V1BaseModel):
    id: str
    work_id: str
    name: str
    description: str
    aliases: list[str]
    version: int
    created_at: datetime
    updated_at: datetime


class CharacterListResponse(V1BaseModel):
    work_id: str
    items: list[CharacterResponse]
    total: int


class CharacterDeleteResponse(V1BaseModel):
    ok: bool
    id: str


def serialize_work(item: Any) -> dict[str, Any]:
    return WorkResponse(
        id=item.id,
        title=item.title,
        author=item.author,
        current_word_count=item.word_count,
        created_at=item.created_at,
        updated_at=item.updated_at,
    ).model_dump(mode="json")


def serialize_chapter(item: Any) -> dict[str, Any]:
    return ChapterResponse(
        id=item.id.value,
        work_id=item.work_id.value,
        title=item.title,
        content=item.content,
        chapter_number=item.order_index,
        order_index=item.order_index,
        version=item.version,
        word_count=item.word_count,
        created_at=item.created_at,
        updated_at=item.updated_at,
    ).model_dump(mode="json")


def serialize_session(item: Any) -> dict[str, Any]:
    return SessionResponse(
        work_id=item.work_id,
        last_open_chapter_id=item.last_open_chapter_id,
        cursor_position=item.cursor_position,
        scroll_top=item.scroll_top,
        updated_at=item.updated_at,
    ).model_dump(mode="json")


def serialize_work_outline(item: Any) -> dict[str, Any]:
    return WorkOutlineResponse(
        id=item.id,
        work_id=item.work_id,
        content_text=item.content_text,
        content_tree_json=item.content_tree_json,
        version=item.version,
        created_at=item.created_at,
        updated_at=item.updated_at,
    ).model_dump(mode="json")


def serialize_chapter_outline(item: Any) -> dict[str, Any]:
    return ChapterOutlineResponse(
        id=item.id,
        chapter_id=item.chapter_id,
        content_text=item.content_text,
        content_tree_json=item.content_tree_json,
        version=item.version,
        created_at=item.created_at,
        updated_at=item.updated_at,
    ).model_dump(mode="json")


def serialize_timeline_event(item: Any) -> dict[str, Any]:
    return TimelineEventResponse(
        id=item.id,
        work_id=item.work_id,
        order_index=item.order_index,
        title=item.title,
        description=item.description,
        chapter_id=item.chapter_id,
        version=item.version,
        created_at=item.created_at,
        updated_at=item.updated_at,
    ).model_dump(mode="json")


def serialize_foreshadow(item: Any) -> dict[str, Any]:
    return ForeshadowResponse(
        id=item.id,
        work_id=item.work_id,
        status=item.status,
        title=item.title,
        description=item.description,
        introduced_chapter_id=item.introduced_chapter_id,
        resolved_chapter_id=item.resolved_chapter_id,
        version=item.version,
        created_at=item.created_at,
        updated_at=item.updated_at,
    ).model_dump(mode="json")


def serialize_character(item: Any) -> dict[str, Any]:
    try:
        aliases = json.loads(item.aliases_json or "[]")
    except json.JSONDecodeError:
        aliases = []
    if not isinstance(aliases, list):
        aliases = []
    return CharacterResponse(
        id=item.id,
        work_id=item.work_id,
        name=item.name,
        description=item.description,
        aliases=[str(alias) for alias in aliases],
        version=item.version,
        created_at=item.created_at,
        updated_at=item.updated_at,
    ).model_dump(mode="json")
