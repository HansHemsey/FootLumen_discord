"""Fixture read-only routes."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from football_predictor.config.settings import Settings
from football_predictor.web_api.dependencies import get_api_settings, get_read_only_session
from football_predictor.web_api.schemas.fixtures import FixtureSummaryDTO
from football_predictor.web_api.security import require_api_access
from football_predictor.web_api.services.fixture_read_service import FixtureReadService

router = APIRouter(
    prefix="/fixtures",
    tags=["fixtures"],
    dependencies=[Depends(require_api_access)],
)


@router.get("/today", response_model=list[FixtureSummaryDTO], summary="List today fixtures")
def fixtures_today(
    date_: date | None = Query(default=None, alias="date"),
    competition_key: str | None = None,
    settings: Settings = Depends(get_api_settings),
    session: Session = Depends(get_read_only_session),
) -> list[FixtureSummaryDTO]:
    return FixtureReadService(session).fixtures_today(
        target_date=date_,
        competition_key=competition_key,
        timezone_name=settings.app_timezone,
    )


@router.get(
    "/upcoming",
    response_model=list[FixtureSummaryDTO],
    summary="List upcoming fixtures",
)
def fixtures_upcoming(
    days: int = Query(default=7, ge=1, le=30),
    competition_key: str | None = None,
    status: str | None = None,
    limit: int = Query(default=100, ge=1, le=100),
    settings: Settings = Depends(get_api_settings),
    session: Session = Depends(get_read_only_session),
) -> list[FixtureSummaryDTO]:
    return FixtureReadService(session).fixtures_upcoming(
        days=days,
        competition_key=competition_key,
        status=status,
        limit=limit,
        timezone_name=settings.app_timezone,
    )


@router.get("/{fixture_id}", response_model=FixtureSummaryDTO, summary="Get a fixture")
def get_fixture(
    fixture_id: int,
    session: Session = Depends(get_read_only_session),
) -> FixtureSummaryDTO:
    fixture = FixtureReadService(session).get_fixture(fixture_id)
    if fixture is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "fixture_not_found", "message": "Fixture not found."},
        )
    return fixture
