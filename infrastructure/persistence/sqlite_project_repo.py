"""
项目仓储SQLite实现

作者：孔利群
"""

# 文件路径：infrastructure/persistence/sqlite_project_repo.py


import json
import os
import sqlite3
from datetime import datetime
from typing import Optional, List

from domain.entities.project import Project, ProjectConfig
from domain.repositories.project_repository import IProjectRepository
from domain.types import ProjectId, NovelId, ProjectStatus
from domain.utils import repair_mojibake


class SQLiteProjectRepository(IProjectRepository):
    """项目仓储SQLite实现"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        db_dir = os.path.dirname(self.db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)
        self._init_table()
    
    def _init_table(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS projects (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    novel_id TEXT NOT NULL,
                    config TEXT,
                    status TEXT DEFAULT 'active',
                    created_at TEXT,
                    updated_at TEXT,
                    FOREIGN KEY (novel_id) REFERENCES novels(id)
                )
            """)
            conn.commit()
    
    def find_by_id(self, project_id: ProjectId) -> Optional[Project]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM projects WHERE id = ?", (str(project_id),)
            )
            row = cursor.fetchone()
            if row:
                return self._row_to_project(row)
        return None
    
    def find_by_novel_id(self, novel_id: NovelId) -> Optional[Project]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM projects WHERE novel_id = ?", (str(novel_id),)
            )
            row = cursor.fetchone()
            if row:
                return self._row_to_project(row)
        return None
    
    def find_all(self, status: Optional[ProjectStatus] = None) -> List[Project]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            if status:
                cursor = conn.execute(
                    "SELECT * FROM projects WHERE status = ? ORDER BY updated_at DESC",
                    (status.value,)
                )
            else:
                cursor = conn.execute(
                    "SELECT * FROM projects ORDER BY updated_at DESC"
                )
            return [self._row_to_project(row) for row in cursor.fetchall()]
    
    def save(self, project: Project) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO projects 
                (id, name, novel_id, config, status, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                str(project.id),
                project.name,
                str(project.novel_id),
                json.dumps(project.config.to_dict()),
                project.status.value,
                project.created_at.isoformat(),
                project.updated_at.isoformat()
            ))
            conn.commit()
    
    def delete(self, project_id: ProjectId) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM projects WHERE id = ?", (str(project_id),))
            conn.commit()
    
    def count(self, status: Optional[ProjectStatus] = None) -> int:
        with sqlite3.connect(self.db_path) as conn:
            if status:
                cursor = conn.execute(
                    "SELECT COUNT(*) FROM projects WHERE status = ?", (status.value,)
                )
            else:
                cursor = conn.execute("SELECT COUNT(*) FROM projects")
            return cursor.fetchone()[0]
    
    def _row_to_project(self, row: sqlite3.Row) -> Project:
        try:
            status = ProjectStatus(row["status"])
        except Exception:
            status = ProjectStatus.ACTIVE
        config_raw = row["config"]
        if config_raw:
            try:
                config = ProjectConfig.from_dict(json.loads(config_raw))
            except Exception:
                config = ProjectConfig()
        else:
            config = ProjectConfig()
        return Project(
            id=ProjectId(row["id"]),
            name=repair_mojibake(row["name"]),
            novel_id=NovelId(row["novel_id"]),
            config=config,
            status=status,
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"])
        )
