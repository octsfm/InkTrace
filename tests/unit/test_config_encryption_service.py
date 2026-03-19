"""
配置加密服务单元测试

作者：孔利群
"""

import pytest
import os

from domain.services.config_encryption_service import ConfigEncryptionService


class TestConfigEncryptionService:
    """配置加密服务测试"""
    
    def setup_method(self):
        """测试前准备"""
        self.encryption_service = ConfigEncryptionService()
        self.test_key = os.urandom(32)
    
    def test_create_encryption_service_default_salt(self):
        """测试创建加密服务默认盐值"""
        service = ConfigEncryptionService()
        
        assert service.salt == b"inktrace_config_salt"
    
    def test_create_encryption_service_custom_salt(self):
        """测试创建加密服务自定义盐值"""
        custom_salt = b"custom_salt_value"
        service = ConfigEncryptionService(salt=custom_salt)
        
        assert service.salt == custom_salt
    
    def test_derive_key(self):
        """测试从密码派生密钥"""
        password = "test_password_123"
        
        key = self.encryption_service.derive_key(password)
        
        assert len(key) == 32
        assert isinstance(key, bytes)
    
    def test_derive_key_consistent(self):
        """测试相同密码派生相同密钥"""
        password = "test_password_123"
        
        key1 = self.encryption_service.derive_key(password)
        key2 = self.encryption_service.derive_key(password)
        
        assert key1 == key2
    
    def test_encrypt(self):
        """测试加密"""
        plaintext = "my_secret_api_key"
        
        ciphertext = self.encryption_service.encrypt(plaintext, self.test_key)
        
        assert ciphertext != plaintext
        assert isinstance(ciphertext, str)
    
    def test_encrypt_empty_string(self):
        """测试加密空字符串"""
        ciphertext = self.encryption_service.encrypt("", self.test_key)
        
        assert ciphertext == ""
    
    def test_decrypt(self):
        """测试解密"""
        plaintext = "my_secret_api_key"
        
        ciphertext = self.encryption_service.encrypt(plaintext, self.test_key)
        decrypted = self.encryption_service.decrypt(ciphertext, self.test_key)
        
        assert decrypted == plaintext
    
    def test_decrypt_empty_string(self):
        """测试解密空字符串"""
        decrypted = self.encryption_service.decrypt("", self.test_key)
        
        assert decrypted == ""
    
    def test_encrypt_decrypt_chinese(self):
        """测试加密解密中文"""
        plaintext = "这是一个中文密钥测试"
        
        ciphertext = self.encryption_service.encrypt(plaintext, self.test_key)
        decrypted = self.encryption_service.decrypt(ciphertext, self.test_key)
        
        assert decrypted == plaintext
    
    def test_encrypt_decrypt_long_text(self):
        """测试加密解密长文本"""
        plaintext = "a" * 1000
        
        ciphertext = self.encryption_service.encrypt(plaintext, self.test_key)
        decrypted = self.encryption_service.decrypt(ciphertext, self.test_key)
        
        assert decrypted == plaintext
    
    def test_decrypt_wrong_key(self):
        """测试使用错误密钥解密"""
        plaintext = "my_secret_api_key"
        wrong_key = os.urandom(32)
        
        ciphertext = self.encryption_service.encrypt(plaintext, self.test_key)
        
        with pytest.raises(ValueError, match="解密失败"):
            self.encryption_service.decrypt(ciphertext, wrong_key)
    
    def test_decrypt_invalid_ciphertext(self):
        """测试解密无效密文"""
        invalid_ciphertext = "invalid_base64!!!"
        
        with pytest.raises(ValueError, match="解密失败"):
            self.encryption_service.decrypt(invalid_ciphertext, self.test_key)
    
    def test_generate_encryption_key(self):
        """测试生成加密密钥"""
        key1 = self.encryption_service.generate_encryption_key()
        key2 = self.encryption_service.generate_encryption_key()
        
        assert len(key1) == 32
        assert len(key2) == 32
        assert key1 != key2  # 每次生成的密钥应该不同
    
    def test_hash_key(self):
        """测试哈希密钥"""
        key = os.urandom(32)
        
        hash_value = self.encryption_service.hash_key(key)
        
        assert isinstance(hash_value, str)
        assert len(hash_value) == 64  # SHA256 produces 64 hex characters
    
    def test_hash_key_consistent(self):
        """测试相同密钥产生相同哈希"""
        key = os.urandom(32)
        
        hash1 = self.encryption_service.hash_key(key)
        hash2 = self.encryption_service.hash_key(key)
        
        assert hash1 == hash2
    
    def test_validate_key_valid(self):
        """测试验证有效密钥"""
        valid_key = os.urandom(32)
        
        assert self.encryption_service.validate_key(valid_key) is True
    
    def test_validate_key_invalid_length(self):
        """测试验证无效长度密钥"""
        invalid_key = os.urandom(16)  # 太短
        
        assert self.encryption_service.validate_key(invalid_key) is False
    
    def test_validate_key_empty(self):
        """测试验证空密钥"""
        assert self.encryption_service.validate_key(b"") is False
    
    def test_test_encryption_success(self):
        """测试加密功能测试成功"""
        result = self.encryption_service.test_encryption(self.test_key)
        
        assert result is True
    
    def test_test_encryption_invalid_key(self):
        """测试加密功能测试无效密钥"""
        invalid_key = b"short"
        
        result = self.encryption_service.test_encryption(invalid_key)
        
        assert result is False
    
    def test_encrypt_different_keys_different_ciphertext(self):
        """测试不同密钥产生不同密文"""
        plaintext = "same_plaintext"
        key1 = os.urandom(32)
        key2 = os.urandom(32)
        
        ciphertext1 = self.encryption_service.encrypt(plaintext, key1)
        ciphertext2 = self.encryption_service.encrypt(plaintext, key2)
        
        assert ciphertext1 != ciphertext2
    
    def test_encrypt_same_plaintext_twice_different_ciphertext(self):
        """测试相同明文两次加密产生不同密文（因为有随机IV）"""
        plaintext = "same_plaintext"
        
        ciphertext1 = self.encryption_service.encrypt(plaintext, self.test_key)
        ciphertext2 = self.encryption_service.encrypt(plaintext, self.test_key)
        
        # 由于随机IV，相同明文加密两次应该产生不同密文
        assert ciphertext1 != ciphertext2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
