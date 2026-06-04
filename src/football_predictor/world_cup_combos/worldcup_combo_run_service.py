"""Controlled orchestration for World Cup combo ticket generation."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy.orm import Session

from football_predictor.world_cup_combos.config import WorldCupComboConfig
from football_predictor.world_cup_combos.cutoff import compute_effective_cutoff
from football_predictor.world_cup_combos.models import (
    ComboLegSelectionResult,
    ComboTicketCandidate,
)
from football_predictor.world_cup_combos.persistence import (
    persist_combo_ticket_with_snapshots,
)
from football_predictor.world_cup_combos.worldcup_combo_builder import WorldCupComboBuilder
from football_predictor.world_cup_combos.worldcup_combo_leg_selector import (
    WorldCupComboLegSelector,
)
from football_predictor.world_cup_combos.worldcup_combo_sessions import (
    WorldCupComboSessionService,
)

JsonDict = dict[str, Any]


@dataclass(frozen=True)
class WorldCupComboTicketSummary:
    ticket_key: str
    legs_count: int
    combined_decimal_odds: float
    combined_ev_adjusted: float
    combined_confidence_score: float
    combined_confidence_label: str
    publication_decision: str
    no_publish_reason: str | None
    post_lock_risk_score: float
    warnings: list[str] = field(default_factory=list)

    @classmethod
    def from_ticket(cls, ticket: ComboTicketCandidate) -> WorldCupComboTicketSummary:
        return cls(
            ticket_key=ticket.ticket_key,
            legs_count=ticket.legs_count,
            combined_decimal_odds=ticket.combined_decimal_odds,
            combined_ev_adjusted=ticket.combined_ev_adjusted,
            combined_confidence_score=ticket.combined_confidence_score,
            combined_confidence_label=ticket.combined_confidence_label,
            publication_decision=ticket.publication_decision.value,
            no_publish_reason=ticket.no_publish_reason,
            post_lock_risk_score=ticket.post_lock_risk_score,
            warnings=list(ticket.warnings),
        )

    def as_dict(self) -> JsonDict:
        return {
            "ticket_key": self.ticket_key,
            "legs_count": self.legs_count,
            "combined_decimal_odds": self.combined_decimal_odds,
            "combined_ev_adjusted": self.combined_ev_adjusted,
            "combined_confidence_score": self.combined_confidence_score,
            "combined_confidence_label": self.combined_confidence_label,
            "publication_decision": self.publication_decision,
            "no_publish_reason": self.no_publish_reason,
            "post_lock_risk_score": self.post_lock_risk_score,
            "warnings": self.warnings,
        }


@dataclass(frozen=True)
class WorldCupComboSessionRunSummary:
    session_key: str
    lock_time: datetime
    data_cutoff_time: datetime
    generated_at: datetime
    fixtures: int
    candidate_legs: int
    tickets: tuple[WorldCupComboTicketSummary, ...] = field(default_factory=tuple)

    def as_dict(self) -> JsonDict:
        return {
            "session_key": self.session_key,
            "lock_time": self.lock_time.isoformat(),
            "data_cutoff_time": self.data_cutoff_time.isoformat(),
            "generated_at": self.generated_at.isoformat(),
            "fixtures": self.fixtures,
            "candidate_legs": self.candidate_legs,
            "tickets": [ticket.as_dict() for ticket in self.tickets],
        }


@dataclass(frozen=True)
class WorldCupComboRunSummary:
    enabled: bool
    execute: bool
    target_date: str | None
    generated_at: datetime | None
    sessions: int
    candidate_legs: int
    tickets: int
    persisted_tickets: int
    no_candidate_reasons: dict[str, int] = field(default_factory=dict)
    session_summaries: tuple[WorldCupComboSessionRunSummary, ...] = field(default_factory=tuple)
    message: str | None = None

    def as_dict(self) -> JsonDict:
        return {
            "enabled": self.enabled,
            "execute": self.execute,
            "target_date": self.target_date,
            "generated_at": self.generated_at.isoformat() if self.generated_at else None,
            "sessions": self.sessions,
            "candidate_legs": self.candidate_legs,
            "tickets": self.tickets,
            "persisted_tickets": self.persisted_tickets,
            "no_candidate_reasons": self.no_candidate_reasons,
            "session_summaries": [
                session_summary.as_dict() for session_summary in self.session_summaries
            ],
            "message": self.message,
        }


class WorldCupComboRunService:
    """Generate and optionally persist combo tickets without publishing Discord."""

    def __init__(
        self,
        db_session: Session,
        config: WorldCupComboConfig,
        *,
        session_service: WorldCupComboSessionService | None = None,
        leg_selector: WorldCupComboLegSelector | None = None,
        builder: WorldCupComboBuilder | None = None,
    ) -> None:
        self.db_session = db_session
        self.config = config
        self.session_service = session_service or WorldCupComboSessionService(
            db_session,
            config,
        )
        self.leg_selector = leg_selector or WorldCupComboLegSelector(db_session, config)
        self.builder = builder or WorldCupComboBuilder(config)

    def run(
        self,
        *,
        target_date: date | None = None,
        execute: bool = False,
        captured_at: datetime | None = None,
    ) -> WorldCupComboRunSummary:
        if not self.config.enabled:
            return WorldCupComboRunSummary(
                enabled=False,
                execute=execute,
                target_date=target_date.isoformat() if target_date else None,
                generated_at=None,
                sessions=0,
                candidate_legs=0,
                tickets=0,
                persisted_tickets=0,
                message="worldcup_combos disabled",
            )

        captured_at = captured_at or datetime.now(tz=UTC)
        combo_sessions = self.session_service.build_sessions(target_date=target_date)
        selection = self.leg_selector.select_candidates(combo_sessions, now=captured_at)
        candidates_by_session = _candidates_by_session(selection)

        persisted = 0
        session_summaries: list[WorldCupComboSessionRunSummary] = []
        for combo_session in combo_sessions:
            session_candidates = candidates_by_session.get(combo_session.session_key, [])
            tickets = self.builder.build_for_session(combo_session, session_candidates)
            if execute:
                for ticket in tickets:
                    persist_combo_ticket_with_snapshots(
                        self.db_session,
                        ticket,
                        captured_at=captured_at,
                        model_versions_json={"worldcup_combos": "v1"},
                    )
                    persisted += 1
            session_summaries.append(
                WorldCupComboSessionRunSummary(
                    session_key=combo_session.session_key,
                    lock_time=combo_session.lock_time,
                    data_cutoff_time=compute_effective_cutoff(
                        captured_at,
                        combo_session.lock_time,
                    ),
                    generated_at=captured_at,
                    fixtures=len(combo_session.fixtures),
                    candidate_legs=len(session_candidates),
                    tickets=tuple(
                        WorldCupComboTicketSummary.from_ticket(ticket) for ticket in tickets
                    ),
                )
            )

        ticket_count = sum(len(summary.tickets) for summary in session_summaries)
        return WorldCupComboRunSummary(
            enabled=True,
            execute=execute,
            target_date=target_date.isoformat() if target_date else None,
            generated_at=captured_at,
            sessions=len(combo_sessions),
            candidate_legs=len(selection.candidates),
            tickets=ticket_count,
            persisted_tickets=persisted,
            no_candidate_reasons=dict(
                sorted(Counter(item.reason for item in selection.no_candidates).items())
            ),
            session_summaries=tuple(session_summaries),
        )


def _candidates_by_session(
    selection: ComboLegSelectionResult,
) -> dict[str, list]:
    result: dict[str, list] = defaultdict(list)
    fixture_session_map: dict[int, str] = {}
    for combo_session in selection.sessions:
        for fixture in combo_session.fixtures:
            fixture_session_map[fixture.fixture_id] = combo_session.session_key
    for candidate in selection.candidates:
        session_key = fixture_session_map.get(candidate.fixture_id)
        if session_key is not None:
            result[session_key].append(candidate)
    return result
