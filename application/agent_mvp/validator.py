from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

from application.agent_mvp.models import ActionType, ExecutionContext, NextAction, TaskContext


@dataclass
class ValidationResult:
    valid: bool
    reason: str = ""


class ActionValidator:
    def validate(
        self,
        action: NextAction,
        task_context: TaskContext,
        execution_context: ExecutionContext,
        tools: Dict[str, Any]
    ) -> ValidationResult:
        if execution_context.deadline_exceeded():
            return ValidationResult(valid=False, reason="deadline已超时")
        if execution_context.step_exceeded():
            return ValidationResult(valid=False, reason="step_count已达上限")
        if action.action_type == ActionType.TERMINATE:
            return ValidationResult(valid=True)
        if action.action_type != ActionType.TOOL_CALL:
            return ValidationResult(valid=False, reason="不支持的动作类型")
        if not action.tool_name:
            return ValidationResult(valid=False, reason="TOOL_CALL缺少tool_name")
        if action.tool_name not in tools:
            return ValidationResult(valid=False, reason=f"工具不存在: {action.tool_name}")
        if not isinstance(action.tool_input, dict):
            return ValidationResult(valid=False, reason="tool_input必须是字典")
        tool = tools[action.tool_name]
        side_effect_type = getattr(tool, "side_effect_type", "read")
        if side_effect_type in {"write", "external_write"}:
            idempotency_key = action.tool_input.get("idempotency_key")
            if not isinstance(idempotency_key, str) or not idempotency_key.strip():
                return ValidationResult(valid=False, reason="写操作缺少idempotency_key")
        if not task_context.goal.strip():
            return ValidationResult(valid=False, reason="task_context.goal不能为空")
        return ValidationResult(valid=True)
