"""
配置加密服务模块

作者：孔利群
"""

import base64
import hashlib
import os
from typing import Optional

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


class ConfigEncryptionService:
    """配置加密服务"""
    
    def __init__(self, salt: Optional[bytes] = None):
        """初始化加密服务"""
        self.salt = salt or b"inktrace_config_salt"
    
    def derive_key(self, password: str) -> bytes:
        """从密码派生加密密钥"""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=self.salt,
            iterations=100000,
        )
        return kdf.derive(password.encode('utf-8'))
    
    def encrypt(self, plaintext: str, key: bytes) -> str:
        """加密文本"""
        if not plaintext:
            return ""
            
        # 生成随机IV
        iv = os.urandom(12)
        
        # 创建加密器
        cipher = Cipher(algorithms.AES(key), modes.GCM(iv))
        encryptor = cipher.encryptor()
        
        # 加密数据
        ciphertext = encryptor.update(plaintext.encode('utf-8')) + encryptor.finalize()
        
        # 组合IV + 密文 + 认证标签
        encrypted_data = iv + encryptor.tag + ciphertext
        
        # Base64编码
        return base64.b64encode(encrypted_data).decode('utf-8')
    
    def decrypt(self, ciphertext: str, key: bytes) -> str:
        """解密文本"""
        if not ciphertext:
            return ""
            
        try:
            # Base64解码
            encrypted_data = base64.b64decode(ciphertext)
            
            # 分离IV、认证标签和密文
            iv = encrypted_data[:12]
            tag = encrypted_data[12:28]
            ciphertext_data = encrypted_data[28:]
            
            # 创建解密器
            cipher = Cipher(algorithms.AES(key), modes.GCM(iv, tag))
            decryptor = cipher.decryptor()
            
            # 解密数据
            plaintext = decryptor.update(ciphertext_data) + decryptor.finalize()
            
            return plaintext.decode('utf-8')
        except Exception as e:
            raise ValueError(f"解密失败: {str(e)}")
    
    def generate_encryption_key(self) -> bytes:
        """生成随机加密密钥"""
        return os.urandom(32)
    
    def hash_key(self, key: bytes) -> str:
        """哈希加密密钥用于存储"""
        return hashlib.sha256(key).hexdigest()
    
    def validate_key(self, key: bytes) -> bool:
        """验证加密密钥有效性"""
        return len(key) == 32
    
    def test_encryption(self, key: bytes) -> bool:
        """测试加密功能是否正常"""
        try:
            test_text = "test_encryption"
            encrypted = self.encrypt(test_text, key)
            decrypted = self.decrypt(encrypted, key)
            return decrypted == test_text
        except Exception:
            return False