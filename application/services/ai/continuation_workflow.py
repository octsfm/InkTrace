from __future__ import annotations

import re
import uuid
from datetime import UTC, datetime

from application.services.ai.ai_job_service import AIJobService
from application.services.ai.tool_facade import ToolExecutionContext
from application.services.v1.chapter_service import ChapterService
from application.services.v1.work_service import WorkService
from domain.entities.ai.models import (
    CandidateDraft,
    ContextPackStatus,
    ContinuationResult,
    WritingTask,
)
from domain.repositories.ai.ai_job_attempt_repository import AIJobAttemptRepository
from domain.repositories.ai.ai_job_repository import AIJobRepository
from domain.repositories.ai.ai_job_step_repository import AIJobStepRepository
from domain.repositories.ai.candidate_draft_repository import CandidateDraftRepository


class MinimalContinuationWorkflow:
    def __init__(
        self,
        *,
        work_service: WorkService,
        chapter_service: ChapterService,
        tool_facade,
        candidate_draft_repository: CandidateDraftRepository,
        job_repository: AIJobRepository,
        step_repository: AIJobStepRepository,
        attempt_repository: AIJobAttemptRepository,
    ) -> None:
        self._work_service = work_service
        self._chapter_service = chapter_service
        self._tool_facade = tool_facade
        self._candidate_draft_repository = candidate_draft_repository
        self._job_service = AIJobService(
            job_repository=job_repository,
            step_repository=step_repository,
            attempt_repository=attempt_repository,
        )
        if getattr(self._tool_facade, "_job_service", None) is None:
            self._tool_facade._job_service = self._job_service  # type: ignore[attr-defined]  # noqa: SLF001

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
        tool_context = ToolExecutionContext(
            caller_type="workflow",
            work_id=work_id,
            chapter_id=chapter_id,
            request_id=job.job_id,
            trace_id=workflow_id,
        )

        self._call_job_tool(
            "update_job_step_progress",
            context=tool_context,
            payload={"job_id": job.job_id, "step_id": step_ids["build_context_pack"], "status": "running"},
        )
        context_pack_result = self._tool_facade.call(
            "build_context_pack",
            context=tool_context,
            payload={
                "work_id": work_id,
                "chapter_id": chapter_id,
                "user_instruction": writing_task.user_instruction,
                "continuation_mode": writing_task.continuation_mode,
                "model_role": writing_task.model_role,
            },
        )
        if not context_pack_result.ok:
            self._call_job_tool(
                "mark_job_step_failed",
                context=tool_context,
                payload={
                    "job_id": job.job_id,
                    "step_id": step_ids["build_context_pack"],
                    "error_code": context_pack_result.error_code or "tool_execution_failed",
                    "error_message": context_pack_result.safe_message or context_pack_result.error_code,
                },
            )
            self._call_job_tool(
                "mark_job_failed",
                context=tool_context,
                payload={
                    "job_id": job.job_id,
                    "error_code": context_pack_result.error_code or "tool_execution_failed",
                    "error_message": context_pack_result.safe_message or context_pack_result.error_code,
                },
            )
            return ContinuationResult(
                workflow_id=workflow_id,
                job_id=job.job_id,
                writing_task_id=writing_task.writing_task_id,
                status="failed",
                warnings=context_pack_result.warnings,
                error_code=context_pack_result.error_code or "tool_execution_failed",
                error_message=context_pack_result.safe_message or context_pack_result.error_code,
            )
        context_pack = context_pack_result.payload["context_pack"]
        self._call_job_tool(
            "mark_job_step_completed",
            context=tool_context,
            payload={
                "job_id": job.job_id,
                "step_id": step_ids["build_context_pack"],
                "summary": f"context_pack:{context_pack.status.value}",
            },
        )

        if context_pack.status == ContextPackStatus.BLOCKED:
            self._call_job_tool(
                "update_job_step_progress",
                context=tool_context,
                payload={"job_id": job.job_id, "step_id": step_ids["run_writer_step"], "status": "skipped", "reason": "context_pack_blocked"},
            )
            self._call_job_tool(
                "update_job_step_progress",
                context=tool_context,
                payload={"job_id": job.job_id, "step_id": step_ids["validate_writer_output"], "status": "skipped", "reason": "context_pack_blocked"},
            )
            self._call_job_tool(
                "update_job_step_progress",
                context=tool_context,
                payload={"job_id": job.job_id, "step_id": step_ids["save_candidate_draft"], "status": "skipped", "reason": "context_pack_blocked"},
            )
            self._call_job_tool(
                "mark_job_failed",
                context=tool_context,
                payload={"job_id": job.job_id, "error_code": "context_pack_blocked", "error_message": context_pack.blocked_reason},
            )
            return ContinuationResult(
                workflow_id=workflow_id,
                job_id=job.job_id,
                writing_task_id=writing_task.writing_task_id,
                status="blocked",
                warnings=context_pack.warnings,
                error_code="context_pack_blocked",
                error_message=context_pack.blocked_reason,
            )

        self._call_job_tool(
            "update_job_step_progress",
            context=tool_context,
            payload={"job_id": job.job_id, "step_id": step_ids["run_writer_step"], "status": "running"},
        )
        writer_result = self._tool_facade.call(
            "run_writer_step",
            context=tool_context,
            payload={"context_pack": context_pack, "writing_task": writing_task},
        )
        if not writer_result.ok:
            self._call_job_tool(
                "mark_job_step_failed",
                context=tool_context,
                payload={
                    "job_id": job.job_id,
                    "step_id": step_ids["run_writer_step"],
                    "error_code": writer_result.error_code or "tool_execution_failed",
                    "error_message": writer_result.safe_message or writer_result.error_code,
                },
            )
            self._call_job_tool(
                "mark_job_failed",
                context=tool_context,
                payload={
                    "job_id": job.job_id,
                    "error_code": writer_result.error_code or "tool_execution_failed",
                    "error_message": writer_result.safe_message or writer_result.error_code,
                },
            )
            return ContinuationResult(
                workflow_id=workflow_id,
                job_id=job.job_id,
                writing_task_id=writing_task.writing_task_id,
                status="failed",
                warnings=context_pack.warnings,
                error_code=writer_result.error_code or "tool_execution_failed",
                error_message=writer_result.safe_message or writer_result.error_code,
            )
        writer_output = writer_result.payload["writer_output"]
        self._call_job_tool(
            "mark_job_step_completed",
            context=tool_context,
            payload={"job_id": job.job_id, "step_id": step_ids["run_writer_step"], "summary": "writer_generated_candidate"},
        )

        self._call_job_tool(
            "update_job_step_progress",
            context=tool_context,
            payload={"job_id": job.job_id, "step_id": step_ids["validate_writer_output"], "status": "running"},
        )
        validation_result = self._tool_facade.call(
            "validate_writer_output",
            context=tool_context,
            payload={"content": writer_output.get("content", "")},
        )
        if not validation_result.ok:
            self._call_job_tool(
                "mark_job_step_failed",
                context=tool_context,
                payload={
                    "job_id": job.job_id,
                    "step_id": step_ids["validate_writer_output"],
                    "error_code": "writer_output_invalid",
                    "error_message": validation_result.safe_message or validation_result.error_code,
                },
            )
            self._call_job_tool(
                "update_job_step_progress",
                context=tool_context,
                payload={"job_id": job.job_id, "step_id": step_ids["save_candidate_draft"], "status": "skipped", "reason": "validation_failed"},
            )
            self._call_job_tool(
                "mark_job_failed",
                context=tool_context,
                payload={
                    "job_id": job.job_id,
                    "error_code": "writer_output_invalid",
                    "error_message": validation_result.safe_message or validation_result.error_code,
                },
            )
            return ContinuationResult(
                workflow_id=workflow_id,
                job_id=job.job_id,
                writing_task_id=writing_task.writing_task_id,
                status="validation_failed",
                warnings=context_pack.warnings,
                error_code="writer_output_invalid",
                error_message=validation_result.safe_message or validation_result.error_code,
            )
        validated_content = str(validation_result.payload["validated_content"])
        self._call_job_tool(
            "mark_job_step_completed",
            context=tool_context,
            payload={"job_id": job.job_id, "step_id": step_ids["validate_writer_output"], "summary": "writer_output_valid"},
        )

        self._call_job_tool(
            "update_job_step_progress",
            context=tool_context,
            payload={"job_id": job.job_id, "step_id": step_ids["save_candidate_draft"], "status": "running"},
        )
        save_result = self._tool_facade.call(
            "save_candidate_draft",
            context=tool_context,
            payload={
                "candidate_draft_id": f"cd_{uuid.uuid4().hex[:12]}",
                "work_id": work_id,
                "chapter_id": chapter_id,
                "source_context_pack_id": context_pack.context_pack_id,
                "source_job_id": job.job_id,
                "content": validated_content,
                "writer_model_role": writer_output.get("model_role", "writer"),
                "provider_name": writer_output.get("provider_name", ""),
                "model_name": writer_output.get("model_name", ""),
                "created_by": created_by,
                "metadata": {
                    "workflow_id": workflow_id,
                    "writing_task_id": writing_task.writing_task_id,
                    "context_pack_status": context_pack.status.value,
                    "degraded_reason": context_pack.degraded_reason,
                    "warnings": list(context_pack.warnings),
                    "chapter_version": chapter.version,
                },
            },
        )
        if not save_result.ok:
            self._call_job_tool(
                "mark_job_step_failed",
                context=tool_context,
                payload={
                    "job_id": job.job_id,
                    "step_id": step_ids["save_candidate_draft"],
                    "error_code": "candidate_save_failed",
                    "error_message": save_result.safe_message or save_result.error_code,
                },
            )
            self._call_job_tool(
                "mark_job_failed",
                context=tool_context,
                payload={
                    "job_id": job.job_id,
                    "error_code": "candidate_save_failed",
                    "error_message": save_result.safe_message or save_result.error_code,
                },
            )
            return ContinuationResult(
                workflow_id=workflow_id,
                job_id=job.job_id,
                writing_task_id=writing_task.writing_task_id,
                status="candidate_save_failed",
                warnings=context_pack.warnings,
                error_code="candidate_save_failed",
                error_message="candidate_save_failed",
            )
        draft = save_result.payload["candidate_draft"]

        self._call_job_tool(
            "mark_job_step_completed",
            context=tool_context,
            payload={"job_id": job.job_id, "step_id": step_ids["save_candidate_draft"], "summary": "candidate_draft_saved"},
        )
        self._call_job_tool(
            "mark_job_completed",
            context=tool_context,
            payload={
                "job_id": job.job_id,
                "result_summary": {"candidate_draft_id": draft.candidate_draft_id},
                "result_ref": draft.candidate_draft_id,
            },
        )

        return ContinuationResult(
            workflow_id=workflow_id,
            job_id=job.job_id,
            writing_task_id=writing_task.writing_task_id,
            candidate_draft_id=draft.candidate_draft_id,
            status="pending_review",
            warnings=context_pack.warnings,
        )

    def get_candidate_draft(self, candidate_draft_id: str) -> CandidateDraft:
        return self._candidate_draft_repository.get(candidate_draft_id)

    def list_candidate_drafts(self, work_id: str, chapter_id: str | None = None) -> list[CandidateDraft]:
        return self._candidate_draft_repository.list_by_work(work_id, chapter_id=chapter_id or "")

    def _get_chapter(self, work_id: str, chapter_id: str):
        chapters = self._chapter_service.list_chapters(work_id)
        for chapter in chapters:
            if chapter.id.value == chapter_id:
                return chapter
        raise ValueError("chapter_not_found")

    def _call_job_tool(self, tool_name: str, *, context: ToolExecutionContext, payload: dict[str, object]) -> None:
        result = self._tool_facade.call(tool_name, context=context, payload=dict(payload))
        if not result.ok:
            raise RuntimeError(result.error_code or "job_tool_failed")

    def _now(self) -> str:
        return datetime.now(UTC).isoformat()
