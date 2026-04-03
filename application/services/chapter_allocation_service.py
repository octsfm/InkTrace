from __future__ import annotations

from application.services.logging_service import build_log_context, get_logger
from domain.constants.story_constants import CHAPTER_TITLE_FALLBACK_TEMPLATE
from domain.types import ProjectId


class ChapterAllocationService:
    def __init__(self, workflow_service):
        self.workflow_service = workflow_service
        self.logger = get_logger(__name__)

    def allocate(
        self,
        project_id: str,
        generated_count: int,
        plan_titles: list[str],
        model_titles: list[str],
        task_titles: list[str] | None = None,
        branch_id: str = "",
        plan_ids: list[str] | None = None,
    ) -> list[dict]:
        project = self.workflow_service.project_service.get_project(ProjectId(project_id))
        if not project:
            raise ValueError("项目不存在")
        chapters = self.workflow_service.chapter_repo.find_by_novel(project.novel_id)
        start_number = max([int(ch.number) for ch in chapters], default=0) + 1
        allocations = []
        task_titles = task_titles or []
        plan_ids = plan_ids or []
        for index in range(max(0, int(generated_count or 0))):
            chapter_number = start_number + index
            title = str((model_titles[index] if index < len(model_titles) else "") or "").strip()
            if not title:
                title = str((plan_titles[index] if index < len(plan_titles) else "") or "").strip()
            if not title:
                task_title = str((task_titles[index] if index < len(task_titles) else "") or "").strip()
                if task_title:
                    title = f"{CHAPTER_TITLE_FALLBACK_TEMPLATE.format(chapter_number=chapter_number)} {task_title}"
                else:
                    title = CHAPTER_TITLE_FALLBACK_TEMPLATE.format(chapter_number=chapter_number)
            title = self.workflow_service._ensure_chapter_title(title, chapter_number)
            allocations.append({"chapter_number": chapter_number, "final_title": title})
            self.logger.info(
                "章节编号分配完成",
                extra=build_log_context(
                    event="chapter_allocation_assigned",
                    project_id=project_id,
                    chapter_number=chapter_number,
                    plan_id=str(plan_ids[index] if index < len(plan_ids) else ""),
                    branch_id=branch_id,
                    used_structural_fallback=False,
                ),
            )
        return allocations
