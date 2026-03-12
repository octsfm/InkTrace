"""
SQLite大纲仓储实现

作者：孔利群
"""

import sqlite3
import json
from typing import Optional
from datetime import datetime

from domain.types import OutlineId, NovelId, PlotType, PlotStatus
from domain.entities.outline import Outline, VolumeOutline, PlotNode
from domain.repositories.outline_repository import IOutlineRepository


class SQLiteOutlineRepository(IOutlineRepository):
    """SQLite大纲仓储实现"""

    def __init__(self, db_path: str):
        """
        初始化仓储
        
        Args:
            db_path: 数据库文件路径
        """
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """初始化数据库表"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS outlines (
                    id TEXT PRIMARY KEY,
                    novel_id TEXT UNIQUE NOT NULL,
                    premise TEXT,
                    story_background TEXT,
                    world_setting TEXT,
                    main_plots TEXT,
                    sub_plots TEXT,
                    volumes TEXT,
                    created_at TIMESTAMP,
                    updated_at TIMESTAMP,
                    FOREIGN KEY (novel_id) REFERENCES novels(id)
                )
            ''')

    def save(self, outline: Outline) -> None:
        """保存大纲"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                INSERT OR REPLACE INTO outlines 
                (id, novel_id, premise, story_background, world_setting, main_plots, sub_plots, volumes, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                outline.id.value,
                outline.novel_id.value,
                outline.premise,
                outline.story_background,
                outline.world_setting,
                json.dumps([self._plot_node_to_dict(p) for p in outline.main_plots], ensure_ascii=False),
                json.dumps([self._plot_node_to_dict(p) for p in outline.sub_plots], ensure_ascii=False),
                json.dumps([self._volume_to_dict(v) for v in outline.volumes], ensure_ascii=False),
                outline.created_at.isoformat(),
                outline.updated_at.isoformat()
            ))

    def find_by_id(self, outline_id: OutlineId) -> Optional[Outline]:
        """根据ID查找大纲"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                'SELECT * FROM outlines WHERE id = ?', 
                (outline_id.value,)
            )
            row = cursor.fetchone()
            
            if row:
                return self._row_to_outline(row)
            return None

    def find_by_novel(self, novel_id: NovelId) -> Optional[Outline]:
        """查找小说的大纲"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                'SELECT * FROM outlines WHERE novel_id = ?',
                (novel_id.value,)
            )
            row = cursor.fetchone()
            
            if row:
                return self._row_to_outline(row)
            return None

    def delete(self, outline_id: OutlineId) -> None:
        """删除大纲"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('DELETE FROM outlines WHERE id = ?', (outline_id.value,))

    def _row_to_outline(self, row: sqlite3.Row) -> Outline:
        """将数据库行转换为大纲实体"""
        main_plots = []
        if row['main_plots']:
            for p in json.loads(row['main_plots']):
                main_plots.append(self._dict_to_plot_node(p))
        
        sub_plots = []
        if row['sub_plots']:
            for p in json.loads(row['sub_plots']):
                sub_plots.append(self._dict_to_plot_node(p))
        
        volumes = []
        if row['volumes']:
            for v in json.loads(row['volumes']):
                volumes.append(self._dict_to_volume(v))
        
        return Outline(
            id=OutlineId(row['id']),
            novel_id=NovelId(row['novel_id']),
            premise=row['premise'] or '',
            story_background=row['story_background'] or '',
            world_setting=row['world_setting'] or '',
            main_plots=main_plots,
            sub_plots=sub_plots,
            volumes=volumes,
            created_at=datetime.fromisoformat(row['created_at']),
            updated_at=datetime.fromisoformat(row['updated_at'])
        )

    def _plot_node_to_dict(self, node: PlotNode) -> dict:
        """将剧情节点转换为字典"""
        return {
            'id': node.id,
            'title': node.title,
            'description': node.description,
            'type': node.type.value,
            'status': node.status.value,
            'start_chapter': node.start_chapter,
            'end_chapter': node.end_chapter,
            'involved_characters': node.involved_characters,
            'dependencies': node.dependencies
        }

    def _dict_to_plot_node(self, d: dict) -> PlotNode:
        """将字典转换为剧情节点"""
        return PlotNode(
            id=d['id'],
            title=d['title'],
            description=d['description'],
            type=PlotType(d['type']),
            status=PlotStatus(d['status']),
            start_chapter=d.get('start_chapter'),
            end_chapter=d.get('end_chapter'),
            involved_characters=d.get('involved_characters', []),
            dependencies=d.get('dependencies', [])
        )

    def _volume_to_dict(self, volume: VolumeOutline) -> dict:
        """将分卷转换为字典"""
        return {
            'number': volume.number,
            'title': volume.title,
            'summary': volume.summary,
            'target_word_count': volume.target_word_count,
            'plot_nodes': [self._plot_node_to_dict(p) for p in volume.plot_nodes]
        }

    def _dict_to_volume(self, d: dict) -> VolumeOutline:
        """将字典转换为分卷"""
        return VolumeOutline(
            number=d['number'],
            title=d['title'],
            summary=d['summary'],
            target_word_count=d['target_word_count'],
            plot_nodes=[self._dict_to_plot_node(p) for p in d.get('plot_nodes', [])]
        )
