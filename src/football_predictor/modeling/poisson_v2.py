"""V2 Poisson expert with light low-score correction."""

from __future__ import annotations

import math
from collections.abc import Mapping
from typing import Any

from football_predictor.modeling.poisson import _poisson_pmf
from football_predictor.modeling.probabilities import ProbabilityTriple

JsonRow = Mapping[str, Any]

DEFAULT_HOME_LAMBDA = 1.38
DEFAULT_AWAY_LAMBDA = 1.12
MAX_GOALS_V2 = 10


def estimate_lambda_home_away_v2(features: JsonRow) -> tuple[float, float]:
    """Estimate expected goals from team form, pseudo-xG and availability signals."""
    home_attack = _weighted_first(
        features,
        (
            ("home_team_home_goals_for_avg_last10", 0.35),
            ("home_team_home_goals_for_avg_last5", 0.25),
            ("home_team_global_goals_for_avg_last10", 0.25),
            ("home_team_global_goals_for_avg_last5", 0.15),
        ),
    )
    away_defense = _weighted_first(
        features,
        (
            ("away_team_away_goals_against_avg_last10", 0.35),
            ("away_team_away_goals_against_avg_last5", 0.25),
            ("away_team_global_goals_against_avg_last10", 0.25),
            ("away_team_global_goals_against_avg_last5", 0.15),
        ),
    )
    away_attack = _weighted_first(
        features,
        (
            ("away_team_away_goals_for_avg_last10", 0.35),
            ("away_team_away_goals_for_avg_last5", 0.25),
            ("away_team_global_goals_for_avg_last10", 0.25),
            ("away_team_global_goals_for_avg_last5", 0.15),
        ),
    )
    home_defense = _weighted_first(
        features,
        (
            ("home_team_home_goals_against_avg_last10", 0.35),
            ("home_team_home_goals_against_avg_last5", 0.25),
            ("home_team_global_goals_against_avg_last10", 0.25),
            ("home_team_global_goals_against_avg_last5", 0.15),
        ),
    )
    home_lambda = _mean_or_default(home_attack, away_defense, DEFAULT_HOME_LAMBDA)
    away_lambda = _mean_or_default(away_attack, home_defense, DEFAULT_AWAY_LAMBDA)
    home_xg = _weighted_first(
        features,
        (
            ("home_team_global_pseudo_xg_for_avg_last10", 0.50),
            ("home_team_global_pseudo_xg_avg_last10", 0.30),
            ("home_team_pseudo_xg_for_avg_last10", 0.20),
        ),
    )
    away_xg = _weighted_first(
        features,
        (
            ("away_team_global_pseudo_xg_for_avg_last10", 0.50),
            ("away_team_global_pseudo_xg_avg_last10", 0.30),
            ("away_team_pseudo_xg_for_avg_last10", 0.20),
        ),
    )
    if home_xg is not None:
        home_lambda = 0.70 * home_lambda + 0.30 * home_xg
    if away_xg is not None:
        away_lambda = 0.70 * away_lambda + 0.30 * away_xg

    home_lambda += 0.10
    home_lambda -= 0.10 * (_numeric(features.get("home_team_absence_impact_score"), 0.0) or 0.0)
    away_lambda -= 0.10 * (_numeric(features.get("away_team_absence_impact_score"), 0.0) or 0.0)
    return _bound_lambda(home_lambda, DEFAULT_HOME_LAMBDA), _bound_lambda(
        away_lambda,
        DEFAULT_AWAY_LAMBDA,
    )


def poisson_v2_predict(features: JsonRow) -> list[float]:
    home_lambda, away_lambda = estimate_lambda_home_away_v2(features)
    return poisson_v2_probabilities(home_lambda, away_lambda).to_vector()


def poisson_v2_probabilities(
    home_lambda: float,
    away_lambda: float,
    *,
    max_goals: int = MAX_GOALS_V2,
    low_score_rho: float = -0.08,
) -> ProbabilityTriple:
    """Convert lambdas to 1X2 probabilities with a light Dixon-Coles style correction."""
    home_lambda = _bound_lambda(home_lambda, DEFAULT_HOME_LAMBDA)
    away_lambda = _bound_lambda(away_lambda, DEFAULT_AWAY_LAMBDA)
    p_home = 0.0
    p_draw = 0.0
    p_away = 0.0
    total = 0.0
    for home_goals in range(max_goals + 1):
        for away_goals in range(max_goals + 1):
            probability = (
                _poisson_pmf(home_goals, home_lambda)
                * _poisson_pmf(away_goals, away_lambda)
                * _low_score_adjustment(
                    home_goals,
                    away_goals,
                    home_lambda,
                    away_lambda,
                    low_score_rho,
                )
            )
            probability = max(probability, 0.0)
            total += probability
            if home_goals > away_goals:
                p_home += probability
            elif home_goals == away_goals:
                p_draw += probability
            else:
                p_away += probability
    if total > 0:
        p_home /= total
        p_draw /= total
        p_away /= total
    return ProbabilityTriple(p_home, p_draw, p_away).normalized()


def _low_score_adjustment(
    home_goals: int,
    away_goals: int,
    home_lambda: float,
    away_lambda: float,
    rho: float,
) -> float:
    if home_goals == 0 and away_goals == 0:
        return 1 - home_lambda * away_lambda * rho
    if home_goals == 0 and away_goals == 1:
        return 1 + home_lambda * rho
    if home_goals == 1 and away_goals == 0:
        return 1 + away_lambda * rho
    if home_goals == 1 and away_goals == 1:
        return 1 - rho
    return 1.0


def _weighted_first(row: JsonRow, keys: tuple[tuple[str, float], ...]) -> float | None:
    values: list[tuple[float, float]] = []
    for key, weight in keys:
        value = row.get(key)
        numeric = _numeric(value)
        if numeric is not None:
            values.append((numeric, weight))
    if not values:
        return None
    total_weight = sum(weight for _, weight in values)
    return sum(value * weight for value, weight in values) / total_weight


def _numeric(value: Any, default: float | None = None) -> float | None:
    if value is None:
        return default
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return default
    return numeric if math.isfinite(numeric) else default


def _mean_or_default(left: float | None, right: float | None, default: float) -> float:
    values = [value for value in (left, right) if value is not None]
    return default if not values else sum(values) / len(values)


def _bound_lambda(value: float, default: float) -> float:
    if not math.isfinite(value) or value <= 0:
        return default
    return min(max(value, 0.05), 5.5)
