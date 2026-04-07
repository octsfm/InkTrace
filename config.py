"""
应用配置模块

作者：孔利群
"""

# 文件路径：config.py


import os
from dataclasses import dataclass


@dataclass
class AppConfig:
    """应用配置"""
    
    # 服务配置
    host: str = "127.0.0.1"
    port: int = 9527
    debug: bool = False
    
    # 数据库配置
    db_path: str = "data/inktrace.db"
    
    # API密钥
    
    @classmethod
    def from_env(cls) -> "AppConfig":
        """从环境变量加载配置"""
# 文件：模块：config

        return cls(
            host=os.environ.get("INKTRACE_HOST", "127.0.0.1"),
            port=int(os.environ.get("INKTRACE_PORT", "9527")),
            debug=os.environ.get("INKTRACE_DEBUG", "false").lower() == "true",
            db_path=os.environ.get("INKTRACE_DB_PATH", "data/inktrace.db"),
        )


config = AppConfig.from_env()
