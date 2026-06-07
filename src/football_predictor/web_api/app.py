"""FastAPI application for the read-only FootLumen API."""

from __future__ import annotations

import logging
from collections.abc import Callable
from time import perf_counter

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from football_predictor import __version__
from football_predictor.config.settings import get_settings
from football_predictor.web_api.errors import install_error_handlers
from football_predictor.web_api.routes.combos import router as combos_router
from football_predictor.web_api.routes.competitions import router as competitions_router
from football_predictor.web_api.routes.fixtures import router as fixtures_router
from football_predictor.web_api.routes.health import router as health_router
from football_predictor.web_api.routes.ou import router as ou_router
from football_predictor.web_api.routes.performance import router as performance_router
from football_predictor.web_api.routes.predictions import router as predictions_router
from football_predictor.web_api.routes.results import router as results_router

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    settings = get_settings()
    docs_enabled = settings.footlumen_api_enabled and settings.footlumen_api_docs_enabled
    app = FastAPI(
        title="FootLumen API",
        version=__version__,
        docs_url="/docs" if docs_enabled else None,
        redoc_url="/redoc" if docs_enabled else None,
        openapi_url="/openapi.json" if docs_enabled else None,
        description="Read-only API V1 for FootLumen data already produced by jobs.",
    )
    _install_request_logging(app)
    _install_security_headers(app)
    _install_cors(app, settings.footlumen_api_cors_origins)
    install_error_handlers(app)
    app.include_router(health_router, prefix="/api/v1")
    app.include_router(competitions_router, prefix="/api/v1")
    app.include_router(fixtures_router, prefix="/api/v1")
    app.include_router(predictions_router, prefix="/api/v1")
    app.include_router(ou_router, prefix="/api/v1")
    app.include_router(combos_router, prefix="/api/v1")
    app.include_router(results_router, prefix="/api/v1")
    app.include_router(performance_router, prefix="/api/v1")
    return app


def _install_cors(app: FastAPI, origins_csv: str) -> None:
    origins = _parse_cors_origins(origins_csv)
    if not origins:
        return
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=False,
        allow_methods=["GET"],
        allow_headers=["Authorization", "X-FootLumen-Api-Key"],
    )


def _parse_cors_origins(origins_csv: str) -> list[str]:
    origins: list[str] = []
    for raw_origin in origins_csv.split(","):
        origin = raw_origin.strip().rstrip("/")
        if not origin or origin == "*":
            continue
        if origin.startswith(("https://", "http://localhost", "http://127.0.0.1")):
            origins.append(origin)
    return origins


def _install_request_logging(app: FastAPI) -> None:
    @app.middleware("http")
    async def _request_logging(request: Request, call_next: Callable) -> Response:
        started_at = perf_counter()
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        except Exception:
            logger.exception(
                "web_api.request_failed",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "client_ip": _client_ip(request),
                },
            )
            raise
        finally:
            duration_ms = round((perf_counter() - started_at) * 1000, 2)
            logger.info(
                "web_api.request",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "status": status_code,
                    "duration_ms": duration_ms,
                    "client_ip": _client_ip(request),
                },
            )


def _install_security_headers(app: FastAPI) -> None:
    @app.middleware("http")
    async def _security_headers(request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault(
            "Permissions-Policy",
            "camera=(), microphone=(), geolocation=()",
        )
        return response


def _client_ip(request: Request) -> str | None:
    return request.client.host if request.client is not None else None


app = create_app()
