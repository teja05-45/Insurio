"""Liveness and readiness endpoints."""

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.core.config import get_settings
from app.db.session import engine

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/live")
def live() -> dict[str, str]:
    return {"status": "ok", "version": get_settings().APP_VERSION}


@router.get("/ready")
def ready() -> JSONResponse:
    settings = get_settings()
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except Exception:
        return JSONResponse(
            status_code=503,
            content={
                "status": "unavailable",
                "database": "disconnected",
                "version": settings.APP_VERSION,
            },
        )
    return JSONResponse(
        status_code=200,
        content={
            "status": "ok",
            "database": "connected",
            "version": settings.APP_VERSION,
        },
    )
