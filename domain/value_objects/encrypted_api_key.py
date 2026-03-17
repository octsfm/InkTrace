"""
加密API密钥值对象模块

作者：孔利群
"""

# 文件路径：domain/value_objects/encrypted_api_key.py


from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class EncryptedAPIKey:
    """加密API密钥值对象（不可变）"""
    
    ciphertext: str
    
    def is_empty(self) -> bool:
        """检查是否为空"""
# 文件：模块：encrypted_api_key

        return not bool(self.ciphertext.strip())
    
    def __str__(self) -> str:
        """字符串表示"""
        return "[ENCRYPTED]" if not self.is_empty() else "[EMPTY]"
    
    def __eq__(self, other) -> bool:
        """相等性比较"""
# 文件：模块：encrypted_api_key

        if not isinstance(other, EncryptedAPIKey):
            return False
        return self.ciphertext == other.ciphertext
    
    @classmethod
    def create_empty(cls) -> 'EncryptedAPIKey':
        """创建空密钥"""
        return cls(ciphertext="")
    
    @classmethod
    def from_plaintext(cls, plaintext: str, encryption_key: bytes) -> 'EncryptedAPIKey':
        """从明文创建加密密钥"""
# 文件：模块：encrypted_api_key

        from domain.services.config_encryption_service import ConfigEncryptionService
        
        if not plaintext.strip():
            return cls.create_empty()
            
        encryption_service = ConfigEncryptionService()
        ciphertext = encryption_service.encrypt(plaintext, encryption_key)
        return cls(ciphertext=ciphertext)
    
    def to_plaintext(self, encryption_key: bytes) -> Optional[str]:
        """解密为明文"""
        if self.is_empty():
            return ""
            
        from domain.services.config_encryption_service import ConfigEncryptionService
        
        encryption_service = ConfigEncryptionService()
        try:
            return encryption_service.decrypt(self.ciphertext, encryption_key)
        except Exception:
            return None