from __future__ import annotations

from typing import Dict, Any, Optional

from application.agent_mvp.models import (
    ActionType,
    ExecutionContext,
    NextAction,
    TaskContext,
    ToolResult,
    TraceRecord
)
from application.agent_mvp.policy import TerminationPolicy
from application.agent_mvp.validator import ActionValidator


class AgentOrchestrator:
    def __init__(
        self,
        tools: Dict[str, Any],
        termination_policy: Optional[TerminationPolicy] = None,
        action_validator: Optional[ActionValidator] = None
    ):
        self.tools = tools
        self.termination_policy = termination_policy or TerminationPolicy()
        self.action_validator = action_validator or ActionValidator()

    def run(self, task_context: TaskContext, execution_context: ExecutionContext) -> Dict[str, Any]:
        last_result: Optional[ToolResult] = None

        while True:
            should_stop, reason = self.termination_policy.evaluate(task_context, execution_context, last_result)
            if should_stop:
                task_context.traces.append(
                    TraceRecord(
                        step=execution_context.current_step,
                        layer="Decision",
                        data={"action": "TERMINATE", "reason": reason}
                    )
                )
                break

            action = self._plan_next_action(task_context, last_result)
            self._ensure_idempotency_key(action, task_context, execution_context)
            task_context.traces.append(
                TraceRecord(
                    step=execution_context.current_step,
                    layer="Decision",
                    data={
                        "action_type": action.action_type.value,
                        "tool_name": action.tool_name,
                        "tool_input": action.tool_input,
                        "reason": action.reason
                    }
                )
            )

            validation = self.action_validator.validate(action, task_context, execution_context, self.tools)
            if not validation.valid:
                task_context.traces.append(
                    TraceRecord(
                        step=execution_context.current_step,
                        layer="Execution",
                        data={
                            "validator": "ActionValidator",
                            "accepted": False,
                            "reason": validation.reason
                        }
                    )
                )
                task_context.traces.append(
                    TraceRecord(
                        step=execution_context.current_step,
                        layer="Observation",
                        data={
                            "status": "failed",
                            "observation": f"动作被拒绝: {validation.reason}",
                            "progress_made": False,
                            "progress_state": {
                                "no_progress_streak": execution_context.no_progress_streak + 1,
                                "max_no_progress_steps": execution_context.max_no_progress_steps
                            },
                            "error": {"code": "INVALID_ACTION", "message": validation.reason}
                        }
                    )
                )
                execution_context.record_progress(False)
                break

            if action.action_type == ActionType.TERMINATE:
                break

            execution_context.next_step()
            tool = self.tools[action.tool_name or ""]
            max_attempts = execution_context.max_retries_per_action + 1
            result: Optional[ToolResult] = None
            for attempt in range(1, max_attempts + 1):
                task_context.traces.append(
                    TraceRecord(
                        step=execution_context.current_step,
                        layer="Execution",
                        data={
                            "tool_name": action.tool_name,
                            "deadline_at": execution_context.deadline_at.isoformat(),
                            "attempt": attempt,
                            "max_attempts": max_attempts
                        }
                    )
                )
                result = tool.execute(task_context, action.tool_input)
                retryable = self._is_retryable_error(result.error)
                should_retry = (
                    result.status == "failed"
                    and retryable
                    and attempt < max_attempts
                    and not execution_context.deadline_exceeded()
                )
                task_context.traces.append(
                    TraceRecord(
                        step=execution_context.current_step,
                        layer="Observation",
                        data={
                            "status": result.status,
                            "observation": result.observation,
                            "progress_made": result.progress_made,
                            "progress_state": {
                                "no_progress_streak": execution_context.no_progress_streak,
                                "max_no_progress_steps": execution_context.max_no_progress_steps
                            },
                            "retry": {
                                "attempt": attempt,
                                "max_attempts": max_attempts,
                                "retryable": retryable,
                                "will_retry": should_retry
                            },
                            "error": result.error
                        }
                    )
                )
                if not should_retry:
                    break
            if result is None:
                result = ToolResult(status="failed", observation="工具未返回结果", progress_made=False)
            last_result = result
            execution_context.record_progress(result.progress_made)

            if (
                action.tool_name == "RAGSearchTool"
                and result.status == "success"
                and result.payload.get("context_blocks")
            ):
                task_context.context_blocks = list(result.payload["context_blocks"])
                task_context.rag_called_count += 1

            if result.status == "success" and result.progress_made:
                if action.tool_name == "WritingGenerateTool":
                    task_context.final_output = result.payload

        return {
            "request_id": task_context.request_id,
            "final_output": task_context.final_output,
            "trace": [record.__dict__ for record in task_context.traces],
            "steps": execution_context.current_step
        }

    def _plan_next_action(self, task_context: TaskContext, last_result: Optional[ToolResult]) -> NextAction:
        if last_result and last_result.status == "failed":
            return NextAction(action_type=ActionType.TERMINATE, reason="工具执行失败")

        if not task_context.context_blocks and task_context.rag_called_count < 1:
            return NextAction(
                action_type=ActionType.TOOL_CALL,
                tool_name="RAGSearchTool",
                tool_input={"query": task_context.goal},
                reason="上下文为空，先执行一次RAG补充信息"
            )

        return NextAction(
            action_type=ActionType.TOOL_CALL,
            tool_name="WritingGenerateTool",
            tool_input={
                "goal": task_context.goal,
                "target_word_count": task_context.target_word_count,
                "context_blocks": task_context.context_blocks
            },
            reason="MVP默认执行写作生成"
        )

    def _is_retryable_error(self, error: Optional[Dict[str, Any]]) -> bool:
        return bool(error and error.get("is_retryable") is True)

    def _ensure_idempotency_key(
        self,
        action: NextAction,
        task_context: TaskContext,
        execution_context: ExecutionContext
    ) -> None:
        if action.action_type != ActionType.TOOL_CALL or not action.tool_name:
            return
        tool = self.tools.get(action.tool_name)
        if not tool:
            return
        side_effect_type = getattr(tool, "side_effect_type", "read")
        if side_effect_type not in {"write", "external_write"}:
            return
        key = action.tool_input.get("idempotency_key")
        if isinstance(key, str) and key.strip():
            return
        action.tool_input["idempotency_key"] = (
            f"{task_context.request_id}:{action.tool_name}:{execution_context.current_step}"
        )
