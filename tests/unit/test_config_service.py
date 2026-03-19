"""
配置管理服务单元测试

作者：孔利群
"""

import pytest
import os
from unittest.mock import Mock, MagicMock, patch

from application.services.config_service import ConfigService
from domain.entities.llm_config import LLMConfig


class TestConfigService:
    """配置管理服务测试"""
    
    def setup_method(self):
        """测试前准备"""
        self.mock_repository = Mock()
        self.encryption_key = os.urandom(32)
        self.service = ConfigService(self.mock_repository, self.encryption_key)
    
    def test_save_config(self):
        """测试保存配置"""
        self.mock_repository.save.return_value = LLMConfig(
            id=1,
            deepseek_api_key="encrypted_deepseek",
            kimi_api_key="encrypted_kimi",
            encryption_key_hash="hash"
        )
        
        result = self.service.save_config("deepseek_key", "kimi_key")
        
        assert result is not None
        self.mock_repository.save.assert_called_once()
    
    def test_get_config(self):
        """测试获取配置"""
        mock_config = LLMConfig(
            id=1,
            deepseek_api_key="encrypted",
            kimi_api_key="encrypted",
            encryption_key_hash=self.service.encryption_key.hex() if hasattr(self.service, 'encryption_key') else ""
        )
        # 修正：使用正确的hash
        import hashlib
        correct_hash = hashlib.sha256(self.encryption_key).hexdigest()
        mock_config.encryption_key_hash = correct_hash
        
        self.mock_repository.get.return_value = mock_config
        
        result = self.service.get_config()
        
        assert result is not None
        self.mock_repository.get.assert_called_once()
    
    def test_get_config_not_found(self):
        """测试获取不存在的配置"""
        self.mock_repository.get.return_value = None
        
        result = self.service.get_config()
        
        assert result is None
    
    def test_get_config_key_mismatch(self):
        """测试获取配置时密钥不匹配"""
        mock_config = LLMConfig(
            id=1,
            deepseek_api_key="encrypted",
            kimi_api_key="encrypted",
            encryption_key_hash="wrong_hash"
        )
        
        self.mock_repository.get.return_value = mock_config
        
        with pytest.raises(ValueError, match="加密密钥不匹配"):
            self.service.get_config()
    
    def test_get_decrypted_config(self):
        """测试获取解密后的配置"""
        # 先保存一个配置
        original_deepseek = "my_deepseek_key"
        original_kimi = "my_kimi_key"
        
        # 加密
        encrypted_deepseek = self.service.aes_encryption.encrypt(original_deepseek, self.encryption_key)
        encrypted_kimi = self.service.aes_encryption.encrypt(original_kimi, self.encryption_key)
        
        import hashlib
        correct_hash = hashlib.sha256(self.encryption_key).hexdigest()
        
        mock_config = LLMConfig(
            id=1,
            deepseek_api_key=encrypted_deepseek,
            kimi_api_key=encrypted_kimi,
            encryption_key_hash=correct_hash
        )
        
        self.mock_repository.get.return_value = mock_config
        
        result = self.service.get_decrypted_config()
        
        assert result is not None
        deepseek, kimi = result
        assert deepseek == original_deepseek
        assert kimi == original_kimi
    
    def test_get_decrypted_config_not_found(self):
        """测试获取解密配置不存在"""
        self.mock_repository.get.return_value = None
        
        result = self.service.get_decrypted_config()
        
        assert result is None
    
    def test_config_exists_true(self):
        """测试配置存在"""
        self.mock_repository.exists.return_value = True
        
        result = self.service.config_exists()
        
        assert result is True
        self.mock_repository.exists.assert_called_once()
    
    def test_config_exists_false(self):
        """测试配置不存在"""
        self.mock_repository.exists.return_value = False
        
        result = self.service.config_exists()
        
        assert result is False
    
    def test_delete_config(self):
        """测试删除配置"""
        self.mock_repository.delete.return_value = True
        
        result = self.service.delete_config()
        
        assert result is True
        self.mock_repository.delete.assert_called_once()
    
    def test_validate_config_valid(self):
        """测试验证有效配置"""
        valid_key = "sk12345678901234567890"  # 22个字符，包含字母和数字
        
        result = self.service.validate_config(valid_key, "")
        
        assert result is True
    
    def test_validate_config_both_keys(self):
        """测试验证两个密钥"""
        valid_key1 = "sk12345678901234567890"
        valid_key2 = "mk12345678901234567890"
        
        result = self.service.validate_config(valid_key1, valid_key2)
        
        assert result is True
    
    def test_validate_config_empty(self):
        """测试验证空配置"""
        result = self.service.validate_config("", "")
        
        assert result is False
    
    def test_validate_config_too_short(self):
        """测试验证过短的密钥"""
        short_key = "short"
        
        result = self.service.validate_config(short_key, "")
        
        assert result is False
    
    def test_validate_config_too_long(self):
        """测试验证过长的密钥"""
        long_key = "a" * 101
        
        result = self.service.validate_config(long_key, "")
        
        assert result is False
    
    def test_validate_config_no_letter(self):
        """测试验证没有字母的密钥"""
        no_letter_key = "12345678901234567890"
        
        result = self.service.validate_config(no_letter_key, "")
        
        assert result is False
    
    def test_validate_config_no_digit(self):
        """测试验证没有数字的密钥"""
        no_digit_key = "abcdefghijklmnopqrst"
        
        result = self.service.validate_config(no_digit_key, "")
        
        assert result is False
    
    def test_test_connection_both_keys(self):
        """测试连接测试两个密钥"""
        result = self.service.test_connection("deepseek_key", "kimi_key")
        
        assert result['deepseek']['success'] is True
        assert result['kimi']['success'] is True
    
    def test_test_connection_deepseek_only(self):
        """测试连接测试只有DeepSeek密钥"""
        result = self.service.test_connection("deepseek_key", "")
        
        assert result['deepseek']['success'] is True
        assert result['kimi']['success'] is False
        assert "未配置" in result['kimi']['message']
    
    def test_test_connection_kimi_only(self):
        """测试连接测试只有Kimi密钥"""
        result = self.service.test_connection("", "kimi_key")
        
        assert result['deepseek']['success'] is False
        assert result['kimi']['success'] is True
        assert "未配置" in result['deepseek']['message']
    
    def test_test_connection_no_keys(self):
        """测试连接测试没有密钥"""
        result = self.service.test_connection("", "")
        
        assert result['deepseek']['success'] is False
        assert result['kimi']['success'] is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
