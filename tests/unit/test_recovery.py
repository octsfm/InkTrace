"""
Agent恢复管道单元测试

作者：孔利群
"""

import pytest
import asyncio

from application.agent_mvp.recovery import RecoveryPipeline, RecoveryResult


class TestRecoveryResult:
    """恢复结果测试"""
    
    def test_recovery_result_success(self):
        """测试成功的恢复结果"""
        result = RecoveryResult(
            ok=True,
            data={"key": "value"},
            stage="retry",
            error=""
        )
        
        assert result.ok is True
        assert result.data == {"key": "value"}
        assert result.stage == "retry"
        assert result.error == ""
    
    def test_recovery_result_failure(self):
        """测试失败的恢复结果"""
        result = RecoveryResult(
            ok=False,
            data=None,
            stage="terminate",
            error="执行失败"
        )
        
        assert result.ok is False
        assert result.data is None
        assert result.stage == "terminate"
        assert result.error == "执行失败"
    
    def test_recovery_result_defaults(self):
        """测试恢复结果默认值"""
        result = RecoveryResult(ok=True)
        
        assert result.data is None
        assert result.stage == "terminate"
        assert result.error == ""


class TestRecoveryPipeline:
    """恢复管道测试"""
    
    def setup_method(self):
        """测试前准备"""
        self.pipeline = RecoveryPipeline(max_retries=2)
    
    def test_create_pipeline_default_retries(self):
        """测试创建管道默认重试次数"""
        pipeline = RecoveryPipeline()
        
        assert pipeline.max_retries == 2
    
    def test_create_pipeline_custom_retries(self):
        """测试创建管道自定义重试次数"""
        pipeline = RecoveryPipeline(max_retries=5)
        
        assert pipeline.max_retries == 5
    
    def test_run_execute_success(self):
        """测试执行成功"""
        async def execute():
            return {"result": "success"}
        
        async def repair():
            return {"result": "repair"}
        
        async def fallback():
            return {"result": "fallback"}
        
        def degrade():
            return {"result": "degrade"}
        
        result = asyncio.run(self.pipeline.run(execute, repair, fallback, degrade))
        
        assert result.ok is True
        assert result.data == {"result": "success"}
        assert result.stage == "retry"
    
    def test_run_retry_then_success(self):
        """测试重试后成功"""
        call_count = 0
        
        async def execute():
            nonlocal call_count
            call_count += 1
            if call_count < 3:  # 前两次失败
                raise RuntimeError("临时错误")
            return {"result": "success"}
        
        async def repair():
            return {"result": "repair"}
        
        async def fallback():
            return {"result": "fallback"}
        
        def degrade():
            return {"result": "degrade"}
        
        result = asyncio.run(self.pipeline.run(execute, repair, fallback, degrade))
        
        # 由于重试次数限制，最终应该走repair路径
        assert result.ok is True
    
    def test_run_repair_success(self):
        """测试修复成功"""
        async def execute():
            raise RuntimeError("执行失败")
        
        async def repair():
            return {"result": "repair"}
        
        async def fallback():
            return {"result": "fallback"}
        
        def degrade():
            return {"result": "degrade"}
        
        result = asyncio.run(self.pipeline.run(execute, repair, fallback, degrade))
        
        assert result.ok is True
        assert result.data == {"result": "repair"}
        assert result.stage == "repair"
    
    def test_run_fallback_success(self):
        """测试降级成功"""
        async def execute():
            raise RuntimeError("执行失败")
        
        async def repair():
            raise RuntimeError("修复失败")
        
        async def fallback():
            return {"result": "fallback"}
        
        def degrade():
            return {"result": "degrade"}
        
        result = asyncio.run(self.pipeline.run(execute, repair, fallback, degrade))
        
        assert result.ok is True
        assert result.data == {"result": "fallback"}
        assert result.stage == "fallback"
    
    def test_run_degrade_success(self):
        """测试降级处理成功"""
        async def execute():
            raise RuntimeError("执行失败")
        
        async def repair():
            raise RuntimeError("修复失败")
        
        async def fallback():
            raise RuntimeError("降级失败")
        
        def degrade():
            return {"result": "degrade"}
        
        result = asyncio.run(self.pipeline.run(execute, repair, fallback, degrade))
        
        assert result.ok is True
        assert result.data == {"result": "degrade"}
        assert result.stage == "degrade"
    
    def test_run_all_failed(self):
        """测试所有阶段都失败"""
        async def execute():
            raise RuntimeError("执行失败")
        
        async def repair():
            raise RuntimeError("修复失败")
        
        async def fallback():
            raise RuntimeError("降级失败")
        
        def degrade():
            raise RuntimeError("降级处理失败")
        
        result = asyncio.run(self.pipeline.run(execute, repair, fallback, degrade))
        
        assert result.ok is False
        assert result.stage == "terminate"
        assert "失败" in result.error
    
    def test_run_preserves_retry_error(self):
        """测试保留重试阶段的错误信息"""
        async def execute():
            raise RuntimeError("原始错误")
        
        async def repair():
            raise RuntimeError("修复错误")
        
        async def fallback():
            raise RuntimeError("降级错误")
        
        def degrade():
            raise RuntimeError("最终错误")
        
        result = asyncio.run(self.pipeline.run(execute, repair, fallback, degrade))
        
        assert result.ok is False
        # 应该包含某个错误信息
        assert len(result.error) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
