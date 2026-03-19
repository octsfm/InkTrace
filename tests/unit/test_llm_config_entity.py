"""
LLM配置实体单元测试

作者：孔利群
"""

import pytest
from datetime import datetime

from domain.entities.llm_config import LLMConfig


class TestLLMConfig:
    """LLM配置实体测试"""
    
    def test_create_llm_config(self):
        """测试创建LLM配置"""
        config = LLMConfig(
            id=1,
            deepseek_api_key="encrypted_deepseek_key",
            kimi_api_key="encrypted_kimi_key",
            encryption_key_hash="hash_value"
        )
        
        assert config.id == 1
        assert config.deepseek_api_key == "encrypted_deepseek_key"
        assert config.kimi_api_key == "encrypted_kimi_key"
        assert config.encryption_key_hash == "hash_value"
        assert config.created_at is not None
        assert config.updated_at is not None
    
    def test_create_llm_config_defaults(self):
        """测试创建LLM配置默认值"""
        config = LLMConfig()
        
        assert config.id is None
        assert config.deepseek_api_key == ""
        assert config.kimi_api_key == ""
        assert config.encryption_key_hash == ""
        assert config.created_at is not None
        assert config.updated_at is not None
    
    def test_post_init_sets_timestamps(self):
        """测试初始化后自动设置时间戳"""
        before = datetime.now()
        config = LLMConfig()
        after = datetime.now()
        
        assert before <= config.created_at <= after
        assert before <= config.updated_at <= after
    
    def test_update_timestamp(self):
        """测试更新时间戳"""
        config = LLMConfig()
        old_updated_at = config.updated_at
        
        # 稍微等待一下确保时间不同
        import time
        time.sleep(0.001)
        
        config.update_timestamp()
        
        assert config.updated_at > old_updated_at
    
    def test_has_valid_config_with_deepseek(self):
        """测试有DeepSeek配置时有效"""
        config = LLMConfig(
            deepseek_api_key="some_key",
            kimi_api_key="",
            encryption_key_hash="hash"
        )
        
        assert config.has_valid_config() is True
    
    def test_has_valid_config_with_kimi(self):
        """测试有Kimi配置时有效"""
        config = LLMConfig(
            deepseek_api_key="",
            kimi_api_key="some_key",
            encryption_key_hash="hash"
        )
        
        assert config.has_valid_config() is True
    
    def test_has_valid_config_with_both(self):
        """测试同时有两个配置时有效"""
        config = LLMConfig(
            deepseek_api_key="deepseek_key",
            kimi_api_key="kimi_key",
            encryption_key_hash="hash"
        )
        
        assert config.has_valid_config() is True
    
    def test_has_valid_config_empty(self):
        """测试空配置无效"""
        config = LLMConfig(
            deepseek_api_key="",
            kimi_api_key="",
            encryption_key_hash="hash"
        )
        
        assert config.has_valid_config() is False
    
    def test_has_valid_config_whitespace_only(self):
        """测试只有空白字符的配置无效"""
        config = LLMConfig(
            deepseek_api_key="   ",
            kimi_api_key="  ",
            encryption_key_hash="hash"
        )
        
        assert config.has_valid_config() is False
    
    def test_validate_success(self):
        """测试验证成功"""
        config = LLMConfig(
            deepseek_api_key="some_key",
            kimi_api_key="",
            encryption_key_hash="hash_value"
        )
        
        assert config.validate() is True
    
    def test_validate_no_api_key(self):
        """测试没有API密钥时验证失败"""
        config = LLMConfig(
            deepseek_api_key="",
            kimi_api_key="",
            encryption_key_hash="hash_value"
        )
        
        assert config.validate() is False
    
    def test_validate_no_encryption_hash(self):
        """测试没有加密哈希时验证失败"""
        config = LLMConfig(
            deepseek_api_key="some_key",
            kimi_api_key="",
            encryption_key_hash=""
        )
        
        assert config.validate() is False
    
    def test_validate_both_conditions_fail(self):
        """测试两个条件都不满足时验证失败"""
        config = LLMConfig(
            deepseek_api_key="",
            kimi_api_key="",
            encryption_key_hash=""
        )
        
        assert config.validate() is False
    
    def test_config_immutability_of_id(self):
        """测试配置ID可以设置"""
        config = LLMConfig(id=1)
        assert config.id == 1
        
        # ID可以被重新设置
        config.id = 2
        assert config.id == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
