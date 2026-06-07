"""Health and version routes for the read-only API."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from football_predictor import __version__
from football_predictor.config.settings import Settings
from football_predictor.utils.time import utc_now
from football_predictor.web_api.dependencies import get_api_settings, get_read_only_session
from football_predictor.web_api.schemas.common import HealthResponse, VersionResponse
from football_predictor.web_api.security import require_api_access

router = APIRouter(dependencies=[Depends(require_api_access)])


@router.get("/health", response_model=HealthResponse)
def health(
    settings: Settings = Depends(get_api_settings),
    session: Session = Depends(get_read_only_session),
) -> HealthResponse:
    database_ok = _database_ok(session)
    status = "ok" if database_ok else "degraded"
    return HealthResponse(
        status=status,
        api_enabled=settings.footlumen_api_enabled,
        read_only=settings.footlumen_api_read_only,
        database_ok=database_ok,
        app_timezone=settings.app_timezone,
        version=__version__,
        timestamp=utc_now(),
    )


@router.get("/version", response_model=VersionResponse)
def version(settings: Settings = Depends(get_api_settings)) -> VersionResponse:
    return VersionResponse(
        name="FootLumen API",
        version=__version__,
        api_version="v1",
        read_only=settings.footlumen_api_read_only,
    )


def _database_ok(session: Session) -> bool:
    try:
        session.execute(text("select 1")).scalar_one()
    except Exception:
        return False
    return True
