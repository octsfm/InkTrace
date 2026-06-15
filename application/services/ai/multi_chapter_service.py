from __future__ import annotations

import threading
import time
import uuid
from datetime import UTC, datetime

from application.services.ai.ai_job_service import AIJobService
from application.services.ai.continuation_workflow import MinimalContinuationWorkflow
from application.services.v1.chapter_service import ChapterService
from domain.entities.ai.models import (
    ChapterAdvanceDecision,
    ChapterProgressEntry,
    ChapterStatusEntry,
    MultiChapterProgress,
    MultiChapterSession,
    MultiChapterStatus,
    PerChapterStatus,
)
from domain.repositories.ai.candidate_draft_repository import CandidateDraftRepository
from domain.repositories.ai.multi_chapter_session_repository import MultiChapterSessionRepository


class MultiChapterContinuationService:
    def __init__(
        self,
        *,
        chapter_service: ChapterService,
        continuation_workflow: MinimalContinuationWorkflow,
        candidate_draft_repository: CandidateDraftRepository,
        multi_chapter_repository: MultiChapterSessionRepository,
        job_service: AIJobService,
    ) -> None:
        self._chapter_service = chapter_service
        self._continuation_workflow = continuation_workflow
        self._candidate_draft_repository = candidate_draft_repository
        self._multi_chapter_repository = multi_chapter_repository
        self._job_service = job_service

    def start(
        self,
        *,
        work_id: str,
        start_chapter_id: str,
        target_chapters: int,
        user_instruction: str = "",
        caller_type: str = "user_action",
    ) -> MultiChapterSession:
        if caller_type != "user_action":
            raise ValueError("P2_CALLER_FORBIDDEN")
        if int(target_chapters) < 1 or int(target_chapters) > 10:
            raise ValueError("invalid_target_chapters")
        start_chapter = self._get_chapter(work_id, start_chapter_id)
        target_entries: list[ChapterStatusEntry] = []
        previous_chapter_id = start_chapter.id.value
        for chapter_index in range(1, int(target_chapters) + 1):
            created = self._chapter_service.create_chapter(
                work_id,
                title=f"第{start_chapter.order_index + chapter_index}章",
                after_chapter_id=previous_chapter_id,
            )
            target_entries.append(
                ChapterStatusEntry(
                    chapter_index=chapter_index,
                    chapter_id=created.id.value,
                    status=PerChapterStatus.PENDING,
                )
            )
            previous_chapter_id = created.id.value

        now = self._now()
        session_id = f"mcs_{uuid.uuid4().hex[:12]}"
        job = self._job_service.create_job(
            job_type="multi_chapter_continuation",
            work_id=work_id,
            chapter_id=start_chapter_id,
            created_by=caller_type,
            payload={"session_id": session_id},
            steps=[
                {
                    "step_type": f"generate_chapter_{index}",
                    "step_name": f"Generate Chapter {index}",
                }
                for index in range(1, int(target_chapters) + 1)
            ],
        )
        session = MultiChapterSession(
            session_id=session_id,
            work_id=work_id,
            start_chapter_id=start_chapter_id,
            target_chapters=int(target_chapters),
            current_index=0,
            status=MultiChapterStatus.PENDING,
            per_chapter_status=target_entries,
            request_id=job.job_id,
            trace_id=f"trace_{uuid.uuid4().hex[:12]}",
            created_by=caller_type,
            created_at=now,
            updated_at=now,
            metadata={"job_id": job.job_id, "user_instruction": user_instruction},
        )
        saved = self._multi_chapter_repository.save(session)
        self._submit_session(saved.session_id)
        return saved

    def get_session(self, session_id: str) -> MultiChapterSession:
        session = self._multi_chapter_repository.get_by_id(session_id)
        if session is None:
            raise ValueError("multi_chapter_session_not_found")
        return session

    def get_progress(self, session_id: str) -> MultiChapterProgress:
        session = self.get_session(session_id)
        per_chapter: list[ChapterProgressEntry] = []
        completed_count = 0
        blocked_count = 0
        for item in session.per_chapter_status:
            draft = None
            if item.candidate_draft_id:
                try:
                    draft = self._candidate_draft_repository.get(item.candidate_draft_id)
                except ValueError:
                    draft = None
            if item.status in {PerChapterStatus.READY, PerChapterStatus.APPLIED, PerChapterStatus.SKIPPED}:
                completed_count += 1
            if item.status == PerChapterStatus.BLOCKED:
                blocked_count += 1
            per_chapter.append(
                ChapterProgressEntry(
                    chapter_index=item.chapter_index,
                    status=item.status,
                    candidate_draft_id=item.candidate_draft_id,
                    candidate_draft_status=draft.status.value if draft is not None else "",
                    word_count=draft.word_count if draft is not None else 0,
                    review_summary=str(draft.metadata.get("review_summary", "")) if draft is not None else "",
                )
            )
        return MultiChapterProgress(
            session_id=session.session_id,
            status=session.status,
            current_index=session.current_index,
            target_chapters=session.target_chapters,
            completed_count=completed_count,
            blocked_count=blocked_count,
            per_chapter=per_chapter,
        )

    def pause(self, session_id: str) -> MultiChapterSession:
        session = self.get_session(session_id)
        session = session.model_copy(
            update={
                "status": MultiChapterStatus.PAUSED,
                "paused_reason": "user_paused",
                "pending_pause": True,
                "updated_at": self._now(),
            }
        )
        self._pause_job_if_needed(session)
        return self._multi_chapter_repository.save(session)

    def resume(self, session_id: str) -> MultiChapterSession:
        session = self.get_session(session_id)
        next_status = (
            MultiChapterStatus.WAITING_USER_DECISION
            if session.current_index and session.per_chapter_status[session.current_index - 1].status == PerChapterStatus.READY
            else MultiChapterStatus.RUNNING
        )
        session = session.model_copy(
            update={
                "status": next_status,
                "paused_reason": "",
                "pending_pause": False,
                "updated_at": self._now(),
            }
        )
        saved = self._multi_chapter_repository.save(session)
        if next_status == MultiChapterStatus.RUNNING:
            self._submit_session(saved.session_id)
        return saved

    def cancel(self, session_id: str) -> MultiChapterSession:
        session = self.get_session(session_id)
        session = session.model_copy(
            update={
                "status": MultiChapterStatus.CANCELLED,
                "updated_at": self._now(),
                "finished_at": self._now(),
                "blocked_reason_code": "user_manual_cancel",
            }
        )
        saved = self._multi_chapter_repository.save(session)
        job_id = str(saved.metadata.get("job_id", ""))
        if job_id:
            self._job_service.cancel_job(job_id, reason="user_cancelled")
        return saved

    def advance_to_next_chapter(self, session_id: str, *, decision: ChapterAdvanceDecision) -> MultiChapterSession:
        session = self.get_session(session_id)
        if session.status == MultiChapterStatus.COMPLETED:
            return session
        if session.status not in {MultiChapterStatus.WAITING_USER_DECISION, MultiChapterStatus.BLOCKED}:
            raise ValueError("not_waiting_user_decision")
        if session.current_index <= 0:
            raise ValueError("invalid_session_progress")

        current = session.per_chapter_status[session.current_index - 1]
        if decision == ChapterAdvanceDecision.APPLIED:
            current = current.model_copy(update={"status": PerChapterStatus.APPLIED})
        elif decision == ChapterAdvanceDecision.SKIPPED:
            current = current.model_copy(update={"status": PerChapterStatus.SKIPPED})
        elif decision == ChapterAdvanceDecision.CONTINUE_WITHOUT_APPLY:
            current = current.model_copy(update={"status": PerChapterStatus.READY})
        elif decision == ChapterAdvanceDecision.REGENERATE:
            current = current.model_copy(
                update={
                    "status": PerChapterStatus.PENDING,
                    "candidate_draft_id": "",
                    "agent_session_id": "",
                    "error_code": "",
                    "started_at": "",
                    "finished_at": "",
                }
            )
        per_chapter_status = list(session.per_chapter_status)
        per_chapter_status[session.current_index - 1] = current

        if decision == ChapterAdvanceDecision.REGENERATE:
            updated = session.model_copy(
                update={
                    "status": MultiChapterStatus.RUNNING,
                    "per_chapter_status": per_chapter_status,
                    "updated_at": self._now(),
                }
            )
            saved = self._multi_chapter_repository.save(updated)
            self._submit_session(saved.session_id)
            return saved

        next_index = session.current_index + 1
        if next_index > session.target_chapters:
            updated = session.model_copy(
                update={
                    "status": MultiChapterStatus.COMPLETED,
                    "per_chapter_status": per_chapter_status,
                    "finished_at": self._now(),
                    "updated_at": self._now(),
                }
            )
            saved = self._multi_chapter_repository.save(updated)
            job_id = str(saved.metadata.get("job_id", ""))
            if job_id:
                self._job_service.mark_job_completed(
                    job_id,
                    result_summary={"session_id": saved.session_id, "target_chapters": saved.target_chapters},
                    result_ref=saved.session_id,
                )
            return saved

        updated = session.model_copy(
            update={
                "current_index": next_index,
                "status": MultiChapterStatus.RUNNING,
                "per_chapter_status": per_chapter_status,
                "updated_at": self._now(),
            }
        )
        saved = self._multi_chapter_repository.save(updated)
        self._submit_session(saved.session_id)
        return saved

    def list_chapters(self, session_id: str) -> list[ChapterProgressEntry]:
        return self.get_progress(session_id).per_chapter

    def _submit_session(self, session_id: str) -> None:
        thread = threading.Thread(target=self._run_session_once, args=(session_id,), daemon=True)
        thread.start()

    def _run_session_once(self, session_id: str) -> None:
        session = self.get_session(session_id)
        if session.status == MultiChapterStatus.CANCELLED:
            return
        job_id = str(session.metadata.get("job_id", ""))
        if job_id:
            try:
                self._job_service.start_job(job_id)
            except ValueError:
                pass

        if session.current_index <= 0:
            session = session.model_copy(update={"current_index": 1})
        if session.current_index > session.target_chapters:
            return

        chapter_index = session.current_index
        step_id = self._get_job_step_id(job_id, chapter_index)
        if step_id:
            self._job_service.mark_step_running(job_id, step_id)

        per_chapter_status = list(session.per_chapter_status)
        current_entry = per_chapter_status[chapter_index - 1].model_copy(
            update={"status": PerChapterStatus.GENERATING, "started_at": self._now()}
        )
        per_chapter_status[chapter_index - 1] = current_entry
        session = session.model_copy(
            update={
                "status": MultiChapterStatus.RUNNING,
                "started_at": session.started_at or self._now(),
                "updated_at": self._now(),
                "per_chapter_status": per_chapter_status,
            }
        )
        session = self._multi_chapter_repository.save(session)

        if chapter_index > 1:
            self._update_inter_chapter_state(session, chapter_index - 1)
            session = self.get_session(session_id)

        target_chapter_id = session.per_chapter_status[chapter_index - 1].chapter_id
        result = self._continuation_workflow.start_continuation(
            session.work_id,
            target_chapter_id,
            user_instruction=str(session.metadata.get("user_instruction", "")),
            created_by=session.created_by,
        )
        latest = self.get_session(session_id)
        per_chapter_status = list(latest.per_chapter_status)
        current_entry = per_chapter_status[chapter_index - 1]

        if result.status == "pending_review":
            draft = self._candidate_draft_repository.get(result.candidate_draft_id)
            current_entry = current_entry.model_copy(
                update={
                    "candidate_draft_id": draft.candidate_draft_id,
                    "status": PerChapterStatus.READY,
                    "finished_at": self._now(),
                }
            )
            agent_ids = list(latest.agent_session_ids)
            if draft.agent_session_id:
                agent_ids.append(draft.agent_session_id)
            candidate_ids = list(latest.candidate_draft_ids)
            candidate_ids.append(draft.candidate_draft_id)
            per_chapter_status[chapter_index - 1] = current_entry
            updated = latest.model_copy(
                update={
                    "status": MultiChapterStatus.WAITING_USER_DECISION,
                    "per_chapter_status": per_chapter_status,
                    "agent_session_ids": agent_ids,
                    "candidate_draft_ids": candidate_ids,
                    "updated_at": self._now(),
                }
            )
            self._multi_chapter_repository.save(updated)
            if step_id:
                self._job_service.mark_step_completed(job_id, step_id, summary=f"candidate:{draft.candidate_draft_id}")
            if job_id:
                self._job_service.pause_job(job_id, reason="waiting_user_decision")
            return

        blocked_status = MultiChapterStatus.BLOCKED if result.status == "blocked" else MultiChapterStatus.FAILED
        chapter_status = PerChapterStatus.BLOCKED if result.status == "blocked" else PerChapterStatus.FAILED
        per_chapter_status[chapter_index - 1] = current_entry.model_copy(
            update={
                "status": chapter_status,
                "error_code": result.error_code,
                "finished_at": self._now(),
            }
        )
        updated = latest.model_copy(
            update={
                "status": blocked_status,
                "per_chapter_status": per_chapter_status,
                "error_code": result.error_code,
                "error_message": result.error_message,
                "updated_at": self._now(),
            }
        )
        self._multi_chapter_repository.save(updated)
        if step_id:
            self._job_service.mark_step_failed(job_id, step_id, error_code=result.error_code or "multi_chapter_failed", error_message=result.error_message or result.status)
        if job_id:
            self._job_service.mark_job_failed(job_id, error_code=result.error_code or "multi_chapter_failed", error_message=result.error_message or result.status)

    def _update_inter_chapter_state(self, session: MultiChapterSession, previous_index: int) -> None:
        previous_entry = session.per_chapter_status[previous_index - 1]
        if not previous_entry.candidate_draft_id:
            return
        draft = self._candidate_draft_repository.get(previous_entry.candidate_draft_id)
        snapshot = {
            "chapter_index": previous_index,
            "candidate_draft_id": draft.candidate_draft_id,
            "chapter_id": draft.chapter_id,
            "content_preview": draft.content_preview,
            "updated_at": self._now(),
        }
        updated = session.model_copy(
            update={
                "candidate_story_state": {
                    "latest_candidate_draft_id": draft.candidate_draft_id,
                    "latest_chapter_id": draft.chapter_id,
                    "content_preview": draft.content_preview,
                },
                "queue_state_snapshots": [*session.queue_state_snapshots, snapshot],
                "updated_at": self._now(),
            }
        )
        self._multi_chapter_repository.save(updated)

    def _pause_job_if_needed(self, session: MultiChapterSession) -> None:
        job_id = str(session.metadata.get("job_id", ""))
        if not job_id:
            return
        try:
            self._job_service.pause_job(job_id, reason=session.paused_reason or "user_paused")
        except ValueError:
            pass

    def _get_job_step_id(self, job_id: str, chapter_index: int) -> str:
        if not job_id:
            return ""
        steps = self._job_service.get_job_steps(job_id)
        if 1 <= chapter_index <= len(steps):
            return steps[chapter_index - 1].step_id
        return ""

    def _get_chapter(self, work_id: str, chapter_id: str):
        chapters = self._chapter_service.list_chapters(work_id)
        for chapter in chapters:
            if chapter.id.value == chapter_id:
                return chapter
        raise ValueError("chapter_not_found")

    def _now(self) -> str:
        return datetime.now(UTC).isoformat()

