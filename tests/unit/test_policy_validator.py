"""
Agent策略和验证器单元测试

作者：孔利群
"""

import pytest
from datetime import datetime, timedelta

from application.agent_mvp.policy import TerminationPolicy
from application.agent_mvp.validator import ActionValidator, ValidationResult
from application.agent_mvp.models import (
    ActionType,
    NextAction,
    TaskContext,
    ExecutionContext,
    ToolResult
)


class TestTerminationPolicy:
    """终止策略测试"""
    
    def setup_method(self):
        """测试前准备"""
        self.policy = TerminationPolicy()
    
    def test_evaluate_task_completed(self):
        """测试任务已完成"""
        task_context = TaskContext(
            novel_id="novel_001",
            goal="续写章节",
            final_output={"content": "章节内容"}
        )
        execution_context = ExecutionContext()
        
        should_stop, reason = self.policy.evaluate(task_context, execution_context, None)
        
        assert should_stop is True
        assert reason == "任务已完成"
    
    def test_evaluate_deadline_exceeded(self):
        """测试超过截止时间"""
        task_context = TaskContext(novel_id="novel_001", goal="续写章节")
        execution_context = ExecutionContext(timeout_seconds=-1)  # 已经过期
        
        should_stop, reason = self.policy.evaluate(task_context, execution_context, None)
        
        assert should_stop is True
        assert reason == "超过deadline"
    
    def test_evaluate_step_exceeded(self):
        """测试超过最大步数"""
        task_context = TaskContext(novel_id="novel_001", goal="续写章节")
        execution_context = ExecutionContext()
        execution_context.current_step = execution_context.max_steps
        
        should_stop, reason = self.policy.evaluate(task_context, execution_context, None)
        
        assert should_stop is True
        assert reason == "超过最大步数"
    
    def test_evaluate_no_progress_exceeded(self):
        """测试连续无进展"""
        task_context = TaskContext(novel_id="novel_001", goal="续写章节")
        execution_context = ExecutionContext(max_no_progress_steps=2)
        execution_context.record_progress(False)
        execution_context.record_progress(False)
        
        should_stop, reason = self.policy.evaluate(task_context, execution_context, None)
        
        assert should_stop is True
        assert "连续" in reason
        assert "无进展" in reason
    
    def test_evaluate_failed_result_no_progress(self):
        """测试工具执行失败且无进展"""
        task_context = TaskContext(novel_id="novel_001", goal="续写章节")
        execution_context = ExecutionContext()
        last_result = ToolResult(
            status="failed",
            observation="执行失败",
            progress_made=False
        )
        
        should_stop, reason = self.policy.evaluate(task_context, execution_context, last_result)
        
        assert should_stop is True
        assert "失败" in reason
    
    def test_evaluate_should_continue(self):
        """测试应该继续执行"""
        task_context = TaskContext(novel_id="novel_001", goal="续写章节")
        execution_context = ExecutionContext()
        
        should_stop, reason = self.policy.evaluate(task_context, execution_context, None)
        
        assert should_stop is False
        assert reason == ""


class TestValidationResult:
    """验证结果测试"""
    
    def test_validation_result_valid(self):
        """测试有效验证结果"""
        result = ValidationResult(valid=True)
        
        assert result.valid is True
        assert result.reason == ""
    
    def test_validation_result_invalid(self):
        """测试无效验证结果"""
        result = ValidationResult(valid=False, reason="工具不存在")
        
        assert result.valid is False
        assert result.reason == "工具不存在"


class TestActionValidator:
    """动作验证器测试"""
    
    def setup_method(self):
        """测试前准备"""
        self.validator = ActionValidator()
        
        # 创建模拟工具
        self.mock_read_tool = type('MockTool', (), {
            'name': 'ReadTool',
            'side_effect_type': 'read'
        })()
        
        self.mock_write_tool = type('MockTool', (), {
            'name': 'WriteTool',
            'side_effect_type': 'write'
        })()
        
        self.tools = {
            'ReadTool': self.mock_read_tool,
            'WriteTool': self.mock_write_tool
        }
    
    def test_validate_terminate_action(self):
        """测试验证终止动作"""
        task_context = TaskContext(novel_id="novel_001", goal="续写章节")
        execution_context = ExecutionContext()
        action = NextAction(action_type=ActionType.TERMINATE, reason="任务完成")
        
        result = self.validator.validate(action, task_context, execution_context, self.tools)
        
        assert result.valid is True
    
    def test_validate_tool_call_valid(self):
        """测试验证有效的工具调用"""
        task_context = TaskContext(novel_id="novel_001", goal="续写章节")
        execution_context = ExecutionContext()
        action = NextAction(
            action_type=ActionType.TOOL_CALL,
            tool_name="ReadTool",
            tool_input={"query": "test"},
            reason="需要读取数据"
        )
        
        result = self.validator.validate(action, task_context, execution_context, self.tools)
        
        assert result.valid is True
    
    def test_validate_tool_call_missing_tool_name(self):
        """测试工具调用缺少工具名称"""
        task_context = TaskContext(novel_id="novel_001", goal="续写章节")
        execution_context = ExecutionContext()
        action = NextAction(
            action_type=ActionType.TOOL_CALL,
            tool_input={"query": "test"},
            reason="缺少工具名"
        )
        
        result = self.validator.validate(action, task_context, execution_context, self.tools)
        
        assert result.valid is False
        assert "tool_name" in result.reason
    
    def test_validate_tool_call_nonexistent_tool(self):
        """测试调用不存在的工具"""
        task_context = TaskContext(novel_id="novel_001", goal="续写章节")
        execution_context = ExecutionContext()
        action = NextAction(
            action_type=ActionType.TOOL_CALL,
            tool_name="NonExistentTool",
            tool_input={"query": "test"},
            reason="调用不存在的工具"
        )
        
        result = self.validator.validate(action, task_context, execution_context, self.tools)
        
        assert result.valid is False
        assert "不存在" in result.reason
    
    def test_validate_tool_call_invalid_tool_input(self):
        """测试工具输入不是字典"""
        task_context = TaskContext(novel_id="novel_001", goal="续写章节")
        execution_context = ExecutionContext()
        action = NextAction(
            action_type=ActionType.TOOL_CALL,
            tool_name="ReadTool",
            tool_input="not_a_dict",
            reason="无效输入"
        )
        
        result = self.validator.validate(action, task_context, execution_context, self.tools)
        
        assert result.valid is False
        assert "字典" in result.reason
    
    def test_validate_write_tool_missing_idempotency_key(self):
        """测试写工具缺少幂等键"""
        task_context = TaskContext(novel_id="novel_001", goal="续写章节")
        execution_context = ExecutionContext()
        action = NextAction(
            action_type=ActionType.TOOL_CALL,
            tool_name="WriteTool",
            tool_input={"content": "test"},
            reason="写入数据"
        )
        
        result = self.validator.validate(action, task_context, execution_context, self.tools)
        
        assert result.valid is False
        assert "idempotency_key" in result.reason
    
    def test_validate_write_tool_with_idempotency_key(self):
        """测试写工具有幂等键"""
        task_context = TaskContext(novel_id="novel_001", goal="续写章节")
        execution_context = ExecutionContext()
        action = NextAction(
            action_type=ActionType.TOOL_CALL,
            tool_name="WriteTool",
            tool_input={"content": "test", "idempotency_key": "key_001"},
            reason="写入数据"
        )
        
        result = self.validator.validate(action, task_context, execution_context, self.tools)
        
        assert result.valid is True
    
    def test_validate_empty_goal(self):
        """测试空目标"""
        task_context = TaskContext(novel_id="novel_001", goal="   ")
        execution_context = ExecutionContext()
        action = NextAction(
            action_type=ActionType.TOOL_CALL,
            tool_name="ReadTool",
            tool_input={"query": "test"},
            reason="读取数据"
        )
        
        result = self.validator.validate(action, task_context, execution_context, self.tools)
        
        assert result.valid is False
        assert "goal" in result.reason
    
    def test_validate_deadline_exceeded(self):
        """测试截止时间已过"""
        task_context = TaskContext(novel_id="novel_001", goal="续写章节")
        execution_context = ExecutionContext(timeout_seconds=-1)
        action = NextAction(
            action_type=ActionType.TOOL_CALL,
            tool_name="ReadTool",
            tool_input={"query": "test"},
            reason="读取数据"
        )
        
        result = self.validator.validate(action, task_context, execution_context, self.tools)
        
        assert result.valid is False
        assert "deadline" in result.reason
    
    def test_validate_step_exceeded(self):
        """测试步数超限"""
        task_context = TaskContext(novel_id="novel_001", goal="续写章节")
        execution_context = ExecutionContext()
        execution_context.current_step = execution_context.max_steps
        action = NextAction(
            action_type=ActionType.TOOL_CALL,
            tool_name="ReadTool",
            tool_input={"query": "test"},
            reason="读取数据"
        )
        
        result = self.validator.validate(action, task_context, execution_context, self.tools)
        
        assert result.valid is False
        assert "step" in result.reason.lower() or "上限" in result.reason
    
    def test_validate_unsupported_action_type(self):
        """测试不支持的动作类型"""
        # 创建一个模拟的不支持的动作类型
        task_context = TaskContext(novel_id="novel_001", goal="续写章节")
        execution_context = ExecutionContext()
        action = NextAction(
            action_type="UNSUPPORTED_TYPE",  # 不支持的动作类型
            tool_name="ReadTool",
            tool_input={"query": "test"},
            reason="不支持的类型"
        )
        action.action_type = "UNSUPPORTED_TYPE"  # 强制设置
        
        result = self.validator.validate(action, task_context, execution_context, self.tools)
        
        assert result.valid is False
        assert "不支持" in result.reason


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
