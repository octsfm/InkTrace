from __future__ import annotations

import uuid
from datetime import UTC, datetime

from domain.entities.ai.models import (
    AISuggestion,
    AISuggestionAction,
    AISuggestionActionType,
    AISuggestionPriority,
    AISuggestionSeverity,
    AISuggestionSource,
    AISuggestionStatus,
    AISuggestionTarget,
    AISuggestionType,
    ConflictDecisionType,
    ConflictDetectionResult,
    ConflictDetectionStatus,
    ConflictGuardDecision,
    ConflictGuardRecord,
    ConflictRecordStatus,
    ConflictSeverity,
    ConflictType,
)
from domain.repositories.ai.conflict_guard_repository import ConflictGuardRepository
from domain.repositories.ai.ai_review_repository import AIReviewRepository
from domain.repositories.ai.candidate_draft_repository import CandidateDraftRepository
from domain.repositories.ai.direction_plan_repository import DirectionPlanRepository


class ConflictGuardService:
    def __init__(
        self,
        *,
        conflict_guard_repository: ConflictGuardRepository,
        candidate_draft_repository: CandidateDraftRepository,
        chapter_service,
        ai_suggestion_repository=None,
        direction_plan_repository: DirectionPlanRepository | None = None,
        ai_review_repository: AIReviewRepository | None = None,
        trace_service=None,
        allow_override_blocking: bool = False,
    ) -> None:
        self._conflict_guard_repository = conflict_guard_repository
        self._candidate_draft_repository = candidate_draft_repository
        self._chapter_service = chapter_service
        self._ai_suggestion_repository = ai_suggestion_repository
        self._direction_plan_repository = direction_plan_repository
        self._ai_review_repository = ai_review_repository
        self._trace_service = trace_service
        self._allow_override_blocking = allow_override_blocking

    def precheck_apply_conflicts(
        self,
        *,
        candidate_draft_id: str,
        candidate_version_id: str = "",
        expected_chapter_version: int,
        request_id: str = "",
        trace_id: str = "",
    ) -> ConflictDetectionResult:
        draft = self._candidate_draft_repository.get(candidate_draft_id)
        version_id = str(candidate_version_id or draft.accepted_version_id or draft.selected_version_id or "")
        chapter = self._get_chapter(draft.work_id, draft.chapter_id)
        version = self._candidate_draft_repository.get_version(version_id) if version_id else None
        started_at = self._now()
        record_refs: list[str] = []
        blocking_count = 0
        warning_count = 0
        info_count = 0

        if chapter.version != int(expected_chapter_version):
            record = ConflictGuardRecord(
                record_id=f"cgr_{uuid.uuid4().hex[:10]}",
                work_id=draft.work_id,
                chapter_id=draft.chapter_id,
                candidate_draft_id=draft.candidate_draft_id,
                candidate_version_id=version_id,
                agent_session_id=draft.agent_session_id,
                source_type="apply_precheck",
                source_ref_id=version_id or draft.candidate_draft_id,
                target_type="chapter",
                target_ref_id=draft.chapter_id,
                conflict_type=ConflictType.APPLY_VERSION_CONFLICT,
                severity=ConflictSeverity.BLOCKING,
                status=ConflictRecordStatus.DETECTED,
                title="章节版本已变化",
                summary="当前章节版本与 apply 请求的目标版本不一致，已阻止 apply。",
                evidence_refs=[
                    f"expected_chapter_version:{expected_chapter_version}",
                    f"actual_chapter_version:{chapter.version}",
                ],
                suggested_action_refs=["refresh_chapter_and_retry_apply"],
                resolution_status="unresolved",
                created_by="conflict_guard",
                created_at=started_at,
                updated_at=started_at,
                request_id=request_id,
                trace_id=trace_id,
            )
            self._conflict_guard_repository.save_record(record)
            record_refs.append(record.record_id)
            blocking_count += 1

        if version is not None and (
            str(getattr(version, "stale_status", "") or "") != "fresh"
            or list(getattr(version, "warning_codes", []) or [])
        ):
            warning_codes = list(getattr(version, "warning_codes", []) or [])
            warning = ConflictGuardRecord(
                record_id=f"cgr_{uuid.uuid4().hex[:10]}",
                work_id=draft.work_id,
                chapter_id=draft.chapter_id,
                candidate_draft_id=draft.candidate_draft_id,
                candidate_version_id=version_id,
                agent_session_id=draft.agent_session_id,
                source_type="candidate_version_state",
                source_ref_id=version_id or draft.candidate_draft_id,
                target_type="candidate_draft_version",
                target_ref_id=version_id or draft.candidate_draft_id,
                conflict_type=ConflictType.CANDIDATE_VERSION_CONFLICT,
                severity=ConflictSeverity.WARNING,
                status=ConflictRecordStatus.DETECTED,
                title="检测结果可能不完整",
                summary="当前版本依赖的上下文存在降级或过期风险，继续 apply 代表已知风险。",
                evidence_refs=[f"stale_status:{getattr(version, 'stale_status', 'fresh')}"] + [f"warning_code:{code}" for code in warning_codes],
                suggested_action_refs=["open_conflict_resolution", "review_context_before_apply"],
                resolution_status="unresolved",
                warning_codes=warning_codes,
                created_by="conflict_guard",
                created_at=started_at,
                updated_at=started_at,
                request_id=request_id,
                trace_id=trace_id,
            )
            self._conflict_guard_repository.save_record(warning)
            record_refs.append(warning.record_id)
            warning_count += 1
            self._create_conflict_resolution_suggestion(warning)

        task_conflicts = self._detect_direction_plan_conflicts(
            draft=draft,
            version=version,
            version_id=version_id,
            request_id=request_id,
            trace_id=trace_id,
            created_at=started_at,
        )
        if task_conflicts:
            for task_conflict in task_conflicts:
                self._conflict_guard_repository.save_record(task_conflict)
                record_refs.append(task_conflict.record_id)
                warning_count += 1
                self._create_conflict_resolution_suggestion(task_conflict)
        elif version is not None and blocking_count == 0 and warning_count == 0:
            info = ConflictGuardRecord(
                record_id=f"cgr_{uuid.uuid4().hex[:10]}",
                work_id=draft.work_id,
                chapter_id=draft.chapter_id,
                candidate_draft_id=draft.candidate_draft_id,
                candidate_version_id=version_id,
                agent_session_id=draft.agent_session_id,
                source_type="candidate_version_state",
                source_ref_id=version_id or draft.candidate_draft_id,
                target_type="candidate_draft_version",
                target_ref_id=version_id or draft.candidate_draft_id,
                conflict_type=ConflictType.CANDIDATE_VERSION_CONFLICT,
                severity=ConflictSeverity.INFO,
                status=ConflictRecordStatus.DETECTED,
                title="未发现阻断性冲突",
                summary="当前版本未发现阻断性冲突，可继续人工判断。",
                evidence_refs=[f"stale_status:{getattr(version, 'stale_status', 'fresh')}"],
                suggested_action_refs=["open_conflict_resolution"],
                resolution_status="unresolved",
                warning_codes=[],
                created_by="conflict_guard",
                created_at=started_at,
                updated_at=started_at,
                request_id=request_id,
                trace_id=trace_id,
            )
            self._conflict_guard_repository.save_record(info)
            record_refs.append(info.record_id)
            info_count += 1

        result = ConflictDetectionResult(
            result_id=f"cgrs_{uuid.uuid4().hex[:10]}",
            work_id=draft.work_id,
            chapter_id=draft.chapter_id,
            candidate_version_id=version_id,
            total_conflicts=len(record_refs),
            blocking_count=blocking_count,
            warning_count=warning_count,
            info_count=info_count,
            record_refs=record_refs,
            detection_status=ConflictDetectionStatus.COMPLETED,
            detection_started_at=started_at,
            detection_finished_at=self._now(),
        )
        self._conflict_guard_repository.save_result(result)
        return result

    def detect_candidate_version_async(
        self,
        *,
        candidate_draft_id: str,
        candidate_version_id: str = "",
        request_id: str = "",
        trace_id: str = "",
    ) -> ConflictDetectionResult:
        try:
            draft = self._candidate_draft_repository.get(candidate_draft_id)
            chapter = self._get_chapter(draft.work_id, draft.chapter_id)
            return self.precheck_apply_conflicts(
                candidate_draft_id=candidate_draft_id,
                candidate_version_id=candidate_version_id,
                expected_chapter_version=chapter.version,
                request_id=request_id,
                trace_id=trace_id,
            )
        except Exception as exc:
            return self.record_async_detection_failure(
                candidate_draft_id=candidate_draft_id,
                candidate_version_id=candidate_version_id,
                error_code=exc.__class__.__name__.lower() or "async_conflict_detection_failed",
                safe_message="检测结果可能不完整",
                request_id=request_id,
                trace_id=trace_id,
            )

    def detect_review_conflicts(
        self,
        *,
        review_id: str,
        request_id: str = "",
        trace_id: str = "",
    ) -> ConflictDetectionResult:
        if self._ai_review_repository is None:
            raise ValueError("ai_review_repository_not_configured")
        try:
            review = self._ai_review_repository.get(review_id)
            draft = self._candidate_draft_repository.get(review.candidate_draft_id)
            version_id = str(draft.selected_version_id or draft.accepted_version_id or "")
            created_at = self._now()
            record_refs: list[str] = []
            warning_count = 0
            for issue in list(review.issues or []):
                record = self._map_review_issue_to_conflict_record(
                    draft=draft,
                    version_id=version_id,
                    review_id=review.review_id,
                    issue=issue,
                    created_at=created_at,
                    request_id=request_id,
                    trace_id=trace_id,
                )
                if record is None:
                    continue
                self._conflict_guard_repository.save_record(record)
                self._create_conflict_resolution_suggestion(record)
                record_refs.append(record.record_id)
                warning_count += 1
            result = ConflictDetectionResult(
                result_id=f"cgrs_{uuid.uuid4().hex[:10]}",
                work_id=review.work_id,
                chapter_id=review.chapter_id,
                candidate_version_id=version_id,
                total_conflicts=len(record_refs),
                blocking_count=0,
                warning_count=warning_count,
                info_count=0,
                record_refs=record_refs,
                detection_status=ConflictDetectionStatus.COMPLETED,
                detection_started_at=created_at,
                detection_finished_at=self._now(),
            )
            self._conflict_guard_repository.save_result(result)
            return result
        except Exception as exc:
            draft_id = ""
            try:
                review = self._ai_review_repository.get(review_id)
                draft_id = review.candidate_draft_id
            except Exception:
                draft_id = ""
            return self.record_async_detection_failure(
                candidate_draft_id=draft_id,
                candidate_version_id="",
                error_code=exc.__class__.__name__.lower() or "review_conflict_detection_failed",
                safe_message="检测结果可能不完整",
                request_id=request_id or review_id,
                trace_id=trace_id,
            )

    def record_async_detection_failure(
        self,
        *,
        candidate_draft_id: str,
        candidate_version_id: str = "",
        error_code: str,
        safe_message: str,
        request_id: str = "",
        trace_id: str = "",
    ) -> ConflictDetectionResult:
        draft = self._candidate_draft_repository.get(candidate_draft_id)
        version_id = str(candidate_version_id or draft.selected_version_id or draft.accepted_version_id or "")
        now = self._now()
        record = ConflictGuardRecord(
            record_id=f"cgr_{uuid.uuid4().hex[:10]}",
            work_id=draft.work_id,
            chapter_id=draft.chapter_id,
            candidate_draft_id=draft.candidate_draft_id,
            candidate_version_id=version_id,
            agent_session_id=draft.agent_session_id,
            source_type="async_detection",
            source_ref_id=version_id or draft.candidate_draft_id,
            target_type="candidate_draft_version",
            target_ref_id=version_id or draft.candidate_draft_id,
            conflict_type=ConflictType.CANDIDATE_VERSION_CONFLICT,
            severity=ConflictSeverity.WARNING,
            status=ConflictRecordStatus.FAILED,
            title="检测失败",
            summary=safe_message,
            evidence_refs=[f"error_code:{error_code}"],
            suggested_action_refs=["retry_conflict_detection", "open_conflict_resolution"],
            resolution_status="unresolved",
            warning_codes=[error_code],
            created_by="conflict_guard",
            created_at=now,
            updated_at=now,
            request_id=request_id,
            trace_id=trace_id,
        )
        self._conflict_guard_repository.save_record(record)
        result = ConflictDetectionResult(
            result_id=f"cgrs_{uuid.uuid4().hex[:10]}",
            work_id=draft.work_id,
            chapter_id=draft.chapter_id,
            candidate_version_id=version_id,
            total_conflicts=1,
            blocking_count=0,
            warning_count=1,
            info_count=0,
            record_refs=[record.record_id],
            detection_status=ConflictDetectionStatus.FAILED,
            detection_started_at=now,
            detection_finished_at=now,
        )
        self._conflict_guard_repository.save_result(result)
        return result

    def list_records(
        self,
        *,
        work_id: str = "",
        chapter_id: str = "",
        candidate_draft_id: str = "",
        candidate_version_id: str = "",
    ) -> list[ConflictGuardRecord]:
        items = self._conflict_guard_repository.list_records(
            work_id=work_id,
            chapter_id=chapter_id,
            candidate_draft_id=candidate_draft_id,
            candidate_version_id=candidate_version_id,
        )
        shown: list[ConflictGuardRecord] = []
        for item in items:
            if item.status == ConflictRecordStatus.DETECTED:
                item = self._conflict_guard_repository.save_record(
                    item.model_copy(update={"status": ConflictRecordStatus.SHOWN, "updated_at": self._now()})
                )
            shown.append(item)
        return shown

    def get_record(self, record_id: str) -> ConflictGuardRecord:
        item = self._conflict_guard_repository.get_record(record_id)
        if item.status == ConflictRecordStatus.DETECTED:
            item = self._conflict_guard_repository.save_record(
                item.model_copy(update={"status": ConflictRecordStatus.SHOWN, "updated_at": self._now()})
            )
        return item

    def decide_record(
        self,
        record_id: str,
        *,
        decision: str,
        user_id: str,
        user_action: bool,
        request_id: str = "",
        trace_id: str = "",
        note: str = "",
    ) -> ConflictGuardRecord:
        if not user_action:
            raise ValueError("action_not_allowed")
        item = self._conflict_guard_repository.get_record(record_id)
        normalized = ConflictDecisionType(decision)
        if item.severity == ConflictSeverity.BLOCKING and normalized == ConflictDecisionType.DISMISSED:
            raise ValueError("blocking_conflict_unresolved")
        if normalized == ConflictDecisionType.OVERRIDDEN and (
            not self._allow_override_blocking
            or item.severity != ConflictSeverity.BLOCKING
            or item.conflict_type == ConflictType.APPLY_VERSION_CONFLICT
        ):
            raise ValueError("cannot_override_blocking")
        status_mapping = {
            ConflictDecisionType.ACKNOWLEDGED: ConflictRecordStatus.ACKNOWLEDGED,
            ConflictDecisionType.RESOLVED: ConflictRecordStatus.RESOLVED,
            ConflictDecisionType.DISMISSED: ConflictRecordStatus.DISMISSED,
            ConflictDecisionType.OVERRIDDEN: ConflictRecordStatus.OVERRIDDEN,
        }
        updated = item.model_copy(
            update={
                "status": status_mapping.get(normalized, item.status),
                "resolution_status": normalized.value,
                "resolved_by": user_id,
                "resolved_at": self._now(),
                "updated_at": self._now(),
            }
        )
        self._conflict_guard_repository.save_decision(
            ConflictGuardDecision(
                decision_id=f"cgd_{uuid.uuid4().hex[:10]}",
                record_id=record_id,
                decision=normalized,
                decided_by=user_id,
                decided_at=self._now(),
                decision_note=note,
                request_id=request_id,
                trace_id=trace_id,
            )
        )
        saved = self._conflict_guard_repository.save_record(updated)
        self._record_trace_decision(saved, decision=normalized, request_id=request_id, trace_id=trace_id)
        return saved

    def _record_trace_decision(
        self,
        record: ConflictGuardRecord,
        *,
        decision: ConflictDecisionType,
        request_id: str,
        trace_id: str,
    ) -> None:
        if self._trace_service is None or not str(trace_id or record.trace_id or "").strip():
            return
        event_type = {
            ConflictDecisionType.RESOLVED: "conflict_resolved",
            ConflictDecisionType.OVERRIDDEN: "conflict_overridden",
        }.get(decision)
        if not event_type:
            return
        self._trace_service.record_audit_event(
            trace_id=trace_id or record.trace_id,
            session_id=record.agent_session_id,
            step_id="",
            event_type=event_type,
            summary=record.record_id,
            payload_digest={
                "record_id": record.record_id,
                "conflict_type": record.conflict_type.value,
                "decision": decision.value,
                "request_id": request_id,
            },
            high_risk_user_action=True,
        )

    def _get_chapter(self, work_id: str, chapter_id: str):
        chapters = self._chapter_service.list_chapters(work_id)
        for chapter in chapters:
            if chapter.id.value == chapter_id:
                return chapter
        raise ValueError("chapter_not_found")

    def _create_conflict_resolution_suggestion(self, record: ConflictGuardRecord) -> None:
        if self._ai_suggestion_repository is None:
            return
        suggestion = AISuggestion(
            suggestion_id=f"ais_{uuid.uuid4().hex[:10]}",
            work_id=record.work_id,
            chapter_id=record.chapter_id,
            agent_session_id=record.agent_session_id,
            source=AISuggestionSource(
                source_type="conflict_guard_record",
                source_ref_id=record.record_id,
                source_agent_type="conflict_guard",
                source_agent_session_id=record.agent_session_id,
                source_version_id=record.candidate_version_id,
            ),
            target=AISuggestionTarget(
                target_type="conflict_guard_record",
                target_ref_id=record.record_id,
                target_scope="record",
                target_snapshot_ref=record.candidate_version_id,
            ),
            suggestion_type=AISuggestionType.CONFLICT_RESOLUTION_SUGGESTION,
            severity=AISuggestionSeverity.HIGH if record.severity == ConflictSeverity.BLOCKING else AISuggestionSeverity.MEDIUM,
            priority=AISuggestionPriority.HIGH,
            title=record.title,
            summary=record.summary,
            rationale="ConflictGuard 检测到冲突，需要用户进入冲突处理流程。",
            proposed_action="打开冲突处理入口并记录用户决策",
            status=AISuggestionStatus.GENERATED,
            created_by="conflict_guard",
            created_at=self._now(),
            updated_at=self._now(),
            request_id=record.request_id,
            trace_id=record.trace_id,
            action=AISuggestionAction(
                action_type=AISuggestionActionType.OPEN_CONFLICT_RESOLUTION,
                requires_user_action=True,
                action_status="pending",
            ),
            metadata={"conflict_record_id": record.record_id, "candidate_draft_id": record.candidate_draft_id},
        )
        self._ai_suggestion_repository.save(suggestion)

    def _detect_direction_plan_conflicts(
        self,
        *,
        draft,
        version,
        version_id: str,
        request_id: str,
        trace_id: str,
        created_at: str,
    ) -> list[ConflictGuardRecord]:
        if self._direction_plan_repository is None or version is None or not draft.writing_task_id:
            return []
        try:
            task = self._direction_plan_repository.get_writing_task(draft.writing_task_id)
        except ValueError:
            return []
        content = str(getattr(version, "content", "") or "")
        records: list[ConflictGuardRecord] = []
        for item in list(getattr(task, "must_not_include", []) or []):
            forbidden = str(item or "").strip()
            if forbidden and forbidden in content:
                records.append(
                    ConflictGuardRecord(
                        record_id=f"cgr_{uuid.uuid4().hex[:10]}",
                        work_id=draft.work_id,
                        chapter_id=draft.chapter_id,
                        candidate_draft_id=draft.candidate_draft_id,
                        candidate_version_id=version_id,
                        agent_session_id=draft.agent_session_id,
                        source_type="writing_task_constraint",
                        source_ref_id=task.writing_task_id,
                        target_type="candidate_draft_version",
                        target_ref_id=version_id or draft.candidate_draft_id,
                        conflict_type=ConflictType.DIRECTION_PLAN_CONFLICT,
                        severity=ConflictSeverity.WARNING,
                        status=ConflictRecordStatus.DETECTED,
                        title="候选稿违反写作任务禁止项",
                        summary=f"候选稿命中了 WritingTask.must_not_include：{forbidden}",
                        evidence_refs=[f"must_not_include:{forbidden}", f"writing_task_id:{task.writing_task_id}"],
                        suggested_action_refs=["revise_candidate", "open_conflict_resolution"],
                        resolution_status="unresolved",
                        warning_codes=["writing_task_forbidden_item_hit"],
                        created_by="conflict_guard",
                        created_at=created_at,
                        updated_at=created_at,
                        request_id=request_id,
                        trace_id=trace_id,
                    )
                )
        for item in list(getattr(task, "must_include", []) or []):
            required = str(item or "").strip()
            if required and required not in content:
                records.append(
                    ConflictGuardRecord(
                        record_id=f"cgr_{uuid.uuid4().hex[:10]}",
                        work_id=draft.work_id,
                        chapter_id=draft.chapter_id,
                        candidate_draft_id=draft.candidate_draft_id,
                        candidate_version_id=version_id,
                        agent_session_id=draft.agent_session_id,
                        source_type="writing_task_constraint",
                        source_ref_id=task.writing_task_id,
                        target_type="candidate_draft_version",
                        target_ref_id=version_id or draft.candidate_draft_id,
                        conflict_type=ConflictType.DIRECTION_PLAN_CONFLICT,
                        severity=ConflictSeverity.WARNING,
                        status=ConflictRecordStatus.DETECTED,
                        title="候选稿缺少写作任务必含项",
                        summary=f"候选稿未覆盖 WritingTask.must_include：{required}",
                        evidence_refs=[f"must_include:{required}", f"writing_task_id:{task.writing_task_id}"],
                        suggested_action_refs=["revise_candidate", "open_conflict_resolution"],
                        resolution_status="unresolved",
                        warning_codes=["writing_task_required_item_missing"],
                        created_by="conflict_guard",
                        created_at=created_at,
                        updated_at=created_at,
                        request_id=request_id,
                        trace_id=trace_id,
                    )
                )
        for item in list(getattr(task, "required_beats", []) or []):
            beat = str(item or "").strip()
            if beat and beat not in content:
                records.append(
                    ConflictGuardRecord(
                        record_id=f"cgr_{uuid.uuid4().hex[:10]}",
                        work_id=draft.work_id,
                        chapter_id=draft.chapter_id,
                        candidate_draft_id=draft.candidate_draft_id,
                        candidate_version_id=version_id,
                        agent_session_id=draft.agent_session_id,
                        source_type="writing_task_constraint",
                        source_ref_id=task.writing_task_id,
                        target_type="candidate_draft_version",
                        target_ref_id=version_id or draft.candidate_draft_id,
                        conflict_type=ConflictType.DIRECTION_PLAN_CONFLICT,
                        severity=ConflictSeverity.WARNING,
                        status=ConflictRecordStatus.DETECTED,
                        title="候选稿缺少关键节拍",
                        summary=f"候选稿未覆盖 WritingTask.required_beats：{beat}",
                        evidence_refs=[f"required_beats:{beat}", f"writing_task_id:{task.writing_task_id}"],
                        suggested_action_refs=["revise_candidate", "open_conflict_resolution"],
                        resolution_status="unresolved",
                        warning_codes=["writing_task_required_beat_missing"],
                        created_by="conflict_guard",
                        created_at=created_at,
                        updated_at=created_at,
                        request_id=request_id,
                        trace_id=trace_id,
                    )
                )
        return records

    def _map_review_issue_to_conflict_record(
        self,
        *,
        draft,
        version_id: str,
        review_id: str,
        issue,
        created_at: str,
        request_id: str,
        trace_id: str,
    ) -> ConflictGuardRecord | None:
        category = str(getattr(issue, "category", "") or "").strip()
        mapping = {
            "continuity": ConflictType.TIMELINE_CONFLICT,
            "timeline": ConflictType.TIMELINE_CONFLICT,
            "character": ConflictType.CHARACTER_CONFLICT,
            "setting": ConflictType.SETTING_CONFLICT,
            "foreshadow": ConflictType.FORESHADOW_CONFLICT,
        }
        conflict_type = mapping.get(category)
        if conflict_type is None:
            return None
        return ConflictGuardRecord(
            record_id=f"cgr_{uuid.uuid4().hex[:10]}",
            work_id=draft.work_id,
            chapter_id=draft.chapter_id,
            candidate_draft_id=draft.candidate_draft_id,
            candidate_version_id=version_id,
            agent_session_id=draft.agent_session_id,
            source_type="review_issue",
            source_ref_id=str(getattr(issue, "issue_id", "") or review_id),
            target_type="candidate_draft_version",
            target_ref_id=version_id or draft.candidate_draft_id,
            conflict_type=conflict_type,
            severity=ConflictSeverity.WARNING,
            status=ConflictRecordStatus.DETECTED,
            title=str(getattr(issue, "message", "") or "审阅发现冲突"),
            summary=str(getattr(issue, "suggestion", "") or str(getattr(issue, "message", "") or "")),
            evidence_refs=[f"review_id:{review_id}", f"review_issue:{str(getattr(issue, 'issue_id', '') or '')}"],
            suggested_action_refs=["revise_candidate", "open_conflict_resolution"],
            resolution_status="unresolved",
            warning_codes=["review_issue_detected"],
            created_by="conflict_guard",
            created_at=created_at,
            updated_at=created_at,
            request_id=request_id or review_id,
            trace_id=trace_id,
        )

    @staticmethod
    def _now() -> str:
        return datetime.now(UTC).isoformat()
