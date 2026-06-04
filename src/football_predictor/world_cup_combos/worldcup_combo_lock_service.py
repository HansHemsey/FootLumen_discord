"""Pre-lock revalidation and lock service for World Cup combo tickets."""

from __future__ import annotations

from dataclasses import replace
from datetime import date, datetime
from typing import Any

from sqlalchemy.orm import Session

from football_predictor.db import models as db_models
from football_predictor.world_cup_combos.config import WorldCupComboConfig
from football_predictor.world_cup_combos.enums import (
    ComboMarketScope,
    ComboMarketType,
    ComboTicketStatus,
)
from football_predictor.world_cup_combos.models import (
    ComboLegCandidate,
    ComboTicketCandidate,
    ComboTicketSnapshot,
)
from football_predictor.world_cup_combos.persistence import persist_combo_ticket_snapshot
from football_predictor.world_cup_combos.worldcup_combo_publication_policy import (
    WorldCupComboPublicationPolicy,
)
from football_predictor.world_cup_combos.worldcup_combo_refresh_policy import (
    WorldCupComboRefreshPolicy,
)
from football_predictor.world_cup_combos.worldcup_combo_scoring import WorldCupComboScoring

FINAL_LOCK_STATUSES = {
    ComboTicketStatus.LOCKED,
    ComboTicketStatus.PUBLIC_PUBLISHED,
    ComboTicketStatus.SETTLED,
}


class WorldCupComboLockService:
    def __init__(self, config: WorldCupComboConfig) -> None:
        self.config = config
        self.scoring = WorldCupComboScoring()
        self.policy = WorldCupComboPublicationPolicy(config)
        self.refresh_policy = WorldCupComboRefreshPolicy(config)

    def lock_ticket(
        self,
        ticket: ComboTicketCandidate,
        *,
        now: datetime,
    ) -> ComboTicketCandidate:
        if ticket.publication_decision in FINAL_LOCK_STATUSES:
            return ticket

        scored = self._rescore(ticket, now=now)
        decided = self.policy.decide(scored)
        if decided.publication_decision == ComboTicketStatus.PUBLIC_PUBLISHED:
            warnings = [
                *decided.warnings,
                "pre_lock_policy:PUBLIC_PUBLISHED",
                f"locked_at:{now.isoformat()}",
            ]
            return replace(
                decided,
                publication_decision=ComboTicketStatus.LOCKED,
                no_publish_reason=None,
                warnings=_dedupe(warnings),
            )
        return decided

    def lock_persisted_ticket(
        self,
        session: Session,
        record: db_models.ComboTicket,
        *,
        now: datetime,
        execute: bool = False,
    ) -> ComboTicketCandidate:
        ticket = combo_ticket_candidate_from_payload(record.payload_json)
        if record.status in {
            ComboTicketStatus.LOCKED.value,
            ComboTicketStatus.PUBLIC_PUBLISHED.value,
            ComboTicketStatus.SETTLED.value,
        }:
            return ticket

        locked = self.lock_ticket(ticket, now=now)
        if execute:
            _apply_ticket_to_record(record, locked)
            persist_combo_ticket_snapshot(
                session,
                ComboTicketSnapshot(
                    ticket_key=locked.ticket_key,
                    status="pre_lock",
                    candidate=locked,
                    captured_at=now,
                    warnings_json=locked.warnings,
                ),
                ticket_id=record.id,
            )
        return locked

    def _rescore(
        self,
        ticket: ComboTicketCandidate,
        *,
        now: datetime,
    ) -> ComboTicketCandidate:
        is_matchday3 = "matchday3_public_risk" in ticket.warnings
        is_knockout = "knockout_public_risk" in ticket.warnings
        same_group_violation = "same_group_matchday3_risk" in ticket.warnings
        correlated = "correlation_risk" in ticket.warnings
        scoring = self.scoring.score(
            ticket.legs,
            is_matchday3=is_matchday3,
            is_knockout=is_knockout,
            same_group_violation=same_group_violation,
            correlated=correlated,
        )
        post_lock_risk = self.refresh_policy.compute_post_lock_risk(ticket, now)
        warnings = _dedupe([*ticket.warnings, *scoring.warnings, "snapshot_type:pre_lock"])
        return replace(
            ticket,
            combined_decimal_odds=scoring.combined_decimal_odds,
            combined_probability_raw=scoring.combined_probability_raw,
            combined_probability_adjusted=scoring.combined_probability_adjusted,
            combined_fair_odds=scoring.combined_fair_odds,
            combined_ev_raw=scoring.combined_ev_raw,
            combined_ev_adjusted=scoring.combined_ev_adjusted,
            combined_confidence_score=scoring.combined_confidence_score,
            combined_confidence_label=scoring.combined_confidence_label,
            post_lock_risk_score=max(scoring.post_lock_risk_score, post_lock_risk),
            freshness_score=scoring.freshness_score,
            lineup_risk_score=scoring.lineup_risk_score,
            publication_decision=ComboTicketStatus.PRE_LOCK_REVALIDATION,
            warnings=warnings,
        )


def combo_ticket_candidate_from_payload(payload: dict[str, Any] | None) -> ComboTicketCandidate:
    if not isinstance(payload, dict):
        raise ValueError("combo ticket payload_json is missing or invalid")
    legs = tuple(
        _leg_from_payload(item)
        for item in payload.get("legs", [])
        if isinstance(item, dict)
    )
    return ComboTicketCandidate(
        competition_key=str(payload["competition_key"]),
        league_id=int(payload["league_id"]),
        season=int(payload["season"]),
        combo_date=_date_from_iso(payload["combo_date"]),
        session_key=str(payload["session_key"]),
        ticket_key=str(payload["ticket_key"]),
        first_kickoff_at=_datetime_from_iso(payload["first_kickoff_at"]),
        last_kickoff_at=_datetime_from_iso(payload["last_kickoff_at"]),
        lock_time=_datetime_from_iso(payload["lock_time"]),
        legs_count=int(payload["legs_count"]),
        combined_decimal_odds=float(payload["combined_decimal_odds"]),
        combined_probability_raw=float(payload["combined_probability_raw"]),
        combined_probability_adjusted=float(payload["combined_probability_adjusted"]),
        combined_fair_odds=float(payload["combined_fair_odds"]),
        combined_ev_raw=float(payload["combined_ev_raw"]),
        combined_ev_adjusted=float(payload["combined_ev_adjusted"]),
        combined_confidence_score=float(payload["combined_confidence_score"]),
        combined_confidence_label=str(payload["combined_confidence_label"]),
        post_lock_risk_score=float(payload["post_lock_risk_score"]),
        freshness_score=float(payload["freshness_score"]),
        lineup_risk_score=float(payload["lineup_risk_score"]),
        publication_decision=ComboTicketStatus(str(payload["publication_decision"])),
        no_publish_reason=payload.get("no_publish_reason"),
        legs=legs,
        data_cutoff_time=_optional_datetime(payload.get("data_cutoff_time")),
        generated_at=_optional_datetime(payload.get("generated_at")),
        warnings=list(payload.get("warnings") or []),
    )


def _leg_from_payload(payload: dict[str, Any]) -> ComboLegCandidate:
    return ComboLegCandidate(
        fixture_id=int(payload["fixture_id"]),
        kickoff_at_utc=_datetime_from_iso(payload["kickoff_at_utc"]),
        kickoff_at_paris=_optional_datetime(payload.get("kickoff_at_paris")),
        market_type=ComboMarketType(str(payload["market_type"])),
        market_scope=ComboMarketScope(str(payload["market_scope"])),
        selection=str(payload["selection"]),
        decimal_odd=float(payload["decimal_odd"]),
        model_probability=float(payload["model_probability"]),
        market_probability=float(payload["market_probability"]),
        edge=float(payload["edge"]),
        ev=float(payload["ev"]),
        confidence_score=float(payload["confidence_score"]),
        confidence_label=str(payload["confidence_label"]),
        data_quality_score=float(payload["data_quality_score"]),
        odds_snapshot_id=payload.get("odds_snapshot_id"),
        prediction_snapshot_id=payload.get("prediction_snapshot_id"),
        lineup_status=str(payload["lineup_status"]),
        odds_last_update=_optional_datetime(payload.get("odds_last_update")),
        prediction_generated_at=_optional_datetime(payload.get("prediction_generated_at")),
        freshness_score=payload.get("freshness_score"),
        data_cutoff_time=_optional_datetime(payload.get("data_cutoff_time")),
        generated_at=_optional_datetime(payload.get("generated_at")),
        lock_time=_optional_datetime(payload.get("lock_time")),
        no_candidate_reason=payload.get("no_candidate_reason"),
        warnings=list(payload.get("warnings") or []),
    )


def _apply_ticket_to_record(record: db_models.ComboTicket, ticket: ComboTicketCandidate) -> None:
    record.status = ticket.publication_decision.value
    record.combined_decimal_odds = ticket.combined_decimal_odds
    record.combined_probability_raw = ticket.combined_probability_raw
    record.combined_probability_adjusted = ticket.combined_probability_adjusted
    record.combined_fair_odds = ticket.combined_fair_odds
    record.combined_ev_raw = ticket.combined_ev_raw
    record.combined_ev_adjusted = ticket.combined_ev_adjusted
    record.combined_confidence_score = ticket.combined_confidence_score
    record.combined_confidence_label = ticket.combined_confidence_label
    record.post_lock_risk_score = ticket.post_lock_risk_score
    record.freshness_score = ticket.freshness_score
    record.lineup_risk_score = ticket.lineup_risk_score
    record.publication_decision = ticket.publication_decision.value
    record.no_publish_reason = ticket.no_publish_reason
    record.warnings_json = ticket.warnings
    record.payload_json = ticket.to_json_dict()


def _datetime_from_iso(value: str) -> datetime:
    return datetime.fromisoformat(value)


def _optional_datetime(value: object) -> datetime | None:
    if value in {None, ""}:
        return None
    return datetime.fromisoformat(str(value))


def _date_from_iso(value: str):
    return datetime.fromisoformat(str(value)).date() if "T" in str(value) else date.fromisoformat(
        str(value)
    )


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value not in seen:
            result.append(value)
            seen.add(value)
    return result
