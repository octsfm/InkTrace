"""
模板仓储SQLite实现

作者：孔利群
"""

import json
import sqlite3
import os
from datetime import datetime
from typing import Optional, List

from domain.entities.template import Template, CharacterTemplate, PlotTemplate
from domain.repositories.template_repository import ITemplateRepository
from domain.types import TemplateId, GenreType


class SQLiteTemplateRepository(ITemplateRepository):
    """模板仓储SQLite实现"""
    
    def __init__(self, db_path: str, templates_dir: str = None):
        self.db_path = db_path
        self.templates_dir = templates_dir or "infrastructure/templates"
        self._init_table()
        self._load_builtin_templates()
    
    def _init_table(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS templates (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    genre TEXT NOT NULL,
                    description TEXT,
                    worldview_framework TEXT,
                    character_templates TEXT,
                    plot_templates TEXT,
                    style_reference TEXT,
                    is_builtin INTEGER DEFAULT 0,
                    created_at TEXT,
                    updated_at TEXT
                )
            """)
            conn.commit()
    
    def _load_builtin_templates(self) -> None:
        """加载内置模板"""
        if not os.path.exists(self.templates_dir):
            return
        
        for filename in os.listdir(self.templates_dir):
            if filename.endswith('.json'):
                filepath = os.path.join(self.templates_dir, filename)
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    template = Template.from_dict(data)
                    template.is_builtin = True
                    self.save(template)
    
    def find_by_id(self, template_id: TemplateId) -> Optional[Template]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM templates WHERE id = ?", (str(template_id),)
            )
            row = cursor.fetchone()
            if row:
                return self._row_to_template(row)
        return None
    
    def find_by_genre(self, genre: GenreType) -> List[Template]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM templates WHERE genre = ?", (genre.value,)
            )
            return [self._row_to_template(row) for row in cursor.fetchall()]
    
    def find_all(self, include_builtin: bool = True) -> List[Template]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            if include_builtin:
                cursor = conn.execute("SELECT * FROM templates ORDER BY name")
            else:
                cursor = conn.execute(
                    "SELECT * FROM templates WHERE is_builtin = 0 ORDER BY name"
                )
            return [self._row_to_template(row) for row in cursor.fetchall()]
    
    def find_builtin(self) -> List[Template]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM templates WHERE is_builtin = 1 ORDER BY name"
            )
            return [self._row_to_template(row) for row in cursor.fetchall()]
    
    def find_custom(self) -> List[Template]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM templates WHERE is_builtin = 0 ORDER BY name"
            )
            return [self._row_to_template(row) for row in cursor.fetchall()]
    
    def save(self, template: Template) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO templates 
                (id, name, genre, description, worldview_framework, character_templates, 
                 plot_templates, style_reference, is_builtin, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                str(template.id),
                template.name,
                template.genre.value,
                template.description,
                json.dumps(template.worldview_framework, ensure_ascii=False),
                json.dumps([t.to_dict() for t in template.character_templates], ensure_ascii=False),
                json.dumps([t.to_dict() for t in template.plot_templates], ensure_ascii=False),
                json.dumps(template.style_reference, ensure_ascii=False),
                1 if template.is_builtin else 0,
                template.created_at.isoformat(),
                template.updated_at.isoformat()
            ))
            conn.commit()
    
    def delete(self, template_id: TemplateId) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "DELETE FROM templates WHERE id = ? AND is_builtin = 0",
                (str(template_id),)
            )
            conn.commit()
    
    def _row_to_template(self, row: sqlite3.Row) -> Template:
        return Template(
            id=TemplateId(row["id"]),
            name=row["name"],
            genre=GenreType(row["genre"]),
            description=row["description"] or "",
            worldview_framework=json.loads(row["worldview_framework"]) if row["worldview_framework"] else {},
            character_templates=[
                CharacterTemplate.from_dict(t) 
                for t in json.loads(row["character_templates"])
            ] if row["character_templates"] else [],
            plot_templates=[
                PlotTemplate.from_dict(t) 
                for t in json.loads(row["plot_templates"])
            ] if row["plot_templates"] else [],
            style_reference=json.loads(row["style_reference"]) if row["style_reference"] else {},
            is_builtin=bool(row["is_builtin"]),
            created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else datetime.now(),
            updated_at=datetime.fromisoformat(row["updated_at"]) if row["updated_at"] else datetime.now()
        )
