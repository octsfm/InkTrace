from __future__ import annotations

from typing import Optional, Tuple

from application.agent_mvp.models import ExecutionContext, TaskContext, ToolResult


class TerminationPolicy:
    def evaluate(
        self,
        task_context: TaskContext,
        execution_context: ExecutionContext,
        last_result: Optional[ToolResult]
    ) -> Tuple[bool, str]:
        if task_context.final_output is not None:
            return True, "任务已完成"
        if execution_context.deadline_exceeded():
            return True, "超过deadline"
        if execution_context.step_exceeded():
            return True, "超过最大步数"
        if execution_context.no_progress_exceeded():
            return True, f"连续{execution_context.no_progress_streak}次无进展"
        if last_result and last_result.status == "failed" and not last_result.progress_made:
            return True, "工具执行失败且无进展"
        return False, ""
