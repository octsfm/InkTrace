"""
LLM配置单元测试模块

作者：孔利群
"""

import unittest
import tempfile
import os
from datetime import datetime

from domain.entities.llm_config import LLMConfig
from domain.value_objects.encrypted_api_key import EncryptedAPIKey
from domain.services.config_encryption_service import ConfigEncryptionService
from infrastructure.persistence.sqlite_llm_config_repo import SQLiteLLMConfigRepository
from application.services.config_service import ConfigService


class TestLLMConfig(unittest.TestCase):
    """LLM配置实体测试"""
    
    def test_llm_config_creation(self):
        """测试配置实体创建"""
        config = LLMConfig(
            deepseek_api_key="test_deepseek_key",
            kimi_api_key="test_kimi_key",
            encryption_key_hash="test_hash"
        )
        
        self.assertEqual(config.deepseek_api_key, "test_deepseek_key")
        self.assertEqual(config.kimi_api_key, "test_kimi_key")
        self.assertEqual(config.encryption_key_hash, "test_hash")
        self.assertIsNotNone(config.created_at)
        self.assertIsNotNone(config.updated_at)
    
    def test_llm_config_validation(self):
        """测试配置验证"""
        # 有效配置
        config1 = LLMConfig(
            deepseek_api_key="valid_key",
            kimi_api_key="",
            encryption_key_hash="hash"
        )
        self.assertTrue(config1.validate())
        
        # 无效配置（缺少加密密钥哈希）
        config2 = LLMConfig(
            deepseek_api_key="valid_key",
            kimi_api_key="",
            encryption_key_hash=""
        )
        self.assertFalse(config2.validate())
    
    def test_has_valid_config(self):
        """测试是否有有效配置"""
        # 有DeepSeek配置
        config1 = LLMConfig(deepseek_api_key="key1")
        self.assertTrue(config1.has_valid_config())
        
        # 有Kimi配置
        config2 = LLMConfig(kimi_api_key="key2")
        self.assertTrue(config2.has_valid_config())
        
        # 无配置
        config3 = LLMConfig()
        self.assertFalse(config3.has_valid_config())


class TestEncryptedAPIKey(unittest.TestCase):
    """加密API密钥值对象测试"""
    
    def setUp(self):
        """测试前准备"""
        self.encryption_service = ConfigEncryptionService()
        self.encryption_key = b"test_encryption_key_32bytes_1234"
    
    def test_empty_key(self):
        """测试空密钥"""
        empty_key = EncryptedAPIKey.create_empty()
        self.assertTrue(empty_key.is_empty())
        self.assertEqual(str(empty_key), "[EMPTY]")
    
    def test_encryption_decryption(self):
        """测试加密解密"""
        plaintext = "test_api_key_1234567890"
        
        # 加密
        encrypted_key = EncryptedAPIKey.from_plaintext(plaintext, self.encryption_key)
        self.assertFalse(encrypted_key.is_empty())
        self.assertNotEqual(encrypted_key.ciphertext, plaintext)
        
        # 解密
        decrypted = encrypted_key.to_plaintext(self.encryption_key)
        self.assertEqual(decrypted, plaintext)
    
    def test_equality(self):
        """测试相等性"""
        key1 = EncryptedAPIKey(ciphertext="cipher1")
        key2 = EncryptedAPIKey(ciphertext="cipher1")
        key3 = EncryptedAPIKey(ciphertext="cipher2")
        
        self.assertEqual(key1, key2)
        self.assertNotEqual(key1, key3)


class TestConfigEncryptionService(unittest.TestCase):
    """配置加密服务测试"""
    
    def setUp(self):
        """测试前准备"""
        self.service = ConfigEncryptionService()
        self.test_key = self.service.generate_encryption_key()
    
    def test_encryption_decryption(self):
        """测试加密解密"""
        plaintext = "test_secret_api_key"
        
        # 加密
        ciphertext = self.service.encrypt(plaintext, self.test_key)
        self.assertNotEqual(ciphertext, plaintext)
        self.assertTrue(ciphertext)
        
        # 解密
        decrypted = self.service.decrypt(ciphertext, self.test_key)
        self.assertEqual(decrypted, plaintext)
    
    def test_empty_text(self):
        """测试空文本"""
        ciphertext = self.service.encrypt("", self.test_key)
        self.assertEqual(ciphertext, "")
        
        decrypted = self.service.decrypt("", self.test_key)
        self.assertEqual(decrypted, "")
    
    def test_key_validation(self):
        """测试密钥验证"""
        self.assertTrue(self.service.validate_key(self.test_key))
        
        # 无效密钥
        invalid_key = b"short"
        self.assertFalse(self.service.validate_key(invalid_key))
    
    def test_test_encryption(self):
        """测试加密功能测试"""
        self.assertTrue(self.service.test_encryption(self.test_key))


class TestSQLiteLLMConfigRepository(unittest.TestCase):
    """SQLite配置仓储测试"""
    
    def setUp(self):
        """测试前准备"""
        # 创建临时数据库
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        self.repo = SQLiteLLMConfigRepository(self.temp_db.name)
        
        # 保存数据库连接引用以便清理
        self.conn = self.repo._get_connection()
    
    def tearDown(self):
        """测试后清理"""
        # 关闭数据库连接
        if hasattr(self, 'conn'):
            self.conn.close()
        
        # 删除临时文件
        if os.path.exists(self.temp_db.name):
            try:
                os.unlink(self.temp_db.name)
            except PermissionError:
                # 如果文件被占用，等待一下再尝试
                import time
                time.sleep(0.1)
                try:
                    os.unlink(self.temp_db.name)
                except:
                    pass
    
    def test_save_and_get_config(self):
        """测试保存和获取配置"""
        config = LLMConfig(
            deepseek_api_key="encrypted_deepseek",
            kimi_api_key="encrypted_kimi",
            encryption_key_hash="test_hash"
        )
        
        # 保存配置
        saved_config = self.repo.save(config)
        self.assertIsNotNone(saved_config.id)
        
        # 获取配置
        retrieved_config = self.repo.get()
        self.assertIsNotNone(retrieved_config)
        self.assertEqual(retrieved_config.deepseek_api_key, "encrypted_deepseek")
        self.assertEqual(retrieved_config.kimi_api_key, "encrypted_kimi")
    
    def test_config_exists(self):
        """测试配置存在检查"""
        # 初始状态
        self.assertFalse(self.repo.exists())
        
        # 保存配置后
        config = LLMConfig(
            deepseek_api_key="key1",
            kimi_api_key="key2",
            encryption_key_hash="hash"
        )
        self.repo.save(config)
        self.assertTrue(self.repo.exists())
    
    def test_delete_config(self):
        """测试删除配置"""
        # 保存配置
        config = LLMConfig(
            deepseek_api_key="key1",
            kimi_api_key="key2",
            encryption_key_hash="hash"
        )
        self.repo.save(config)
        self.assertTrue(self.repo.exists())
        
        # 删除配置
        success = self.repo.delete()
        self.assertTrue(success)
        self.assertFalse(self.repo.exists())


class TestConfigService(unittest.TestCase):
    """配置服务测试"""
    
    def setUp(self):
        """测试前准备"""
        # 创建临时数据库
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        
        # 创建仓储和服务
        self.repo = SQLiteLLMConfigRepository(self.temp_db.name)
        self.encryption_key = b"test_encryption_key_32bytes_1234"
        self.service = ConfigService(self.repo, self.encryption_key)
        
        # 保存数据库连接引用以便清理
        self.conn = self.repo._get_connection()
    
    def tearDown(self):
        """测试后清理"""
        # 关闭数据库连接
        if hasattr(self, 'conn'):
            self.conn.close()
        
        # 删除临时文件
        if os.path.exists(self.temp_db.name):
            try:
                os.unlink(self.temp_db.name)
            except PermissionError:
                # 如果文件被占用，等待一下再尝试
                import time
                time.sleep(0.1)
                try:
                    os.unlink(self.temp_db.name)
                except:
                    pass
    
    def test_save_and_retrieve_config(self):
        """测试保存和检索配置"""
        deepseek_key = "test_deepseek_api_key_1234567890"
        kimi_key = "test_kimi_api_key_1234567890"
        
        # 保存配置
        saved_config = self.service.save_config(deepseek_key, kimi_key)
        self.assertIsNotNone(saved_config.id)
        
        # 检索配置
        retrieved_config = self.service.get_config()
        self.assertIsNotNone(retrieved_config)
        
        # 解密配置
        decrypted_config = self.service.get_decrypted_config()
        self.assertIsNotNone(decrypted_config)
        decrypted_deepseek, decrypted_kimi = decrypted_config
        self.assertEqual(decrypted_deepseek, deepseek_key)
        self.assertEqual(decrypted_kimi, kimi_key)
    
    def test_config_validation(self):
        """测试配置验证"""
        # 有效配置
        self.assertTrue(self.service.validate_config("valid_key_1234567890", ""))
        
        # 无效配置（密钥太短）
        self.assertFalse(self.service.validate_config("short", ""))
        
        # 无效配置（两个都为空）
        self.assertFalse(self.service.validate_config("", ""))
    
    def test_api_key_format_validation(self):
        """测试API密钥格式验证"""
        # 有效格式
        self.assertTrue(self.service._validate_api_key_format("sk-1234567890abcdefghij"))
        
        # 无效格式（太短）
        self.assertFalse(self.service._validate_api_key_format("short"))
        
        # 无效格式（太长）
        self.assertFalse(self.service._validate_api_key_format("a" * 101))


if __name__ == '__main__':
    unittest.main()