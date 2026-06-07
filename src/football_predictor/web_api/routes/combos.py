"""Read-only World Cup combo routes."""

from __future__ import annotations

from datetime import date, datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from football_predictor.config.settings import Settings
from football_predictor.web_api.dependencies import get_api_settings, get_read_only_session
from football_predictor.web_api.schemas.combos import ComboTicketDTO, ComboTicketListResponse
from football_predictor.web_api.schemas.common import PaginationMeta
from football_predictor.web_api.security import require_api_access
from football_predictor.web_api.services.combo_read_service import ComboReadService

router = APIRouter(
    prefix="/combos",
    tags=["combos"],
    dependencies=[Depends(require_api_access)],
)


@router.get("/today", response_model=ComboTicketListResponse, summary="List today combos")
def combos_today(
    date_: date | None = Query(default=None, alias="date"),
    competition_key: str | None = "fifa_world_cup_2026",
    include_staff: bool = False,
    limit: int = Query(default=10, ge=1, le=50),
    settings: Settings = Depends(get_api_settings),
    session: Session = Depends(get_read_only_session),
) -> ComboTicketListResponse:
    try:
        timezone = ZoneInfo(settings.app_timezone)
    except ZoneInfoNotFoundError:
        timezone = ZoneInfo("Europe/Paris")
    target_date = date_ or datetime.now(timezone).date()
    items = ComboReadService(session).list_for_date(
        target_date,
        competition_key=competition_key,
        include_staff=include_staff,
        limit=limit,
    )
    return ComboTicketListResponse(
        items=items,
        meta=PaginationMeta(limit=limit, total=len(items), has_more=False),
    )


@router.get("/latest", response_model=ComboTicketListResponse, summary="List latest combos")
def latest_combos(
    competition_key: str | None = None,
    include_staff: bool = False,
    limit: int = Query(default=10, ge=1, le=50),
    session: Session = Depends(get_read_only_session),
) -> ComboTicketListResponse:
    items = ComboReadService(session).list_latest(
        competition_key=competition_key,
        include_staff=include_staff,
        limit=limit,
    )
    return ComboTicketListResponse(
        items=items,
        meta=PaginationMeta(limit=limit, total=len(items), has_more=False),
    )


@router.get("/{ticket_key}", response_model=ComboTicketDTO, summary="Get combo ticket")
def combo_detail(
    ticket_key: str,
    include_staff: bool = True,
    session: Session = Depends(get_read_only_session),
) -> ComboTicketDTO:
    ticket = ComboReadService(session).get_ticket(ticket_key, include_staff=include_staff)
    if ticket is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "combo_not_found", "message": "Combo ticket not found."},
        )
    return ticket
