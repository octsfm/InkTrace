"""
世界观仓储SQLite实现

作者：孔利群
"""

# 文件路径：infrastructure/persistence/sqlite_worldview_repo.py


import json
import sqlite3
from datetime import datetime
from typing import Optional, List

from domain.entities.worldview import Worldview, PowerSystem
from domain.entities.technique import Technique, TechniqueLevel
from domain.entities.faction import Faction, FactionRelation
from domain.entities.location import Location
from domain.entities.item import Item
from domain.repositories.worldview_repository import IWorldviewRepository
from domain.types import WorldviewId, NovelId, TechniqueId, FactionId, LocationId, ItemId


class SQLiteWorldviewRepository(IWorldviewRepository):
    """世界观仓储SQLite实现"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_tables()
    
    def _init_tables(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
# 文件：模块：sqlite_worldview_repo

                CREATE TABLE IF NOT EXISTS worldviews (
                    id TEXT PRIMARY KEY,
                    novel_id TEXT NOT NULL,
                    name TEXT,
                    power_system TEXT,
                    currency_system TEXT,
                    timeline TEXT,
                    created_at TEXT,
                    updated_at TEXT,
                    FOREIGN KEY (novel_id) REFERENCES novels(id)
                )
            """)
            
            conn.execute("""
# 文件：模块：sqlite_worldview_repo

                CREATE TABLE IF NOT EXISTS techniques (
                    id TEXT PRIMARY KEY,
                    novel_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    level TEXT,
                    description TEXT,
                    effect TEXT,
                    requirement TEXT,
                    creator TEXT,
                    created_at TEXT,
                    updated_at TEXT,
                    FOREIGN KEY (novel_id) REFERENCES novels(id)
                )
            """)
            
            conn.execute("""
# 文件：模块：sqlite_worldview_repo

                CREATE TABLE IF NOT EXISTS factions (
                    id TEXT PRIMARY KEY,
                    novel_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    level TEXT,
                    description TEXT,
                    territory TEXT,
                    leader TEXT,
                    headquarters TEXT,
                    relations TEXT,
                    created_at TEXT,
                    updated_at TEXT,
                    FOREIGN KEY (novel_id) REFERENCES novels(id)
                )
            """)
            
            conn.execute("""
# 文件：模块：sqlite_worldview_repo

                CREATE TABLE IF NOT EXISTS locations (
                    id TEXT PRIMARY KEY,
                    novel_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    description TEXT,
                    faction_id TEXT,
                    parent_id TEXT,
                    importance INTEGER DEFAULT 0,
                    created_at TEXT,
                    updated_at TEXT,
                    FOREIGN KEY (novel_id) REFERENCES novels(id)
                )
            """)
            
            conn.execute("""
# 文件：模块：sqlite_worldview_repo

                CREATE TABLE IF NOT EXISTS items (
                    id TEXT PRIMARY KEY,
                    novel_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    type TEXT,
                    description TEXT,
                    effect TEXT,
                    rarity TEXT,
                    owner TEXT,
                    origin TEXT,
                    created_at TEXT,
                    updated_at TEXT,
                    FOREIGN KEY (novel_id) REFERENCES novels(id)
                )
            """)
            
            conn.commit()
    
    def find_by_id(self, worldview_id: WorldviewId) -> Optional[Worldview]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM worldviews WHERE id = ?", (str(worldview_id),)
            )
            row = cursor.fetchone()
            if row:
                return self._row_to_worldview(row)
        return None
    
    def find_by_novel_id(self, novel_id: NovelId) -> Optional[Worldview]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM worldviews WHERE novel_id = ?", (str(novel_id),)
            )
            row = cursor.fetchone()
            if row:
                return self._row_to_worldview(row)
        return None
    
    def save(self, worldview: Worldview) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
# 文件：模块：sqlite_worldview_repo

                INSERT OR REPLACE INTO worldviews 
                (id, novel_id, name, power_system, currency_system, timeline, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                str(worldview.id),
                str(worldview.novel_id),
                worldview.name,
                json.dumps(worldview.power_system.to_dict()) if worldview.power_system else None,
                json.dumps(worldview.currency_system, ensure_ascii=False),
                json.dumps(worldview.timeline, ensure_ascii=False),
                worldview.created_at.isoformat(),
                worldview.updated_at.isoformat()
            ))
            
            for technique in worldview.techniques:
                self._save_technique(conn, technique)
            
            for faction in worldview.factions:
                self._save_faction(conn, faction)
            
            for location in worldview.locations:
                self._save_location(conn, location)
            
            for item in worldview.items:
                self._save_item(conn, item)
            
            conn.commit()
    
    def delete(self, worldview_id: WorldviewId) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM worldviews WHERE id = ?", (str(worldview_id),))
            conn.commit()
    
    def find_technique_by_id(self, technique_id: TechniqueId) -> Optional[Technique]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM techniques WHERE id = ?", (str(technique_id),)
            )
            row = cursor.fetchone()
            if row:
                return self._row_to_technique(row)
        return None
    
    def find_techniques_by_novel(self, novel_id: NovelId) -> List[Technique]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM techniques WHERE novel_id = ?", (str(novel_id),)
            )
            return [self._row_to_technique(row) for row in cursor.fetchall()]
    
    def save_technique(self, technique: Technique) -> None:
        with sqlite3.connect(self.db_path) as conn:
            self._save_technique(conn, technique)
            conn.commit()
    
    def delete_technique(self, technique_id: TechniqueId) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM techniques WHERE id = ?", (str(technique_id),))
            conn.commit()
    
    def find_faction_by_id(self, faction_id: FactionId) -> Optional[Faction]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM factions WHERE id = ?", (str(faction_id),)
            )
            row = cursor.fetchone()
            if row:
                return self._row_to_faction(row)
        return None
    
    def find_factions_by_novel(self, novel_id: NovelId) -> List[Faction]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM factions WHERE novel_id = ?", (str(novel_id),)
            )
            return [self._row_to_faction(row) for row in cursor.fetchall()]
    
    def save_faction(self, faction: Faction) -> None:
        with sqlite3.connect(self.db_path) as conn:
            self._save_faction(conn, faction)
            conn.commit()
    
    def delete_faction(self, faction_id: FactionId) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM factions WHERE id = ?", (str(faction_id),))
            conn.commit()
    
    def find_location_by_id(self, location_id: LocationId) -> Optional[Location]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM locations WHERE id = ?", (str(location_id),)
            )
            row = cursor.fetchone()
            if row:
                return self._row_to_location(row)
        return None
    
    def find_locations_by_novel(self, novel_id: NovelId) -> List[Location]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM locations WHERE novel_id = ?", (str(novel_id),)
            )
            return [self._row_to_location(row) for row in cursor.fetchall()]
    
    def save_location(self, location: Location) -> None:
        with sqlite3.connect(self.db_path) as conn:
            self._save_location(conn, location)
            conn.commit()
    
    def delete_location(self, location_id: LocationId) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM locations WHERE id = ?", (str(location_id),))
            conn.commit()
    
    def find_item_by_id(self, item_id: ItemId) -> Optional[Item]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM items WHERE id = ?", (str(item_id),)
            )
            row = cursor.fetchone()
            if row:
                return self._row_to_item(row)
        return None
    
    def find_items_by_novel(self, novel_id: NovelId) -> List[Item]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM items WHERE novel_id = ?", (str(novel_id),)
            )
            return [self._row_to_item(row) for row in cursor.fetchall()]
    
    def save_item(self, item: Item) -> None:
        with sqlite3.connect(self.db_path) as conn:
            self._save_item(conn, item)
            conn.commit()
    
    def delete_item(self, item_id: ItemId) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM items WHERE id = ?", (str(item_id),))
            conn.commit()
    
    def _save_technique(self, conn: sqlite3.Connection, technique: Technique) -> None:
        conn.execute("""
# 文件：模块：sqlite_worldview_repo

            INSERT OR REPLACE INTO techniques 
            (id, novel_id, name, level, description, effect, requirement, creator, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            str(technique.id),
            str(technique.novel_id),
            technique.name,
            json.dumps(technique.level.to_dict()) if technique.level else None,
            technique.description,
            technique.effect,
            technique.requirement,
            technique.creator,
            technique.created_at.isoformat(),
            technique.updated_at.isoformat()
        ))
    
    def _save_faction(self, conn: sqlite3.Connection, faction: Faction) -> None:
        conn.execute("""
# 文件：模块：sqlite_worldview_repo

            INSERT OR REPLACE INTO factions 
            (id, novel_id, name, level, description, territory, leader, headquarters, relations, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            str(faction.id),
            str(faction.novel_id),
            faction.name,
            faction.level,
            faction.description,
            faction.territory,
            faction.leader,
            faction.headquarters,
            json.dumps([r.to_dict() for r in faction.relations], ensure_ascii=False),
            faction.created_at.isoformat(),
            faction.updated_at.isoformat()
        ))
    
    def _save_location(self, conn: sqlite3.Connection, location: Location) -> None:
        conn.execute("""
# 文件：模块：sqlite_worldview_repo

            INSERT OR REPLACE INTO locations 
            (id, novel_id, name, description, faction_id, parent_id, importance, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            str(location.id),
            str(location.novel_id),
            location.name,
            location.description,
            str(location.faction_id) if location.faction_id else None,
            str(location.parent_id) if location.parent_id else None,
            location.importance,
            location.created_at.isoformat(),
            location.updated_at.isoformat()
        ))
    
    def _save_item(self, conn: sqlite3.Connection, item: Item) -> None:
        conn.execute("""
# 文件：模块：sqlite_worldview_repo

            INSERT OR REPLACE INTO items 
            (id, novel_id, name, type, description, effect, rarity, owner, origin, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            str(item.id),
            str(item.novel_id),
            item.name,
            item.item_type.value,
            item.description,
            item.effect,
            item.rarity,
            item.owner,
            item.origin,
            item.created_at.isoformat(),
            item.updated_at.isoformat()
        ))
    
    def _row_to_worldview(self, row: sqlite3.Row) -> Worldview:
        novel_id = NovelId(row["novel_id"])
        return Worldview(
            id=WorldviewId(row["id"]),
            novel_id=novel_id,
            name=row["name"] or "",
            power_system=PowerSystem.from_dict(json.loads(row["power_system"])) if row["power_system"] else None,
            currency_system=json.loads(row["currency_system"]) if row["currency_system"] else {},
            timeline=json.loads(row["timeline"]) if row["timeline"] else {},
            techniques=self.find_techniques_by_novel(novel_id),
            factions=self.find_factions_by_novel(novel_id),
            locations=self.find_locations_by_novel(novel_id),
            items=self.find_items_by_novel(novel_id),
            created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else datetime.now(),
            updated_at=datetime.fromisoformat(row["updated_at"]) if row["updated_at"] else datetime.now()
        )
    
    def _row_to_technique(self, row: sqlite3.Row) -> Technique:
        return Technique(
            id=TechniqueId(row["id"]),
            novel_id=NovelId(row["novel_id"]),
            name=row["name"],
            level=TechniqueLevel.from_dict(json.loads(row["level"])) if row["level"] else None,
            description=row["description"] or "",
            effect=row["effect"] or "",
            requirement=row["requirement"] or "",
            creator=row["creator"] or "",
            created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else datetime.now(),
            updated_at=datetime.fromisoformat(row["updated_at"]) if row["updated_at"] else datetime.now()
        )
    
    def _row_to_faction(self, row: sqlite3.Row) -> Faction:
        return Faction(
            id=FactionId(row["id"]),
            novel_id=NovelId(row["novel_id"]),
            name=row["name"],
            level=row["level"] or "",
            description=row["description"] or "",
            territory=row["territory"] or "",
            leader=row["leader"] or "",
            headquarters=row["headquarters"] or "",
            relations=[FactionRelation.from_dict(r) for r in json.loads(row["relations"])] if row["relations"] else [],
            created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else datetime.now(),
            updated_at=datetime.fromisoformat(row["updated_at"]) if row["updated_at"] else datetime.now()
        )
    
    def _row_to_location(self, row: sqlite3.Row) -> Location:
        return Location(
            id=LocationId(row["id"]),
            novel_id=NovelId(row["novel_id"]),
            name=row["name"],
            description=row["description"] or "",
            faction_id=FactionId(row["faction_id"]) if row["faction_id"] else None,
            parent_id=LocationId(row["parent_id"]) if row["parent_id"] else None,
            importance=row["importance"] or 0,
            created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else datetime.now(),
            updated_at=datetime.fromisoformat(row["updated_at"]) if row["updated_at"] else datetime.now()
        )
    
    def _row_to_item(self, row: sqlite3.Row) -> Item:
        from domain.types import ItemType
        return Item(
            id=ItemId(row["id"]),
            novel_id=NovelId(row["novel_id"]),
            name=row["name"],
            item_type=ItemType(row["type"]) if row["type"] else ItemType.OTHER,
            description=row["description"] or "",
            effect=row["effect"] or "",
            rarity=row["rarity"] or "",
            owner=row["owner"] or "",
            origin=row["origin"] or "",
            created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else datetime.now(),
            updated_at=datetime.fromisoformat(row["updated_at"]) if row["updated_at"] else datetime.now()
        )
