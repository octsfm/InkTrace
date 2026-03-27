# 文件：模块：app
"""
FastAPI应用配置模块

作者：孔利群
"""

# 文件路径：presentation/api/app.py


import time
import traceback
import uuid
from fastapi import FastAPI, Request
from fastapi.exceptions import HTTPException as FastAPIHTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from application.services.logging_service import (
    build_log_context,
    get_logger,
    reset_request_id,
    set_request_id,
    setup_logging,
)
from presentation.api.routers import novel, content, writing, export, chapter_editor
from presentation.api.routers import project, template, character, worldview
from presentation.api.routers import vector, rag, config
from presentation.api.routers import projects_v2

logger = get_logger(__name__)
APP_VERSION = "3.0.0"


def create_app() -> FastAPI:
    setup_logging()
    logger.info("应用启动开始", extra=build_log_context(event="app_starting", module="app", version=APP_VERSION))
    app = FastAPI(
        title="InkTrace Novel AI",
        description="AI小说自动编写助手API",
        version=APP_VERSION
    )
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    logger.info("中间件加载完成", extra=build_log_context(event="app_middleware_registered", module="app", version=APP_VERSION))

    @app.middleware("http")
    async def request_log_middleware(request: Request, call_next):
        started_at = time.perf_counter()
        header_request_id = request.headers.get("X-Request-Id", "").strip()
        request_id = header_request_id or f"req_{int(time.time())}_{uuid.uuid4().hex[:6]}"
        token = set_request_id(request_id)
        request.state.request_id = request_id
        client_ip = request.client.host if request.client else ""
        logger.info(
            "请求开始",
            extra=build_log_context(
                event="request_started",
                request_id=request_id,
                method=request.method,
                path=request.url.path,
                client_ip=client_ip,
                module="app",
            ),
        )
        try:
            response = await call_next(request)
            duration_ms = int((time.perf_counter() - started_at) * 1000)
            response.headers["X-Request-Id"] = request_id
            logger.info(
                "请求完成",
                extra=build_log_context(
                    event="request_finished",
                    request_id=request_id,
                    method=request.method,
                    path=request.url.path,
                    status_code=getattr(response, "status_code", 200),
                    duration_ms=duration_ms,
                    client_ip=client_ip,
                    module="app",
                ),
            )
            return response
        except Exception as exc:
            duration_ms = int((time.perf_counter() - started_at) * 1000)
            logger.exception(
                "请求异常",
                extra=build_log_context(
                    event="request_failed",
                    request_id=request_id,
                    method=request.method,
                    path=request.url.path,
                    duration_ms=duration_ms,
                    client_ip=client_ip,
                    exception_type=type(exc).__name__,
                    exception_message=str(exc),
                    module="app",
                ),
            )
            raise
        finally:
            reset_request_id(token)
    
    # 一期路由
    app.include_router(novel.router)
    app.include_router(content.router)
    app.include_router(writing.router)
    app.include_router(export.router, prefix="/api")
    app.include_router(chapter_editor.router)
    
    # 二期路由
    app.include_router(project.router)
    app.include_router(template.router)
    app.include_router(character.router)
    app.include_router(worldview.router)
    
    # 三期路由
    app.include_router(vector.router)
    app.include_router(rag.router)
    
    # 配置管理路由
    app.include_router(config.router)
    app.include_router(projects_v2.router)
    logger.info("路由加载完成", extra=build_log_context(event="app_router_registered", module="app", version=APP_VERSION))

    @app.exception_handler(FastAPIHTTPException)
    async def http_exception_handler(request: Request, exc: FastAPIHTTPException):
        request_id = getattr(request.state, "request_id", "")
        logger.warning(
            "HTTP异常",
            extra=build_log_context(
                event="http_exception",
                request_id=request_id,
                path=request.url.path,
                exception_type=type(exc).__name__,
                exception_message=str(exc.detail),
                status_code=exc.status_code,
                module="app",
            ),
        )
        response = JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
        if request_id:
            response.headers["X-Request-Id"] = request_id
        return response

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        request_id = getattr(request.state, "request_id", "")
        logger.error(
            "未捕获异常",
            extra=build_log_context(
                event="unhandled_exception",
                request_id=request_id,
                path=request.url.path,
                exception_type=type(exc).__name__,
                exception_message=str(exc),
                traceback=traceback.format_exc(),
                module="app",
            ),
        )
        response = JSONResponse(status_code=500, content={"detail": "Internal Server Error"})
        if request_id:
            response.headers["X-Request-Id"] = request_id
        return response
    
    @app.get("/")
    async def root():
        return {"message": "InkTrace Novel AI", "version": APP_VERSION}
    
    @app.get("/health")
    async def health():
        return {"status": "healthy"}
    
    logger.info("应用启动成功", extra=build_log_context(event="app_started", module="app", version=APP_VERSION))
    return app


app = create_app()
