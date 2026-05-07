"""Head-to-head goals features for O/U 2.5 prediction."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from football_predictor.db import models
from football_predictor.utils.time import ensure_aware_utc

JsonDict = dict[str, Any]

_THRESHOLD = 2.5
_FINISHED = {"FT", "AET", "PEN"}


def build_h2h_features(
    session: Session,
    home_team_id: int,
    away_team_id: int,
    prediction_time: datetime,
    *,
    league_id: int | None = None,
) -> JsonDict:
    """Build H2H goals history features between two specific teams."""
    cutoff = ensure_aware_utc(prediction_time)
    stmt = (
        select(models.Fixture)
        .where(
            models.Fixture.date.is_not(None),
            models.Fixture.date < cutoff,
            models.Fixture.home_goals.is_not(None),
            models.Fixture.away_goals.is_not(None),
            models.Fixture.status.in_(list(_FINISHED)),
            models.Fixture.home_team_id.in_([home_team_id, away_team_id]),
            models.Fixture.away_team_id.in_([home_team_id, away_team_id]),
        )
        .order_by(models.Fixture.date.desc())
        .limit(10)
    )
    h2h_fixtures = list(session.execute(stmt).scalars())
    h2h_fixtures = [
        f for f in h2h_fixtures
        if {f.home_team_id, f.away_team_id} == {home_team_id, away_team_id}
    ]

    if not h2h_fixtures:
        return {
            "h2h_total_goals_avg_last3": None,
            "h2h_total_goals_avg_last5": None,
            "h2h_over25_rate_last5": None,
            "h2h_matches_available": 0,
        }

    total_goals = [
        (f.home_goals or 0) + (f.away_goals or 0)
        for f in h2h_fixtures
    ]
    count = len(total_goals)
    features: JsonDict = {"h2h_matches_available": count}

    for window in (3, 5):
        selected = total_goals[:window]
        if selected:
            features[f"h2h_total_goals_avg_last{window}"] = sum(selected) / len(selected)
        else:
            features[f"h2h_total_goals_avg_last{window}"] = None

    selected5 = total_goals[:5]
    if selected5:
        features["h2h_over25_rate_last5"] = sum(1 for g in selected5 if g > _THRESHOLD) / len(selected5)
    else:
        features["h2h_over25_rate_last5"] = None

    return features
