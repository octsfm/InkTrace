from __future__ import annotations

import os
import time
import traceback
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exception_handlers import request_validation_exception_handler as fastapi_request_validation_exception_handler
from fastapi.exceptions import HTTPException as FastAPIHTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from application.services.logging_service import (
    build_log_context,
    get_logger,
    reset_request_id,
    set_request_id,
    setup_logging,
)
from application.services.runtime_metrics_service import (
    get_runtime_metrics_snapshot,
    mark_request_finish,
    mark_request_start,
)
from application.services.v1.logging import build_v1_log_context, get_v1_logger
from infrastructure.persistence.sqlite_utils import get_sqlite_metrics_snapshot
from presentation.api.dependencies import warmup_singletons_for_startup
from presentation.api.routers.v1 import chapters as chapters_v1
from presentation.api.routers.v1 import characters as characters_v1
from presentation.api.routers.v1 import foreshadows as foreshadows_v1
from presentation.api.routers.v1 import health as health_v1
from presentation.api.routers.v1 import io as io_v1
from presentation.api.routers.v1 import outlines as outlines_v1
from presentation.api.routers.v1 import sessions as sessions_v1
from presentation.api.routers.v1 import timeline as timeline_v1
from presentation.api.routers.v1 import works as works_v1
from presentation.api.routers.v2.ai import continuation as ai_continuation_v2
from presentation.api.routers.v2.ai import context_pack as ai_context_pack_v2
from presentation.api.routers.v2.ai import initialization as ai_initialization_v2
from presentation.api.routers.v2.ai import jobs as ai_jobs_v2
from presentation.api.routers.v2.ai import settings as ai_settings_v2
from presentation.api.routers.v1.schemas import V1APIError, build_error_response

logger = get_logger(__name__)
v1_api_logger = get_v1_logger("api")
APP_VERSION = "3.0.0"
SUPPRESS_PROGRESS_POLL = str(os.getenv("INKTRACE_LOG_SUPPRESS_PROGRESS_POLL", "1")).strip().lower() not in {"0", "false"}


def _is_progress_poll_request(method: str, path: str) -> bool:
    return str(method).upper() == "GET" and str(path or "").startswith("/api/content/organize/progress/")


def create_app() -> FastAPI:
    setup_logging()
    logger.info("app starting", extra=build_log_context(event="app_starting", module="app", version=APP_VERSION))

    @asynccontextmanager
    async def _lifespan(_app: FastAPI):
        logger.info("startup warmup begin", extra=build_log_context(event="app_startup_warmup_begin", module="app"))
        warmup_singletons_for_startup()
        logger.info("startup warmup done", extra=build_log_context(event="app_startup_warmup_done", module="app"))
        yield

    app = FastAPI(
        title="InkTrace Novel AI",
        description="InkTrace API",
        version=APP_VERSION,
        lifespan=_lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    logger.info("middleware registered", extra=build_log_context(event="app_middleware_registered", module="app", version=APP_VERSION))

    @app.middleware("http")
    async def request_log_middleware(request: Request, call_next):
        started_at = time.perf_counter()
        mark_request_start()
        header_request_id = request.headers.get("X-Request-Id", "").strip()
        request_id = header_request_id or f"req_{int(time.time())}_{uuid.uuid4().hex[:6]}"
        token = set_request_id(request_id)
        request.state.request_id = request_id
        client_ip = request.client.host if request.client else ""
        suppress_poll_info = SUPPRESS_PROGRESS_POLL and _is_progress_poll_request(request.method, request.url.path)
        if not suppress_poll_info:
            logger.info(
                "request started",
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
            mark_request_finish(request.url.path, getattr(response, "status_code", 200), duration_ms)
            response.headers["X-Request-Id"] = request_id
            if duration_ms >= 800:
                logger.warning(
                    "request slow",
                    extra=build_log_context(
                        event="request_slow",
                        request_id=request_id,
                        method=request.method,
                        path=request.url.path,
                        status_code=getattr(response, "status_code", 200),
                        duration_ms=duration_ms,
                        client_ip=client_ip,
                        module="app",
                    ),
                )
            if not suppress_poll_info:
                logger.info(
                    "request finished",
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
            if request.url.path.startswith("/api/v1/"):
                v1_api_logger.info(
                    "v1 api request finished",
                    extra=build_v1_log_context(
                        category="api",
                        event="request_finished",
                        request_id=request_id,
                        method=request.method,
                        path=request.url.path,
                        status_code=getattr(response, "status_code", 200),
                        duration_ms=duration_ms,
                    ),
                )
            return response
        except Exception as exc:
            duration_ms = int((time.perf_counter() - started_at) * 1000)
            mark_request_finish(request.url.path, 500, duration_ms)
            logger.exception(
                "request failed",
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

    app.include_router(health_v1.router)
    app.include_router(works_v1.router)
    app.include_router(chapters_v1.router)
    app.include_router(sessions_v1.router)
    app.include_router(io_v1.router)
    app.include_router(outlines_v1.router)
    app.include_router(timeline_v1.router)
    app.include_router(foreshadows_v1.router)
    app.include_router(characters_v1.router)
    app.include_router(ai_settings_v2.router)
    app.include_router(ai_jobs_v2.router)
    app.include_router(ai_initialization_v2.router)
    app.include_router(ai_context_pack_v2.router)
    app.include_router(ai_continuation_v2.router)
    logger.info("routers registered", extra=build_log_context(event="app_router_registered", module="app", version=APP_VERSION))

    @app.exception_handler(FastAPIHTTPException)
    async def http_exception_handler(request: Request, exc: FastAPIHTTPException):
        request_id = getattr(request.state, "request_id", "")
        logger.warning(
            "http exception",
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

    @app.exception_handler(V1APIError)
    async def v1_api_exception_handler(request: Request, exc: V1APIError):
        request_id = getattr(request.state, "request_id", "")
        logger.warning(
            f"v1 api error error_code={exc.error_code}",
            extra=build_v1_log_context(
                category="error",
                event="exception",
                request_id=request_id,
                path=request.url.path,
                error_code=exc.error_code,
                status_code=exc.status_code,
            ),
        )
        response = JSONResponse(status_code=exc.status_code, content=exc.payload)
        if request_id:
            response.headers["X-Request-Id"] = request_id
        return response

    @app.exception_handler(RequestValidationError)
    async def request_validation_exception_handler(request: Request, exc: RequestValidationError):
        request_id = getattr(request.state, "request_id", "")
        if str(request.url.path).startswith("/api/v1/"):
            v1_api_logger.warning(
                "v1 request validation failed",
                extra=build_v1_log_context(
                    category="error",
                    event="validation_error",
                    request_id=request_id,
                    path=request.url.path,
                    error_code="invalid_input",
                    status_code=400,
                ),
            )
            response = JSONResponse(status_code=400, content=build_error_response("invalid_input"))
            if request_id:
                response.headers["X-Request-Id"] = request_id
            return response
        return await fastapi_request_validation_exception_handler(request, exc)

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        request_id = getattr(request.state, "request_id", "")
        logger.error(
            "unhandled exception",
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

    @app.get("/metrics/runtime")
    async def runtime_metrics():
        return {
            "runtime": get_runtime_metrics_snapshot(),
            "sqlite": get_sqlite_metrics_snapshot(),
        }

    logger.info("app started", extra=build_log_context(event="app_started", module="app", version=APP_VERSION))
    return app


app = create_app()
