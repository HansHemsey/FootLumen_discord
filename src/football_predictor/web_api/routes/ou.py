"""Read-only O/U prediction routes."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from football_predictor.config.settings import Settings
from football_predictor.web_api.dependencies import get_api_settings, get_read_only_session
from football_predictor.web_api.schemas.common import PaginationMeta
from football_predictor.web_api.schemas.ou import OUPredictionDTO, OUPredictionListResponse
from football_predictor.web_api.security import require_api_access
from football_predictor.web_api.services.ou_read_service import OUReadService

router = APIRouter(prefix="/ou", dependencies=[Depends(require_api_access)])


@router.get("/latest", response_model=OUPredictionListResponse)
def latest_ou_predictions(
    competition_key: str | None = None,
    date_: date | None = Query(default=None, alias="date"),
    limit: int = Query(default=20, ge=1, le=100),
    only_value_picks: bool = False,
    include_no_bet: bool = True,
    settings: Settings = Depends(get_api_settings),
    session: Session = Depends(get_read_only_session),
) -> OUPredictionListResponse:
    items = OUReadService(session).list_latest(
        competition_key=competition_key,
        target_date=date_,
        timezone_name=settings.app_timezone,
        limit=limit,
        only_value_picks=only_value_picks,
        include_no_bet=include_no_bet,
    )
    return OUPredictionListResponse(
        items=items,
        meta=PaginationMeta(limit=limit, total=len(items), has_more=False),
    )


@router.get("/{fixture_id}", response_model=OUPredictionDTO)
def ou_prediction_detail(
    fixture_id: int,
    session: Session = Depends(get_read_only_session),
) -> OUPredictionDTO:
    prediction = OUReadService(session).get_latest_for_fixture(fixture_id)
    if prediction is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "ou_prediction_not_found", "message": "O/U prediction not found."},
        )
    return prediction
