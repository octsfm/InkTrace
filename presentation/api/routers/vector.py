"""
向量索引API路由

作者：孔利群
"""

# 文件路径：presentation/api/routers/vector.py


from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from application.services.vector_index_service import VectorIndexService
from domain.types import NovelId


router = APIRouter(prefix="/api/novels/{novel_id}/vector", tags=["vector"])


class IndexStatusResponse(BaseModel):
    total_vectors: int
    chapters_count: int
    is_indexed: bool


class IndexResultResponse(BaseModel):
    chapters_indexed: int
    characters_indexed: int
    worldview_indexed: int
    errors: List[str]


def get_vector_index_service() -> VectorIndexService:
    from presentation.api.dependencies import get_vector_index_service
    return get_vector_index_service()


@router.post("/index", response_model=IndexResultResponse)
def index_novel(
    novel_id: str,
    service: VectorIndexService = Depends(get_vector_index_service)
):
    """索引小说内容"""
    try:
        stats = service.index_novel(NovelId(novel_id))
        return IndexResultResponse(
            chapters_indexed=stats["chapters_indexed"],
            characters_indexed=stats["characters_indexed"],
            worldview_indexed=stats["worldview_indexed"],
            errors=stats["errors"]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status", response_model=IndexStatusResponse)
def get_index_status(
    novel_id: str,
    service: VectorIndexService = Depends(get_vector_index_service)
):
    """获取索引状态"""
# 文件：模块：vector

    status = service.get_index_status(NovelId(novel_id))
    return IndexStatusResponse(**status)


@router.delete("/index")
def delete_index(
    novel_id: str,
    service: VectorIndexService = Depends(get_vector_index_service)
):
    """删除索引"""
    count = service.delete_novel_index(NovelId(novel_id))
    return {"message": f"已删除 {count} 个向量"}
