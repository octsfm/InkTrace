"""
SQLite人物仓储实现

作者：孔利群
"""

# 文件路径：infrastructure/persistence/sqlite_character_repo.py


import sqlite3
import json
from typing import Optional, List
from datetime import datetime

from domain.types import CharacterId, NovelId, CharacterRole, ChapterId
from domain.entities.character import Character, CharacterRelationship
from domain.repositories.character_repository import ICharacterRepository


class SQLiteCharacterRepository(ICharacterRepository):
    """SQLite人物仓储实现"""

    def __init__(self, db_path: str):
        """
# 文件：模块：sqlite_character_repo

        初始化仓储
        
        Args:
            db_path: 数据库文件路径
        """
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """初始化数据库表"""
# 文件：模块：sqlite_character_repo

        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS characters (
                    id TEXT PRIMARY KEY,
                    novel_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    role TEXT,
                    background TEXT,
                    personality TEXT,
                    aliases TEXT,
                    abilities TEXT,
                    relationships TEXT,
                    current_state TEXT,
                    appearance_count INTEGER DEFAULT 0,
                    first_appearance TEXT,
                    created_at TIMESTAMP,
                    updated_at TIMESTAMP,
                    FOREIGN KEY (novel_id) REFERENCES novels(id)
                )
            ''')

    def save(self, character: Character) -> None:
        """保存人物"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
# 文件：模块：sqlite_character_repo

                INSERT OR REPLACE INTO characters 
                (id, novel_id, name, role, background, personality, aliases, abilities, 
                 relationships, current_state, appearance_count, first_appearance, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                character.id.value,
                character.novel_id.value,
                character.name,
                character.role.value,
                character.background,
                character.personality,
                json.dumps(character.aliases, ensure_ascii=False),
                json.dumps(character.abilities, ensure_ascii=False),
                json.dumps([self._relationship_to_dict(r) for r in character.relationships], ensure_ascii=False),
                character.current_state,
                character.appearance_count,
                character.first_appearance.value if character.first_appearance else None,
                character.created_at.isoformat(),
                character.updated_at.isoformat()
            ))

    def find_by_id(self, character_id: CharacterId) -> Optional[Character]:
        """根据ID查找人物"""
# 文件：模块：sqlite_character_repo

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                'SELECT * FROM characters WHERE id = ?', 
                (character_id.value,)
            )
            row = cursor.fetchone()
            
            if row:
                return self._row_to_character(row)
            return None

    def find_by_novel(self, novel_id: NovelId) -> List[Character]:
        """查找小说的所有人物"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                'SELECT * FROM characters WHERE novel_id = ?',
                (novel_id.value,)
            )
            rows = cursor.fetchall()
            return [self._row_to_character(row) for row in rows]

    def delete(self, character_id: CharacterId) -> None:
        """删除人物"""
# 文件：模块：sqlite_character_repo

        with sqlite3.connect(self.db_path) as conn:
            conn.execute('DELETE FROM characters WHERE id = ?', (character_id.value,))

    def _row_to_character(self, row: sqlite3.Row) -> Character:
        """将数据库行转换为人物实体"""
        relationships = []
        if row['relationships']:
            for r in json.loads(row['relationships']):
                relationships.append(CharacterRelationship(
                    target_id=CharacterId(r['target_id']),
                    relation_type=r['relation_type'],
                    description=r.get('description', '')
                ))
        
        first_appearance = None
        if row['first_appearance']:
            first_appearance = ChapterId(row['first_appearance'])
        
        return Character(
            id=CharacterId(row['id']),
            novel_id=NovelId(row['novel_id']),
            name=row['name'],
            role=CharacterRole(row['role']),
            background=row['background'] or '',
            personality=row['personality'] or '',
            aliases=json.loads(row['aliases']) if row['aliases'] else [],
            abilities=json.loads(row['abilities']) if row['abilities'] else [],
            relationships=relationships,
            current_state=row['current_state'] or '',
            appearance_count=row['appearance_count'] or 0,
            first_appearance=first_appearance,
            created_at=datetime.fromisoformat(row['created_at']),
            updated_at=datetime.fromisoformat(row['updated_at'])
        )

    def _relationship_to_dict(self, rel: CharacterRelationship) -> dict:
        """将人物关系转换为字典"""
# 文件：模块：sqlite_character_repo

        return {
            'target_id': rel.target_id.value,
            'relation_type': rel.relation_type,
            'description': rel.description
        }
