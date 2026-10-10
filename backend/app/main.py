"""SentinelWeb AI — Main FastAPI application."""

from __future__ import annotations

import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.core.database import init_db
from app.core.logging import get_logger, setup_logging

from app.api.v1.auth import router as auth_router
from app.api.v1.engagements import router as engagements_router
from app.api.v1.findings import router as findings_router
from app.api.v1.scans import router as scans_router
from app.api.v1.system import router as system_router
from app.api.v1.reports import router as reports_router
from app.api.v1.blueteam import router as blueteam_router
from app.api.v1.har import router as har_router


settings = get_settings()
setup_logging(settings.log_level, settings.log_format)
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown."""
    logger.info("application_starting", app=settings.app_name, env=settings.app_env)

    # Initialize database tables
    await init_db()
    logger.info("database_initialized")

    # Detect available tools
    from app.core.execution import get_execution_broker
    broker = get_execution_broker()
    inventory = await broker.detect_tools()
    available = sum(1 for t in inventory.values() if t["available"])
    logger.info("tools_detected", available=available, total=len(inventory))

    # Check AI provider
    from app.ai.providers import get_ai_manager
    ai_manager = get_ai_manager()
    ai_healthy, ai_name = await ai_manager.health_check()
    logger.info("ai_provider_status", provider=ai_name, available=ai_healthy)

    logger.info("application_ready")
    yield
    logger.info("application_shutting_down")


app = FastAPI(
    title="SentinelWeb AI",
    description="AI-Powered Red Team, Blue Team & Vulnerability Research Platform",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.app_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request logging middleware
@app.middleware("http")
async def request_logging(request: Request, call_next):
    start = time.monotonic()
    response: Response = await call_next(request)
    duration = time.monotonic() - start
    logger.info(
        "http_request",
        method=request.method,
        path=request.url.path,
        status=response.status_code,
        duration_ms=round(duration * 1000, 1),
    )
    return response


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(
        "unhandled_exception",
        method=request.method,
        path=request.url.path,
        error=f"{type(exc).__name__}: {str(exc)[:200]}",
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


# Mount API routes
PREFIX = "/api/v1"
app.include_router(auth_router, prefix=PREFIX)
app.include_router(engagements_router, prefix=PREFIX)
app.include_router(findings_router, prefix=PREFIX)
app.include_router(scans_router, prefix=PREFIX)
app.include_router(system_router, prefix=PREFIX)
app.include_router(reports_router, prefix=PREFIX)
app.include_router(blueteam_router, prefix=PREFIX)
app.include_router(har_router, prefix=PREFIX)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "SentinelWeb AI",
        "version": "0.1.0",
        "description": "AI-Powered Security Assessment Platform",
        "docs": "/api/docs",
    }
