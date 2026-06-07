"""Read-only World Cup combo queries for the API."""

from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from football_predictor.db import models
from football_predictor.web_api.schemas.combos import ComboTicketDTO, combo_ticket_from_model

_PUBLIC_TICKET_STATUSES = {"LOCKED", "PUBLIC_PUBLISHED", "SETTLED"}
_PUBLIC_DECISIONS = {"PUBLIC", "PUBLIC_PUBLISHED"}
_STAFF_ONLY_STATUSES = {"DRAFT", "WATCHLIST_STAFF", "PRE_LOCK_REVALIDATION", "STAFF_ONLY"}


class ComboReadService:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_ticket(self, ticket_key: str, *, include_staff: bool = True) -> ComboTicketDTO | None:
        ticket = self._session.scalar(
            select(models.ComboTicket)
            .where(models.ComboTicket.ticket_key == ticket_key)
            .limit(1)
        )
        if ticket is None or (not include_staff and not _is_public_visible(ticket)):
            return None
        return combo_ticket_from_model(ticket, self._legs_for_ticket(ticket.id))

    def list_for_date(
        self,
        combo_date: date,
        *,
        competition_key: str | None = None,
        include_staff: bool = False,
        limit: int = 10,
    ) -> list[ComboTicketDTO]:
        stmt = (
            select(models.ComboTicket)
            .where(models.ComboTicket.combo_date == combo_date)
            .order_by(models.ComboTicket.first_kickoff_at.asc(), models.ComboTicket.id.asc())
            .limit(min(limit * 3, 150))
        )
        if competition_key:
            stmt = stmt.where(models.ComboTicket.competition_key == competition_key)
        return self._tickets_from_query(stmt, include_staff=include_staff, limit=min(limit, 50))

    def list_latest(
        self,
        *,
        competition_key: str | None = None,
        include_staff: bool = False,
        limit: int = 10,
    ) -> list[ComboTicketDTO]:
        stmt = (
            select(models.ComboTicket)
            .order_by(
                models.ComboTicket.combo_date.desc(),
                models.ComboTicket.created_at.desc(),
                models.ComboTicket.id.desc(),
            )
            .limit(min(limit * 3, 150))
        )
        if competition_key:
            stmt = stmt.where(models.ComboTicket.competition_key == competition_key)
        return self._tickets_from_query(stmt, include_staff=include_staff, limit=min(limit, 50))

    def _tickets_from_query(
        self,
        stmt,
        *,
        include_staff: bool,
        limit: int,
    ) -> list[ComboTicketDTO]:
        items: list[ComboTicketDTO] = []
        for ticket in self._session.scalars(stmt).all():
            if not include_staff and not _is_public_visible(ticket):
                continue
            items.append(combo_ticket_from_model(ticket, self._legs_for_ticket(ticket.id)))
            if len(items) >= limit:
                break
        return items

    def _legs_for_ticket(self, ticket_id: int) -> list[models.ComboTicketLeg]:
        return list(
            self._session.scalars(
                select(models.ComboTicketLeg)
                .where(models.ComboTicketLeg.ticket_id == ticket_id)
                .order_by(models.ComboTicketLeg.leg_order.asc())
            ).all()
        )


def _is_public_visible(ticket: models.ComboTicket) -> bool:
    status = (ticket.status or "").upper()
    decision = (ticket.publication_decision or "").upper()
    if status in _STAFF_ONLY_STATUSES:
        return False
    if status == "NO_BET":
        return False
    return status in _PUBLIC_TICKET_STATUSES or decision in _PUBLIC_DECISIONS
