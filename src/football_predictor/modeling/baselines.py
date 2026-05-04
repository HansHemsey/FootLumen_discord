"""Baseline probability sources for 1X2 prediction."""

from __future__ import annotations

import math
from collections.abc import Mapping
from typing import Any

from football_predictor.modeling.constants import CLASSES, DEFAULT_PRIOR
from football_predictor.modeling.probabilities import ProbabilityTriple

JsonRow = Mapping[str, Any]


def fallback_prior() -> ProbabilityTriple:
    return ProbabilityTriple.conservative_prior()


def uniform_predict() -> list[float]:
    return [1.0 / len(CLASSES)] * len(CLASSES)


def odds_only_predict(
    features: JsonRow,
    *,
    prior: list[float] | tuple[float, float, float] | None = None,
) -> list[float]:
    probability = _triple_from_keys(features, ("p_market_home", "p_market_draw", "p_market_away"))
    if probability is None:
        probability = _triple_from_keys(features, ("market_home", "market_draw", "market_away"))
    if probability is None:
        probability = ProbabilityTriple.from_vector(prior or DEFAULT_PRIOR)
    return probability.to_vector()


def odds_only_probability(row: JsonRow) -> ProbabilityTriple:
    """Read market probabilities from a feature row, or return the conservative prior."""
    for keys in (
        ("market_home", "market_draw", "market_away"),
        ("p_market_home", "p_market_draw", "p_market_away"),
    ):
        probability = _triple_from_keys(row, keys)
        if probability is not None:
            return probability
    return fallback_prior()


def api_prediction_predict(features: JsonRow) -> list[float] | None:
    probability = api_prediction_probability(features)
    return None if probability is None else probability.to_vector()


def api_prediction_probability(row: JsonRow) -> ProbabilityTriple | None:
    """Read API-Football prediction probabilities when available."""
    return _triple_from_keys(row, ("api_pred_home", "api_pred_draw", "api_pred_away"))


def _triple_from_keys(row: JsonRow, keys: tuple[str, str, str]) -> ProbabilityTriple | None:
    values: list[float] = []
    for key in keys:
        value = row.get(key)
        if value is None:
            return None
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            return None
        if not math.isfinite(numeric) or numeric < 0:
            return None
        values.append(numeric)
    try:
        return ProbabilityTriple(values[0], values[1], values[2]).normalized()
    except ValueError:
        return None
