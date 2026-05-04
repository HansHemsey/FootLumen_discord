"""Configurable probability stacking."""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from football_predictor.modeling.constants import CLASSES
from football_predictor.modeling.probabilities import ProbabilityTriple


@dataclass(frozen=True)
class StackingWeights:
    sport: float = 0.55
    market: float = 0.35
    api: float = 0.10


@dataclass(frozen=True)
class StackingResult:
    probabilities: ProbabilityTriple
    normalized_weights: dict[str, float]
    sources_used: list[str]


def stack_probabilities(
    *,
    sport: ProbabilityTriple | None,
    market: ProbabilityTriple | None,
    api: ProbabilityTriple | None,
    weights: StackingWeights = StackingWeights(),
) -> ProbabilityTriple:
    return ProbabilityTriple.from_vector(
        blend_probabilities(
            p_sport=sport,
            p_market=market,
            p_api=api,
            weights=weights,
        )
    )


def blend_probabilities(
    p_sport: ProbabilityTriple | Sequence[float] | Mapping[str, Any] | None,
    p_market: ProbabilityTriple | Sequence[float] | Mapping[str, Any] | None,
    p_api: ProbabilityTriple | Sequence[float] | Mapping[str, Any] | None,
    weights: StackingWeights | Mapping[str, float] = StackingWeights(),
) -> list[float]:
    """Blend sources through weighted log probabilities and softmax normalization."""
    details = stack_probabilities_with_details(
        sport=_coerce_probability(p_sport),
        market=_coerce_probability(p_market),
        api=_coerce_probability(p_api),
        weights=_coerce_weights(weights),
    )
    return details.probabilities.to_vector()


def stack_probabilities_with_details(
    *,
    sport: ProbabilityTriple | None,
    market: ProbabilityTriple | None,
    api: ProbabilityTriple | None,
    weights: StackingWeights = StackingWeights(),
) -> StackingResult:
    return _stack_with_log_softmax(
        sport=sport,
        market=market,
        api=api,
        weights=weights,
    )


def _stack_with_log_softmax(
    *,
    sport: ProbabilityTriple | None,
    market: ProbabilityTriple | None,
    api: ProbabilityTriple | None,
    weights: StackingWeights,
) -> StackingResult:
    available: list[tuple[str, ProbabilityTriple, float]] = []
    if sport is not None:
        available.append(("sport", sport.normalized(), weights.sport))
    if market is not None:
        available.append(("market", market.normalized(), weights.market))
    if api is not None:
        available.append(("api", api.normalized(), weights.api))
    if not available:
        return StackingResult(
            probabilities=ProbabilityTriple.conservative_prior(),
            normalized_weights={},
            sources_used=[],
        )

    total_weight = sum(weight for _, _, weight in available)
    if total_weight <= 0:
        normalized_weight = 1.0 / len(available)
        normalized_weights = {source: normalized_weight for source, _, _ in available}
    else:
        normalized_weights = {
            source: weight / total_weight for source, _, weight in available
        }
    blended_logits = []
    for index in range(len(CLASSES)):
        blended_logits.append(
            sum(
                normalized_weights[source] * math.log(max(prob.to_vector()[index], 1e-12))
                for source, prob, _ in available
            )
        )
    probabilities = ProbabilityTriple.from_vector(_softmax(blended_logits))
    return StackingResult(
        probabilities=probabilities,
        normalized_weights=normalized_weights,
        sources_used=list(normalized_weights),
    )


def _coerce_probability(
    value: ProbabilityTriple | Sequence[float] | Mapping[str, Any] | None,
) -> ProbabilityTriple | None:
    if value is None:
        return None
    if isinstance(value, ProbabilityTriple):
        return value.normalized()
    if isinstance(value, Mapping):
        return ProbabilityTriple.from_mapping(value)
    return ProbabilityTriple.from_vector([float(item) for item in value])


def _coerce_weights(weights: StackingWeights | Mapping[str, float]) -> StackingWeights:
    if isinstance(weights, StackingWeights):
        return weights
    return StackingWeights(
        sport=float(weights.get("sport", StackingWeights.sport)),
        market=float(weights.get("market", StackingWeights.market)),
        api=float(weights.get("api", StackingWeights.api)),
    )


def _softmax(values: Sequence[float]) -> list[float]:
    maximum = max(values)
    exps = [math.exp(value - maximum) for value in values]
    total = sum(exps)
    return [value / total for value in exps]
