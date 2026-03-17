"""
RAG检索API路由

作者：孔利群
"""

# 文件路径：presentation/api/routers/rag.py


from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from application.services.rag_retrieval_service import RAGRetrievalService
from domain.types import NovelId


router = APIRouter(prefix="/api/novels/{novel_id}/rag", tags=["rag"])


class SearchRequest(BaseModel):
    query: str
    n_results: int = 5


class SearchResultItem(BaseModel):
    id: str
    content: str
    score: float
    source_type: str
    source_id: str


class RAGContextResponse(BaseModel):
    query: str
    chapters: List[SearchResultItem]
    characters: List[SearchResultItem]
    worldview: List[SearchResultItem]


def get_rag_retrieval_service() -> RAGRetrievalService:
    from presentation.api.dependencies import get_rag_retrieval_service
    return get_rag_retrieval_service()


@router.post("/search", response_model=List[SearchResultItem])
def search_content(
    novel_id: str,
    request: SearchRequest,
    service: RAGRetrievalService = Depends(get_rag_retrieval_service)
):
    """语义搜索"""
    results = service.search_relevant_content(
        NovelId(novel_id),
        request.query,
        request.n_results
    )
    return [
        SearchResultItem(
            id=r.id,
            content=r.content[:500] + "..." if len(r.content) > 500 else r.content,
            score=r.score,
            source_type=r.metadata.source_type,
            source_id=r.metadata.source_id
        ) for r in results
    ]


@router.post("/context", response_model=RAGContextResponse)
def get_context(
    novel_id: str,
    request: SearchRequest,
    service: RAGRetrievalService = Depends(get_rag_retrieval_service)
):
    """获取RAG上下文"""
# 文件：模块：rag

    context = service.get_context_for_writing(
        NovelId(novel_id),
        request.query
    )
    
    def to_item(r):
        return SearchResultItem(
            id=r.id,
            content=r.content[:300] + "..." if len(r.content) > 300 else r.content,
            score=r.score,
            source_type=r.metadata.source_type,
            source_id=r.metadata.source_id
        )
    
    return RAGContextResponse(
        query=request.query,
        chapters=[to_item(r) for r in context["chapters"]],
        characters=[to_item(r) for r in context["characters"]],
        worldview=[to_item(r) for r in context["worldview"]]
    )


@router.post("/prompt")
def build_prompt(
    novel_id: str,
    request: SearchRequest,
    service: RAGRetrievalService = Depends(get_rag_retrieval_service)
):
    """构建RAG Prompt"""
    prompt = service.build_rag_prompt(
        NovelId(novel_id),
        request.query
    )
    return {"prompt": prompt}
