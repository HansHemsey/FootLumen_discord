"""M-30 official lineup availability and formation features."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from football_predictor.db import models
from football_predictor.utils.time import ensure_aware_utc

JsonDict = dict[str, Any]

P_START_REGULAR_THRESHOLD = 0.55


def build_lineup_m30_features(
    session: Session,
    fixture_id: int,
    prediction_time: datetime,
) -> JsonDict:
    """Return M-30 official lineup availability and formation change features.

    All DB access is strictly gated to fetched_at <= prediction_time to preserve
    point-in-time discipline at M-30.
    """
    session.flush()
    cutoff = ensure_aware_utc(prediction_time)
    fixture = session.get(models.Fixture, fixture_id)
    if fixture is None:
        return _empty_features()

    home_lineup = _latest_official_lineup(session, fixture_id, fixture.home_team_id, cutoff)
    away_lineup = _latest_official_lineup(session, fixture_id, fixture.away_team_id, cutoff)

    home_available = home_lineup is not None
    away_available = away_lineup is not None
    both_available = home_available and away_available

    home_formation_features = _formation_features(
        session,
        fixture_id=fixture_id,
        team_id=fixture.home_team_id,
        official_lineup=home_lineup,
        prediction_time=cutoff,
        prefix="home_team",
    )
    away_formation_features = _formation_features(
        session,
        fixture_id=fixture_id,
        team_id=fixture.away_team_id,
        official_lineup=away_lineup,
        prediction_time=cutoff,
        prefix="away_team",
    )

    return {
        "official_lineup_available_flag": int(both_available),
        "official_lineup_home_available_flag": int(home_available),
        "official_lineup_away_available_flag": int(away_available),
        **home_formation_features,
        **away_formation_features,
    }


def _empty_features() -> JsonDict:
    return {
        "official_lineup_available_flag": 0,
        "official_lineup_home_available_flag": 0,
        "official_lineup_away_available_flag": 0,
        "home_team_official_formation": None,
        "home_team_formation_change_flag": 0,
        "home_team_formation_stability_score": None,
        "home_team_lineup_surprise_score": None,
        "away_team_official_formation": None,
        "away_team_formation_change_flag": 0,
        "away_team_formation_stability_score": None,
        "away_team_lineup_surprise_score": None,
    }


def _latest_official_lineup(
    session: Session,
    fixture_id: int,
    team_id: int | None,
    cutoff: datetime,
) -> models.FixtureLineup | None:
    if team_id is None:
        return None
    return session.execute(
        select(models.FixtureLineup)
        .where(
            models.FixtureLineup.fixture_id == fixture_id,
            models.FixtureLineup.team_id == team_id,
            models.FixtureLineup.fetched_at <= cutoff,
        )
        .order_by(models.FixtureLineup.fetched_at.desc())
        .limit(1)
    ).scalar_one_or_none()


def _formation_features(
    session: Session,
    *,
    fixture_id: int,
    team_id: int | None,
    official_lineup: models.FixtureLineup | None,
    prediction_time: datetime,
    prefix: str,
) -> JsonDict:
    if team_id is None:
        return {
            f"{prefix}_official_formation": None,
            f"{prefix}_formation_change_flag": 0,
            f"{prefix}_formation_stability_score": None,
            f"{prefix}_lineup_surprise_score": None,
        }

    probable = _probable_formation(session, team_id, fixture_id, prediction_time)
    probable_formation = probable.get("formation")
    stability = probable.get("formation_stability")

    official_formation: str | None = None
    formation_change_flag = 0
    surprise_score: float | None = None

    if official_lineup is not None:
        official_formation = official_lineup.formation
        if probable_formation and official_formation and official_formation != probable_formation:
            formation_change_flag = 1
        surprise_score = _lineup_surprise_score(
            session,
            official_lineup=official_lineup,
            team_id=team_id,
            fixture_id=fixture_id,
            prediction_time=prediction_time,
        )

    return {
        f"{prefix}_official_formation": official_formation,
        f"{prefix}_formation_change_flag": formation_change_flag,
        f"{prefix}_formation_stability_score": stability,
        f"{prefix}_lineup_surprise_score": surprise_score,
    }


def _probable_formation(
    session: Session,
    team_id: int,
    fixture_id: int,
    prediction_time: datetime,
) -> JsonDict:
    """Infer probable formation from historical lineups for other fixtures."""
    past_lineups = session.execute(
        select(models.FixtureLineup)
        .join(
            models.Fixture,
            models.FixtureLineup.fixture_id == models.Fixture.fixture_id,
        )
        .where(
            models.FixtureLineup.team_id == team_id,
            models.FixtureLineup.fixture_id != fixture_id,
            models.FixtureLineup.formation.is_not(None),
            models.Fixture.date < prediction_time,
            models.FixtureLineup.fetched_at <= prediction_time,
        )
        .order_by(models.Fixture.date.desc())
        .limit(10)
    ).scalars()

    formation_counts: dict[str, int] = {}
    lineups_used = 0
    for lineup in past_lineups:
        if lineup.formation:
            formation_counts[lineup.formation] = formation_counts.get(lineup.formation, 0) + 1
            lineups_used += 1

    if not formation_counts:
        return {"formation": None, "formation_stability": None}

    dominant = max(formation_counts, key=lambda k: formation_counts[k])
    stability = formation_counts[dominant] / lineups_used if lineups_used else 0.0
    return {"formation": dominant, "formation_stability": stability}


def _lineup_surprise_score(
    session: Session,
    *,
    official_lineup: models.FixtureLineup,
    team_id: int,
    fixture_id: int,
    prediction_time: datetime,
) -> float:
    """Fraction of official starters who never started in the last 10 historical matches."""
    starters_json = official_lineup.start_xi_json
    if not starters_json or not isinstance(starters_json, list):
        return 0.0

    official_player_ids = {
        int(row["player"]["id"])
        for row in starters_json
        if isinstance(row, dict) and "player" in row and "id" in row["player"]
    }
    if not official_player_ids:
        return 0.0

    past_lineups = list(
        session.execute(
            select(models.FixtureLineup)
            .join(
                models.Fixture,
                models.FixtureLineup.fixture_id == models.Fixture.fixture_id,
            )
            .where(
                models.FixtureLineup.team_id == team_id,
                models.FixtureLineup.fixture_id != fixture_id,
                models.Fixture.date < prediction_time,
                models.FixtureLineup.fetched_at <= prediction_time,
            )
            .order_by(models.Fixture.date.desc())
            .limit(10)
        ).scalars()
    )

    historical_starters: set[int] = set()
    for lineup in past_lineups:
        xi = lineup.start_xi_json
        if not isinstance(xi, list):
            continue
        for row in xi:
            if isinstance(row, dict) and "player" in row and "id" in row.get("player", {}):
                historical_starters.add(int(row["player"]["id"]))

    if not historical_starters:
        return 0.0

    surprises = sum(1 for pid in official_player_ids if pid not in historical_starters)
    return surprises / len(official_player_ids)
