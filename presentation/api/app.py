"""
FastAPI应用配置模块

作者：孔利群
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from presentation.api.routers import novel, content, writing, export
from presentation.api.routers import project, template, character, worldview


def create_app() -> FastAPI:
    """创建FastAPI应用"""
    app = FastAPI(
        title="InkTrace Novel AI",
        description="AI小说自动编写助手API",
        version="2.0.0"
    )
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # 一期路由
    app.include_router(novel.router)
    app.include_router(content.router)
    app.include_router(writing.router)
    app.include_router(export.router)
    
    # 二期路由
    app.include_router(project.router)
    app.include_router(template.router)
    app.include_router(character.router)
    app.include_router(worldview.router)
    
    @app.get("/")
    async def root():
        return {"message": "InkTrace Novel AI", "version": "2.0.0"}
    
    @app.get("/health")
    async def health():
        return {"status": "healthy"}
    
    return app


app = create_app()
