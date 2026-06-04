"""Settlement service for World Cup combo tickets."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from football_predictor.db import models as db_models
from football_predictor.world_cup_combos.enums import ComboMarketType, ComboTicketStatus
from football_predictor.world_cup_combos.models import ComboTicketSnapshot
from football_predictor.world_cup_combos.persistence import persist_combo_ticket_snapshot
from football_predictor.world_cup_combos.worldcup_combo_lock_service import (
    combo_ticket_candidate_from_payload,
)

FINISHED_STATUSES = {"FT", "AET", "PEN"}


@dataclass(frozen=True)
class ComboSettlementResult:
    ticket_key: str
    status: str
    leg_results: tuple[str, ...]
    profit_unit: float
    reason: str | None = None


class WorldCupComboSettlementService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def settle_record(
        self,
        record: db_models.ComboTicket,
        *,
        settled_at: datetime,
        execute: bool = False,
    ) -> ComboSettlementResult:
        if record.status == ComboTicketStatus.SETTLED.value:
            payload = record.payload_json if isinstance(record.payload_json, dict) else {}
            settlement = payload.get("settlement") if isinstance(payload, dict) else {}
            return ComboSettlementResult(
                ticket_key=record.ticket_key,
                status=str(settlement.get("status") or "SETTLED"),
                leg_results=tuple(settlement.get("leg_results") or ()),
                profit_unit=float(settlement.get("profit_unit") or 0.0),
                reason="already_settled",
            )

        ticket = combo_ticket_candidate_from_payload(record.payload_json)
        fixture_map = self._fixtures_for_ticket(ticket)
        if any(fixture is None for fixture in fixture_map.values()):
            return ComboSettlementResult(
                ticket_key=ticket.ticket_key,
                status="PENDING",
                leg_results=(),
                profit_unit=0.0,
                reason="missing_fixture",
            )
        if any(
            (fixture.status_short or "") not in FINISHED_STATUSES
            for fixture in fixture_map.values()
        ):
            return ComboSettlementResult(
                ticket_key=ticket.ticket_key,
                status="PENDING",
                leg_results=(),
                profit_unit=0.0,
                reason="fixtures_not_finished",
            )

        leg_results = tuple(_settle_leg(leg, fixture_map[leg.fixture_id]) for leg in ticket.legs)
        status, profit_unit = _ticket_settlement_status(leg_results, ticket.combined_decimal_odds)
        if execute:
            payload: dict[str, Any] = (
                record.payload_json if isinstance(record.payload_json, dict) else {}
            )
            record.status = ComboTicketStatus.SETTLED.value
            record.publication_decision = ComboTicketStatus.SETTLED.value
            record.payload_json = {
                **payload,
                "settlement": {
                    "status": status,
                    "leg_results": list(leg_results),
                    "profit_unit": profit_unit,
                    "settled_at": settled_at.isoformat(),
                },
            }
            persist_combo_ticket_snapshot(
                self.session,
                ComboTicketSnapshot(
                    ticket_key=ticket.ticket_key,
                    status="settled",
                    candidate=ticket,
                    captured_at=settled_at,
                    warnings_json=[f"settlement:{status}", f"profit_unit:{profit_unit}"],
                ),
                ticket_id=record.id,
            )
        return ComboSettlementResult(
            ticket_key=ticket.ticket_key,
            status=status,
            leg_results=leg_results,
            profit_unit=profit_unit,
        )

    def settle_open_records(
        self,
        *,
        settled_at: datetime,
        execute: bool = False,
    ) -> list[ComboSettlementResult]:
        stmt = select(db_models.ComboTicket).where(
            db_models.ComboTicket.status.notin_((ComboTicketStatus.SETTLED.value,))
        )
        return [
            self.settle_record(record, settled_at=settled_at, execute=execute)
            for record in self.session.execute(stmt).scalars()
        ]

    def _fixtures_for_ticket(self, ticket) -> dict[int, db_models.Fixture | None]:
        return {
            leg.fixture_id: self.session.get(db_models.Fixture, leg.fixture_id)
            for leg in ticket.legs
        }


def _settle_leg(leg, fixture: db_models.Fixture | None) -> str:
    if fixture is None:
        return "VOID"
    home_goals = _goal_value(fixture.home_goals, fixture.goals_home)
    away_goals = _goal_value(fixture.away_goals, fixture.goals_away)
    if home_goals is None or away_goals is None:
        return "VOID"
    if leg.market_type == ComboMarketType.HOME:
        return "WON" if home_goals > away_goals else "LOST"
    if leg.market_type == ComboMarketType.DRAW:
        return "WON" if home_goals == away_goals else "LOST"
    if leg.market_type == ComboMarketType.AWAY:
        return "WON" if away_goals > home_goals else "LOST"
    if leg.market_type == ComboMarketType.OVER_25:
        return "WON" if home_goals + away_goals > 2.5 else "LOST"
    if leg.market_type == ComboMarketType.UNDER_25:
        return "WON" if home_goals + away_goals < 2.5 else "LOST"
    return "VOID"


def _ticket_settlement_status(
    leg_results: tuple[str, ...],
    combined_decimal_odds: float,
) -> tuple[str, float]:
    if not leg_results or all(result == "VOID" for result in leg_results):
        return "VOID", 0.0
    if any(result == "LOST" for result in leg_results):
        return "LOST", -1.0
    if all(result in {"WON", "VOID"} for result in leg_results):
        if any(result == "VOID" for result in leg_results):
            return "PARTIAL_VOID", 0.0
        return "WON", round(combined_decimal_odds - 1.0, 6)
    return "VOID", 0.0


def _goal_value(*values: int | None) -> int | None:
    for value in values:
        if value is not None:
            return int(value)
    return None
