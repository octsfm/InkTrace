"""
项目管理服务模块

作者：孔利群
"""

from datetime import datetime
from typing import List, Optional
import uuid

from domain.entities.novel import Novel
from domain.types import NovelId
from domain.repositories.novel_repository import INovelRepository
from application.dto.request_dto import CreateNovelRequest
from application.dto.response_dto import NovelResponse


class ProjectService:
    """
    项目管理服务
    
    负责小说项目的创建、查询、删除。
    """

    def __init__(self, novel_repo: INovelRepository):
        """
        初始化服务
        
        Args:
            novel_repo: 小说仓储
        """
        self.novel_repo = novel_repo

    def create_novel(self, request: CreateNovelRequest) -> NovelResponse:
        """
        创建小说项目
        
        Args:
            request: 创建请求
            
        Returns:
            小说响应
        """
        now = datetime.now()
        novel_id = NovelId(str(uuid.uuid4()))
        
        novel = Novel(
            id=novel_id,
            title=request.title,
            author=request.author,
            genre=request.genre,
            target_word_count=request.target_word_count,
            current_word_count=0,
            created_at=now,
            updated_at=now
        )
        
        self.novel_repo.save(novel)
        
        return self._to_response(novel)

    def get_novel(self, novel_id: str) -> Optional[NovelResponse]:
        """
        获取小说
        
        Args:
            novel_id: 小说ID
            
        Returns:
            小说响应，不存在则返回None
        """
        novel = self.novel_repo.find_by_id(NovelId(novel_id))
        
        if novel:
            return self._to_response(novel)
        return None

    def list_novels(self) -> List[NovelResponse]:
        """
        列出所有小说
        
        Returns:
            小说响应列表
        """
        novels = self.novel_repo.find_all()
        return [self._to_response(novel) for novel in novels]

    def delete_novel(self, novel_id: str) -> None:
        """
        删除小说
        
        Args:
            novel_id: 小说ID
        """
        self.novel_repo.delete(NovelId(novel_id))

    def _to_response(self, novel: Novel) -> NovelResponse:
        """
        将实体转换为响应
        
        Args:
            novel: 小说实体
            
        Returns:
            小说响应
        """
        return NovelResponse(
            id=novel.id.value,
            title=novel.title,
            author=novel.author,
            genre=novel.genre,
            target_word_count=novel.target_word_count,
            current_word_count=novel.current_word_count,
            chapter_count=novel.chapter_count,
            created_at=novel.created_at.isoformat(),
            updated_at=novel.updated_at.isoformat()
        )
