"""
项目实体

作者：孔利群
"""

# 文件路径：domain/entities/project.py


from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from domain.types import ProjectId, NovelId, ProjectStatus, GenreType


@dataclass
class ProjectConfig:
    """项目配置值对象"""
    genre: GenreType = GenreType.XUANHUAN
    target_words: int = 8000000
    chapter_words: int = 2100
    style_intensity: float = 0.8
    check_consistency: bool = True
    memory: dict = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        return {
            "genre": self.genre.value,
            "target_words": self.target_words,
            "chapter_words": self.chapter_words,
            "style_intensity": self.style_intensity,
            "check_consistency": self.check_consistency,
            "memory": self.memory
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "ProjectConfig":
        return cls(
            genre=GenreType(data.get("genre", "xuanhuan")),
            target_words=data.get("target_words", 8000000),
            chapter_words=data.get("chapter_words", 2100),
            style_intensity=data.get("style_intensity", 0.8),
            check_consistency=data.get("check_consistency", True),
            memory=data.get("memory", {}) or {}
        )


@dataclass
class Project:
    """项目实体"""
# 文件：模块：project

    id: ProjectId
    name: str
    novel_id: NovelId
    config: ProjectConfig = field(default_factory=ProjectConfig)
    status: ProjectStatus = ProjectStatus.ACTIVE
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def is_active(self) -> bool:
        return self.status == ProjectStatus.ACTIVE
    
    def is_archived(self) -> bool:
        return self.status == ProjectStatus.ARCHIVED
    
    def archive(self) -> None:
        if self.status == ProjectStatus.ARCHIVED:
            raise ValueError("项目已归档")
        self.status = ProjectStatus.ARCHIVED
        self.updated_at = datetime.now()
    
    def activate(self) -> None:
        if self.status == ProjectStatus.ACTIVE:
            raise ValueError("项目已激活")
        self.status = ProjectStatus.ACTIVE
        self.updated_at = datetime.now()
    
    def update_config(self, config: ProjectConfig) -> None:
        self.config = config
        self.updated_at = datetime.now()
    
    def update_name(self, name: str) -> None:
        if not name or not name.strip():
            raise ValueError("项目名称不能为空")
        self.name = name.strip()
        self.updated_at = datetime.now()
    
    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "name": self.name,
            "novel_id": str(self.novel_id),
            "config": self.config.to_dict(),
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Project":
        return cls(
            id=ProjectId(data["id"]),
            name=data["name"],
            novel_id=NovelId(data["novel_id"]),
            config=ProjectConfig.from_dict(data.get("config", {})),
            status=ProjectStatus(data.get("status", "active")),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"])
        )
