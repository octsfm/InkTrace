from __future__ import annotations

import re
import uuid
from datetime import UTC, datetime

from application.services.ai.ai_job_service import AIJobService
from application.services.ai.output_validation_service import OutputValidationService
from application.services.ai.writer_service import WriterService
from application.services.v1.chapter_service import ChapterService
from application.services.v1.work_service import WorkService
from domain.entities.ai.models import (
    CandidateDraft,
    CandidateDraftStatus,
    CandidateDraftValidationStatus,
    ContextPackBuildRequest,
    ContextPackStatus,
    ContinuationResult,
    OutputValidationResult,
    WritingTask,
)
from domain.repositories.ai.ai_job_attempt_repository import AIJobAttemptRepository
from domain.repositories.ai.ai_job_repository import AIJobRepository
from domain.repositories.ai.ai_job_step_repository import AIJobStepRepository
from domain.repositories.ai.candidate_draft_repository import CandidateDraftRepository
from domain.services.ai.writer import WriterPort


class MinimalContinuationWorkflow:
    def __init__(
        self,
        *,
        work_service: WorkService,
        chapter_service: ChapterService,
        context_pack_service,
        candidate_draft_repository: CandidateDraftRepository,
        writer: WriterPort,
        job_repository: AIJobRepository,
        step_repository: AIJobStepRepository,
        attempt_repository: AIJobAttemptRepository,
    ) -> None:
        self._work_service = work_service
        self._chapter_service = chapter_service
        self._context_pack_service = context_pack_service
        self._candidate_draft_repository = candidate_draft_repository
        self._writer_service = WriterService(writer)
        self._output_validation_service = OutputValidationService()
        self._job_service = AIJobService(
            job_repository=job_repository,
            step_repository=step_repository,
            attempt_repository=attempt_repository,
        )

    def start_continuation(
        self,
        work_id: str,
        chapter_id: str,
        user_instruction: str | None = None,
        created_by: str | None = None,
    ) -> ContinuationResult:
        created_by = created_by or "user_action"
        self._work_service.get_work(work_id)
        chapter = self._get_chapter(work_id, chapter_id)
        workflow_id = f"wf_{uuid.uuid4().hex[:12]}"
        writing_task = WritingTask(
            writing_task_id=f"wt_{uuid.uuid4().hex[:12]}",
            work_id=work_id,
            target_chapter_id=chapter_id,
            continuation_mode="continue_chapter",
            user_instruction=str(user_instruction or "").strip(),
            created_by=created_by,
            created_at=self._now(),
        )
        job = self._job_service.create_job(
            job_type="continuation",
            work_id=work_id,
            chapter_id=chapter_id,
            created_by=created_by,
            payload={
                "workflow_id": workflow_id,
                "writing_task_id": writing_task.writing_task_id,
                "user_instruction_preview": writing_task.user_instruction[:80],
            },
            steps=[
                {"step_type": "build_context_pack", "step_name": "Build Context Pack"},
                {"step_type": "run_writer_step", "step_name": "Run Writer Step"},
                {"step_type": "validate_writer_output", "step_name": "Validate Writer Output"},
                {"step_type": "save_candidate_draft", "step_name": "Save Candidate Draft"},
            ],
        )
        step_ids = {step.step_type: step.step_id for step in self._job_service.get_job_steps(job.job_id)}
        self._job_service.start_job(job.job_id)

        self._job_service.mark_step_running(job.job_id, step_ids["build_context_pack"])
        context_pack = self._context_pack_service.build_and_save(
            ContextPackBuildRequest(
                work_id=work_id,
                chapter_id=chapter_id,
                user_instruction=writing_task.user_instruction,
                continuation_mode=writing_task.continuation_mode,
                model_role=writing_task.model_role,
            )
        )
        self._job_service.mark_step_completed(
            job.job_id,
            step_ids["build_context_pack"],
            summary=f"context_pack:{context_pack.status.value}",
        )

        if context_pack.status == ContextPackStatus.BLOCKED:
            self._job_service.mark_step_skipped(job.job_id, step_ids["run_writer_step"], reason="context_pack_blocked")
            self._job_service.mark_step_skipped(job.job_id, step_ids["validate_writer_output"], reason="context_pack_blocked")
            self._job_service.mark_step_skipped(job.job_id, step_ids["save_candidate_draft"], reason="context_pack_blocked")
            self._job_service.mark_job_failed(job.job_id, error_code="context_pack_blocked", error_message=context_pack.blocked_reason)
            return ContinuationResult(
                workflow_id=workflow_id,
                job_id=job.job_id,
                writing_task_id=writing_task.writing_task_id,
                status="blocked",
                warnings=context_pack.warnings,
                error_code="context_pack_blocked",
                error_message=context_pack.blocked_reason,
            )

        self._job_service.mark_step_running(job.job_id, step_ids["run_writer_step"])
        writer_output = self._writer_service.generate_candidate_text(context_pack=context_pack, writing_task=writing_task)
        self._job_service.mark_step_completed(job.job_id, step_ids["run_writer_step"], summary="writer_generated_candidate")

        self._job_service.mark_step_running(job.job_id, step_ids["validate_writer_output"])
        validation = self.validate_writer_output(writer_output.get("content", ""))
        if not validation.success:
            self._job_service.mark_step_failed(
                job.job_id,
                step_ids["validate_writer_output"],
                error_code="writer_output_invalid",
                error_message=validation.message or validation.error_code,
            )
            self._job_service.mark_step_skipped(job.job_id, step_ids["save_candidate_draft"], reason="validation_failed")
            self._job_service.mark_job_failed(
                job.job_id,
                error_code="writer_output_invalid",
                error_message=validation.message or validation.error_code,
            )
            return ContinuationResult(
                workflow_id=workflow_id,
                job_id=job.job_id,
                writing_task_id=writing_task.writing_task_id,
                status="validation_failed",
                warnings=context_pack.warnings,
                error_code="writer_output_invalid",
                error_message=validation.message or validation.error_code,
            )
        self._job_service.mark_step_completed(job.job_id, step_ids["validate_writer_output"], summary="writer_output_valid")

        self._job_service.mark_step_running(job.job_id, step_ids["save_candidate_draft"])
        try:
            draft = self.save_candidate_draft(
                work_id=work_id,
                chapter_id=chapter_id,
                source_context_pack_id=context_pack.context_pack_id,
                source_job_id=job.job_id,
                content=str(validation.parsed_output),
                writer_model_role=writer_output.get("model_role", "writer"),
                provider_name=writer_output.get("provider_name", ""),
                model_name=writer_output.get("model_name", ""),
                created_by=created_by,
                metadata={
                    "workflow_id": workflow_id,
                    "writing_task_id": writing_task.writing_task_id,
                    "context_pack_status": context_pack.status.value,
                    "degraded_reason": context_pack.degraded_reason,
                    "warnings": list(context_pack.warnings),
                    "chapter_version": chapter.version,
                },
            )
        except Exception as exc:
            self._job_service.mark_step_failed(
                job.job_id,
                step_ids["save_candidate_draft"],
                error_code="candidate_save_failed",
                error_message=str(exc),
            )
            self._job_service.mark_job_failed(job.job_id, error_code="candidate_save_failed", error_message=str(exc))
            return ContinuationResult(
                workflow_id=workflow_id,
                job_id=job.job_id,
                writing_task_id=writing_task.writing_task_id,
                status="candidate_save_failed",
                warnings=context_pack.warnings,
                error_code="candidate_save_failed",
                error_message="candidate_save_failed",
            )

        self._job_service.mark_step_completed(job.job_id, step_ids["save_candidate_draft"], summary="candidate_draft_saved")
        self._job_service.mark_job_completed(job.job_id, result_summary={"candidate_draft_id": draft.candidate_draft_id}, result_ref=draft.candidate_draft_id)

        return ContinuationResult(
            workflow_id=workflow_id,
            job_id=job.job_id,
            writing_task_id=writing_task.writing_task_id,
            candidate_draft_id=draft.candidate_draft_id,
            status="degraded_completed" if context_pack.status == ContextPackStatus.DEGRADED else "completed_with_candidate",
            warnings=context_pack.warnings,
        )

    def get_candidate_draft(self, candidate_draft_id: str) -> CandidateDraft:
        return self._candidate_draft_repository.get(candidate_draft_id)

    def list_candidate_drafts(self, work_id: str, chapter_id: str | None = None) -> list[CandidateDraft]:
        return self._candidate_draft_repository.list_by_work(work_id, chapter_id=chapter_id or "")

    def validate_writer_output(self, raw_output: str) -> OutputValidationResult:
        base_validation = self._output_validation_service.validate("plain_text", raw_output)
        if not base_validation.success:
            return OutputValidationResult(
                success=False,
                error_code="writer_output_invalid",
                message=base_validation.message or base_validation.error_code,
            )

        text = str(base_validation.parsed_output or "").strip()
        lowered = text.lower()
        if len(text) < 20:
            return OutputValidationResult(success=False, error_code="writer_output_invalid", message="output_too_short")
        if len(text) > 5000:
            return OutputValidationResult(success=False, error_code="writer_output_invalid", message="output_too_long")
        if lowered in {"todo", "tbd", "placeholder"}:
            return OutputValidationResult(success=False, error_code="writer_output_invalid", message="output_placeholder")
        if "traceback" in lowered or "exception" in lowered:
            return OutputValidationResult(success=False, error_code="writer_output_invalid", message="output_system_error")
        return OutputValidationResult(success=True, parsed_output=text)

    def save_candidate_draft(
        self,
        *,
        work_id: str,
        chapter_id: str,
        source_context_pack_id: str,
        source_job_id: str,
        content: str,
        writer_model_role: str,
        provider_name: str,
        model_name: str,
        created_by: str,
        metadata: dict[str, object] | None = None,
    ) -> CandidateDraft:
        content = str(content or "").strip()
        draft = CandidateDraft(
            candidate_draft_id=f"cd_{uuid.uuid4().hex[:12]}",
            work_id=work_id,
            chapter_id=chapter_id,
            source_context_pack_id=source_context_pack_id,
            source_job_id=source_job_id,
            status=CandidateDraftStatus.GENERATED,
            content=content,
            content_preview=content[:120],
            word_count=max(1, len(re.findall(r"\S+", content))),
            char_count=len(content),
            validation_status=CandidateDraftValidationStatus.PASSED,
            writer_model_role=writer_model_role,
            provider_name=provider_name,
            model_name=model_name,
            created_by=created_by,
            created_at=self._now(),
            updated_at=self._now(),
            metadata=dict(metadata or {}),
        )
        return self._candidate_draft_repository.save(draft)

    def _get_chapter(self, work_id: str, chapter_id: str):
        chapters = self._chapter_service.list_chapters(work_id)
        for chapter in chapters:
            if chapter.id.value == chapter_id:
                return chapter
        raise ValueError("chapter_not_found")

    def _now(self) -> str:
        return datetime.now(UTC).isoformat()
