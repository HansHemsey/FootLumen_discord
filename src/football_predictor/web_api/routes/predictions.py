"""Read-only 1X2 prediction routes."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from football_predictor.config.settings import Settings
from football_predictor.web_api.dependencies import get_api_settings, get_read_only_session
from football_predictor.web_api.schemas.common import PaginationMeta
from football_predictor.web_api.schemas.predictions import (
    Prediction1X2DTO,
    Prediction1X2ListResponse,
)
from football_predictor.web_api.security import require_api_access
from football_predictor.web_api.services.prediction_read_service import PredictionReadService

router = APIRouter(
    prefix="/predictions",
    tags=["predictions"],
    dependencies=[Depends(require_api_access)],
)


@router.get(
    "/latest",
    response_model=Prediction1X2ListResponse,
    summary="List latest 1X2 predictions",
)
def latest_predictions(
    competition_key: str | None = None,
    date_: date | None = Query(default=None, alias="date"),
    limit: int = Query(default=20, ge=1, le=100),
    only_public: bool = False,
    include_no_bet: bool = True,
    settings: Settings = Depends(get_api_settings),
    session: Session = Depends(get_read_only_session),
) -> Prediction1X2ListResponse:
    items = PredictionReadService(session).list_latest(
        competition_key=competition_key,
        target_date=date_,
        timezone_name=settings.app_timezone,
        limit=limit,
        only_public=only_public,
        include_no_bet=include_no_bet,
    )
    return Prediction1X2ListResponse(
        items=items,
        meta=PaginationMeta(limit=limit, total=len(items), has_more=False),
    )


@router.get(
    "/{fixture_id}",
    response_model=Prediction1X2DTO,
    summary="Get latest 1X2 prediction for fixture",
)
def prediction_detail(
    fixture_id: int,
    session: Session = Depends(get_read_only_session),
) -> Prediction1X2DTO:
    prediction = PredictionReadService(session).get_latest_for_fixture(fixture_id)
    if prediction is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "prediction_not_found", "message": "Prediction not found."},
        )
    return prediction
