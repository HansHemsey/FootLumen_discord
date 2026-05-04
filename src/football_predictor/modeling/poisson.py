"""Simple independent Poisson 1X2 baseline."""

from __future__ import annotations

import math
from collections.abc import Mapping
from typing import Any

from football_predictor.modeling.probabilities import ProbabilityTriple

JsonRow = Mapping[str, Any]

DEFAULT_HOME_LAMBDA = 1.35
DEFAULT_AWAY_LAMBDA = 1.10
MAX_GOALS = 10
V1_SCORE_MATRIX_MAX_GOALS = 8


def estimate_lambda_home_away(features: JsonRow) -> tuple[float, float]:
    """Heuristic expected goals with form, pseudo-xG and a small home advantage."""
    home_goals = _mean_or_default(
        _first_numeric(
            features,
            (
                "home_team_global_goals_for_avg_last10",
                "home_team_global_goals_for_avg_last5",
                "home_team_home_goals_for_avg_last10",
                "home_team_home_goals_for_avg_last5",
            ),
        ),
        _first_numeric(
            features,
            (
                "away_team_global_goals_against_avg_last10",
                "away_team_global_goals_against_avg_last5",
                "away_team_away_goals_against_avg_last10",
                "away_team_away_goals_against_avg_last5",
            ),
        ),
        DEFAULT_HOME_LAMBDA,
    )
    away_goals = _mean_or_default(
        _first_numeric(
            features,
            (
                "away_team_global_goals_for_avg_last10",
                "away_team_global_goals_for_avg_last5",
                "away_team_away_goals_for_avg_last10",
                "away_team_away_goals_for_avg_last5",
            ),
        ),
        _first_numeric(
            features,
            (
                "home_team_global_goals_against_avg_last10",
                "home_team_global_goals_against_avg_last5",
                "home_team_home_goals_against_avg_last10",
                "home_team_home_goals_against_avg_last5",
            ),
        ),
        DEFAULT_AWAY_LAMBDA,
    )
    home_xg = _first_numeric(
        features,
        ("home_team_global_pseudo_xg_avg_last10", "home_team_pseudo_xg_for_avg_last10"),
    )
    away_xg = _first_numeric(
        features,
        ("away_team_global_pseudo_xg_avg_last10", "away_team_pseudo_xg_for_avg_last10"),
    )
    if home_xg is not None:
        home_goals = 0.75 * home_goals + 0.25 * home_xg
    if away_xg is not None:
        away_goals = 0.75 * away_goals + 0.25 * away_xg
    return _bound_lambda(home_goals + 0.10, DEFAULT_HOME_LAMBDA), _bound_lambda(
        away_goals,
        DEFAULT_AWAY_LAMBDA,
    )


def score_matrix(
    home_lambda: float,
    away_lambda: float,
    *,
    max_goals: int = V1_SCORE_MATRIX_MAX_GOALS,
) -> list[list[float]]:
    home_lambda = _bound_lambda(home_lambda, DEFAULT_HOME_LAMBDA)
    away_lambda = _bound_lambda(away_lambda, DEFAULT_AWAY_LAMBDA)
    return [
        [
            _poisson_pmf(home_goals, home_lambda) * _poisson_pmf(away_goals, away_lambda)
            for away_goals in range(max_goals + 1)
        ]
        for home_goals in range(max_goals + 1)
    ]


def poisson_predict(features: JsonRow) -> list[float]:
    home_lambda, away_lambda = estimate_lambda_home_away(features)
    return poisson_probabilities(
        home_lambda,
        away_lambda,
        max_goals=V1_SCORE_MATRIX_MAX_GOALS,
    ).to_vector()


def poisson_baseline_probability(row: JsonRow, max_goals: int = MAX_GOALS) -> ProbabilityTriple:
    """Estimate HOME/DRAW/AWAY from expected goals derived from feature means."""
    home_lambda, away_lambda = estimate_lambda_home_away(row)
    return poisson_probabilities(home_lambda, away_lambda, max_goals=max_goals)


def poisson_probabilities(
    home_lambda: float,
    away_lambda: float,
    *,
    max_goals: int = MAX_GOALS,
) -> ProbabilityTriple:
    home_lambda = _bound_lambda(home_lambda, DEFAULT_HOME_LAMBDA)
    away_lambda = _bound_lambda(away_lambda, DEFAULT_AWAY_LAMBDA)
    home_probs = [_poisson_pmf(goal, home_lambda) for goal in range(max_goals + 1)]
    away_probs = [_poisson_pmf(goal, away_lambda) for goal in range(max_goals + 1)]
    p_home = 0.0
    p_draw = 0.0
    p_away = 0.0
    for home_goals, home_prob in enumerate(home_probs):
        for away_goals, away_prob in enumerate(away_probs):
            probability = home_prob * away_prob
            if home_goals > away_goals:
                p_home += probability
            elif home_goals == away_goals:
                p_draw += probability
            else:
                p_away += probability
    return ProbabilityTriple(p_home, p_draw, p_away).normalized()


def _expected_home_goals(row: JsonRow) -> float:
    attacking = _first_numeric(
        row,
        (
            "home_team_global_goals_for_avg_last10",
            "home_team_global_goals_for_avg_last5",
            "home_team_home_goals_for_avg_last10",
            "home_team_home_goals_for_avg_last5",
        ),
    )
    defending = _first_numeric(
        row,
        (
            "away_team_global_goals_against_avg_last10",
            "away_team_global_goals_against_avg_last5",
            "away_team_away_goals_against_avg_last10",
            "away_team_away_goals_against_avg_last5",
        ),
    )
    return _mean_or_default(attacking, defending, DEFAULT_HOME_LAMBDA)


def _expected_away_goals(row: JsonRow) -> float:
    attacking = _first_numeric(
        row,
        (
            "away_team_global_goals_for_avg_last10",
            "away_team_global_goals_for_avg_last5",
            "away_team_away_goals_for_avg_last10",
            "away_team_away_goals_for_avg_last5",
        ),
    )
    defending = _first_numeric(
        row,
        (
            "home_team_global_goals_against_avg_last10",
            "home_team_global_goals_against_avg_last5",
            "home_team_home_goals_against_avg_last10",
            "home_team_home_goals_against_avg_last5",
        ),
    )
    return _mean_or_default(attacking, defending, DEFAULT_AWAY_LAMBDA)


def _first_numeric(row: JsonRow, keys: tuple[str, ...]) -> float | None:
    for key in keys:
        value = row.get(key)
        if value is None:
            continue
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            continue
        if math.isfinite(numeric):
            return numeric
    return None


def _mean_or_default(left: float | None, right: float | None, default: float) -> float:
    values = [value for value in (left, right) if value is not None]
    if not values:
        return default
    return sum(values) / len(values)


def _bound_lambda(value: float, default: float) -> float:
    if not math.isfinite(value) or value <= 0:
        return default
    return min(max(value, 0.05), 5.0)


def _poisson_pmf(k: int, lambda_value: float) -> float:
    return math.exp(-lambda_value) * lambda_value**k / math.factorial(k)
