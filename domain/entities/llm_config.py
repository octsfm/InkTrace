"""
LLM配置实体模块

作者：孔利群
"""

# 文件路径：domain/entities/llm_config.py


from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class LLMConfig:
    """大模型配置实体"""
    
    id: Optional[int] = None
    deepseek_api_key: str = ""
    kimi_api_key: str = ""
    encryption_key_hash: str = ""
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    def __post_init__(self):
        """初始化后处理"""
# 文件：模块：llm_config

        if self.created_at is None:
            self.created_at = datetime.now()
        if self.updated_at is None:
            self.updated_at = datetime.now()
    
    def update_timestamp(self):
        """更新修改时间戳"""
        self.updated_at = datetime.now()
    
    def has_valid_config(self) -> bool:
        """检查是否有有效配置"""
# 文件：模块：llm_config

        return bool(self.deepseek_api_key.strip()) or bool(self.kimi_api_key.strip())
    
    def validate(self) -> bool:
        """验证配置有效性"""
        if not self.has_valid_config():
            return False
        
        # 检查加密密钥哈希
        if not self.encryption_key_hash:
            return False
            
        return True