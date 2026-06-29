from __future__ import annotations

import time
from datetime import UTC, datetime

from fastapi.testclient import TestClient

from application.services.ai.ai_job_service import AIJobService
from domain.entities.ai.models import StyleDNAExtractionResult, StyleProfile, StyleProfileSourceType, StyleProfileStatus
from infrastructure.database.repositories.ai.file_ai_job_store import FileAIJobStore
from presentation.api import dependencies
from presentation.api.app import app


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _build_profile(
    *,
    profile_id: str,
    work_id: str = "work_001",
    status: StyleProfileStatus = StyleProfileStatus.PENDING_CONFIRM,
    version: int = 1,
) -> StyleProfile:
    now = _now()
    confirmed_at = now if status == StyleProfileStatus.ACTIVE else ""
    return StyleProfile(
        profile_id=profile_id,
        work_id=work_id,
        source_type=StyleProfileSourceType.USER_UPLOAD,
        source_ref="upload_001",
        source_text_hash=f"sha256:{profile_id}",
        source_text_length=2400,
        confidence=0.82,
        low_confidence_reason="",
        avg_sentence_length=18.0,
        sentence_length_variance=4.0,
        short_sentence_ratio=0.2,
        long_sentence_ratio=0.08,
        compound_sentence_ratio=0.33,
        avg_paragraph_length=75.0,
        paragraph_length_variance=11.0,
        dialogue_ratio=0.21,
        psychological_ratio=0.24,
        action_ratio=0.29,
        description_ratio=0.26,
        narrative_perspective="third_person_limited",
        tense_preference="past",
        style_summary="简洁冷静，情绪压抑。",
        style_tags=["简洁", "冷静"],
        version=version,
        status=status,
        created_at=now,
        updated_at=now,
        confirmed_at=confirmed_at,
    )


class _FakeStyleDNAService:
    def __init__(self) -> None:
        self.profiles: dict[str, StyleProfile] = {}

    async def extract(
        self,
        *,
        work_id: str,
        source_text: str,
        source_type: StyleProfileSourceType,
        source_ref: str = "",
    ) -> StyleDNAExtractionResult:
        profile = _build_profile(
            profile_id=f"sp_{len(self.profiles) + 1:03d}",
            work_id=work_id,
            status=StyleProfileStatus.PENDING_CONFIRM,
            version=len([item for item in self.profiles.values() if item.work_id == work_id]) + 1,
        ).model_copy(
            update={
                "source_type": source_type,
                "source_ref": source_ref,
                "source_text_length": len(source_text),
            }
        )
        self.profiles[profile.profile_id] = profile
        return StyleDNAExtractionResult(profile=profile, confidence=profile.confidence, warnings=[])

    def get_profile(self, profile_id: str) -> StyleProfile:
        profile = self.profiles.get(profile_id)
        if profile is None:
            raise ValueError("style_profile_not_found")
        return profile

    def get_active(self, work_id: str) -> StyleProfile | None:
        for profile in self.profiles.values():
            if profile.work_id == work_id and profile.status == StyleProfileStatus.ACTIVE:
                return profile
        return None

    def get_history(self, work_id: str) -> list[StyleProfile]:
        items = [item for item in self.profiles.values() if item.work_id == work_id]
        return sorted(items, key=lambda item: item.version, reverse=True)

    def confirm(self, profile_id: str) -> StyleProfile:
        profile = self.get_profile(profile_id)
        if profile.status != StyleProfileStatus.PENDING_CONFIRM:
            raise ValueError("profile_not_confirmable")
        for item in list(self.profiles.values()):
            if item.work_id == profile.work_id and item.status == StyleProfileStatus.ACTIVE:
                self.profiles[item.profile_id] = item.model_copy(update={"status": StyleProfileStatus.ARCHIVED})
        updated = profile.model_copy(update={"status": StyleProfileStatus.ACTIVE, "confirmed_at": _now(), "updated_at": _now()})
        self.profiles[profile_id] = updated
        return updated

    def disable(self, profile_id: str) -> StyleProfile:
        profile = self.get_profile(profile_id)
        if profile.status != StyleProfileStatus.ACTIVE:
            raise ValueError("profile_not_disableable")
        updated = profile.model_copy(update={"status": StyleProfileStatus.DISABLED, "updated_at": _now()})
        self.profiles[profile_id] = updated
        return updated

    def delete(self, profile_id: str) -> None:
        profile = self.get_profile(profile_id)
        if profile.status in {StyleProfileStatus.PENDING_CONFIRM, StyleProfileStatus.DRAFT}:
            self.profiles.pop(profile_id, None)
            return
        self.profiles[profile_id] = profile.model_copy(update={"status": StyleProfileStatus.ARCHIVED, "updated_at": _now()})


def _build_job_service(tmp_path) -> AIJobService:
    store = FileAIJobStore(tmp_path / "ai_jobs.json")
    return AIJobService(job_repository=store, step_repository=store, attempt_repository=store)


def _install_test_dependencies(monkeypatch, tmp_path):
    fake_service = _FakeStyleDNAService()
    job_service = _build_job_service(tmp_path)
    monkeypatch.setenv("INKTRACE_P2_ENABLE_STYLE_DNA", "1")
    monkeypatch.setattr(dependencies, "get_style_dna_service", lambda: fake_service)
    monkeypatch.setattr(dependencies, "get_ai_job_service", lambda: job_service)
    return fake_service, job_service


def _wait_for_job_completion(client: TestClient, job_id: str, *, timeout_s: float = 2.0) -> dict[str, object]:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        response = client.get(f"/api/v2/ai/jobs/{job_id}")
        assert response.status_code == 200
        data = response.json()["data"]
        if data["status"] in {"completed", "failed", "cancelled"}:
            return data
        time.sleep(0.05)
    raise AssertionError("style dna job did not reach terminal state in time")


def test_style_dna_extract_api_creates_async_job_and_persists_profile(monkeypatch, tmp_path) -> None:
    _fake_service, _job_service = _install_test_dependencies(monkeypatch, tmp_path)
    client = TestClient(app)

    response = client.post(
        "/api/v2/ai/style-dna/extract",
        json={
            "work_id": "work_001",
            "source_text": "这是用于提取文风的标杆文本。" * 80,
            "source_type": "user_upload",
            "source_ref": "upload_001",
            "caller_type": "user_action",
            "idempotency_key": "style-dna-extract-001",
        },
    )

    assert response.status_code == 202
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["data"]["job_type"] == "style_dna_extraction"
    assert payload["data"]["status"] == "queued"
    assert payload["data"]["operation"] == "extract"
    assert payload["data"]["polling_hint"]["next_poll_after_ms"] == 3000

    job_id = payload["data"]["job_id"]
    job_data = _wait_for_job_completion(client, job_id)
    assert job_data["status"] == "completed"
    assert job_data["result_summary"]["profile_id"].startswith("sp_")
    assert job_data["result_summary"]["profile_status"] == "pending_confirm"


def test_style_dna_query_endpoints_return_profile_active_and_history(monkeypatch, tmp_path) -> None:
    fake_service, _job_service = _install_test_dependencies(monkeypatch, tmp_path)
    pending = _build_profile(profile_id="sp_pending_001", status=StyleProfileStatus.PENDING_CONFIRM, version=2)
    active = _build_profile(profile_id="sp_active_001", status=StyleProfileStatus.ACTIVE, version=1)
    fake_service.profiles[pending.profile_id] = pending
    fake_service.profiles[active.profile_id] = active
    client = TestClient(app)

    profile_response = client.get("/api/v2/ai/style-dna/profiles/sp_pending_001")
    active_response = client.get("/api/v2/ai/style-dna/work_001/active")
    history_response = client.get("/api/v2/ai/style-dna/work_001/history")

    assert profile_response.status_code == 200
    assert profile_response.json()["data"]["profile"]["profile_id"] == "sp_pending_001"
    assert active_response.status_code == 200
    assert active_response.json()["data"]["profile"]["profile_id"] == "sp_active_001"
    assert history_response.status_code == 200
    assert [item["profile_id"] for item in history_response.json()["data"]["profiles"]] == ["sp_pending_001", "sp_active_001"]


def test_style_dna_confirm_api_rejects_non_user_action_caller(monkeypatch, tmp_path) -> None:
    fake_service, _job_service = _install_test_dependencies(monkeypatch, tmp_path)
    fake_service.profiles["sp_pending_001"] = _build_profile(profile_id="sp_pending_001", status=StyleProfileStatus.PENDING_CONFIRM)
    client = TestClient(app)

    response = client.post(
        "/api/v2/ai/style-dna/profiles/sp_pending_001/confirm",
        json={"caller_type": "agent", "idempotency_key": "style-confirm-001"},
    )

    assert response.status_code == 403
    assert response.json()["error"]["error_code"] == "P2_CALLER_FORBIDDEN"


def test_style_dna_confirm_and_disable_api_update_profile_status(monkeypatch, tmp_path) -> None:
    fake_service, _job_service = _install_test_dependencies(monkeypatch, tmp_path)
    fake_service.profiles["sp_pending_001"] = _build_profile(profile_id="sp_pending_001", status=StyleProfileStatus.PENDING_CONFIRM)
    client = TestClient(app)

    confirm_response = client.post(
        "/api/v2/ai/style-dna/profiles/sp_pending_001/confirm",
        json={"caller_type": "user_action", "idempotency_key": "style-confirm-allow-001"},
    )
    disable_response = client.post(
        "/api/v2/ai/style-dna/profiles/sp_pending_001/disable",
        json={"caller_type": "user_action", "idempotency_key": "style-disable-allow-001"},
    )

    assert confirm_response.status_code == 200
    assert confirm_response.json()["data"]["profile"]["status"] == "active"
    assert disable_response.status_code == 200
    assert disable_response.json()["data"]["profile"]["status"] == "disabled"


def test_style_dna_delete_api_returns_deleted_or_archived_by_previous_status(monkeypatch, tmp_path) -> None:
    fake_service, _job_service = _install_test_dependencies(monkeypatch, tmp_path)
    fake_service.profiles["sp_pending_001"] = _build_profile(profile_id="sp_pending_001", status=StyleProfileStatus.PENDING_CONFIRM)
    fake_service.profiles["sp_active_001"] = _build_profile(profile_id="sp_active_001", status=StyleProfileStatus.ACTIVE)
    client = TestClient(app)

    pending_response = client.request(
        "DELETE",
        "/api/v2/ai/style-dna/profiles/sp_pending_001",
        json={"caller_type": "user_action", "idempotency_key": "style-delete-001"},
    )
    active_response = client.request(
        "DELETE",
        "/api/v2/ai/style-dna/profiles/sp_active_001",
        json={"caller_type": "user_action", "idempotency_key": "style-delete-002"},
    )

    assert pending_response.status_code == 200
    assert pending_response.json()["data"] == {"deleted": True, "status": "deleted"}
    assert active_response.status_code == 200
    assert active_response.json()["data"] == {"deleted": True, "status": "archived"}
