"""Insurio API application factory."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import auth, health
from app.core.config import DEFAULT_SECRET, get_settings
from app.core.errors import register_exception_handlers
from app.core.logging import configure_logging
from app.core.middleware import RequestContextMiddleware


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.LOG_LEVEL)

    if settings.is_production and settings.SECRET_KEY == DEFAULT_SECRET:
        raise RuntimeError("SECRET_KEY must be set to a unique value in production.")

    Path(settings.UPLOAD_DIR).mkdir(parents=True, exist_ok=True)

    app = FastAPI(
        title="Insurio API",
        version=settings.APP_VERSION,
        description=(
            "Evidence-grounded insurance policy intelligence. Answers are produced only "
            "from retrieved pages of documents owned by the authenticated user."
        ),
        docs_url=None if settings.is_production else "/docs",
        redoc_url=None if settings.is_production else "/redoc",
        openapi_url=None if settings.is_production else "/openapi.json",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
        expose_headers=["X-Request-ID"],
    )
    app.add_middleware(RequestContextMiddleware)

    register_exception_handlers(app)

    app.include_router(health.router)
    app.include_router(auth.router, prefix=settings.API_V1_PREFIX)

    @app.get("/", include_in_schema=False)
    def root() -> dict[str, str]:
        return {"name": "Insurio API", "version": settings.APP_VERSION, "docs": "/docs"}

    return app


app = create_app()
