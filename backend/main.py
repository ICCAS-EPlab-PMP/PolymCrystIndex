"""PolymCrystIndex FastAPI Backend Application.

Profile-driven: APP_PROFILE=local skips auth routes and docs are enabled;
APP_PROFILE=cloud enables full auth and hardens error output.
"""
import logging
import os
import sys
import time
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent))

_entry_profile = (os.getenv("APP_PROFILE") or os.getenv("PROFILE") or "").strip()
if _entry_profile:
    os.environ["APP_PROFILE"] = _entry_profile
    os.environ["PROFILE"] = _entry_profile

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import RequestValidationError

from core.config import settings, ensure_directories
from core.dependencies import get_user_service
from services.fortran_runtime import ensure_fortran_binaries
from api import (
    auth_router,
    data_router,
    analysis_router,
    results_router,
    visualizer_router,
    status_router,
    update_router,
    peak_raw_router,
    peak_integrated_router,
    admin_users_router,
    admin_tasks_router,
    admin_dashboard_router,
    admin_system_router,
)

logger = logging.getLogger("polycryindex")

_docs_url = "/docs" if settings.ENABLE_DOCS else None
_redoc_url = "/redoc" if settings.ENABLE_DOCS else None

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="API for PolymCrystIndex fiber diffraction analysis system",
    docs_url=_docs_url,
    redoc_url=_redoc_url,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle request validation errors."""
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "success": False,
            "message": "Validation error",
            "errors": exc.errors()
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
    if settings.AUTH_DISABLED:
        detail = f"Internal server error: {str(exc)}"
    else:
        detail = "Internal server error"
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "message": detail
        }
    )


@app.on_event("startup")
async def startup_event():
    app.state.start_time = time.time()
    ensure_directories()

    if settings.APP_PROFILE == "cloud":
        if not settings.SECRET_KEY or settings.SECRET_KEY == "your-secret-key-change-in-production":
            raise RuntimeError(
                "SECRET_KEY is not configured for production. "
                "Set a strong SECRET_KEY via environment variable or .env file."
            )
        if not settings.DEFAULT_ADMIN_PASSWORD or settings.DEFAULT_ADMIN_PASSWORD == "admin123":
            raise RuntimeError(
                "DEFAULT_ADMIN_PASSWORD is not configured for production. "
                "Set a strong password via ADMIN_PASSWORD environment variable or .env file."
            )

    user_service = get_user_service()
    if settings.AUTH_DISABLED:
        await user_service.ensure_local_user_exists()
    else:
        await user_service.ensure_admin_exists()

    try:
        opt_path, post_path = ensure_fortran_binaries()
        logger.info("Fortran runtime ready: %s ; %s", opt_path, post_path)
    except Exception as exc:
        logger.warning("Fortran runtime unavailable: %s", exc)


app.include_router(data_router, prefix=settings.API_PREFIX)
app.include_router(analysis_router, prefix=settings.API_PREFIX)
app.include_router(results_router, prefix=settings.API_PREFIX)
app.include_router(visualizer_router, prefix=settings.API_PREFIX)
app.include_router(status_router, prefix=settings.API_PREFIX)
app.include_router(update_router, prefix=settings.API_PREFIX)
app.include_router(peak_raw_router, prefix=settings.API_PREFIX)
app.include_router(peak_integrated_router, prefix=settings.API_PREFIX)
if not settings.AUTH_DISABLED:
    app.include_router(auth_router, prefix=settings.API_PREFIX)
    app.include_router(admin_users_router, prefix=settings.API_PREFIX)
    app.include_router(admin_tasks_router, prefix=settings.API_PREFIX)
    app.include_router(admin_dashboard_router, prefix=settings.API_PREFIX)
    app.include_router(admin_system_router, prefix=settings.API_PREFIX)


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "profile": settings.APP_PROFILE,
        "frontendProfile": settings.APP_PROFILE,
        "app_env": settings.APP_ENV,
        "version": settings.VERSION,
        "auth_disabled": settings.AUTH_DISABLED,
    }


FRONTEND_DIST = Path(__file__).parent.parent / "frontend" / "dist"
_FRONTEND_ROOT = FRONTEND_DIST.resolve()


def _safe_resolve_frontend_path(full_path: str) -> Optional[Path]:
    try:
        resolved = (FRONTEND_DIST / full_path).resolve()
        resolved.relative_to(_FRONTEND_ROOT)
        if resolved.is_file():
            return resolved
        return None
    except (OSError, ValueError):
        return None


def _frontend_file_response(file_path: Path) -> FileResponse:
    response = FileResponse(file_path)
    if file_path.suffix.lower() == ".html":
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response

if FRONTEND_DIST.exists():
    app.mount("/assets", StaticFiles(directory=str(FRONTEND_DIST / "assets")), name="frontend-assets")

    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        safe_path = _safe_resolve_frontend_path(full_path)
        if safe_path is not None:
            return _frontend_file_response(safe_path)
        return _frontend_file_response(FRONTEND_DIST / "index.html")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=True,
        log_level=settings.LOG_LEVEL,
    )
