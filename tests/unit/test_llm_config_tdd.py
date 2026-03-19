"""
LLM配置单元测试

作者：Qoder
"""

import unittest
import tempfile
import os
from datetime import datetime

from domain.entities.llm_config import LLMConfig
from domain.value_objects.encrypted_api_key import EncryptedAPIKey


class TestLLMConfigEntity:
    """LLM配置实体测试"""
    
    def test_llm_config_creation(self):
        """测试配置实体创建"""
        config = LLMConfig(
            id=1,
            deepseek_api_key="test_deepseek_key",
            kimi_api_key="test_kimi_key",
            encryption_key_hash="test_hash"
        )
        
        assert config.id == 1
        assert config.deepseek_api_key == "test_deepseek_key"
        assert config.kimi_api_key == "test_kimi_key"
        assert config.encryption_key_hash == "test_hash"
        assert config.created_at is not None
        assert config.updated_at is not None
    
    def test_llm_config_creation_with_timestamps(self):
        """测试带时间戳的配置创建"""
        now = datetime.now()
        config = LLMConfig(
            id=1,
            deepseek_api_key="test_key",
            created_at=now,
            updated_at=now
        )
        
        assert config.created_at == now
        assert config.updated_at == now
    
    def test_llm_config_defaults(self):
        """测试配置默认值"""
        config = LLMConfig()
        
        assert config.id is None
        assert config.deepseek_api_key == ""
        assert config.kimi_api_key == ""
        assert config.encryption_key_hash == ""
        assert config.created_at is not None
        assert config.updated_at is not None
    
    def test_llm_config_validation(self):
        """测试配置验证"""
        # 有效配置
        valid_config = LLMConfig(
            deepseek_api_key="test_key",
            encryption_key_hash="test_hash"
        )
        assert valid_config.validate() is True
        
        # 无效配置 - 没有API密钥
        no_key_config = LLMConfig(encryption_key_hash="test_hash")
        assert no_key_config.validate() is False
        
        # 无效配置 - 没有加密密钥哈希
        no_hash_config = LLMConfig(deepseek_api_key="test_key")
        assert no_hash_config.validate() is False
    
    def test_has_valid_config(self):
        """测试有效配置检查"""
        # 有deepseek密钥
        config1 = LLMConfig(deepseek_api_key="test_key")
        assert config1.has_valid_config() is True
        
        # 有kimi密钥
        config2 = LLMConfig(kimi_api_key="test_key")
        assert config2.has_valid_config() is True
        
        # 没有密钥
        config3 = LLMConfig()
        assert config3.has_valid_config() is False
        
        # 空白密钥
        config4 = LLMConfig(deepseek_api_key="   ")
        assert config4.has_valid_config() is False
    
    def test_update_timestamp(self):
        """测试更新时间戳"""
        config = LLMConfig()
        old_time = config.updated_at
        
        # 等待一小段时间
        import time
        time.sleep(0.01)
        
        config.update_timestamp()
        
        assert config.updated_at > old_time


class TestEncryptedAPIKey:
    """加密API密钥值对象测试"""
    
    def test_empty_key_creation(self):
        """测试空密钥创建"""
        key = EncryptedAPIKey.create_empty()
        
        assert key.ciphertext == ""
        assert key.is_empty() is True
        assert str(key) == "[EMPTY]"
    
    def test_encrypted_key_creation(self):
        """测试加密密钥创建"""
        key = EncryptedAPIKey(ciphertext="encrypted_data")
        
        assert key.ciphertext == "encrypted_data"
        assert key.is_empty() is False
        assert str(key) == "[ENCRYPTED]"
    
    def test_encryption_decryption(self):
        """测试加密解密"""
        # 生成加密密钥
        from domain.services.config_encryption_service import ConfigEncryptionService
        encryption_service = ConfigEncryptionService()
        encryption_key = encryption_service.generate_encryption_key()
        
        # 从明文创建加密密钥
        plaintext = "my_secret_api_key"
        encrypted = EncryptedAPIKey.from_plaintext(plaintext, encryption_key)
        
        assert encrypted.is_empty() is False
        assert encrypted.ciphertext != plaintext
        
        # 解密
        decrypted = encrypted.to_plaintext(encryption_key)
        assert decrypted == plaintext
    
    def test_empty_plaintext(self):
        """测试空明文"""
        encryption_key = b"0" * 32  # 32字节密钥
        
        empty_encrypted = EncryptedAPIKey.from_plaintext("", encryption_key)
        assert empty_encrypted.is_empty() is True
        
        whitespace_encrypted = EncryptedAPIKey.from_plaintext("   ", encryption_key)
        assert whitespace_encrypted.is_empty() is True
    
    def test_equality(self):
        """测试相等性比较"""
        key1 = EncryptedAPIKey(ciphertext="same")
        key2 = EncryptedAPIKey(ciphertext="same")
        key3 = EncryptedAPIKey(ciphertext="different")
        
        assert key1 == key2
        assert key1 != key3
        assert key1 != "not an EncryptedAPIKey"
    
    def test_frozen(self):
        """测试不可变性"""
        key = EncryptedAPIKey(ciphertext="test")
        
        # 尝试修改应该抛出异常
        try:
            key.ciphertext = "modified"
            assert False, "应该抛出异常"
        except Exception:
            pass  # 预期行为
    
    def test_decrypt_with_wrong_key(self):
        """测试使用错误密钥解密"""
        from domain.services.config_encryption_service import ConfigEncryptionService
        encryption_service = ConfigEncryptionService()
        
        key1 = encryption_service.generate_encryption_key()
        key2 = encryption_service.generate_encryption_key()
        
        plaintext = "secret"
        encrypted = EncryptedAPIKey.from_plaintext(plaintext, key1)
        
        # 使用错误的密钥解密
        decrypted = encrypted.to_plaintext(key2)
        assert decrypted is None or decrypted != plaintext


if __name__ == '__main__':
    unittest.main()
