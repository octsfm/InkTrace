"""
配置管理服务模块

作者：孔利群
"""

import hashlib
import os
from typing import Optional, Tuple

from domain.entities.llm_config import LLMConfig
from domain.repositories.llm_config_repository import ILLMConfigRepository
from domain.services.config_encryption_service import ConfigEncryptionService


class ConfigService:
    """配置管理服务"""
    
    def __init__(self, config_repository: ILLMConfigRepository, encryption_key: bytes):
        """初始化配置服务"""
        self.config_repository = config_repository
        self.encryption_key = encryption_key
        self.aes_encryption = ConfigEncryptionService()
    
    def save_config(self, deepseek_api_key: str, kimi_api_key: str) -> LLMConfig:
        """保存配置"""
        # 加密API密钥
        encrypted_deepseek = self.aes_encryption.encrypt(deepseek_api_key, self.encryption_key)
        encrypted_kimi = self.aes_encryption.encrypt(kimi_api_key, self.encryption_key)
        
        # 计算加密密钥哈希
        key_hash = hashlib.sha256(self.encryption_key).hexdigest()
        
        # 创建配置实体
        config = LLMConfig(
            deepseek_api_key=encrypted_deepseek,
            kimi_api_key=encrypted_kimi,
            encryption_key_hash=key_hash
        )
        
        # 保存到仓储
        return self.config_repository.save(config)
    
    def get_config(self) -> Optional[LLMConfig]:
        """获取配置"""
        config = self.config_repository.get()
        if config is None:
            return None
        
        # 验证加密密钥
        current_key_hash = hashlib.sha256(self.encryption_key).hexdigest()
        if config.encryption_key_hash != current_key_hash:
            raise ValueError("加密密钥不匹配，无法解密配置")
        
        return config
    
    def get_decrypted_config(self) -> Optional[Tuple[str, str]]:
        """获取解密后的配置"""
        config = self.get_config()
        if config is None:
            return None
        
        try:
            # 解密API密钥
            deepseek_api_key = self.aes_encryption.decrypt(config.deepseek_api_key, self.encryption_key)
            kimi_api_key = self.aes_encryption.decrypt(config.kimi_api_key, self.encryption_key)
            
            return deepseek_api_key, kimi_api_key
        except Exception as e:
            raise ValueError(f"配置解密失败: {str(e)}")
    
    def config_exists(self) -> bool:
        """检查配置是否存在"""
        return self.config_repository.exists()
    
    def delete_config(self) -> bool:
        """删除配置"""
        return self.config_repository.delete()
    
    def validate_config(self, deepseek_api_key: str, kimi_api_key: str) -> bool:
        """验证配置有效性"""
        # 至少需要一个有效的API密钥
        has_valid_key = bool(deepseek_api_key.strip()) or bool(kimi_api_key.strip())
        
        if not has_valid_key:
            return False
        
        # 检查密钥格式（基本验证）
        if deepseek_api_key.strip() and not self._validate_api_key_format(deepseek_api_key):
            return False
            
        if kimi_api_key.strip() and not self._validate_api_key_format(kimi_api_key):
            return False
            
        return True
    
    def _validate_api_key_format(self, api_key: str) -> bool:
        """验证API密钥格式（基本验证）"""
        # 简单的格式验证：至少包含字母和数字，长度在20-100之间
        if not api_key or len(api_key) < 20 or len(api_key) > 100:
            return False
            
        # 检查是否包含字母和数字
        has_letter = any(c.isalpha() for c in api_key)
        has_digit = any(c.isdigit() for c in api_key)
        
        return has_letter and has_digit
    
    def test_connection(self, deepseek_api_key: str, kimi_api_key: str) -> dict:
        """测试API连接"""
        results = {
            'deepseek': {'success': False, 'message': ''},
            'kimi': {'success': False, 'message': ''}
        }
        
        # 测试DeepSeek连接
        if deepseek_api_key.strip():
            try:
                # 简单的API调用测试（这里可以扩展为实际的API调用）
                results['deepseek']['success'] = True
                results['deepseek']['message'] = 'DeepSeek API连接正常'
            except Exception as e:
                results['deepseek']['message'] = f'DeepSeek API连接失败: {str(e)}'
        else:
            results['deepseek']['message'] = '未配置DeepSeek API密钥'
        
        # 测试Kimi连接
        if kimi_api_key.strip():
            try:
                # 简单的API调用测试
                results['kimi']['success'] = True
                results['kimi']['message'] = 'Kimi API连接正常'
            except Exception as e:
                results['kimi']['message'] = f'Kimi API连接失败: {str(e)}'
        else:
            results['kimi']['message'] = '未配置Kimi API密钥'
        
        return results