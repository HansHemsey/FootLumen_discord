"""Read-only performance routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from football_predictor.web_api.dependencies import get_read_only_session
from football_predictor.web_api.schemas.performance import PerformanceSummaryDTO
from football_predictor.web_api.security import require_api_access
from football_predictor.web_api.services.performance_read_service import PerformanceReadService

router = APIRouter(prefix="/performance", dependencies=[Depends(require_api_access)])


@router.get("/summary", response_model=PerformanceSummaryDTO)
def performance_summary(
    competition_key: str | None = None,
    days: int = Query(default=30, ge=1, le=365),
    session: Session = Depends(get_read_only_session),
) -> PerformanceSummaryDTO:
    return PerformanceReadService(session).summary(
        competition_key=competition_key,
        days=days,
    )
