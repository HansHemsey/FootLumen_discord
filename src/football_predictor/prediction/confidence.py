"""Confidence scoring for probabilistic outputs."""

from __future__ import annotations

from collections.abc import Sequence

from football_predictor.features.data_quality import DataQuality
from football_predictor.modeling.probabilities import ProbabilityTriple


def confidence_gap(probabilities: ProbabilityTriple | Sequence[float]) -> float:
    """Return p_max - p_second for HOME/DRAW/AWAY probabilities."""
    values = (
        probabilities.to_vector()
        if isinstance(probabilities, ProbabilityTriple)
        else [float(value) for value in probabilities]
    )
    if len(values) < 2:
        raise ValueError("At least two probabilities are required")
    ordered = sorted(values, reverse=True)
    return ordered[0] - ordered[1]


def confidence_score(probabilities: ProbabilityTriple, data_quality: DataQuality) -> float:
    edge = confidence_gap(probabilities)
    quality_factor = data_quality.score() / 100
    max_probability = probabilities.max_probability()
    probability_factor = max(0.0, max_probability - (1 / 3))
    raw_score = (edge * 120) + (probability_factor * 70) + (quality_factor * 25)
    return round(max(0.0, min(100.0, raw_score)), 1)


def confidence_label(
    value: float | ProbabilityTriple | Sequence[float],
    *,
    gap: float | None = None,
) -> str:
    """Return a human label with an explicit uncertain zone for weak edges."""
    if isinstance(value, ProbabilityTriple) or not isinstance(value, int | float):
        probabilities = (
            value if isinstance(value, ProbabilityTriple) else ProbabilityTriple.from_vector(value)
        )
        p_max = probabilities.max_probability()
        resolved_gap = confidence_gap(probabilities) if gap is None else gap
        if p_max < 0.43 or resolved_gap < 0.07:
            return "Uncertain"
        if p_max >= 0.68 and resolved_gap >= 0.22:
            return "Very High"
        if p_max >= 0.58 and resolved_gap >= 0.16:
            return "High"
        if p_max >= 0.50 and resolved_gap >= 0.11:
            return "Medium"
        return "Low"

    score = float(value)
    if score >= 85:
        return "Very High"
    if score >= 65:
        return "High"
    if score >= 45:
        return "Medium"
    if score >= 20:
        return "Low"
    return "Uncertain"
