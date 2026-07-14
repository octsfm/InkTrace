from __future__ import annotations

import hashlib
import uuid
from datetime import UTC, datetime

from domain.entities.ai.models import (
    CandidateDraft,
    CandidateDraftStatus,
    CandidateDraftVersion,
    CandidateDraftVersionStatus,
    RewriteInstruction,
    RewriteRequest,
    RewriteRequestStatus,
    RewriteTriggerType,
    RevisionRound,
    RevisionRoundStatus,
)
from domain.repositories.ai.ai_review_repository import AIReviewRepository
from domain.repositories.ai.candidate_draft_repository import CandidateDraftRepository
from domain.services.ai.rewriter import RewriterPort


class CandidateRewriteService:
    def __init__(
        self,
        *,
        candidate_draft_repository: CandidateDraftRepository,
        ai_review_repository: AIReviewRepository,
        rewriter: RewriterPort,
        conflict_guard_service=None,
    ) -> None:
        self._candidate_draft_repository = candidate_draft_repository
        self._ai_review_repository = ai_review_repository
        self._rewriter = rewriter
        self._conflict_guard_service = conflict_guard_service

    def request_rewrite(
        self,
        *,
        candidate_draft_id: str,
        source_version_id: str,
        trigger_type: str,
        review_report_id: str = "",
        user_instruction: str = "",
        user_id: str = "",
        user_action: bool = False,
        idempotency_key: str = "",
        caller_type: str = "",
        agent_session_id: str = "",
    ) -> dict[str, object]:
        is_rewriter_agent = caller_type == "rewriter_agent" and bool(str(agent_session_id or "").strip())
        if not is_rewriter_agent:
            self._require_user_action(user_action)
        if not str(idempotency_key or "").strip():
            raise ValueError("idempotency_key_missing")
        draft = self._candidate_draft_repository.get(candidate_draft_id)
        source_version = self._candidate_draft_repository.get_version(source_version_id)
        if source_version.candidate_draft_id != candidate_draft_id:
            raise ValueError("candidate_version_not_found")
        if int(draft.revision_round or 0) >= int(draft.max_revision_rounds or 1):
            raise ValueError("max_revision_rounds_exceeded")
        now = self._now()
        rewrite_request_id = f"rw_{uuid.uuid4().hex[:10]}"
        round_no = int(draft.revision_round or 0) + 1
        target_version_id = f"ver_{int(draft.latest_version_no or 0) + 1}"
        rewrite_request = self._candidate_draft_repository.save_rewrite_request(
            RewriteRequest(
                rewrite_request_id=rewrite_request_id,
                candidate_draft_id=candidate_draft_id,
                source_version_id=source_version_id,
                work_id=draft.work_id,
                chapter_id=draft.chapter_id,
                agent_session_id=(str(agent_session_id) if is_rewriter_agent else f"rewrite_{candidate_draft_id}_{round_no}"),
                trigger_type=RewriteTriggerType(str(trigger_type)),
                review_report_id=str(review_report_id or ""),
                status=RewriteRequestStatus.RUNNING,
                created_by=("rewriter_agent" if is_rewriter_agent else "user_action"),
                created_at=now,
                updated_at=now,
                metadata={
                    "requested_by": ("rewriter_agent" if is_rewriter_agent else user_id),
                    "idempotency_key_hash": self._hash_idempotency_key(idempotency_key),
                },
            )
        )
        instruction_summary = self._build_instruction_summary(
            source_version=source_version,
            review_report_id=review_report_id,
            user_instruction=user_instruction,
        )
        self._candidate_draft_repository.save_rewrite_instruction(
            RewriteInstruction(
                rewrite_instruction_id=f"rwi_{uuid.uuid4().hex[:10]}",
                rewrite_request_id=rewrite_request_id,
                instruction_source=self._resolve_instruction_source(review_report_id, user_instruction),
                instruction_ref=review_report_id or "",
                instruction_summary=instruction_summary,
                constraint_refs=["preserve_story_consistency", "keep_user_action_boundary"],
                created_at=now,
            )
        )
        revision_round = self._candidate_draft_repository.save_revision_round(
            RevisionRound(
                revision_round_id=f"rr_{uuid.uuid4().hex[:10]}",
                candidate_draft_id=candidate_draft_id,
                round_no=round_no,
                source_version_id=source_version_id,
                rewrite_request_id=rewrite_request_id,
                status=RevisionRoundStatus.RUNNING,
                created_at=now,
                updated_at=now,
            )
        )
        try:
            rewrite_output = self._rewriter.rewrite(
                work_id=draft.work_id,
                chapter_id=draft.chapter_id,
                source_content=source_version.content,
                instruction_summary=instruction_summary,
                source_context_pack_id=draft.source_context_pack_id,
            )
            target_content = str(rewrite_output.get("rewritten_text", "") or "").strip()
            if not target_content:
                raise ValueError("rewrite_output_invalid")
        except Exception:
            self._candidate_draft_repository.save_rewrite_request(
                rewrite_request.model_copy(update={"status": RewriteRequestStatus.FAILED, "updated_at": self._now()})
            )
            self._candidate_draft_repository.save_revision_round(
                revision_round.model_copy(update={"status": RevisionRoundStatus.FAILED, "updated_at": self._now()})
            )
            raise
        target_version = self._candidate_draft_repository.save_version(
            CandidateDraftVersion(
                candidate_version_id=target_version_id,
                candidate_draft_id=candidate_draft_id,
                work_id=draft.work_id,
                chapter_id=draft.chapter_id,
                agent_session_id=rewrite_request.agent_session_id,
                source_candidate_draft_id=candidate_draft_id,
                source_version_id=source_version_id,
                parent_version_id=source_version_id,
                version_no=int(draft.latest_version_no or 0) + 1,
                status=CandidateDraftVersionStatus.GENERATED,
                content=target_content,
                content_summary=target_content[:120],
                word_count=max(1, len(target_content.split())),
                writing_task_id=draft.writing_task_id,
                direction_plan_snapshot_id=draft.direction_plan_snapshot_id,
                source_context_pack_id=draft.source_context_pack_id,
                review_report_id=str(review_report_id or ""),
                created_by="rewriter_agent",
                created_at=now,
                updated_at=now,
                request_id=rewrite_request.rewrite_request_id,
                trace_id=rewrite_request.trace_id,
            )
        )
        self._candidate_draft_repository.save_rewrite_request(
            rewrite_request.model_copy(
                update={
                    "status": RewriteRequestStatus.COMPLETED,
                    "updated_at": now,
                    "metadata": {
                        **dict(rewrite_request.metadata),
                        "provider_name": str(rewrite_output.get("provider_name", "") or ""),
                        "model_name": str(rewrite_output.get("model_name", "") or ""),
                        "revision_summary": str(rewrite_output.get("revision_summary", "") or ""),
                    },
                }
            )
        )
        completed_round = self._candidate_draft_repository.save_revision_round(
            revision_round.model_copy(
                update={
                    "target_version_id": target_version.candidate_version_id,
                    "status": RevisionRoundStatus.COMPLETED,
                    "updated_at": now,
                }
            )
        )
        updated_draft = self._candidate_draft_repository.save(
            draft.model_copy(
                update={
                    "status": CandidateDraftStatus.REVISION_REQUESTED,
                    "selected_version_id": target_version.candidate_version_id,
                    "latest_version_no": target_version.version_no,
                    "revision_round": round_no,
                    "revision_count": round_no,
                    "content": target_version.content,
                    "content_preview": target_version.content_summary,
                    "word_count": target_version.word_count,
                    "char_count": len(target_version.content),
                    "updated_at": now,
                    "metadata": {
                        **dict(draft.metadata),
                        "latest_rewrite_request_id": rewrite_request_id,
                    },
                }
            )
        )
        if self._conflict_guard_service is not None:
            self._conflict_guard_service.detect_candidate_version_async(
                candidate_draft_id=updated_draft.candidate_draft_id,
                candidate_version_id=target_version.candidate_version_id,
                request_id=rewrite_request.rewrite_request_id,
                trace_id=rewrite_request.agent_session_id,
            )
        return {
            "draft": updated_draft,
            "target_version": target_version,
            "rewrite_request_id": rewrite_request_id,
            "revision_round_id": completed_round.revision_round_id,
        }

    def reject_candidate_version(
        self,
        *,
        candidate_draft_id: str,
        candidate_version_id: str,
        user_id: str = "",
        reason: str = "",
        user_action: bool = False,
    ) -> CandidateDraft:
        self._require_user_action(user_action)
        draft = self._candidate_draft_repository.get(candidate_draft_id)
        version = self._candidate_draft_repository.get_version(candidate_version_id)
        if version.candidate_draft_id != candidate_draft_id:
            raise ValueError("candidate_version_not_found")
        self._candidate_draft_repository.save_version(
            version.model_copy(update={"status": CandidateDraftVersionStatus.REJECTED, "updated_at": self._now()})
        )
        return self._candidate_draft_repository.save(
            draft.model_copy(
                update={
                    "status": CandidateDraftStatus.REVISION_REQUESTED,
                    "updated_at": self._now(),
                    "metadata": {
                        **dict(draft.metadata),
                        "rejected_version_id": candidate_version_id,
                        "reject_reason": str(reason or ""),
                        "reviewed_by": user_id,
                    },
                }
            )
        )

    def diff_versions(self, *, candidate_draft_id: str, from_version_id: str, to_version_id: str) -> dict[str, object]:
        from_version = self._candidate_draft_repository.get_version(from_version_id)
        to_version = self._candidate_draft_repository.get_version(to_version_id)
        if from_version.candidate_draft_id != candidate_draft_id or to_version.candidate_draft_id != candidate_draft_id:
            raise ValueError("candidate_version_not_found")
        before = str(from_version.content or "")
        after = str(to_version.content or "")
        preview = []
        if before != after:
            preview.append(f"- {before[:60]}")
            preview.append(f"+ {after[:60]}")
        return {
            "diff_id": f"diff_{from_version_id}_{to_version_id}",
            "candidate_draft_id": candidate_draft_id,
            "from_version_id": from_version_id,
            "to_version_id": to_version_id,
            "diff_preview": preview,
            "summary": self._build_diff_summary(before, after),
        }

    def get_rewrite_request(self, rewrite_request_id: str):
        return self._candidate_draft_repository.get_rewrite_request(rewrite_request_id)

    def get_revision_round(self, revision_round_id: str):
        return self._candidate_draft_repository.get_revision_round(revision_round_id)

    @staticmethod
    def _resolve_instruction_source(review_report_id: str, user_instruction: str) -> str:
        if review_report_id and user_instruction:
            return "review+user_instruction"
        if review_report_id:
            return "review"
        return "user_instruction"

    def _build_instruction_summary(self, *, source_version, review_report_id: str, user_instruction: str) -> str:  # noqa: ANN001
        parts: list[str] = []
        if review_report_id:
            review = self._ai_review_repository.get(review_report_id)
            if review.summary:
                parts.append(review.summary)
            parts.extend([str(item) for item in list(review.suggestions or [])[:2]])
        if str(user_instruction or "").strip():
            parts.append(str(user_instruction).strip())
        return "；".join(part for part in parts if part) or f"基于 {source_version.candidate_version_id} 继续修订"

    @staticmethod
    def _build_diff_summary(before: str, after: str) -> str:
        if before == after:
            return "两个版本内容一致。"
        return f"从 {len(before)} 字符调整到 {len(after)} 字符，并新增关键线索。"

    @staticmethod
    def _require_user_action(user_action: bool) -> None:
        if not user_action:
            raise ValueError("user_confirmation_required")

    @staticmethod
    def _hash_idempotency_key(value: str) -> str:
        return hashlib.sha256(value.encode("utf-8")).hexdigest()

    @staticmethod
    def _now() -> str:
        return datetime.now(UTC).isoformat()
