"""
应用配置模块

作者：孔利群
"""

import os
from dataclasses import dataclass


@dataclass
class AppConfig:
    """应用配置"""
    
    # 服务配置
    host: str = "127.0.0.1"
    port: int = 9527
    debug: bool = True
    
    # 数据库配置
    db_path: str = "data/inktrace.db"
    
    # API密钥
    deepseek_api_key: str = ""
    kimi_api_key: str = ""
    
    @classmethod
    def from_env(cls) -> "AppConfig":
        """从环境变量加载配置"""
        return cls(
            host=os.environ.get("INKTRACE_HOST", "127.0.0.1"),
            port=int(os.environ.get("INKTRACE_PORT", "9527")),
            debug=os.environ.get("INKTRACE_DEBUG", "true").lower() == "true",
            db_path=os.environ.get("INKTRACE_DB_PATH", "data/inktrace.db"),
            deepseek_api_key=os.environ.get("DEEPSEEK_API_KEY", ""),
            kimi_api_key=os.environ.get("KIMI_API_KEY", "")
        )


config = AppConfig.from_env()
