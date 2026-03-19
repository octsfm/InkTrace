"""
Agent MVP模块单元测试

作者：孔利群
"""

# 文件路径：tests/unit/test_agent_mvp.py


import pytest
from datetime import datetime, timedelta

from application.agent_mvp.models import (
    ActionType,
    NextAction,
    ToolResult,
    TraceRecord,
    TaskContext,
    ExecutionContext
)
from application.agent_mvp.memory import (
    CharacterMemory,
    PlotThreadMemory,
    StyleProfileMemory,
    NovelMemory,
    merge_memory
)


class TestModels:
    """模型类测试"""
    
    def test_action_type_enum(self):
        """测试动作类型枚举"""
        assert ActionType.TOOL_CALL == "TOOL_CALL"
        assert ActionType.TERMINATE == "TERMINATE"
    
    def test_next_action_tool_call(self):
        """测试工具调用动作"""
        action = NextAction(
            action_type=ActionType.TOOL_CALL,
            tool_name="AnalysisTool",
            tool_input={"mode": "incremental_mode"},
            reason="需要分析文本"
        )
        assert action.action_type == ActionType.TOOL_CALL
        assert action.tool_name == "AnalysisTool"
        assert action.tool_input == {"mode": "incremental_mode"}
        assert action.reason == "需要分析文本"
    
    def test_next_action_terminate(self):
        """测试终止动作"""
        action = NextAction(
            action_type=ActionType.TERMINATE,
            reason="任务完成"
        )
        assert action.action_type == ActionType.TERMINATE
        assert action.tool_name is None
    
    def test_tool_result_success(self):
        """测试工具结果成功"""
        result = ToolResult(
            status="success",
            payload={"chapters": []},
            observation="分析完成",
            progress_made=True
        )
        assert result.status == "success"
        assert result.progress_made is True
    
    def test_tool_result_failed(self):
        """测试工具结果失败"""
        result = ToolResult(
            status="failed",
            error={"code": "INVALID_INPUT", "message": "输入无效"},
            observation="输入验证失败",
            progress_made=False
        )
        assert result.status == "failed"
        assert result.error["code"] == "INVALID_INPUT"
    
    def test_trace_record(self):
        """测试追踪记录"""
        record = TraceRecord(
            step=1,
            layer="tool",
            data={"tool": "AnalysisTool"}
        )
        assert record.step == 1
        assert record.layer == "tool"
    
    def test_task_context(self):
        """测试任务上下文"""
        context = TaskContext(
            novel_id="novel_123",
            goal="续写下一章",
            target_word_count=800
        )
        assert context.novel_id == "novel_123"
        assert context.goal == "续写下一章"
        assert context.target_word_count == 800
        assert context.rag_called_count == 0
        assert context.final_output is None
    
    def test_execution_context_defaults(self):
        """测试执行上下文默认值"""
        context = ExecutionContext()
        assert context.timeout_seconds == 20
        assert context.max_steps == 3
        assert context.max_no_progress_steps == 2
        assert context.current_step == 0
        assert context.no_progress_streak == 0
    
    def test_execution_context_deadline(self):
        """测试执行上下文截止时间"""
        context = ExecutionContext(timeout_seconds=10)
        deadline = context.deadline_at
        assert deadline > datetime.now()
        assert deadline <= datetime.now() + timedelta(seconds=10)
    
    def test_execution_context_can_execute(self):
        """测试执行上下文是否可执行"""
        context = ExecutionContext()
        assert context.can_execute() is True
        
        context.current_step = context.max_steps
        assert context.can_execute() is False
    
    def test_execution_context_record_progress(self):
        """测试记录进度"""
        context = ExecutionContext()
        context.record_progress(True)
        assert context.no_progress_streak == 0
        
        context.record_progress(False)
        assert context.no_progress_streak == 1
        
        context.record_progress(False)
        assert context.no_progress_streak == 2
    
    def test_execution_context_no_progress_exceeded(self):
        """测试无进度超限"""
        context = ExecutionContext(max_no_progress_steps=2)
        assert context.no_progress_exceeded() is False
        
        context.record_progress(False)
        context.record_progress(False)
        assert context.no_progress_exceeded() is True


class TestMemory:
    """记忆模块测试"""
    
    def test_character_memory_merge_traits(self):
        """测试角色记忆合并特征"""
        memory = CharacterMemory(name="张三")
        memory.merge({"traits": ["勇敢", "聪明"]})
        assert "勇敢" in memory.traits
        assert "聪明" in memory.traits
        assert len(memory.traits) == 2
    
    def test_character_memory_merge_relationships(self):
        """测试角色记忆合并关系"""
        memory = CharacterMemory(name="张三")
        memory.merge({"relationships": {"李四": "朋友", "王五": "敌人"}})
        assert memory.relationships["李四"] == "朋友"
        assert memory.relationships["王五"] == "敌人"
    
    def test_character_memory_no_duplicates(self):
        """测试角色记忆不重复"""
        memory = CharacterMemory(name="张三")
        memory.merge({"traits": ["勇敢"]})
        memory.merge({"traits": ["勇敢"]})
        assert len(memory.traits) == 1
    
    def test_plot_thread_memory_merge(self):
        """测试剧情线记忆合并"""
        memory = PlotThreadMemory(title="主线剧情")
        memory.merge({"description": "主角开始冒险"})
        assert "主角开始冒险" in memory.points
        
        memory.merge({"status": "ongoing"})
        assert memory.status == "ongoing"
    
    def test_style_profile_memory_merge(self):
        """测试风格档案记忆合并"""
        memory = StyleProfileMemory()
        memory.merge({"tone": "紧张", "pacing": "快速"})
        assert memory.tone == "紧张"
        assert memory.pacing == "快速"
    
    def test_novel_memory_init(self):
        """测试小说记忆初始化"""
        memory = NovelMemory()
        assert memory._characters == {}
        assert memory._world_settings == []
        assert memory._plot_threads == {}
    
    def test_novel_memory_merge_analysis(self):
        """测试小说记忆合并分析"""
        memory = NovelMemory()
        result = memory.merge_analysis({
            "characters": [{"name": "张三", "traits": ["勇敢"]}],
            "world_settings": ["修仙世界"],
            "plot_outline": [{"title": "主线", "description": "主角成长"}]
        })
        assert "characters" in result
        assert len(result["characters"]) == 1
        assert result["characters"][0]["name"] == "张三"
    
    def test_novel_memory_update_character_relationship(self):
        """测试更新角色关系"""
        memory = NovelMemory()
        result = memory.update_character_relationship("张三", "李四", "朋友")
        assert "张三" in memory._characters
        assert memory._characters["张三"].relationships["李四"] == "朋友"
    
    def test_novel_memory_add_world_setting(self):
        """测试添加世界设定"""
        memory = NovelMemory()
        memory.add_world_setting("修仙世界")
        assert "修仙世界" in memory._world_settings
    
    def test_novel_memory_to_agent_context(self):
        """测试转换为Agent上下文"""
        memory = NovelMemory()
        memory.add_world_setting("修仙世界")
        memory.update_character_relationship("张三", "李四", "朋友")
        
        context = memory.to_agent_context()
        assert "characters" in context
        assert "world_settings" in context
        assert "plot_outline" in context
        assert "writing_style" in context
    
    def test_merge_memory_function(self):
        """测试合并记忆函数"""
        old_memory = {
            "characters": [{"name": "张三", "traits": ["勇敢"]}],
            "world_settings": ["修仙世界"]
        }
        new_memory = {
            "characters": [{"name": "张三", "traits": ["聪明"]}],
            "world_settings": ["仙界"]
        }
        
        merged = merge_memory(old_memory, new_memory)
        assert "张三" in [c["name"] for c in merged["characters"]]
        assert "修仙世界" in merged["world_settings"]
        assert "仙界" in merged["world_settings"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
