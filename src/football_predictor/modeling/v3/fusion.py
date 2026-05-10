"""Deterministic V3 probability fusion helpers."""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from football_predictor.modeling.constants import CLASSES
from football_predictor.modeling.probabilities import ProbabilityTriple

JsonRow = Mapping[str, Any]


@dataclass(frozen=True)
class V3FusionWeights:
    """Weights used by the deterministic V3 fallback fusion."""

    v3: float = 0.60
    v2: float = 0.30
    market: float = 0.10
    extras: dict[str, float] = field(default_factory=dict)

    def as_dict(self) -> dict[str, float]:
        return {"v3": self.v3, "v2": self.v2, "market": self.market, **self.extras}


def v3_component_probability(
    draw_probability: float,
    home_no_draw_probability: float,
) -> ProbabilityTriple:
    """Compose Draw Risk and No-Draw Winner into a raw 1X2 V3 probability."""
    p_draw = _clip_probability(draw_probability)
    p_home_no_draw = _clip_probability(home_no_draw_probability)
    no_draw_mass = 1.0 - p_draw
    return ProbabilityTriple(
        p_home=no_draw_mass * p_home_no_draw,
        p_draw=p_draw,
        p_away=no_draw_mass * (1.0 - p_home_no_draw),
    ).normalized()


def deterministic_v3_fusion(
    *,
    draw_probability: float,
    home_no_draw_probability: float,
    v2_probability: ProbabilityTriple | Sequence[float] | None = None,
    market_probability: ProbabilityTriple | Sequence[float] | None = None,
    weights: V3FusionWeights | None = None,
) -> ProbabilityTriple:
    """Blend V3 component probabilities with optional V2 and market sources."""
    resolved_weights = weights or V3FusionWeights()
    sources: list[tuple[ProbabilityTriple, float]] = [
        (
            v3_component_probability(draw_probability, home_no_draw_probability),
            resolved_weights.v3,
        )
    ]
    v2 = probability_triple_or_none(v2_probability)
    if v2 is not None:
        sources.append((v2, resolved_weights.v2))
    market = probability_triple_or_none(market_probability)
    if market is not None:
        sources.append((market, resolved_weights.market))

    weighted = [(probability, weight) for probability, weight in sources if weight > 0]
    if not weighted:
        return ProbabilityTriple.conservative_prior()
    total_weight = sum(weight for _probability, weight in weighted)
    values = {label: 0.0 for label in CLASSES}
    for probability, weight in weighted:
        for label, value in probability.as_dict().items():
            values[label] += (weight / total_weight) * value
    return ProbabilityTriple.from_mapping(values)


def probability_triple_or_none(
    value: ProbabilityTriple | Sequence[float] | None,
) -> ProbabilityTriple | None:
    if value is None:
        return None
    if isinstance(value, ProbabilityTriple):
        return value.normalized()
    try:
        return ProbabilityTriple.from_vector([float(item) for item in value])
    except Exception:
        return None


def market_probability_from_row(row: JsonRow) -> ProbabilityTriple | None:
    return _probability_from_row(
        row,
        (
            ("p_market_home", "p_market_draw", "p_market_away"),
            ("market_home", "market_draw", "market_away"),
        ),
    )


def api_probability_from_row(row: JsonRow) -> ProbabilityTriple | None:
    return _probability_from_row(
        row,
        (
            ("p_api_home", "p_api_draw", "p_api_away"),
            ("api_pred_home", "api_pred_draw", "api_pred_away"),
        ),
    )


def v2_probability_from_row(row: JsonRow) -> ProbabilityTriple | None:
    return _probability_from_row(row, (("p_v2_home", "p_v2_draw", "p_v2_away"),))


def _probability_from_row(
    row: JsonRow,
    key_groups: Sequence[tuple[str, str, str]],
) -> ProbabilityTriple | None:
    for keys in key_groups:
        values: list[float] = []
        for key in keys:
            value = row.get(key)
            if value is None:
                break
            try:
                numeric = float(value)
            except (TypeError, ValueError):
                break
            if not math.isfinite(numeric) or numeric < 0:
                break
            values.append(numeric)
        if len(values) == 3:
            try:
                return ProbabilityTriple.from_vector(values)
            except ValueError:
                continue
    return None


def _clip_probability(value: float) -> float:
    if not math.isfinite(float(value)):
        return 0.5
    return max(min(float(value), 1.0 - 1e-15), 1e-15)
