from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from application.services.ai.outline_application_service import OutlineApplyResult, OutlineConflictReviewRequired
from domain.entities.ai.suggestion_payloads import SuggestionLaunchResult
from presentation.api import dependencies
from presentation.api.app import app


class _AssistStub:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, object]]] = []

    def _launch(self, name: str, kwargs: dict[str, object]) -> SuggestionLaunchResult:
        self.calls.append((name, kwargs))
        if kwargs.get("caller_type") != "user_action":
            raise ValueError("P2_CALLER_FORBIDDEN")
        if not str(kwargs.get("idempotency_key") or "").strip():
            raise ValueError("P2_IDEMPOTENCY_KEY_REQUIRED")
        return SuggestionLaunchResult(suggestion_id=f"ais-{name}", job_id=f"job-{name}")

    def start_polish(self, **kwargs):
        return self._launch("polish", kwargs)

    def start_expand(self, **kwargs):
        return self._launch("expand", kwargs)

    def start_chapter_outline(self, **kwargs):
        return self._launch("chapter-outline", kwargs)

    def start_writing_task_suggestion(self, **kwargs):
        return self._launch("writing-task", kwargs)


class _ApplicationStub:
    def __init__(self) -> None:
        self.calls = 0

    def apply_suggestion(self, **kwargs):
        self.calls += 1
        if kwargs.get("caller_type") != "user_action":
            raise ValueError("P2_CALLER_FORBIDDEN")
        if kwargs.get("user_action") is not True:
            raise ValueError("P2_USER_ACTION_REQUIRED")
        if not str(kwargs.get("idempotency_key") or "").strip():
            raise ValueError("P2_IDEMPOTENCY_KEY_REQUIRED")
        if kwargs.get("confirm_apply") is not True:
            raise ValueError("P2_OUTLINE_APPLY_CONFIRMATION_REQUIRED")
        return OutlineApplyResult(True, kwargs["suggestion_id"], "work_outline", "work-1", 3, 4, "work_outline:work-1:v4")


def test_outline_assist_four_generation_endpoints_return_202_and_polling_hint(monkeypatch) -> None:
    monkeypatch.setenv("INKTRACE_P2_ENABLE_OUTLINE_ASSIST", "1")
    stub = _AssistStub()
    monkeypatch.setattr(dependencies, "get_outline_assist_service", lambda: stub)
    client = TestClient(app)
    cases = [
        (
            "/api/v2/ai/outline-assist/polish",
            {"caller_type": "user_action", "work_id": "work-1", "target_kind": "work_outline", "target_id": "work-1", "target_revision": 3, "selected_text": "参考", "idempotency_key": "p-1"},
        ),
        (
            "/api/v2/ai/outline-assist/expand",
            {"caller_type": "user_action", "work_id": "work-1", "target_kind": "work_outline", "target_id": "work-1", "target_revision": 3, "selected_text": "参考", "expand_focus": "动机", "idempotency_key": "e-1"},
        ),
        (
            "/api/v2/ai/outline-assist/chapter-outline",
            {"caller_type": "user_action", "work_id": "work-1", "target_kind": "chapter_outline", "target_id": "chapter-1", "target_revision": 5, "chapter_goal": "找到线索", "idempotency_key": "c-1"},
        ),
        (
            "/api/v2/ai/outline-assist/writing-task",
            {"caller_type": "user_action", "work_id": "work-1", "chapter_id": "chapter-1", "target_revision": 5, "idempotency_key": "w-1"},
        ),
    ]

    for path, body in cases:
        response = client.post(path, json=body)
        assert response.status_code == 202, response.text
        data = response.json()["data"]
        assert data["status"] == "pending"
        assert data["suggestion_id"]
        assert data["job_id"]
        assert data["polling_hint"]

    call_count = len(stub.calls)
    missing_target_kind = client.post(
        "/api/v2/ai/outline-assist/chapter-outline",
        json={
            "caller_type": "user_action",
            "work_id": "work-1",
            "target_id": "chapter-1",
            "target_revision": 5,
            "idempotency_key": "missing-kind",
        },
    )
    assert missing_target_kind.status_code == 400
    assert missing_target_kind.json()["error"]["error_code"] == "P2_OUTLINE_TARGET_REQUIRED"
    wrong_target_kind = client.post(
        "/api/v2/ai/outline-assist/chapter-outline",
        json={
            "caller_type": "user_action",
            "work_id": "work-1",
            "target_kind": "work_outline",
            "target_id": "chapter-1",
            "target_revision": 5,
            "idempotency_key": "wrong-kind",
        },
    )
    assert wrong_target_kind.status_code == 400
    assert len(stub.calls) == call_count


def test_outline_apply_endpoint_returns_200_and_enforces_all_gates(monkeypatch) -> None:
    monkeypatch.setenv("INKTRACE_P2_ENABLE_OUTLINE_ASSIST", "1")
    application = _ApplicationStub()
    monkeypatch.setattr(dependencies, "get_outline_application_service", lambda: application)
    client = TestClient(app)
    valid = {
        "caller_type": "user_action",
        "user_action": True,
        "user_id": "writer-1",
        "idempotency_key": "apply-1",
        "confirm_apply": True,
        "target_revision": 3,
    }

    response = client.post("/api/v2/ai/outline-assist/suggestions/ais-1/apply", json=valid)
    assert response.status_code == 200
    assert response.json()["data"]["new_version"] == 4

    invalid_cases = [
        ({**valid, "caller_type": "agent"}, "P2_CALLER_FORBIDDEN", 403),
        ({**valid, "user_action": False}, "P2_USER_ACTION_REQUIRED", 403),
        ({**valid, "idempotency_key": ""}, "P2_IDEMPOTENCY_KEY_REQUIRED", 400),
        ({**valid, "confirm_apply": False}, "P2_OUTLINE_APPLY_CONFIRMATION_REQUIRED", 400),
    ]
    for body, code, status in invalid_cases:
        rejected = client.post("/api/v2/ai/outline-assist/suggestions/ais-1/apply", json=body)
        assert rejected.status_code == status
        assert rejected.json()["error"]["error_code"] == code

    call_count = application.calls
    missing_caller = dict(valid)
    missing_caller.pop("caller_type")
    rejected = client.post("/api/v2/ai/outline-assist/suggestions/ais-1/apply", json=missing_caller)
    assert rejected.status_code == 422
    assert application.calls == call_count

    blank_user = {**valid, "user_id": "   "}
    rejected = client.post("/api/v2/ai/outline-assist/suggestions/ais-1/apply", json=blank_user)
    assert rejected.status_code == 422
    assert application.calls == call_count


def test_outline_assist_feature_flag_blocks_all_module_endpoints(monkeypatch) -> None:
    monkeypatch.setenv("INKTRACE_P2_ENABLE_OUTLINE_ASSIST", "0")
    client = TestClient(app)
    response = client.post(
        "/api/v2/ai/outline-assist/polish",
        json={"caller_type": "user_action", "work_id": "work-1", "target_kind": "selection", "selected_text": "参考", "idempotency_key": "p-1"},
    )
    assert response.status_code == 503
    assert response.json()["error"]["error_code"] == "P2_FEATURE_DISABLED"


def test_reused_convert_endpoint_maps_writing_task_errors_to_409(monkeypatch) -> None:
    class _SuggestionErrorStub:
        def convert_suggestion(self, *args, **kwargs):
            raise ValueError("P2_WRITING_TASK_PREREQUISITE_MISSING")

    monkeypatch.setenv("INKTRACE_P2_ENABLE_OUTLINE_ASSIST", "1")
    monkeypatch.setattr(dependencies, "get_ai_suggestion_service", lambda: _SuggestionErrorStub())
    client = TestClient(app)
    response = client.post(
        "/api/v2/ai/suggestions/ais-writing/convert",
        json={
            "caller_type": "user_action",
            "user_action": True,
            "user_id": "writer-1",
            "idempotency_key": "convert-1",
        },
    )
    assert response.status_code == 409
    assert response.json()["error"]["error_code"] == "P2_WRITING_TASK_PREREQUISITE_MISSING"

    missing_caller = client.post(
        "/api/v2/ai/suggestions/ais-writing/convert",
        json={"user_action": True, "user_id": "writer-1", "idempotency_key": "convert-2"},
    )
    assert missing_caller.status_code == 422
    blank_user = client.post(
        "/api/v2/ai/suggestions/ais-writing/convert",
        json={
            "caller_type": "user_action",
            "user_action": True,
            "user_id": "   ",
            "idempotency_key": "convert-blank-user",
        },
    )
    assert blank_user.status_code == 422
    blank_confirm_user = client.post(
        "/api/v2/ai/writing-tasks/wt-p2/confirm",
        json={
            "caller_type": "user_action",
            "user_action": True,
            "user_id": "   ",
            "idempotency_key": "confirm-blank-user",
        },
    )
    assert blank_confirm_user.status_code == 422


def test_outline_apply_conflict_review_returns_safe_record_refs(monkeypatch) -> None:
    class _ConflictApplicationStub:
        def apply_suggestion(self, **kwargs):
            raise OutlineConflictReviewRequired(["cgr-safe-1", "cgr-safe-2"])

    monkeypatch.setenv("INKTRACE_P2_ENABLE_OUTLINE_ASSIST", "1")
    monkeypatch.setattr(dependencies, "get_outline_application_service", lambda: _ConflictApplicationStub())
    client = TestClient(app)
    response = client.post(
        "/api/v2/ai/outline-assist/suggestions/ais-1/apply",
        json={
            "caller_type": "user_action",
            "user_action": True,
            "user_id": "writer-1",
            "idempotency_key": "apply-conflict",
            "confirm_apply": True,
            "target_revision": 3,
        },
    )
    assert response.status_code == 409
    assert response.json()["error"]["data"] == {"record_refs": ["cgr-safe-1", "cgr-safe-2"]}


class _SerializedItem:
    def __init__(self, item_id: str) -> None:
        self.item_id = item_id

    def model_dump(self, *, mode: str) -> dict[str, str]:
        assert mode == "json"
        return {"id": self.item_id}


class _SourceAwareSuggestionStub:
    def __init__(self, *, audit_failure: bool = False) -> None:
        self.audit_failure = audit_failure
        self.write_calls: list[tuple[str, str]] = []
        self.convert_kwargs: dict[str, object] = {}

    def is_outline_assist_suggestion(self, suggestion_id: str) -> bool:
        return suggestion_id.startswith("p2-")

    def accept_suggestion(self, suggestion_id: str, **kwargs):
        self.write_calls.append(("accept", suggestion_id))
        return _SerializedItem(suggestion_id)

    def dismiss_suggestion(self, suggestion_id: str, **kwargs):
        self.write_calls.append(("dismiss", suggestion_id))
        return _SerializedItem(suggestion_id)

    def convert_suggestion(self, suggestion_id: str, **kwargs):
        self.write_calls.append(("convert", suggestion_id))
        self.convert_kwargs = dict(kwargs)
        if self.audit_failure:
            raise ValueError("P2_OUTLINE_AUDIT_WRITE_FAILED")
        return _SerializedItem(suggestion_id)


def test_reused_convert_endpoint_passes_decision_note_into_idempotency_request(monkeypatch) -> None:
    monkeypatch.setenv("INKTRACE_P2_ENABLE_OUTLINE_ASSIST", "1")
    stub = _SourceAwareSuggestionStub()
    monkeypatch.setattr(dependencies, "get_ai_suggestion_service", lambda: stub)
    client = TestClient(app)

    response = client.post(
        "/api/v2/ai/suggestions/p2-suggestion/convert",
        json={
            "caller_type": "user_action",
            "user_action": True,
            "user_id": "writer-1",
            "decision_note": "保存为本章写作计划",
            "idempotency_key": "convert-with-note",
        },
    )

    assert response.status_code == 200
    assert stub.convert_kwargs["decision_note"] == "保存为本章写作计划"


@pytest.mark.parametrize("action", ["accept", "dismiss", "convert"])
@pytest.mark.parametrize(
    ("field", "value", "expected_code", "expected_status"),
    [
        ("caller_type", "agent", "P2_CALLER_FORBIDDEN", 403),
        ("user_action", False, "P2_USER_ACTION_REQUIRED", 403),
        ("idempotency_key", "", "P2_IDEMPOTENCY_KEY_REQUIRED", 400),
    ],
)
def test_enabled_p2_reused_suggestion_gates_use_p2_error_codes(
    monkeypatch,
    action: str,
    field: str,
    value,
    expected_code: str,
    expected_status: int,
) -> None:
    monkeypatch.setenv("INKTRACE_P2_ENABLE_OUTLINE_ASSIST", "1")
    stub = _SourceAwareSuggestionStub()
    monkeypatch.setattr(dependencies, "get_ai_suggestion_service", lambda: stub)
    body = {
        "caller_type": "user_action",
        "user_action": True,
        "user_id": "writer-1",
        "idempotency_key": f"{action}-gate",
    }
    body[field] = value

    response = TestClient(app).post(f"/api/v2/ai/suggestions/p2-suggestion/{action}", json=body)

    assert response.status_code == expected_status
    assert response.json()["error"]["error_code"] == expected_code
    assert stub.write_calls == []


@pytest.mark.parametrize("action", ["accept", "dismiss", "convert"])
def test_disabled_outline_flag_blocks_only_p2_reused_suggestion_writes(monkeypatch, action: str) -> None:
    monkeypatch.setenv("INKTRACE_P2_ENABLE_OUTLINE_ASSIST", "0")
    stub = _SourceAwareSuggestionStub()
    monkeypatch.setattr(dependencies, "get_ai_suggestion_service", lambda: stub)
    client = TestClient(app)
    body = {
        "caller_type": "user_action",
        "user_action": True,
        "user_id": "writer-1",
        "idempotency_key": f"{action}-1",
    }

    blocked = client.post(f"/api/v2/ai/suggestions/p2-suggestion/{action}", json=body)
    assert blocked.status_code == 503
    assert blocked.json()["error"]["error_code"] == "P2_FEATURE_DISABLED"
    assert stub.write_calls == []

    p1_response = client.post(f"/api/v2/ai/suggestions/p1-suggestion/{action}", json=body)
    assert p1_response.status_code == 200
    assert stub.write_calls == [(action, "p1-suggestion")]


class _SourceAwarePlanningStub:
    def __init__(self, *, audit_failure: bool = False) -> None:
        self.audit_failure = audit_failure
        self.write_calls: list[str] = []

    def is_outline_assist_writing_task(self, writing_task_id: str) -> bool:
        return writing_task_id.startswith("p2-")

    def confirm_writing_task(self, *, writing_task_id: str, **kwargs):
        self.write_calls.append(writing_task_id)
        if self.audit_failure:
            raise ValueError("P2_OUTLINE_AUDIT_WRITE_FAILED")
        return _SerializedItem(writing_task_id)


@pytest.mark.parametrize(
    ("field", "value", "expected_code", "expected_status"),
    [
        ("caller_type", "agent", "P2_CALLER_FORBIDDEN", 403),
        ("user_action", False, "P2_USER_ACTION_REQUIRED", 403),
        ("idempotency_key", "", "P2_IDEMPOTENCY_KEY_REQUIRED", 400),
    ],
)
def test_enabled_p2_reused_writing_task_gate_uses_p2_error_codes(
    monkeypatch,
    field: str,
    value,
    expected_code: str,
    expected_status: int,
) -> None:
    monkeypatch.setenv("INKTRACE_P2_ENABLE_OUTLINE_ASSIST", "1")
    stub = _SourceAwarePlanningStub()
    monkeypatch.setattr(dependencies, "get_planning_api_service", lambda: stub)
    body = {
        "caller_type": "user_action",
        "user_action": True,
        "user_id": "writer-1",
        "idempotency_key": "confirm-gate",
    }
    body[field] = value

    response = TestClient(app).post("/api/v2/ai/writing-tasks/p2-writing-task/confirm", json=body)

    assert response.status_code == expected_status
    assert response.json()["error"]["error_code"] == expected_code
    assert stub.write_calls == []


def test_disabled_outline_flag_blocks_only_p2_reused_writing_task_confirm(monkeypatch) -> None:
    monkeypatch.setenv("INKTRACE_P2_ENABLE_OUTLINE_ASSIST", "0")
    stub = _SourceAwarePlanningStub()
    monkeypatch.setattr(dependencies, "get_planning_api_service", lambda: stub)
    client = TestClient(app)
    body = {
        "caller_type": "user_action",
        "user_action": True,
        "user_id": "writer-1",
        "idempotency_key": "confirm-1",
    }

    blocked = client.post("/api/v2/ai/writing-tasks/p2-writing-task/confirm", json=body)
    assert blocked.status_code == 503
    assert blocked.json()["error"]["error_code"] == "P2_FEATURE_DISABLED"
    assert stub.write_calls == []

    p1_response = client.post("/api/v2/ai/writing-tasks/p1-writing-task/confirm", json=body)
    assert p1_response.status_code == 200
    assert stub.write_calls == ["p1-writing-task"]


@pytest.mark.parametrize("resource", ["suggestion", "writing_task"])
def test_disabled_outline_flag_preserves_normal_not_found_response(monkeypatch, resource: str) -> None:
    monkeypatch.setenv("INKTRACE_P2_ENABLE_OUTLINE_ASSIST", "0")
    client = TestClient(app)
    body = {
        "caller_type": "user_action",
        "user_action": True,
        "user_id": "writer-1",
        "idempotency_key": "missing-1",
    }

    if resource == "suggestion":
        class _MissingSuggestionStub:
            def is_outline_assist_suggestion(self, suggestion_id: str) -> bool:
                raise ValueError("ai_suggestion_not_found")

            def accept_suggestion(self, suggestion_id: str, **kwargs):
                raise ValueError("ai_suggestion_not_found")

        monkeypatch.setattr(dependencies, "get_ai_suggestion_service", lambda: _MissingSuggestionStub())
        response = client.post("/api/v2/ai/suggestions/missing/accept", json=body)
    else:
        class _MissingWritingTaskStub:
            def is_outline_assist_writing_task(self, writing_task_id: str) -> bool:
                raise ValueError("writing_task_not_found")

            def confirm_writing_task(self, *, writing_task_id: str, **kwargs):
                raise ValueError("writing_task_not_found")

        monkeypatch.setattr(dependencies, "get_planning_api_service", lambda: _MissingWritingTaskStub())
        response = client.post("/api/v2/ai/writing-tasks/missing/confirm", json=body)

    assert response.status_code == 404


@pytest.mark.parametrize("endpoint", ["convert", "confirm", "outline"])
def test_outline_audit_write_failure_maps_to_retryable_503(monkeypatch, endpoint: str) -> None:
    monkeypatch.setenv("INKTRACE_P2_ENABLE_OUTLINE_ASSIST", "1")
    client = TestClient(app)
    if endpoint == "convert":
        monkeypatch.setattr(
            dependencies,
            "get_ai_suggestion_service",
            lambda: _SourceAwareSuggestionStub(audit_failure=True),
        )
        response = client.post(
            "/api/v2/ai/suggestions/p2-suggestion/convert",
            json={
                "caller_type": "user_action",
                "user_action": True,
                "user_id": "writer-1",
                "idempotency_key": "convert-audit",
            },
        )
    elif endpoint == "confirm":
        monkeypatch.setattr(
            dependencies,
            "get_planning_api_service",
            lambda: _SourceAwarePlanningStub(audit_failure=True),
        )
        response = client.post(
            "/api/v2/ai/writing-tasks/p2-writing-task/confirm",
            json={
                "caller_type": "user_action",
                "user_action": True,
                "user_id": "writer-1",
                "idempotency_key": "confirm-audit",
            },
        )
    else:
        class _AuditFailureAssistStub:
            def start_polish(self, **kwargs):
                raise ValueError("P2_OUTLINE_AUDIT_WRITE_FAILED")

        monkeypatch.setattr(dependencies, "get_outline_assist_service", lambda: _AuditFailureAssistStub())
        response = client.post(
            "/api/v2/ai/outline-assist/polish",
            json={
                "caller_type": "user_action",
                "work_id": "work-1",
                "target_kind": "selection",
                "selected_text": "参考",
                "idempotency_key": "polish-audit",
            },
        )

    assert response.status_code == 503
    error = response.json()["error"]
    assert error["error_code"] == "P2_OUTLINE_AUDIT_WRITE_FAILED"
    assert error["retryable"] is True
    assert error["safe_message"] != "P2_OUTLINE_AUDIT_WRITE_FAILED"
