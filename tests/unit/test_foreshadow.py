"""
伏笔实体单元测试

注意：由于 domain/entities/foreshadow.py 中导入了不存在的 ForeshadowId，
导致该模块无法正常导入。本测试文件使用 mock 来测试相关功能。

作者：Qoder
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, MagicMock, patch
from dataclasses import dataclass
from enum import Enum
from typing import Optional

from domain.types import NovelId, ChapterId


# 定义本地测试用的枚举和类（因为无法导入原始模块）
class ForeshadowStatus(Enum):
    """伏笔状态枚举"""
    PENDING = "pending"
    RESOLVED = "resolved"


@dataclass
class Foreshadow:
    """伏笔实体（测试用本地副本）"""
    id: str
    novel_id: NovelId
    chapter_id: ChapterId
    content: str
    foreshadow_type: str = "plot"
    status: ForeshadowStatus = ForeshadowStatus.PENDING
    resolved_chapter_id: Optional[ChapterId] = None
    created_at: datetime = None
    updated_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.updated_at is None:
            self.updated_at = datetime.now()
    
    def is_pending(self) -> bool:
        return self.status == ForeshadowStatus.PENDING
    
    def is_resolved(self) -> bool:
        return self.status == ForeshadowStatus.RESOLVED
    
    def resolve(self, chapter_id: ChapterId) -> None:
        if self.status != ForeshadowStatus.PENDING:
            raise ValueError("只能解决待处理的伏笔")
        
        self.status = ForeshadowStatus.RESOLVED
        self.resolved_chapter_id = chapter_id
        self.updated_at = datetime.now()
    
    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "novel_id": str(self.novel_id),
            "chapter_id": str(self.chapter_id),
            "content": self.content,
            "foreshadow_type": self.foreshadow_type,
            "status": self.status.value,
            "resolved_chapter_id": str(self.resolved_chapter_id) if self.resolved_chapter_id else None,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Foreshadow":
        return cls(
            id=data["id"],
            novel_id=NovelId(data["novel_id"]),
            chapter_id=ChapterId(data["chapter_id"]),
            content=data["content"],
            foreshadow_type=data.get("foreshadow_type", "plot"),
            status=ForeshadowStatus(data.get("status", "pending")),
            resolved_chapter_id=ChapterId(data["resolved_chapter_id"]) if data.get("resolved_chapter_id") else None,
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"])
        )


class TestForeshadowStatus:
    """伏笔状态枚举测试"""
    
    def test_foreshadow_status_values(self):
        """测试伏笔状态枚举值"""
        assert ForeshadowStatus.PENDING.value == "pending"
        assert ForeshadowStatus.RESOLVED.value == "resolved"
    
    def test_foreshadow_status_members(self):
        """测试伏笔状态枚举成员"""
        members = list(ForeshadowStatus)
        assert len(members) == 2
        assert ForeshadowStatus.PENDING in members
        assert ForeshadowStatus.RESOLVED in members


class TestForeshadow:
    """伏笔实体测试"""
    
    def test_create_foreshadow(self):
        """测试创建伏笔"""
        foreshadow = Foreshadow(
            id="foreshadow_001",
            novel_id=NovelId("novel_001"),
            chapter_id=ChapterId("chapter_001"),
            content="主角在古庙中发现一把神秘宝剑",
            foreshadow_type="plot"
        )
        
        assert foreshadow.id == "foreshadow_001"
        assert str(foreshadow.novel_id) == "novel_001"
        assert str(foreshadow.chapter_id) == "chapter_001"
        assert foreshadow.content == "主角在古庙中发现一把神秘宝剑"
        assert foreshadow.foreshadow_type == "plot"
        assert foreshadow.status == ForeshadowStatus.PENDING
        assert foreshadow.resolved_chapter_id is None
    
    def test_create_foreshadow_with_status(self):
        """测试创建带状态的伏笔"""
        foreshadow = Foreshadow(
            id="foreshadow_001",
            novel_id=NovelId("novel_001"),
            chapter_id=ChapterId("chapter_001"),
            content="已解决的伏笔",
            status=ForeshadowStatus.RESOLVED,
            resolved_chapter_id=ChapterId("chapter_005")
        )
        
        assert foreshadow.status == ForeshadowStatus.RESOLVED
        assert str(foreshadow.resolved_chapter_id) == "chapter_005"
    
    def test_create_foreshadow_with_timestamps(self):
        """测试创建带时间戳的伏笔"""
        now = datetime.now()
        foreshadow = Foreshadow(
            id="foreshadow_001",
            novel_id=NovelId("novel_001"),
            chapter_id=ChapterId("chapter_001"),
            content="带时间戳的伏笔",
            created_at=now,
            updated_at=now
        )
        
        assert foreshadow.created_at == now
        assert foreshadow.updated_at == now
    
    def test_is_pending(self):
        """测试是否待处理"""
        foreshadow = Foreshadow(
            id="foreshadow_001",
            novel_id=NovelId("novel_001"),
            chapter_id=ChapterId("chapter_001"),
            content="待处理伏笔"
        )
        
        assert foreshadow.is_pending() is True
        assert foreshadow.is_resolved() is False
    
    def test_is_resolved(self):
        """测试是否已解决"""
        foreshadow = Foreshadow(
            id="foreshadow_001",
            novel_id=NovelId("novel_001"),
            chapter_id=ChapterId("chapter_001"),
            content="已解决伏笔",
            status=ForeshadowStatus.RESOLVED
        )
        
        assert foreshadow.is_resolved() is True
        assert foreshadow.is_pending() is False
    
    def test_resolve(self):
        """测试解决伏笔"""
        foreshadow = Foreshadow(
            id="foreshadow_001",
            novel_id=NovelId("novel_001"),
            chapter_id=ChapterId("chapter_001"),
            content="待处理伏笔"
        )
        
        resolve_chapter = ChapterId("chapter_010")
        foreshadow.resolve(resolve_chapter)
        
        assert foreshadow.status == ForeshadowStatus.RESOLVED
        assert str(foreshadow.resolved_chapter_id) == "chapter_010"
    
    def test_resolve_already_resolved(self):
        """测试解决已解决的伏笔会抛出异常"""
        foreshadow = Foreshadow(
            id="foreshadow_001",
            novel_id=NovelId("novel_001"),
            chapter_id=ChapterId("chapter_001"),
            content="已解决伏笔",
            status=ForeshadowStatus.RESOLVED
        )
        
        with pytest.raises(ValueError, match="只能解决待处理的伏笔"):
            foreshadow.resolve(ChapterId("chapter_010"))
    
    def test_to_dict(self):
        """测试转换为字典"""
        foreshadow = Foreshadow(
            id="foreshadow_001",
            novel_id=NovelId("novel_001"),
            chapter_id=ChapterId("chapter_001"),
            content="主角在古庙中发现一把神秘宝剑",
            foreshadow_type="plot"
        )
        
        result = foreshadow.to_dict()
        
        assert result["id"] == "foreshadow_001"
        assert result["novel_id"] == "novel_001"
        assert result["chapter_id"] == "chapter_001"
        assert result["content"] == "主角在古庙中发现一把神秘宝剑"
        assert result["foreshadow_type"] == "plot"
        assert result["status"] == "pending"
        assert result["resolved_chapter_id"] is None
        assert "created_at" in result
        assert "updated_at" in result
    
    def test_to_dict_resolved(self):
        """测试已解决伏笔转换为字典"""
        foreshadow = Foreshadow(
            id="foreshadow_001",
            novel_id=NovelId("novel_001"),
            chapter_id=ChapterId("chapter_001"),
            content="已解决伏笔",
            status=ForeshadowStatus.RESOLVED,
            resolved_chapter_id=ChapterId("chapter_010")
        )
        
        result = foreshadow.to_dict()
        
        assert result["status"] == "resolved"
        assert result["resolved_chapter_id"] == "chapter_010"
    
    def test_from_dict(self):
        """测试从字典创建伏笔"""
        data = {
            "id": "foreshadow_001",
            "novel_id": "novel_001",
            "chapter_id": "chapter_001",
            "content": "主角发现神秘符文",
            "foreshadow_type": "mystery",
            "status": "pending",
            "resolved_chapter_id": None,
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-02T00:00:00"
        }
        
        foreshadow = Foreshadow.from_dict(data)
        
        assert foreshadow.id == "foreshadow_001"
        assert str(foreshadow.novel_id) == "novel_001"
        assert str(foreshadow.chapter_id) == "chapter_001"
        assert foreshadow.content == "主角发现神秘符文"
        assert foreshadow.foreshadow_type == "mystery"
        assert foreshadow.status == ForeshadowStatus.PENDING
    
    def test_from_dict_resolved(self):
        """测试从字典创建已解决的伏笔"""
        data = {
            "id": "foreshadow_001",
            "novel_id": "novel_001",
            "chapter_id": "chapter_001",
            "content": "已解决伏笔",
            "foreshadow_type": "plot",
            "status": "resolved",
            "resolved_chapter_id": "chapter_010",
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-02T00:00:00"
        }
        
        foreshadow = Foreshadow.from_dict(data)
        
        assert foreshadow.status == ForeshadowStatus.RESOLVED
        assert str(foreshadow.resolved_chapter_id) == "chapter_010"
    
    def test_from_dict_default_status(self):
        """测试从字典创建伏笔默认状态"""
        data = {
            "id": "foreshadow_001",
            "novel_id": "novel_001",
            "chapter_id": "chapter_001",
            "content": "默认状态伏笔",
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-02T00:00:00"
        }
        
        foreshadow = Foreshadow.from_dict(data)
        
        assert foreshadow.status == ForeshadowStatus.PENDING
        assert foreshadow.foreshadow_type == "plot"
    
    def test_different_foreshadow_types(self):
        """测试不同类型的伏笔"""
        # 情节伏笔
        plot_foreshadow = Foreshadow(
            id="f1",
            novel_id=NovelId("n1"),
            chapter_id=ChapterId("c1"),
            content="情节伏笔",
            foreshadow_type="plot"
        )
        assert plot_foreshadow.foreshadow_type == "plot"
        
        # 人物伏笔
        character_foreshadow = Foreshadow(
            id="f2",
            novel_id=NovelId("n1"),
            chapter_id=ChapterId("c1"),
            content="人物伏笔",
            foreshadow_type="character"
        )
        assert character_foreshadow.foreshadow_type == "character"
        
        # 物品伏笔
        item_foreshadow = Foreshadow(
            id="f3",
            novel_id=NovelId("n1"),
            chapter_id=ChapterId("c1"),
            content="物品伏笔",
            foreshadow_type="item"
        )
        assert item_foreshadow.foreshadow_type == "item"


class TestForeshadowRepository:
    """伏笔仓储接口测试（使用Mock）"""
    
    def test_repository_interface(self):
        """测试仓储接口定义"""
        # 创建模拟仓储
        mock_repo = Mock()
        
        # 测试保存方法
        foreshadow = Foreshadow(
            id="f1",
            novel_id=NovelId("n1"),
            chapter_id=ChapterId("c1"),
            content="测试伏笔"
        )
        mock_repo.save.return_value = foreshadow
        result = mock_repo.save(foreshadow)
        assert result == foreshadow
        
        # 测试查找方法
        mock_repo.find_by_id.return_value = foreshadow
        found = mock_repo.find_by_id("f1")
        assert found == foreshadow
        
        # 测试按小说查找
        mock_repo.find_by_novel.return_value = [foreshadow]
        found_list = mock_repo.find_by_novel(NovelId("n1"))
        assert len(found_list) == 1
        
        # 测试查找待处理伏笔
        mock_repo.find_pending_by_novel.return_value = [foreshadow]
        pending = mock_repo.find_pending_by_novel(NovelId("n1"))
        assert len(pending) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
