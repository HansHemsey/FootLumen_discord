"""Freshness and post-lock risk policy for World Cup combo tickets."""

from __future__ import annotations

from datetime import datetime, timedelta

from football_predictor.world_cup_combos.config import WorldCupComboConfig
from football_predictor.world_cup_combos.models import ComboTicketCandidate


class WorldCupComboRefreshPolicy:
    def __init__(self, config: WorldCupComboConfig) -> None:
        self.config = config

    def should_refresh_odds(
        self,
        now: datetime,
        kickoff_at: datetime,
        last_update: datetime | None,
    ) -> bool:
        return _should_refresh(
            now=now,
            kickoff_at=kickoff_at,
            last_update=last_update,
            max_age_minutes=self.required_freshness_minutes("odds", now, kickoff_at),
        )

    def should_refresh_prediction(
        self,
        now: datetime,
        kickoff_at: datetime,
        generated_at: datetime | None,
    ) -> bool:
        return _should_refresh(
            now=now,
            kickoff_at=kickoff_at,
            last_update=generated_at,
            max_age_minutes=self.required_freshness_minutes("prediction", now, kickoff_at),
        )

    def should_refresh_lineups(
        self,
        now: datetime,
        kickoff_at: datetime,
        lineup_status: str | None,
    ) -> bool:
        minutes_to_kickoff = _minutes_to_kickoff(now, kickoff_at)
        return minutes_to_kickoff <= 90 and (lineup_status or "missing") != "available"

    def required_freshness_minutes(
        self,
        data_type: str,
        now: datetime,
        kickoff_at: datetime,
    ) -> int:
        minutes_to_kickoff = _minutes_to_kickoff(now, kickoff_at)
        if data_type == "odds":
            if minutes_to_kickoff <= 30:
                return 10
            if minutes_to_kickoff <= 90:
                return 20
            if minutes_to_kickoff <= 360:
                return 45
            return 180
        if data_type == "prediction":
            if minutes_to_kickoff <= 30:
                return 20
            if minutes_to_kickoff <= 90:
                return 45
            if minutes_to_kickoff <= 360:
                return 120
            return 360
        if data_type == "lineups":
            return 15 if minutes_to_kickoff <= 90 else 180
        return 120

    def compute_post_lock_risk(
        self,
        ticket: ComboTicketCandidate,
        now: datetime,
    ) -> float:
        risk = float(ticket.post_lock_risk_score)
        first_kickoff = min(leg.kickoff_at_utc for leg in ticket.legs)
        for leg in ticket.legs:
            if leg.kickoff_at_utc - first_kickoff > timedelta(hours=4):
                risk += 12.0
            if self.should_refresh_odds(now, leg.kickoff_at_utc, leg.odds_last_update):
                risk += 8.0
            if self.should_refresh_prediction(
                now,
                leg.kickoff_at_utc,
                leg.prediction_generated_at,
            ):
                risk += 6.0
            if self.should_refresh_lineups(now, leg.kickoff_at_utc, leg.lineup_status):
                risk += 18.0
        return min(risk, 100.0)


def _should_refresh(
    *,
    now: datetime,
    kickoff_at: datetime,
    last_update: datetime | None,
    max_age_minutes: int,
) -> bool:
    if now >= kickoff_at:
        return False
    if last_update is None:
        return True
    age_minutes = max((now - last_update).total_seconds() / 60.0, 0.0)
    return age_minutes > max_age_minutes


def _minutes_to_kickoff(now: datetime, kickoff_at: datetime) -> float:
    return max((kickoff_at - now).total_seconds() / 60.0, 0.0)
