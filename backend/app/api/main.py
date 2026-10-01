"""CrisisMesh FastAPI Application: Security Middlewares, Structured Errors & Root Contract."""
from __future__ import annotations
import os
import time
from typing import Any, Dict
from fastapi import FastAPI, Request, Response, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from backend.app.api.schemas import HealthResponse
from backend.app.api.routes_auth import router as auth_router
from backend.app.api.routes_operations import router as ops_router
from backend.app.api.routes_plan import router as plan_router
from backend.app.api.routes_audit import router as audit_router
from backend.app.api.routes_scenario import router as scenario_router
from backend.app.api.routes_attacks import router as attacks_router
from backend.app.api.routes_ws import router as ws_router
from backend.app.api.routes_analysis import router as analysis_router
from backend.app.security.secrets import secrets_config
from pathlib import Path
from backend.app.audit.chain import AuditChain

START_TIME = time.time()
MAX_REQUEST_BYTES = 1024 * 1024  # 1 MB maximum request payload size
FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "http://localhost:3000")


# -------------------------------------------------------------------------
# Security Middlewares
# -------------------------------------------------------------------------
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Applies defense-in-depth HTTP security headers to all responses."""

    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        # Allow Swagger UI and ReDoc CDNs on documentation routes; allow Cloudflare tunnels & self for all API routes
        if request.url.path in ("/docs", "/redoc", "/openapi.json"):
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
                "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
                "img-src 'self' data: https://fastapi.tiangolo.com; "
                "connect-src 'self'"
            )
        else:
            response.headers["Content-Security-Policy"] = (
                "default-src 'self' https://*.trycloudflare.com; "
                "connect-src 'self' https://*.trycloudflare.com wss://*.trycloudflare.com ws://localhost:* http://localhost:* ws://127.0.0.1:* http://127.0.0.1:*; "
                "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: blob:;"
            )
        return response


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """Enforces strict body size limits to prevent buffer overflow and memory DoS."""

    async def dispatch(self, request: Request, call_next):
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                if int(content_length) > MAX_REQUEST_BYTES:
                    return JSONResponse(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        content={
                            "error": {
                                "code": "PAYLOAD_TOO_LARGE",
                                "message": f"Request body exceeds 1MB size limit ({content_length} bytes)",
                                "details": None,
                            }
                        },
                    )
            except ValueError:
                pass
        return await call_next(request)


# -------------------------------------------------------------------------
# FastAPI App Factory
# -------------------------------------------------------------------------
def create_app() -> FastAPI:
    app = FastAPI(
        title="CrisisMesh Emergency Response API",
        version="1.0.0",
        description="Gateways 2026 Domain 4: Crisis Command - Multi-Agent Coordination Control Room API",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # 1. CORS Middleware (Restricted to frontend origin + Cloudflare quick tunnels)
    allowed_origins = [FRONTEND_ORIGIN, "http://localhost:3000", "http://127.0.0.1:3000"]
    extra_origins = os.getenv("CRISISMESH_ALLOWED_ORIGINS", "")
    if extra_origins:
        for o in extra_origins.split(","):
            if o.strip() and o.strip() not in allowed_origins:
                allowed_origins.append(o.strip())

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_origin_regex=r"https://.*\.trycloudflare\.com|https://.*\.loca\.lt|http://localhost:\d+|http://127\.0\.0\.1:\d+",
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )

    # 2. Security Headers & Request Limiters
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RequestSizeLimitMiddleware)

    # 3. Structured Error Handling
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": f"HTTP_{exc.status_code}",
                    "message": str(exc.detail),
                    "details": None,
                }
            },
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Schema validation failed for request payload.",
                    "details": exc.errors(),
                }
            },
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": {
                    "code": "INTERNAL_SERVER_ERROR",
                    "message": str(exc),
                    "details": None,
                }
            },
        )

    # 4. Health Check Endpoint
    @app.get("/health", response_model=HealthResponse, tags=["Health"])
    def health_check():
        return HealthResponse(
            status="healthy",
            version="1.0.0",
            mode=secrets_config.mode,
            uptime_seconds=time.time() - START_TIME,
            timestamp=time.time(),
        )

    # 5. Mount Sub-Routers
    app.include_router(auth_router)
    app.include_router(ops_router)
    app.include_router(plan_router)
    app.include_router(audit_router)
    app.include_router(scenario_router)
    app.include_router(attacks_router)
    app.include_router(ws_router)
    app.include_router(analysis_router)

    # 6. Startup Security Warning Banner
    @app.on_event("startup")
    async def startup_event():
        from backend.app.api.auth import is_demo_mode
        if is_demo_mode():
            banner = [
                "!" * 78,
                "! [SECURITY ALERT] CRISISMESH_DEMO_MODE IS EXPLICITLY ENABLED                 !",
                "! Demo authentication bypass and /auth/demo-login endpoints are ACTIVE.     !",
                "! Hardcoded demo roles (viewer, operator, commander) are AVAILABLE.         !",
                "! DO NOT DEPLOY IN PRODUCTION WITH CRISISMESH_DEMO_MODE=true                !",
                "!" * 78,
            ]
            print("\n" + "\n".join(banner) + "\n", flush=True)
        else:
            print("[CrisisMesh Security] Production mode: CRISISMESH_DEMO_MODE is FALSE. Demo accounts are disabled.", flush=True)

        app.state.audit_chain.append("SYSTEM_STARTUP", "SYSTEM", {"mode": secrets_config.mode, "demo": is_demo_mode()})


    # Set up persistent AuditChain
    AUDIT_LOG_DIR = Path(__file__).resolve().parent.parent.parent.parent / 'data' / 'audit'
    app.state.audit_chain = AuditChain(log_path=AUDIT_LOG_DIR / 'audit.jsonl')

    return app


app = create_app()
