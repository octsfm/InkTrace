from __future__ import annotations

from domain.entities.ai.models import ArcStatus, StopCondition, StopEvaluationResult, StopSeverity


class StopConditionEvaluator:
    def __init__(self, *, plot_arc_repository, budget_service=None, foreshadow_repository=None) -> None:
        self._plot_arc_repository = plot_arc_repository
        self._budget_service = budget_service
        self._foreshadow_repository = foreshadow_repository

    def evaluate(self, run, config, last_review_result) -> StopEvaluationResult:
        provider_error = str(getattr(last_review_result, "metadata", {}).get("provider_error", "") or "")
        if provider_error:
            return StopEvaluationResult(
                should_stop=True,
                condition=StopCondition.PROVIDER_UNRECOVERABLE,
                severity=StopSeverity.PROVIDER,
                reason="provider_unrecoverable",
                user_action_required=True,
                suggested_action="check_provider",
            )

        if self._budget_service is not None and bool(getattr(config, "stop_on_budget_exceeded", False)):
            budget_result = self._budget_service.check_auto_queue_budget(run.run_id)
            if bool(getattr(budget_result, "has_indeterminate", False)) or str(
                getattr(budget_result, "determination", "") or ""
            ).lower() == "indeterminate":
                return StopEvaluationResult(
                    should_stop=False,
                    should_pause=True,
                    reason="budget_indeterminate",
                    user_action_required=True,
                    suggested_action="check_cost_settings",
                )
            if bool(getattr(budget_result, "exceeded", False)):
                return StopEvaluationResult(
                    should_stop=True,
                    condition=StopCondition.BUDGET_EXCEEDED,
                    severity=StopSeverity.BUDGET,
                    reason="budget_exceeded",
                    user_action_required=True,
                    suggested_action=str(getattr(budget_result, "suggested_action", "") or "adjust_budget"),
                )

        if bool(getattr(config, "stop_on_blocking_review", False)):
            blocking_count = int(getattr(run, "consecutive_blocking_count", 0) or 0)
            threshold = max(int(getattr(config, "max_consecutive_blocking", 2) or 2), 1)
            if self._is_blocking_review(last_review_result) and blocking_count + 1 >= threshold:
                return StopEvaluationResult(
                    should_stop=True,
                    condition=StopCondition.BLOCKING_REVIEW_CONSECUTIVE,
                    severity=StopSeverity.ABNORMAL,
                    reason="blocking_review_consecutive",
                    user_action_required=True,
                    suggested_action="review_conflicts",
                )

        target_chapters = int(getattr(config, "target_chapters", 0) or 0)
        if target_chapters > 0 and int(getattr(run, "generated_count", 0) or 0) >= target_chapters:
            return StopEvaluationResult(
                should_stop=True,
                condition=StopCondition.TARGET_CHAPTERS_REACHED,
                severity=StopSeverity.NORMAL,
                reason="target_chapters_reached",
                user_action_required=False,
                suggested_action="none",
            )

        target_word_count = int(getattr(config, "target_word_count", 0) or 0)
        if target_word_count > 0 and int(getattr(run, "total_word_count", 0) or 0) >= target_word_count:
            return StopEvaluationResult(
                should_stop=True,
                condition=StopCondition.TARGET_WORDS_REACHED,
                severity=StopSeverity.NORMAL,
                reason="target_words_reached",
                user_action_required=False,
                suggested_action="none",
            )

        if bool(getattr(config, "stop_at_sequence_end", False)):
            sequence_arc = self._plot_arc_repository.get_active_sequence_arc(getattr(run, "work_id", ""), 0)
            if sequence_arc is not None and getattr(sequence_arc, "status", None) in {
                ArcStatus.EMPTY,
                ArcStatus.FAILED,
            }:
                return StopEvaluationResult(
                    should_stop=True,
                    condition=StopCondition.SEQUENCE_ARC_ENDED,
                    severity=StopSeverity.NORMAL,
                    reason="sequence_arc_ended",
                    user_action_required=False,
                    suggested_action="none",
                )

        return StopEvaluationResult(
            should_stop=False,
            condition=None,
            severity=None,
            reason="continue",
            user_action_required=False,
            suggested_action="continue",
        )

    @staticmethod
    def _is_blocking_review(last_review_result) -> bool:
        if last_review_result is None:
            return False
        for issue in list(getattr(last_review_result, "issues", []) or []):
            severity = str(getattr(issue, "severity", "") or "").lower()
            if severity == "blocking":
                return True
        return False
