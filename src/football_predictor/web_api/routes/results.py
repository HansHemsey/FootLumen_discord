"""Read-only recent result routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from football_predictor.web_api.dependencies import get_read_only_session
from football_predictor.web_api.schemas.common import PaginationMeta
from football_predictor.web_api.schemas.results import RecentResultsResponse
from football_predictor.web_api.security import require_api_access
from football_predictor.web_api.services.result_read_service import ResultReadService

router = APIRouter(prefix="/results", dependencies=[Depends(require_api_access)])


@router.get("/recent", response_model=RecentResultsResponse)
def recent_results(
    competition_key: str | None = None,
    days: int = Query(default=7, ge=1, le=30),
    limit: int = Query(default=50, ge=1, le=100),
    session: Session = Depends(get_read_only_session),
) -> RecentResultsResponse:
    items = ResultReadService(session).list_recent(
        competition_key=competition_key,
        days=days,
        limit=limit,
    )
    return RecentResultsResponse(
        items=items,
        meta=PaginationMeta(limit=limit, total=len(items), has_more=False),
    )
