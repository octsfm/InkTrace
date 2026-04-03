from __future__ import annotations

import uuid

from application.services.logging_service import build_log_context, get_logger
from domain.entities.continuation_context_snapshot import ContinuationContextSnapshot


class ContinuationContextBuilder:
    def __init__(self, workflow_service):
        self.workflow_service = workflow_service
        self.logger = get_logger(__name__)

    def build(self, project_id: str, chapter_id: str = "", chapter_number: int = 0, plan_id: str = "", branch_id: str = ""):
        context = self.workflow_service.build_continuation_context(project_id, chapter_id, chapter_number)
        snapshot = ContinuationContextSnapshot(
            id=f"ccs_{uuid.uuid4().hex[:12]}",
            project_id=project_id,
            chapter_id=chapter_id,
            chapter_number=chapter_number,
            recent_chapter_memories=list(context.recent_chapter_memories or []),
            last_chapter_tail=str(context.last_chapter_tail or ""),
            relevant_characters=list(context.relevant_characters or []),
            relevant_foreshadowing=[str(x) for x in (context.relevant_foreshadowing or [])],
            global_constraints=dict(context.global_constraints or {}),
            chapter_task_seed=dict(context.chapter_task_seed or {}),
            style_requirements=dict(context.style_requirements or {}),
        )
        self.workflow_service.continuation_context_snapshot_repo.save(snapshot)
        self.logger.info(
            "续写上下文构建完成",
            extra=build_log_context(
                event="continuation_context_built",
                project_id=project_id,
                chapter_id=chapter_id,
                chapter_number=chapter_number,
                plan_id=plan_id,
                branch_id=branch_id,
                used_structural_fallback=False,
                snapshot_id=snapshot.id,
            ),
        )
        self.logger.info(
            "续写上下文快照已保存",
            extra=build_log_context(
                event="continuation_context_snapshot_saved",
                project_id=project_id,
                chapter_id=chapter_id,
                chapter_number=chapter_number,
                plan_id=plan_id,
                branch_id=branch_id,
                used_structural_fallback=False,
                snapshot_id=snapshot.id,
                recent_memory_count=len(context.recent_chapter_memories or []),
                relevant_character_count=len(context.relevant_characters or []),
            ),
        )
        return context
