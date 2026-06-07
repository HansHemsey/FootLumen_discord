"""Error handlers for the read-only FootLumen API."""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(Exception)
    async def _internal_error(_request: Request, _exc: Exception) -> JSONResponse:
        return JSONResponse(
            status_code=500,
            content={
                "detail": {
                    "code": "internal_error",
                    "message": "Internal server error.",
                }
            },
        )
