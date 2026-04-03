import uuid
from datetime import datetime
from typing import Dict, Optional

from application.services.logging_service import build_log_context, get_logger
from application.prompts.prompt_constants import ARC_STAGE_ORDER
from application.prompts.prompt_rules import ARC_STAGE_TRANSITION_RULES
from domain.entities.arc_progress_snapshot import ArcProgressSnapshot
from domain.entities.chapter_arc_binding import ChapterArcBinding
from domain.repositories.arc_progress_snapshot_repository import IArcProgressSnapshotRepository
from domain.repositories.chapter_arc_binding_repository import IChapterArcBindingRepository
from domain.repositories.plot_arc_repository import IPlotArcRepository


class ArcWritebackService:
    def __init__(
        self,
        plot_arc_repo: IPlotArcRepository,
        arc_snapshot_repo: IArcProgressSnapshotRepository,
        chapter_arc_binding_repo: IChapterArcBindingRepository,
    ):
        self.plot_arc_repo = plot_arc_repo
        self.arc_snapshot_repo = arc_snapshot_repo
        self.chapter_arc_binding_repo = chapter_arc_binding_repo
        self.logger = get_logger(__name__)
        self._stage_order = list(ARC_STAGE_ORDER)
        self._stage_transition_rules = dict(ARC_STAGE_TRANSITION_RULES)

    def writeback_chapter_arc(
        self,
        project_id: str,
        chapter_id: str,
        chapter_number: int,
        target_arc_id: str,
        progress_summary: str = "",
        binding_role: str = "primary",
        push_type: str = "advance",
    ) -> None:
        if not target_arc_id:
            return
        arc = self.plot_arc_repo.find_by_id(target_arc_id)
        if not arc:
            return
        if arc.status != "active":
            arc.status = "active"
            self.logger.info(
                "剧情弧激活",
                extra=build_log_context(
                    event="plot_arc_activated",
                    project_id=project_id,
                    chapter_id=chapter_id,
                    chapter_number=chapter_number,
                    arc_id=arc.arc_id,
                ),
            )
        before = arc.current_stage or "setup"
        transition = self._evaluate_transition(before, progress_summary)
        after = transition["stage_after"]
        arc.current_stage = after
        arc.latest_progress_summary = progress_summary or arc.latest_progress_summary
        arc.covered_chapter_ids = [*arc.covered_chapter_ids, chapter_id]
        arc.updated_at = datetime.now()
        self.plot_arc_repo.save(arc)
        self.arc_snapshot_repo.save(
            ArcProgressSnapshot(
                snapshot_id=f"snap_{uuid.uuid4().hex[:10]}",
                arc_id=arc.arc_id,
                chapter_id=chapter_id,
                chapter_number=int(chapter_number or 0),
                stage_before=before,
                stage_after=after,
                progress_summary=progress_summary or "",
                change_reason="chapter_saved",
            )
        )
        self.chapter_arc_binding_repo.save(
            ChapterArcBinding(
                binding_id=f"bind_{uuid.uuid4().hex[:10]}",
                project_id=project_id,
                chapter_id=chapter_id,
                arc_id=arc.arc_id,
                binding_role=binding_role,
                push_type=push_type,
                confidence=0.8,
            )
        )
        self.logger.info(
            "章节绑定剧情弧",
            extra=build_log_context(
                event="plot_arc_bound_to_chapter",
                project_id=project_id,
                chapter_id=chapter_id,
                chapter_number=chapter_number,
                arc_id=arc.arc_id,
                binding_role=binding_role,
                push_type=push_type,
            ),
        )
        if after == self._stage_order[-1] and arc.status != "completed":
            arc.status = "completed"
            arc.updated_at = datetime.now()
            self.plot_arc_repo.save(arc)
            self.logger.info(
                "剧情弧完成",
                extra=build_log_context(
                    event="plot_arc_completed",
                    project_id=project_id,
                    chapter_id=chapter_id,
                    chapter_number=chapter_number,
                    arc_id=arc.arc_id,
                    stage_after=after,
                ),
            )
        self.logger.info(
            "剧情弧阶段推进",
            extra=build_log_context(
                event="plot_arc_stage_changed",
                project_id=project_id,
                chapter_id=chapter_id,
                chapter_number=chapter_number,
                arc_id=arc.arc_id,
                stage_before=before,
                stage_after=after,
                stage_confidence=transition["confidence"],
                stage_reason=transition["reason"],
                stage_evidence=transition["evidence"],
                stage_advanced=transition["advanced"],
            ),
        )

    def _next_stage(self, current_stage: str, progress_summary: str) -> str:
        return self._evaluate_transition(current_stage, progress_summary)["stage_after"]

    def _evaluate_transition(self, current_stage: str, progress_summary: str) -> Dict[str, object]:
        if current_stage not in self._stage_order:
            return {
                "stage_before": current_stage,
                "stage_after": "setup",
                "confidence": 0.2,
                "reason": "unknown_stage_reset",
                "evidence": [],
                "advanced": False,
            }
        index = self._stage_order.index(current_stage)
        if index >= len(self._stage_order) - 1:
            return {
                "stage_before": current_stage,
                "stage_after": self._stage_order[-1],
                "confidence": 1.0,
                "reason": "already_final_stage",
                "evidence": [],
                "advanced": False,
            }
        evaluation = self._score_transition(current_stage, progress_summary)
        if not evaluation["advanced"]:
            self.logger.info(
                "剧情弧阶段未迁移",
                extra=build_log_context(
                    event="plot_arc_stage_rejected",
                    stage_before=current_stage,
                    stage_after=current_stage,
                    reason=evaluation["reason"],
                    stage_confidence=evaluation["confidence"],
                    stage_evidence=evaluation["evidence"],
                ),
            )
            return {
                "stage_before": current_stage,
                "stage_after": current_stage,
                "confidence": evaluation["confidence"],
                "reason": evaluation["reason"],
                "evidence": evaluation["evidence"],
                "advanced": False,
            }
        return {
            "stage_before": current_stage,
            "stage_after": self._stage_order[index + 1],
            "confidence": evaluation["confidence"],
            "reason": "transition_condition_met",
            "evidence": evaluation["evidence"],
            "advanced": True,
        }

    def _should_advance(self, current_stage: str, progress_summary: str) -> bool:
        return bool(self._score_transition(current_stage, progress_summary)["advanced"])

    def _score_transition(self, current_stage: str, progress_summary: str) -> Dict[str, object]:
        summary = str(progress_summary or "").strip()
        if not summary:
            return {"advanced": False, "confidence": 0.0, "reason": "empty_progress_summary", "evidence": []}
        keywords = self._stage_transition_rules.get(current_stage, [])
        evidence = [keyword for keyword in keywords if keyword and keyword in summary]
        if not evidence:
            return {"advanced": False, "confidence": 0.15, "reason": "transition_condition_not_met", "evidence": []}
        confidence = min(0.95, 0.4 + 0.15 * len(evidence))
        return {"advanced": True, "confidence": confidence, "reason": "transition_condition_met", "evidence": evidence}
