"""Pre-lock revalidation for persisted World Cup combo tickets."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from football_predictor.world_cup_combos.config import WorldCupComboConfig
from football_predictor.world_cup_combos.cutoff import compute_effective_cutoff
from football_predictor.world_cup_combos.enums import ComboMarketType, ComboTicketStatus
from football_predictor.world_cup_combos.models import (
    ComboLegCandidate,
    ComboTicketCandidate,
    WorldCupComboSession,
)
from football_predictor.world_cup_combos.worldcup_combo_builder import WorldCupComboBuilder
from football_predictor.world_cup_combos.worldcup_combo_leg_selector import (
    WorldCupComboLegSelector,
)
from football_predictor.world_cup_combos.worldcup_combo_publication_policy import (
    WorldCupComboPublicationPolicy,
)
from football_predictor.world_cup_combos.worldcup_combo_sessions import (
    WorldCupComboSessionService,
)

MIN_COMBO_LEGS = 2
ODDS_INVALID_WARNINGS = {"odds_stale", "odds_freshness_unknown"}


@dataclass(frozen=True)
class PreLockRevalidationResult:
    ticket: ComboTicketCandidate
    snapshot_types: tuple[str, ...]


class WorldCupComboPreLockRevalidator:
    """Re-read dynamic sources and rebuild a ticket before final lock."""

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
        self.policy = WorldCupComboPublicationPolicy(config)

    def revalidate(
        self,
        ticket: ComboTicketCandidate,
        *,
        now: datetime,
    ) -> PreLockRevalidationResult:
        current_time = _as_utc(now)
        cutoff_time = compute_effective_cutoff(current_time, ticket.lock_time)
        combo_session = self._load_session(ticket)
        if combo_session is None:
            return self._no_bet_result(
                ticket,
                now=current_time,
                cutoff_time=cutoff_time,
                reason="session_unavailable",
                warnings=["session_unavailable", "no_clean_replacement"],
            )

        fixture_status_warning = self._fixture_status_warning(ticket, combo_session, current_time)
        if fixture_status_warning is not None:
            return self._no_bet_result(
                ticket,
                now=current_time,
                cutoff_time=cutoff_time,
                reason="fixture_not_ns",
                warnings=[fixture_status_warning, "fixture_not_ns"],
            )

        selection = self.leg_selector.select_candidates((combo_session,), now=current_time)
        candidates = tuple(
            candidate
            for candidate in selection.candidates
            if candidate.fixture_id in {fixture.fixture_id for fixture in combo_session.fixtures}
        )
        clean_candidates = tuple(
            candidate for candidate in candidates if _is_clean_candidate(candidate)
        )
        warnings = self._original_leg_degradation_warnings(
            ticket,
            candidates=candidates,
            no_candidates=selection.no_candidates,
        )
        if "market_scope_unknown" in warnings:
            return self._no_bet_result(
                ticket,
                now=current_time,
                cutoff_time=cutoff_time,
                reason="market_scope_unknown",
                warnings=warnings,
            )

        rebuilt = self._best_rebuilt_ticket(
            original=ticket,
            combo_session=combo_session,
            candidates=clean_candidates,
            now=current_time,
            cutoff_time=cutoff_time,
            warnings=warnings,
        )
        if rebuilt is None:
            return self._no_bet_result(
                ticket,
                now=current_time,
                cutoff_time=cutoff_time,
                reason="not_enough_clean_legs",
                warnings=[*warnings, "no_clean_replacement"],
            )

        snapshot_types = ["pre_lock_revalidated"]
        if "replacement_used" in rebuilt.warnings:
            snapshot_types.append("pre_lock_replaced_leg")
        if rebuilt.publication_decision == ComboTicketStatus.NO_BET:
            snapshot_types.append("pre_lock_no_bet")
        return PreLockRevalidationResult(
            ticket=rebuilt,
            snapshot_types=tuple(snapshot_types),
        )

    def _load_session(self, ticket: ComboTicketCandidate) -> WorldCupComboSession | None:
        sessions = self.session_service.build_sessions(target_date=ticket.combo_date)
        for combo_session in sessions:
            if combo_session.session_key == ticket.session_key:
                return combo_session
        original_fixture_ids = {leg.fixture_id for leg in ticket.legs}
        for combo_session in sessions:
            session_fixture_ids = {fixture.fixture_id for fixture in combo_session.fixtures}
            if original_fixture_ids.issubset(session_fixture_ids):
                return combo_session
        return None

    def _fixture_status_warning(
        self,
        ticket: ComboTicketCandidate,
        combo_session: WorldCupComboSession,
        now: datetime,
    ) -> str | None:
        fixture_refs = {fixture.fixture_id: fixture for fixture in combo_session.fixtures}
        for leg in ticket.legs:
            fixture = fixture_refs.get(leg.fixture_id)
            if fixture is None:
                return "fixture_missing"
            if (fixture.status_short or "").upper() != "NS":
                return "fixture_not_ns"
            if fixture.kickoff_at_utc <= now:
                return "fixture_not_ns"
        return None

    def _original_leg_degradation_warnings(
        self,
        ticket: ComboTicketCandidate,
        *,
        candidates: tuple[ComboLegCandidate, ...],
        no_candidates,
    ) -> list[str]:
        candidate_by_key = {_leg_key(candidate): candidate for candidate in candidates}
        reasons = {
            (item.fixture_id, item.source_type): item.reason
            for item in no_candidates
        }
        warnings: list[str] = []
        for leg in ticket.legs:
            current = candidate_by_key.get(_leg_key(leg))
            if current is not None and _is_clean_candidate(current):
                continue
            if current is not None:
                warnings.extend(_candidate_degradation_warnings(current))
                continue
            reason = reasons.get((leg.fixture_id, _source_type_for_leg(leg)))
            warnings.extend(_reason_warnings(reason))
        return _dedupe(warnings)

    def _best_rebuilt_ticket(
        self,
        *,
        original: ComboTicketCandidate,
        combo_session: WorldCupComboSession,
        candidates: tuple[ComboLegCandidate, ...],
        now: datetime,
        cutoff_time: datetime,
        warnings: list[str],
    ) -> ComboTicketCandidate | None:
        if len({candidate.fixture_id for candidate in candidates}) < MIN_COMBO_LEGS:
            return None

        tickets = self.builder.build_for_session(combo_session, candidates)
        if not tickets:
            return None

        desired_leg_count = min(original.legs_count, self.config.max_staff_legs)
        preferred = [ticket for ticket in tickets if ticket.legs_count == desired_leg_count]
        rebuilt = max(
            preferred or tickets,
            key=lambda item: (
                item.legs_count == desired_leg_count,
                item.combined_ev_adjusted,
                item.combined_confidence_score,
            ),
        )
        original_keys = {_leg_key(leg) for leg in original.legs}
        rebuilt_keys = {_leg_key(leg) for leg in rebuilt.legs}
        audit_warnings = [
            *warnings,
            *rebuilt.warnings,
            "pre_lock_revalidated",
        ]
        if rebuilt_keys != original_keys:
            audit_warnings.extend(["replacement_used", "pre_lock_replaced_leg"])
        if rebuilt.lineup_risk_score > self.config.max_post_lock_risk_public:
            audit_warnings.append("lineup_risk_too_high")

        rebuilt = replace(
            rebuilt,
            ticket_key=original.ticket_key,
            data_cutoff_time=cutoff_time,
            generated_at=now,
            warnings=_dedupe(audit_warnings),
        )
        decided = self.policy.decide(rebuilt)
        if (
            "lineup_risk_too_high" in decided.warnings
            and decided.publication_decision != ComboTicketStatus.NO_BET
        ):
            decided = replace(
                decided,
                publication_decision=ComboTicketStatus.STAFF_ONLY,
                no_publish_reason="lineup_risk_too_high",
                warnings=_dedupe([*decided.warnings, "lineup_risk_too_high"]),
            )
        return decided

    def _no_bet_result(
        self,
        ticket: ComboTicketCandidate,
        *,
        now: datetime,
        cutoff_time: datetime,
        reason: str,
        warnings: list[str],
    ) -> PreLockRevalidationResult:
        no_bet = replace(
            ticket,
            publication_decision=ComboTicketStatus.NO_BET,
            no_publish_reason=reason,
            data_cutoff_time=cutoff_time,
            generated_at=now,
            warnings=_dedupe([*ticket.warnings, *warnings, "pre_lock_revalidated", reason]),
        )
        return PreLockRevalidationResult(
            ticket=no_bet,
            snapshot_types=("pre_lock_revalidated", "pre_lock_no_bet"),
        )


def _leg_key(leg: ComboLegCandidate) -> tuple[int, ComboMarketType, str]:
    return (leg.fixture_id, leg.market_type, leg.selection)


def _source_type_for_leg(leg: ComboLegCandidate) -> str:
    if leg.market_type in {ComboMarketType.HOME, ComboMarketType.DRAW, ComboMarketType.AWAY}:
        return "worldcup_1x2"
    return "ou25_v2"


def _is_clean_candidate(candidate: ComboLegCandidate) -> bool:
    if candidate.odds_snapshot_id is None or candidate.odds_last_update is None:
        return False
    return not ODDS_INVALID_WARNINGS.intersection(candidate.warnings)


def _candidate_degradation_warnings(candidate: ComboLegCandidate) -> list[str]:
    warnings: list[str] = []
    if "odds_stale" in candidate.warnings:
        warnings.append("odds_stale")
    if "odds_freshness_unknown" in candidate.warnings:
        warnings.append("odds_missing")
    if candidate.odds_snapshot_id is None or candidate.odds_last_update is None:
        warnings.append("odds_missing")
    return warnings or ["no_clean_replacement"]


def _reason_warnings(reason: str | None) -> list[str]:
    mapping = {
        "ev_below_threshold": "leg_ev_dropped",
        "edge_below_threshold": "leg_edge_dropped",
        "market_unavailable": "odds_missing",
        "invalid_odds": "odds_missing",
        "ambiguous_market_scope": "market_scope_unknown",
        "fixture_started": "fixture_not_ns",
        "data_quality_below_threshold": "data_quality_below_threshold",
        "confidence_below_threshold": "confidence_below_threshold",
        "no_ou_value_side": "leg_ev_dropped",
    }
    if reason is None:
        return ["no_clean_replacement"]
    return [mapping.get(reason, reason)]


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value not in seen:
            result.append(value)
            seen.add(value)
    return result
