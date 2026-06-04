"""Build World Cup combo ticket candidates from selected legs."""

from __future__ import annotations

import itertools
import re
from dataclasses import replace

from football_predictor.world_cup_combos.config import WorldCupComboConfig
from football_predictor.world_cup_combos.enums import ComboTicketStatus
from football_predictor.world_cup_combos.models import (
    ComboLegCandidate,
    ComboTicketCandidate,
    WorldCupComboSession,
)
from football_predictor.world_cup_combos.worldcup_combo_publication_policy import (
    WorldCupComboPublicationPolicy,
)
from football_predictor.world_cup_combos.worldcup_combo_scoring import WorldCupComboScoring


class WorldCupComboBuilder:
    """Build short combo tickets for one World Cup session."""

    def __init__(
        self,
        config: WorldCupComboConfig,
        *,
        scoring: WorldCupComboScoring | None = None,
        policy: WorldCupComboPublicationPolicy | None = None,
    ) -> None:
        self.config = config
        self.scoring = scoring or WorldCupComboScoring()
        self.policy = policy or WorldCupComboPublicationPolicy(config)

    def build_for_session(
        self,
        combo_session: WorldCupComboSession,
        candidates: list[ComboLegCandidate] | tuple[ComboLegCandidate, ...],
    ) -> list[ComboTicketCandidate]:
        if not self.config.enabled:
            return []

        session_fixture_ids = {fixture.fixture_id for fixture in combo_session.fixtures}
        session_candidates = [
            candidate
            for candidate in candidates
            if candidate.fixture_id in session_fixture_ids and candidate.no_candidate_reason is None
        ]
        if len({candidate.fixture_id for candidate in session_candidates}) < 2:
            return []

        tickets: list[ComboTicketCandidate] = []
        safe = self._best_ticket(combo_session, session_candidates, leg_count=2, ticket_type="safe")
        if safe is not None:
            tickets.append(safe)

        if self.config.max_staff_legs >= 3 and len({c.fixture_id for c in session_candidates}) >= 3:
            standard = self._best_ticket(
                combo_session,
                session_candidates,
                leg_count=min(3, self.config.max_staff_legs),
                ticket_type="standard",
                exclude_ticket_keys={ticket.ticket_key for ticket in tickets},
            )
            if standard is not None:
                tickets.append(standard)
        return tickets

    def _best_ticket(
        self,
        combo_session: WorldCupComboSession,
        candidates: list[ComboLegCandidate],
        *,
        leg_count: int,
        ticket_type: str,
        exclude_ticket_keys: set[str] | None = None,
    ) -> ComboTicketCandidate | None:
        exclude_ticket_keys = exclude_ticket_keys or set()
        best_ticket: ComboTicketCandidate | None = None
        best_score: tuple[float, float, float] | None = None

        for legs in itertools.combinations(_ranked_candidates(candidates), leg_count):
            if _has_duplicate_fixture(legs):
                continue
            same_group_violation = self._same_group_violation(combo_session, legs)
            if same_group_violation and self.config.forbid_same_group_md3_multiple_legs:
                continue
            correlated = _strongly_correlated(legs)
            if correlated:
                continue

            ticket = self._ticket_from_legs(
                combo_session=combo_session,
                legs=legs,
                ticket_type=ticket_type,
                same_group_violation=same_group_violation,
                correlated=correlated,
            )
            if ticket.ticket_key in exclude_ticket_keys:
                continue

            score_key = (
                ticket.combined_ev_adjusted,
                ticket.combined_confidence_score,
                min(leg.confidence_score for leg in ticket.legs),
            )
            if best_score is None or score_key > best_score:
                best_ticket = ticket
                best_score = score_key
        return best_ticket

    def _ticket_from_legs(
        self,
        *,
        combo_session: WorldCupComboSession,
        legs: tuple[ComboLegCandidate, ...],
        ticket_type: str,
        same_group_violation: bool,
        correlated: bool,
    ) -> ComboTicketCandidate:
        scoring = self.scoring.score(
            legs,
            is_matchday3=combo_session.is_matchday3,
            is_knockout=combo_session.is_knockout,
            same_group_violation=same_group_violation,
            correlated=correlated,
        )
        first_kickoff = min(leg.kickoff_at_utc for leg in legs)
        last_kickoff = max(leg.kickoff_at_utc for leg in legs)
        ticket = ComboTicketCandidate(
            competition_key=self.config.competition_key,
            league_id=self.config.league_id,
            season=self.config.season,
            combo_date=combo_session.combo_date_paris,
            session_key=combo_session.session_key,
            ticket_key=_ticket_key(combo_session, legs, ticket_type),
            first_kickoff_at=first_kickoff,
            last_kickoff_at=last_kickoff,
            lock_time=combo_session.lock_time,
            legs_count=len(legs),
            combined_decimal_odds=scoring.combined_decimal_odds,
            combined_probability_raw=scoring.combined_probability_raw,
            combined_probability_adjusted=scoring.combined_probability_adjusted,
            combined_fair_odds=scoring.combined_fair_odds,
            combined_ev_raw=scoring.combined_ev_raw,
            combined_ev_adjusted=scoring.combined_ev_adjusted,
            combined_confidence_score=scoring.combined_confidence_score,
            combined_confidence_label=scoring.combined_confidence_label,
            post_lock_risk_score=scoring.post_lock_risk_score,
            freshness_score=scoring.freshness_score,
            lineup_risk_score=scoring.lineup_risk_score,
            publication_decision=ComboTicketStatus.DRAFT,
            no_publish_reason=None,
            legs=legs,
            warnings=_dedupe(
                [
                    *combo_session.warnings,
                    *scoring.warnings,
                    f"ticket_type:{ticket_type}",
                    f"penalties:{scoring.penalties_json}",
                ]
            ),
        )
        decided = self.policy.decide(ticket)
        return replace(decided, warnings=_dedupe(decided.warnings))

    def _same_group_violation(
        self,
        combo_session: WorldCupComboSession,
        legs: tuple[ComboLegCandidate, ...],
    ) -> bool:
        if not combo_session.is_matchday3:
            return False
        fixture_groups = {
            fixture.fixture_id: _group_key(fixture.round_name)
            for fixture in combo_session.fixtures
        }
        groups = [
            fixture_groups.get(leg.fixture_id)
            for leg in legs
            if fixture_groups.get(leg.fixture_id) is not None
        ]
        return len(groups) != len(set(groups))


def _ranked_candidates(candidates: list[ComboLegCandidate]) -> list[ComboLegCandidate]:
    return sorted(
        candidates,
        key=lambda leg: (
            leg.ev,
            leg.edge,
            leg.confidence_score,
            leg.data_quality_score,
            leg.freshness_score or 0.0,
        ),
        reverse=True,
    )


def _has_duplicate_fixture(legs: tuple[ComboLegCandidate, ...]) -> bool:
    return len({leg.fixture_id for leg in legs}) != len(legs)


def _strongly_correlated(legs: tuple[ComboLegCandidate, ...]) -> bool:
    return _has_duplicate_fixture(legs)


def _group_key(round_name: str | None) -> str | None:
    if not round_name:
        return None
    normalized = round_name.lower()
    match = re.search(r"group\s+([a-z])", normalized)
    if match:
        return match.group(1).upper()
    return None


def _ticket_key(
    combo_session: WorldCupComboSession,
    legs: tuple[ComboLegCandidate, ...],
    ticket_type: str,
) -> str:
    leg_part = "-".join(
        f"{leg.fixture_id}:{leg.market_type.value}:{leg.selection}" for leg in legs
    )
    return f"{combo_session.session_key}:{ticket_type}:{leg_part}"[:300]


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value not in seen:
            result.append(value)
            seen.add(value)
    return result
