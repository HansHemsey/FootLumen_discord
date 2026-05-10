"""Draw Risk derived features from base feature snapshot."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from football_predictor.db import models
from football_predictor.modeling.poisson import _poisson_pmf, poisson_probabilities
from football_predictor.modeling.poisson_v2 import estimate_lambda_home_away_v2
from football_predictor.utils.time import ensure_aware_utc

JsonDict = dict[str, Any]
FINISHED_STATUSES = ("FT", "AET", "PEN")


def build_draw_risk_features(
    features: Mapping[str, Any],
    *,
    session: Session | None = None,
    fixture_id: int | None = None,
    prediction_time: datetime | None = None,
) -> JsonDict:
    """Compute draw-risk composite features from base features.

    session/fixture_id/prediction_time are required only for league_draw_rate.
    All other features are derived purely from the input features dict.
    """
    home_ppg = _f(features, "home_team_global_points_per_match_last10")
    away_ppg = _f(features, "away_team_global_points_per_match_last10")
    home_xg = _f(
        features,
        "home_team_global_pseudo_xg_for_avg_last10",
        "home_team_global_last10_pseudo_xg_for_avg",
    )
    away_xg = _f(
        features,
        "away_team_global_pseudo_xg_for_avg_last10",
        "away_team_global_last10_pseudo_xg_for_avg",
    )
    home_cs = _f(features, "home_team_global_clean_sheet_rate_last10")
    away_cs = _f(features, "away_team_global_clean_sheet_rate_last10")
    home_fts = _f(features, "home_team_global_failed_to_score_rate_last10")
    away_fts = _f(features, "away_team_global_failed_to_score_rate_last10")
    home_draw_rate = _f(features, "home_team_global_draw_rate_last10")
    home_home_draw_rate = _f(features, "home_team_home_draw_rate_last10")
    away_away_draw_rate = _f(features, "away_team_away_draw_rate_last10")
    market_draw = _f(features, "market_draw")
    market_draw_movement = _f(features, "odds_movement_draw")

    parity_score = _parity_score(home_ppg, away_ppg)
    xg_total_low_score = _xg_total_low_score(home_xg, away_xg)
    xg_gap_abs = _xg_gap_abs(home_xg, away_xg)
    defensive_solidity = _combined(home_cs, away_cs)
    attacking_weakness = _combined(home_fts, away_fts)

    lambdas = estimate_lambda_home_away_v2(features)
    poisson_draw_prob = poisson_probabilities(*lambdas).p_draw
    low_score_prob = _low_scoring_draw_prob(*lambdas)

    league_draw_rate = None
    if session is not None and fixture_id is not None and prediction_time is not None:
        league_draw_rate = _compute_league_draw_rate(session, fixture_id, prediction_time)

    draw_risk_score = _draw_risk_score(
        parity_score=parity_score,
        xg_total_low_score=xg_total_low_score,
        defensive_solidity=defensive_solidity,
        attacking_weakness=attacking_weakness,
        market_draw=market_draw,
        poisson_draw=poisson_draw_prob,
        home_draw_rate=home_draw_rate,
        away_draw_rate=away_away_draw_rate,
    )

    return {
        "draw_risk_parity_score": parity_score,
        "draw_risk_xg_total_low_score": xg_total_low_score,
        "draw_risk_xg_gap_abs": xg_gap_abs,
        "draw_risk_defensive_solidity": defensive_solidity,
        "draw_risk_attacking_weakness": attacking_weakness,
        "draw_risk_home_draw_rate_last10": home_draw_rate,
        "draw_risk_home_at_home_draw_rate_last10": home_home_draw_rate,
        "draw_risk_away_at_away_draw_rate_last10": away_away_draw_rate,
        "draw_risk_league_draw_rate": league_draw_rate,
        "draw_risk_market_prob": market_draw,
        "draw_risk_market_movement": market_draw_movement,
        "draw_risk_poisson_prob": poisson_draw_prob,
        "draw_risk_low_score_prob": low_score_prob,
        "draw_risk_score": draw_risk_score,
    }


def _parity_score(home_ppg: float | None, away_ppg: float | None) -> float | None:
    if home_ppg is None or away_ppg is None:
        return None
    return 1.0 / (1.0 + abs(home_ppg - away_ppg))


def _xg_total_low_score(home_xg: float | None, away_xg: float | None) -> float | None:
    if home_xg is None or away_xg is None:
        return None
    return 1.0 / (1.0 + home_xg + away_xg)


def _xg_gap_abs(home_xg: float | None, away_xg: float | None) -> float | None:
    if home_xg is None or away_xg is None:
        return None
    return abs(home_xg - away_xg)


def _combined(a: float | None, b: float | None) -> float | None:
    if a is None or b is None:
        return None
    return a + b


def _low_scoring_draw_prob(lambda_home: float, lambda_away: float, max_k: int = 3) -> float:
    """P(0-0) + P(1-1) + P(2-2) + P(3-3) as proxy for low-scoring draw."""
    return sum(
        _poisson_pmf(k, lambda_home) * _poisson_pmf(k, lambda_away) for k in range(max_k + 1)
    )


def _draw_risk_score(
    *,
    parity_score: float | None,
    xg_total_low_score: float | None,
    defensive_solidity: float | None,
    attacking_weakness: float | None,
    market_draw: float | None,
    poisson_draw: float,
    home_draw_rate: float | None,
    away_draw_rate: float | None,
) -> float | None:
    """Weighted composite draw risk score in [0, 1]."""
    signals: list[tuple[float, float]] = []

    if parity_score is not None:
        signals.append((parity_score, 0.15))
    if xg_total_low_score is not None:
        signals.append((xg_total_low_score, 0.15))
    if defensive_solidity is not None:
        signals.append((min(defensive_solidity / 2.0, 1.0), 0.10))
    if attacking_weakness is not None:
        signals.append((min(attacking_weakness / 2.0, 1.0), 0.10))
    if market_draw is not None:
        signals.append((market_draw * 3.0, 0.25))
    signals.append((poisson_draw * 3.0, 0.15))
    if home_draw_rate is not None:
        signals.append((home_draw_rate, 0.05))
    if away_draw_rate is not None:
        signals.append((away_draw_rate, 0.05))

    if not signals:
        return None

    total_weight = sum(w for _, w in signals)
    score = sum(v * w for v, w in signals) / total_weight
    return min(max(score, 0.0), 1.0)


def _compute_league_draw_rate(
    session: Session,
    fixture_id: int,
    prediction_time: datetime,
) -> float | None:
    """Fraction of draws in the same league/season, among matches finished before prediction_time.
    """
    cutoff = ensure_aware_utc(prediction_time)
    fixture = session.get(models.Fixture, fixture_id)
    if fixture is None or fixture.league_id is None or fixture.season is None:
        return None

    finished = list(
        session.execute(
            select(models.Fixture)
            .where(
                models.Fixture.league_id == fixture.league_id,
                models.Fixture.season == fixture.season,
                models.Fixture.status_short.in_(FINISHED_STATUSES),
                models.Fixture.fixture_id != fixture_id,
                models.Fixture.date < cutoff,
                models.Fixture.home_goals.is_not(None),
                models.Fixture.away_goals.is_not(None),
            )
        ).scalars()
    )

    if not finished:
        return None

    draws = sum(
        1
        for f in finished
        if f.home_goals is not None and f.away_goals is not None and f.home_goals == f.away_goals
    )
    return draws / len(finished)


def _f(features: Mapping[str, Any], *keys: str) -> float | None:
    """Return first non-None float value from the given keys."""
    for key in keys:
        raw = features.get(key)
        if raw is not None:
            try:
                return float(raw)
            except (TypeError, ValueError):
                continue
    return None
