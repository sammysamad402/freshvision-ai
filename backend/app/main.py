"""
FreshVision AI — FastAPI application entry point (production hardened).
"""
import os
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.core.config import CORS_ORIGINS, ENVIRONMENT, JWT_SECRET
from app.core.limiter import limiter
from app.core.logging_setup import setup_logging
from app.core.security import SecurityHeadersMiddleware, RequestIDMiddleware
from app.db.database import init_db
from app.routes import auth, inspection, analytics

# ── Logging ─────────────────────────────────────────────────────────────────
setup_logging(os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger("freshvision.main")

# ── Fail fast on unsafe production config ───────────────────────────────────
if ENVIRONMENT == "production" and JWT_SECRET == "CHANGE-ME-IN-PRODUCTION":
    raise RuntimeError(
        "FRESHVISION_JWT_SECRET is still the default placeholder. "
        "Set a real random secret before running with ENVIRONMENT=production "
        "(generate one with: python3 -c \"import secrets; print(secrets.token_hex(32))\")."
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    logger.info("FreshVision AI started — database ready")
    # Warm up the YOLO model so first real request isn't slow
    try:
        from app.services.detection import _get_model
        m = _get_model()
        logger.info("Inference model warmed up: %s", "OK" if m else "fallback mode")
    except Exception as exc:
        logger.warning("Model warm-up skipped: %s", exc)
    yield
    logger.info("FreshVision AI shutting down")


app = FastAPI(
    title="FreshVision AI",
    description=(
        "Automated quality inspection & freshness prediction for fresh produce. "
        "Pipeline: YOLOv8 (CPU, Intel-optimised) → OpenCV defect analysis → "
        "quality grading → freshness + shelf-life prediction → decision engine."
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# ── Middleware (order matters — outermost added last) ────────────────────────
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestIDMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
    expose_headers=["X-Request-ID"],
)

# ── Global exception handler ─────────────────────────────────────────────────
@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled error  path=%s  error=%s", request.url.path, exc, exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An internal error occurred. Please try again."},
    )

# ── Routers ──────────────────────────────────────────────────────────────────
app.include_router(auth.router)
app.include_router(inspection.router)
app.include_router(analytics.router)


@app.get("/health", tags=["system"])
async def health():
    return {"status": "ok", "service": "FreshVision AI", "version": "1.0.0"}
