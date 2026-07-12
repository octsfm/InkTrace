from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from threading import RLock

from domain.entities.ai.models import (
    AISuggestionActionType,
    AISuggestionDecision,
    AISuggestionDecisionType,
    AISuggestionStatus,
    AISuggestionType,
    AgentTraceStatus,
)
from domain.repositories.ai.ai_suggestion_repository import AISuggestionRepository
from domain.value_objects.outline_snapshot import outline_content_hash, preserves_outline_node_contract
from domain.entities.ai.suggestion_payloads import (
    ChapterOutlineDetailPayload,
    OutlineExpandPayload,
    OutlinePolishPayload,
)
from application.services.v1.content_tree_schema import validate_content_tree_json


_APPLY_TYPES = {
    AISuggestionType.OUTLINE_POLISH,
    AISuggestionType.OUTLINE_EXPAND,
    AISuggestionType.CHAPTER_OUTLINE_DETAIL,
}


def _sha256(value: str) -> str:
    return hashlib.sha256(str(value or "").encode("utf-8")).hexdigest()


def _fingerprint(payload: dict[str, object]) -> str:
    return _sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str))


@dataclass(frozen=True)
class OutlineApplyResult:
    success: bool
    suggestion_id: str
    target_kind: str
    target_id: str
    previous_version: int
    new_version: int
    result_ref: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


class OutlineConflictReviewRequired(ValueError):
    def __init__(self, record_refs: list[str]) -> None:
        super().__init__("P2_OUTLINE_CONFLICT_REVIEW_REQUIRED")
        self.record_refs = list(record_refs)


class OutlineApplicationService:
    def __init__(
        self,
        *,
        ai_suggestion_repository: AISuggestionRepository,
        writing_asset_service,
        conflict_guard_service,
        trace_service=None,
    ) -> None:
        self._suggestions = ai_suggestion_repository
        self._assets = writing_asset_service
        self._conflict_guard = conflict_guard_service
        self._trace_service = trace_service
        self._apply_lock = RLock()

    def apply_suggestion(
        self,
        *,
        suggestion_id: str,
        caller_type: str,
        user_action: bool,
        user_id: str,
        idempotency_key: str,
        confirm_apply: bool,
        target_revision: int,
        request_id: str = "",
        trace_id: str = "",
    ) -> OutlineApplyResult:
        with self._apply_lock:
            return self._apply_suggestion_locked(
                suggestion_id=suggestion_id,
                caller_type=caller_type,
                user_action=user_action,
                user_id=user_id,
                idempotency_key=idempotency_key,
                confirm_apply=confirm_apply,
                target_revision=target_revision,
                request_id=request_id,
                trace_id=trace_id,
            )

    def _apply_suggestion_locked(
        self,
        *,
        suggestion_id: str,
        caller_type: str,
        user_action: bool,
        user_id: str,
        idempotency_key: str,
        confirm_apply: bool,
        target_revision: int,
        request_id: str = "",
        trace_id: str = "",
    ) -> OutlineApplyResult:
        self._require_gate(caller_type, user_action, user_id, idempotency_key, confirm_apply)
        try:
            suggestion = self._suggestions.get(suggestion_id)
        except ValueError as exc:
            raise ValueError("P2_OUTLINE_SUGGESTION_NOT_FOUND") from exc

        request_hash = _fingerprint(
            {
                "suggestion_id": suggestion_id,
                "user_id": user_id,
                "confirm_apply": confirm_apply,
                "target_revision": target_revision,
            }
        )
        key_hash = _sha256(idempotency_key.strip())
        metadata = dict(suggestion.metadata or {})
        for prior in self._suggestions.list_suggestions(work_id=suggestion.work_id):
            prior_metadata = dict(prior.metadata or {})
            if prior_metadata.get("apply_idempotency_key_hash") != key_hash:
                continue
            if prior_metadata.get("apply_request_hash") != request_hash:
                raise ValueError("P2_IDEMPOTENCY_CONFLICT")
            prior_result = prior_metadata.get("apply_result")
            if isinstance(prior_result, dict):
                result = OutlineApplyResult(**prior_result)
                self._compensate_resolution(
                    prior,
                    result=result,
                    user_id=user_id,
                    user_action=user_action,
                    key_hash=key_hash,
                    request_hash=request_hash,
                    request_id=request_id,
                    trace_id=trace_id,
                )
                return result
        if metadata.get("apply_idempotency_key_hash") == key_hash:
            if metadata.get("apply_request_hash") != request_hash:
                raise ValueError("P2_IDEMPOTENCY_CONFLICT")
            stored_result = metadata.get("apply_result")
            if isinstance(stored_result, dict):
                result = OutlineApplyResult(**stored_result)
                self._compensate_resolution(
                    suggestion,
                    result=result,
                    user_id=user_id,
                    user_action=user_action,
                    key_hash=key_hash,
                    request_hash=request_hash,
                    request_id=request_id,
                    trace_id=trace_id,
                )
                return result
            if metadata.get("apply_state") == "writing":
                recovered = self._recover_written_apply(
                    suggestion,
                    user_id=user_id,
                    user_action=user_action,
                    key_hash=key_hash,
                    request_hash=request_hash,
                    request_id=request_id,
                    trace_id=trace_id,
                )
                if recovered is not None:
                    return recovered

        if suggestion.suggestion_type not in _APPLY_TYPES:
            raise ValueError("P2_OUTLINE_SUGGESTION_TYPE_UNSUPPORTED")
        if suggestion.status != AISuggestionStatus.ACCEPTED:
            raise ValueError("P2_OUTLINE_SUGGESTION_NOT_ACCEPTED")

        payload = self._validate_payload(suggestion)
        target_kind = str(payload.get("target_kind") or "")
        target_id = str(payload.get("target_id") or "")
        base_revision = payload.get("target_revision")
        if target_kind not in {"work_outline", "chapter_outline"} or not target_id or base_revision is None:
            raise ValueError("P2_OUTLINE_SUGGESTION_TYPE_UNSUPPORTED")
        if int(target_revision) != int(base_revision):
            raise ValueError("P2_OUTLINE_TARGET_CONFLICT")

        current = self._get_current(target_kind, target_id)
        target_hash = str(payload.get("target_content_hash") or metadata.get("target_content_hash") or "")
        if (
            int(current.version) != int(base_revision)
            or outline_content_hash(current.content_text, current.content_tree_json) != target_hash
        ):
            self._record_guard(
                work_id=suggestion.work_id,
                chapter_id=suggestion.chapter_id,
                suggestion_id=suggestion_id,
                target_kind=target_kind,
                target_id=target_id,
                target_revision=int(current.version),
                blocking=True,
                reason_code="P2_OUTLINE_TARGET_CONFLICT",
                request_id=request_id,
                trace_id=trace_id,
            )
            raise ValueError("P2_OUTLINE_TARGET_CONFLICT")

        try:
            blocking_records = self._conflict_guard.list_unresolved_outline_blocking(
                work_id=suggestion.work_id,
                target_kind=target_kind,
                target_id=target_id,
            )
            if blocking_records:
                raise OutlineConflictReviewRequired([record.record_id for record in blocking_records])
        except OutlineConflictReviewRequired:
            raise
        except Exception as exc:
            raise ValueError("P2_OUTLINE_CONFLICT_CHECK_FAILED") from exc

        guard = self._record_guard(
            work_id=suggestion.work_id,
            chapter_id=suggestion.chapter_id,
            suggestion_id=suggestion_id,
            target_kind=target_kind,
            target_id=target_id,
            target_revision=int(current.version),
            blocking=False,
            request_id=request_id,
            trace_id=trace_id,
        )
        try:
            self._conflict_guard.acknowledge_outline_apply(
                guard.record_id,
                user_id=user_id,
                user_action=user_action,
                request_id=request_id,
                trace_id=trace_id,
            )
        except Exception as exc:
            raise ValueError("P2_OUTLINE_CONFLICT_CHECK_FAILED") from exc
        try:
            self._record_apply_trace(
                suggestion,
                event_type="user_decision_recorded",
                target_revision=int(base_revision),
                target_hash=target_hash,
                high_risk=True,
            )
        except Exception as exc:
            raise ValueError("P2_OUTLINE_AUDIT_WRITE_FAILED") from exc
        persisted_resolver = getattr(self._assets, "is_outline_persisted", None)
        target_was_persisted = (
            bool(persisted_resolver(target_kind=target_kind, target_id=target_id))
            if callable(persisted_resolver)
            else True
        )
        expected_post_write_version = (
            int(base_revision) + 1 if target_was_persisted else int(base_revision)
        )
        metadata.update(
            {
                "apply_idempotency_key_hash": key_hash,
                "apply_request_hash": request_hash,
                "apply_state": "writing",
                "target_was_persisted": target_was_persisted,
                "expected_post_write_version": expected_post_write_version,
                "conflict_guard_record_id": guard.record_id,
            }
        )
        suggestion = self._suggestions.save(
            suggestion.model_copy(update={"metadata": metadata, "updated_at": datetime.now(UTC).isoformat()})
        )

        try:
            saved = self._save(
                target_kind=target_kind,
                target_id=target_id,
                content_text=str(payload.get("proposed_content_text") or ""),
                content_tree_json=payload.get("proposed_content_tree_json"),
                expected_version=int(base_revision),
                expected_content_hash=target_hash,
            )
        except ValueError as exc:
            if str(exc) == "asset_version_conflict":
                self._record_guard(
                    work_id=suggestion.work_id,
                    chapter_id=suggestion.chapter_id,
                    suggestion_id=suggestion_id,
                    target_kind=target_kind,
                    target_id=target_id,
                    target_revision=int(base_revision),
                    blocking=True,
                    reason_code="P2_OUTLINE_TARGET_CONFLICT",
                    request_id=request_id,
                    trace_id=trace_id,
                )
                raise ValueError("P2_OUTLINE_TARGET_CONFLICT") from exc
            raise

        result = OutlineApplyResult(
            success=True,
            suggestion_id=suggestion_id,
            target_kind=target_kind,
            target_id=target_id,
            previous_version=int(base_revision),
            new_version=int(saved.version),
            result_ref=f"{target_kind}:{target_id}:v{int(saved.version)}",
        )
        completed = self._persist_completed_suggestion(
            suggestion,
            result=result,
            user_id=user_id,
            key_hash=key_hash,
            request_hash=request_hash,
            guard_record_id=guard.record_id,
            resolution_pending=True,
            request_id=request_id,
            trace_id=trace_id,
        )
        if completed is not None:
            self._compensate_resolution(
                completed,
                result=result,
                user_id=user_id,
                user_action=user_action,
                key_hash=key_hash,
                request_hash=request_hash,
                request_id=request_id,
                trace_id=trace_id,
            )
        return result

    def _persist_completed_suggestion(
        self,
        suggestion,
        *,
        result: OutlineApplyResult,
        user_id: str,
        key_hash: str,
        request_hash: str,
        guard_record_id: str,
        resolution_pending: bool,
        request_id: str,
        trace_id: str,
    ):
        now = datetime.now(UTC).isoformat()
        action = suggestion.action.model_copy(
            update={
                "action_type": AISuggestionActionType.APPLY_OUTLINE,
                "action_payload_ref": result.result_ref,
                "action_status": "completed",
            }
        )
        metadata = dict(suggestion.metadata or {})
        metadata.update(
            {
                "apply_idempotency_key_hash": key_hash,
                "apply_request_hash": request_hash,
                "apply_state": "completed",
                "apply_result": result.to_dict(),
                "conflict_guard_record_id": guard_record_id,
                "conflict_guard_resolution_pending": resolution_pending,
            }
        )
        completed = suggestion.model_copy(
            update={
                "status": AISuggestionStatus.CONVERTED,
                "decision": AISuggestionDecisionType.CONVERTED,
                "decided_by": user_id,
                "decision_log": AISuggestionDecision(
                    suggestion_id=suggestion.suggestion_id,
                    decision=AISuggestionDecisionType.CONVERTED,
                    decided_by=user_id,
                    decision_note="outline_apply_completed",
                    decided_at=now,
                    request_id=request_id,
                    trace_id=trace_id,
                ),
                "action": action,
                "metadata": metadata,
                "updated_at": now,
            }
        )
        for _ in range(2):
            try:
                return self._suggestions.save(completed)
            except Exception:
                continue
        return None

    def _recover_written_apply(
        self,
        suggestion,
        *,
        user_id: str,
        user_action: bool,
        key_hash: str,
        request_hash: str,
        request_id: str,
        trace_id: str,
    ) -> OutlineApplyResult | None:
        payload = self._validate_payload(suggestion)
        target_kind = str(payload.get("target_kind") or "")
        target_id = str(payload.get("target_id") or "")
        previous_version = int(payload.get("target_revision") or 0)
        current = self._get_current(target_kind, target_id)
        persisted_resolver = getattr(self._assets, "is_outline_persisted", None)
        current_is_persisted = (
            bool(persisted_resolver(target_kind=target_kind, target_id=target_id))
            if callable(persisted_resolver)
            else True
        )
        current_version = int(current.version)
        expected_post_write_version = suggestion.metadata.get("expected_post_write_version")
        target_tree = validate_content_tree_json(payload.get("target_content_tree_json"))
        proposed_tree = validate_content_tree_json(payload.get("proposed_content_tree_json"))
        proposed_matches_baseline = (
            str(payload.get("proposed_content_text") or "") == str(payload.get("target_content_text") or "")
            and proposed_tree == target_tree
        )
        if expected_post_write_version is not None:
            version_matches = current_version == int(expected_post_write_version)
        else:
            version_matches = current_version in {previous_version, previous_version + 1}
            if current_version == previous_version and proposed_matches_baseline:
                version_matches = False
        if (
            not current_is_persisted
            or not version_matches
            or str(current.content_text or "") != str(payload.get("proposed_content_text") or "")
            or validate_content_tree_json(current.content_tree_json) != proposed_tree
        ):
            return None
        result = OutlineApplyResult(
            success=True,
            suggestion_id=suggestion.suggestion_id,
            target_kind=target_kind,
            target_id=target_id,
            previous_version=previous_version,
            new_version=int(current.version),
            result_ref=f"{target_kind}:{target_id}:v{int(current.version)}",
        )
        guard_record_id = str(suggestion.metadata.get("conflict_guard_record_id") or "")
        completed = self._persist_completed_suggestion(
            suggestion,
            result=result,
            user_id=user_id,
            key_hash=key_hash,
            request_hash=request_hash,
            guard_record_id=guard_record_id,
            resolution_pending=True,
            request_id=request_id,
            trace_id=trace_id,
        )
        if completed is not None:
            self._compensate_resolution(
                completed,
                result=result,
                user_id=user_id,
                user_action=user_action,
                key_hash=key_hash,
                request_hash=request_hash,
                request_id=request_id,
                trace_id=trace_id,
            )
        return result

    def _compensate_resolution(
        self,
        suggestion,
        *,
        result: OutlineApplyResult,
        user_id: str,
        user_action: bool,
        key_hash: str,
        request_hash: str,
        request_id: str,
        trace_id: str,
    ) -> None:
        try:
            persisted = self._suggestions.get(suggestion.suggestion_id)
        except Exception:
            return
        metadata = dict(persisted.metadata or {})
        if (
            not metadata.get("conflict_guard_resolution_pending")
            or metadata.get("apply_idempotency_key_hash") != key_hash
            or metadata.get("apply_request_hash") != request_hash
            or metadata.get("apply_result") != result.to_dict()
        ):
            return
        suggestion = persisted
        guard_record_id = str(metadata.get("conflict_guard_record_id") or "")
        if not guard_record_id:
            return
        try:
            payload = self._validate_payload(suggestion)
            self._record_apply_trace(
                suggestion,
                event_type="checkpoint_saved",
                target_revision=int(result.new_version),
                target_hash=outline_content_hash(
                    str(payload.get("proposed_content_text") or ""),
                    payload.get("proposed_content_tree_json"),
                ),
                result_ref=result.result_ref,
                high_risk=False,
            )
        except Exception:
            return
        for _ in range(2):
            try:
                self._conflict_guard.resolve_outline_apply(
                    guard_record_id,
                    user_id=user_id,
                    user_action=user_action,
                    request_id=request_id,
                    trace_id=trace_id,
                )
                self._persist_completed_suggestion(
                    suggestion,
                    result=result,
                    user_id=user_id,
                    key_hash=key_hash,
                    request_hash=request_hash,
                    guard_record_id=guard_record_id,
                    resolution_pending=False,
                    request_id=request_id,
                    trace_id=trace_id,
                )
                return
            except Exception:
                continue

    def _record_apply_trace(
        self,
        suggestion,
        *,
        event_type: str,
        target_revision: int,
        target_hash: str,
        result_ref: str = "",
        high_risk: bool,
    ) -> None:
        if self._trace_service is None:
            raise ValueError("P2_OUTLINE_AUDIT_WRITE_FAILED")
        trace_id = suggestion.trace_id or f"trace_outline_apply_{suggestion.suggestion_id}"
        trace = self._trace_service.ensure_operation_trace(
            trace_id=trace_id,
            work_id=suggestion.work_id,
            chapter_id=suggestion.chapter_id,
            operation_ref=suggestion.suggestion_id,
            workflow_type="outline_assist",
        )
        if trace is None:
            raise ValueError("P2_OUTLINE_AUDIT_WRITE_FAILED")
        event = self._trace_service.record_audit_event(
            trace_id=trace_id,
            session_id=suggestion.suggestion_id,
            step_id="outline_suggestion_apply",
            event_type=event_type,
            summary=suggestion.suggestion_id,
            payload_digest={
                "suggestion_id": suggestion.suggestion_id,
                "target_kind": suggestion.target.target_type,
                "target_id": suggestion.target.target_ref_id,
                "target_revision": target_revision,
                "target_content_hash": target_hash,
                "result_ref": result_ref,
            },
            high_risk_user_action=high_risk,
        )
        if event is None:
            raise ValueError("P2_OUTLINE_AUDIT_WRITE_FAILED")
        if result_ref:
            finished = self._trace_service.finish_operation_trace(
                trace_id,
                status=AgentTraceStatus.COMPLETED,
                result_ref=result_ref,
            )
            if finished is None:
                raise ValueError("P2_OUTLINE_AUDIT_WRITE_FAILED")

    def _record_guard(self, **kwargs):
        try:
            return self._conflict_guard.record_outline_apply_check(**kwargs)
        except Exception as exc:
            raise ValueError("P2_OUTLINE_CONFLICT_CHECK_FAILED") from exc

    @staticmethod
    def _validate_payload(suggestion) -> dict[str, object]:  # noqa: ANN001
        model_by_type = {
            AISuggestionType.OUTLINE_POLISH: OutlinePolishPayload,
            AISuggestionType.OUTLINE_EXPAND: OutlineExpandPayload,
            AISuggestionType.CHAPTER_OUTLINE_DETAIL: ChapterOutlineDetailPayload,
        }
        try:
            model = model_by_type[suggestion.suggestion_type].model_validate(suggestion.payload)
            payload = model.model_dump()
            payload["target_content_tree_json"] = validate_content_tree_json(payload.get("target_content_tree_json"))
            payload["proposed_content_tree_json"] = validate_content_tree_json(payload.get("proposed_content_tree_json"))
            if not preserves_outline_node_contract(
                payload["target_content_tree_json"],
                payload["proposed_content_tree_json"],
            ):
                raise ValueError("outline_tree_contract_changed")
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("P2_OUTLINE_SUGGESTION_TYPE_UNSUPPORTED") from exc
        target_kind = str(payload.get("target_kind") or "")
        target_id = str(payload.get("target_id") or "")
        target_revision = payload.get("target_revision")
        target_hash = str(payload.get("target_content_hash") or "")
        metadata_hash = str(suggestion.metadata.get("target_content_hash") or "")
        if target_kind == "selection":
            if (
                suggestion.target.target_type != "selection"
                or suggestion.target.target_ref_id
                or target_id
                or target_revision is not None
            ):
                raise ValueError("P2_OUTLINE_TARGET_CONFLICT")
            return payload
        if (
            target_kind != suggestion.target.target_type
            or target_id != suggestion.target.target_ref_id
            or str(target_revision) != str(suggestion.target.target_snapshot_ref)
            or not metadata_hash
            or target_hash != metadata_hash
            or outline_content_hash(
                str(payload.get("target_content_text") or ""),
                payload.get("target_content_tree_json"),
            )
            != target_hash
        ):
            raise ValueError("P2_OUTLINE_TARGET_CONFLICT")
        return payload

    def _get_current(self, target_kind: str, target_id: str):
        try:
            if target_kind == "work_outline":
                return self._assets.get_work_outline(target_id)
            return self._assets.get_chapter_outline(target_id)
        except ValueError as exc:
            raise ValueError("P2_OUTLINE_TARGET_NOT_FOUND") from exc

    def _save(
        self,
        *,
        target_kind: str,
        target_id: str,
        content_text: str,
        content_tree_json,
        expected_version: int,
        expected_content_hash: str,
    ):
        if target_kind == "work_outline":
            return self._assets.save_work_outline(
                target_id,
                content_text=content_text,
                content_tree_json=content_tree_json,
                expected_version=expected_version,
                expected_content_hash=expected_content_hash,
                force_override=False,
            )
        return self._assets.save_chapter_outline(
            target_id,
            content_text=content_text,
            content_tree_json=content_tree_json,
            expected_version=expected_version,
            expected_content_hash=expected_content_hash,
            force_override=False,
        )

    @staticmethod
    def _require_gate(caller_type: str, user_action: bool, user_id: str, idempotency_key: str, confirm_apply: bool) -> None:
        if caller_type != "user_action":
            raise ValueError("P2_CALLER_FORBIDDEN")
        if not user_action or not str(user_id or "").strip():
            raise ValueError("P2_USER_ACTION_REQUIRED")
        if not str(idempotency_key or "").strip():
            raise ValueError("P2_IDEMPOTENCY_KEY_REQUIRED")
        if not confirm_apply:
            raise ValueError("P2_OUTLINE_APPLY_CONFIRMATION_REQUIRED")
