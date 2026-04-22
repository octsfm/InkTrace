"""
SQLite LLM配置仓储实现模块

作者：孔利群
"""

# 文件路径：infrastructure/persistence/sqlite_llm_config_repo.py


import sqlite3
from datetime import datetime
from typing import Optional

from domain.entities.llm_config import LLMConfig
from domain.repositories.llm_config_repository import ILLMConfigRepository
from infrastructure.persistence.sqlite_utils import connect_sqlite


class SQLiteLLMConfigRepository(ILLMConfigRepository):
    """SQLite LLM配置仓储实现"""
    
    def __init__(self, db_path: str):
        """初始化仓储"""
        self.db_path = db_path
        self._ensure_table()
    
    def _get_connection(self) -> sqlite3.Connection:
        """获取数据库连接"""
        conn = connect_sqlite(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def _ensure_table(self):
        """确保表存在"""
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS llm_config (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    deepseek_api_key TEXT NOT NULL,
                    kimi_api_key TEXT NOT NULL,
                    encryption_key_hash TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
    
    def save(self, config: LLMConfig) -> LLMConfig:
        """保存配置"""
        config.update_timestamp()
        
        with self._get_connection() as conn:
            if config.id is None:
                # 插入新配置
                cursor = conn.execute("""
                    INSERT INTO llm_config 
                    (deepseek_api_key, kimi_api_key, encryption_key_hash, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    config.deepseek_api_key,
                    config.kimi_api_key,
                    config.encryption_key_hash,
                    config.created_at.isoformat(),
                    config.updated_at.isoformat()
                ))
                config.id = cursor.lastrowid
            else:
                # 更新现有配置
                conn.execute("""
                    UPDATE llm_config 
                    SET deepseek_api_key = ?, kimi_api_key = ?, encryption_key_hash = ?, 
                        updated_at = ?
                    WHERE id = ?
                """, (
                    config.deepseek_api_key,
                    config.kimi_api_key,
                    config.encryption_key_hash,
                    config.updated_at.isoformat(),
                    config.id
                ))
            
            conn.commit()
        
        return config
    
    def get(self) -> Optional[LLMConfig]:
        """获取配置"""
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT * FROM llm_config ORDER BY id DESC LIMIT 1")
            row = cursor.fetchone()
            
            if row is None:
                return None
            
            return LLMConfig(
                id=row['id'],
                deepseek_api_key=row['deepseek_api_key'],
                kimi_api_key=row['kimi_api_key'],
                encryption_key_hash=row['encryption_key_hash'],
                created_at=datetime.fromisoformat(row['created_at']),
                updated_at=datetime.fromisoformat(row['updated_at'])
            )
    
    def delete(self) -> bool:
        """删除配置"""
        with self._get_connection() as conn:
            cursor = conn.execute("DELETE FROM llm_config")
            conn.commit()
            return cursor.rowcount > 0
    
    def exists(self) -> bool:
        """检查配置是否存在"""
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT COUNT(*) as count FROM llm_config")
            row = cursor.fetchone()
            return row['count'] > 0
    
    def get_all(self) -> list[LLMConfig]:
        """获取所有配置（历史版本）"""
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT * FROM llm_config ORDER BY id DESC")
            rows = cursor.fetchall()
            
            configs = []
            for row in rows:
                configs.append(LLMConfig(
                    id=row['id'],
                    deepseek_api_key=row['deepseek_api_key'],
                    kimi_api_key=row['kimi_api_key'],
                    encryption_key_hash=row['encryption_key_hash'],
                    created_at=datetime.fromisoformat(row['created_at']),
                    updated_at=datetime.fromisoformat(row['updated_at'])
                ))
            
            return configs
