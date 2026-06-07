"""Read-only World Cup combo queries for the API."""

from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from football_predictor.db import models
from football_predictor.web_api.schemas.combos import ComboTicketDTO, combo_ticket_from_model


class ComboReadService:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_ticket(self, ticket_key: str) -> ComboTicketDTO | None:
        ticket = self._session.scalar(
            select(models.ComboTicket)
            .where(models.ComboTicket.ticket_key == ticket_key)
            .limit(1)
        )
        if ticket is None:
            return None
        return combo_ticket_from_model(ticket, self._legs_for_ticket(ticket.id))

    def list_for_date(self, combo_date: date, *, limit: int = 25) -> list[ComboTicketDTO]:
        tickets = self._session.scalars(
            select(models.ComboTicket)
            .where(models.ComboTicket.combo_date == combo_date)
            .order_by(models.ComboTicket.first_kickoff_at.asc(), models.ComboTicket.id.asc())
            .limit(min(limit, 100))
        ).all()
        return [
            combo_ticket_from_model(ticket, self._legs_for_ticket(ticket.id))
            for ticket in tickets
        ]

    def _legs_for_ticket(self, ticket_id: int) -> list[models.ComboTicketLeg]:
        return list(
            self._session.scalars(
                select(models.ComboTicketLeg)
                .where(models.ComboTicketLeg.ticket_id == ticket_id)
                .order_by(models.ComboTicketLeg.leg_order.asc())
            ).all()
        )
