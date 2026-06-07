"""Competition read-only routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from football_predictor.web_api.dependencies import get_read_only_session
from football_predictor.web_api.schemas.common import CompetitionSummary
from football_predictor.web_api.security import require_api_access
from football_predictor.web_api.services.fixture_read_service import FixtureReadService

router = APIRouter(prefix="/competitions", dependencies=[Depends(require_api_access)])


@router.get("", response_model=list[CompetitionSummary])
def list_competitions(
    session: Session = Depends(get_read_only_session),
) -> list[CompetitionSummary]:
    return FixtureReadService(session).list_competitions()


@router.get("/{competition_key}", response_model=CompetitionSummary)
def get_competition(
    competition_key: str,
    session: Session = Depends(get_read_only_session),
) -> CompetitionSummary:
    competition = FixtureReadService(session).get_competition(competition_key)
    if competition is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "competition_not_found", "message": "Competition not found."},
        )
    return competition
