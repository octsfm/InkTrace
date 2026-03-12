"""
FastAPI应用配置模块

作者：孔利群
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from presentation.api.routers import novel, content, writing, export


def create_app() -> FastAPI:
    """
    创建FastAPI应用
    
    Returns:
        FastAPI应用实例
    """
    app = FastAPI(
        title="InkTrace Novel AI",
        description="AI小说自动编写助手API",
        version="1.0.0",
        author="孔利群"
    )
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    app.include_router(novel.router, prefix="/api/novels", tags=["小说管理"])
    app.include_router(content.router, prefix="/api/content", tags=["内容管理"])
    app.include_router(writing.router, prefix="/api/writing", tags=["续写服务"])
    app.include_router(export.router, prefix="/api/export", tags=["导出服务"])
    
    @app.get("/")
    async def root():
        return {"message": "InkTrace Novel AI", "version": "1.0.0"}
    
    @app.get("/health")
    async def health():
        return {"status": "healthy"}
    
    return app


app = create_app()
