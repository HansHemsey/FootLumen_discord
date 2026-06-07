"""FastAPI application for the read-only FootLumen API."""

from __future__ import annotations

from collections.abc import Callable

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from football_predictor import __version__
from football_predictor.config.settings import get_settings
from football_predictor.web_api.errors import install_error_handlers
from football_predictor.web_api.routes.health import router as health_router


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="FootLumen API",
        version=__version__,
        docs_url="/docs" if settings.footlumen_api_enabled else None,
        redoc_url="/redoc" if settings.footlumen_api_enabled else None,
        openapi_url="/openapi.json" if settings.footlumen_api_enabled else None,
    )
    _install_security_headers(app)
    _install_cors(app, settings.footlumen_api_cors_origins)
    install_error_handlers(app)
    app.include_router(health_router, prefix="/api/v1")
    return app


def _install_cors(app: FastAPI, origins_csv: str) -> None:
    origins = [origin.strip() for origin in origins_csv.split(",") if origin.strip()]
    if not origins:
        return
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=False,
        allow_methods=["GET"],
        allow_headers=["Authorization", "X-FootLumen-Api-Key"],
    )


def _install_security_headers(app: FastAPI) -> None:
    @app.middleware("http")
    async def _security_headers(request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        return response


app = create_app()
