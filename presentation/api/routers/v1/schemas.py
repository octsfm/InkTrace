"""V1.1 Workbench API response schemas."""

from __future__ import annotations

from dataclasses import dataclass
from http import HTTPStatus
import re
from typing import Any, Mapping


SNAKE_CASE_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")


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
