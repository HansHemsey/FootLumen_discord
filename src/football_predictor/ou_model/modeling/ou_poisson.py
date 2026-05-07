"""Dixon-Coles Poisson model for Over/Under 2.5 prediction.

Reuses estimate_lambda_home_away_v2() from poisson_v2.py — no duplication.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from football_predictor.modeling.poisson import _poisson_pmf
from football_predictor.modeling.poisson_v2 import (
    _low_score_adjustment,
    estimate_lambda_home_away_v2,
)
from football_predictor.ou_model.constants import (
    DEFAULT_AWAY_LAMBDA,
    DEFAULT_HOME_LAMBDA,
    OU_THRESHOLD,
)

JsonRow = Mapping[str, Any]

MAX_GOALS = 12
DEFAULT_RHO = -0.08


def ou_poisson_probability(
    home_lambda: float,
    away_lambda: float,
    threshold: float = OU_THRESHOLD,
    *,
    max_goals: int = MAX_GOALS,
    low_score_rho: float = DEFAULT_RHO,
) -> tuple[float, float]:
    """Compute P(Over threshold) and P(Under threshold) via Dixon-Coles Poisson.

    Returns (p_over, p_under) using the joint goals distribution with
    Dixon-Coles low-score correction (same rho=-0.08 as the 1X2 model).
    """
    p_over = 0.0
    total = 0.0
    for h in range(max_goals + 1):
        for a in range(max_goals + 1):
            prob = (
                _poisson_pmf(h, home_lambda)
                * _poisson_pmf(a, away_lambda)
                * _low_score_adjustment(h, a, home_lambda, away_lambda, low_score_rho)
            )
            prob = max(prob, 0.0)
            total += prob
            if h + a > threshold:
                p_over += prob
    if total > 0:
        p_over /= total
    p_under = 1.0 - p_over
    return p_over, p_under


def poisson_ou_predict(features: JsonRow, threshold: float = OU_THRESHOLD) -> tuple[float, float]:
    """High-level helper: extract lambdas from features, return (p_over, p_under)."""
    home_lambda, away_lambda = estimate_lambda_home_away_v2(features)
    return ou_poisson_probability(home_lambda, away_lambda, threshold)


def extract_lambdas(features: JsonRow) -> tuple[float, float]:
    """Return (home_lambda, away_lambda) from feature row."""
    return estimate_lambda_home_away_v2(features)
