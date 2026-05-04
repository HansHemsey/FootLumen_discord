"""Probability primitives for HOME/DRAW/AWAY outputs."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from football_predictor.modeling.constants import CLASSES

VALID_RESULTS = tuple(CLASSES)
RESULT_INDEX = {label: index for index, label in enumerate(VALID_RESULTS)}

_MAPPING_ALIASES = {
    "HOME": ("HOME", "home", "p_home", "market_home", "api_pred_home"),
    "DRAW": ("DRAW", "draw", "p_draw", "market_draw", "api_pred_draw"),
    "AWAY": ("AWAY", "away", "p_away", "market_away", "api_pred_away"),
}


@dataclass(frozen=True)
class ProbabilityTriple:
    p_home: float
    p_draw: float
    p_away: float

    def __post_init__(self) -> None:
        values = (self.p_home, self.p_draw, self.p_away)
        if any(value < 0 for value in values):
            raise ValueError("Probabilities must be non-negative")
        total = sum(values)
        if total <= 0:
            raise ValueError("At least one probability must be positive")

    def normalized(self) -> ProbabilityTriple:
        total = self.p_home + self.p_draw + self.p_away
        return ProbabilityTriple(
            p_home=self.p_home / total,
            p_draw=self.p_draw / total,
            p_away=self.p_away / total,
        )

    def as_dict(self) -> dict[str, float]:
        normalized = self.normalized()
        return {
            "HOME": normalized.p_home,
            "DRAW": normalized.p_draw,
            "AWAY": normalized.p_away,
        }

    def to_vector(self, labels: Sequence[str] = VALID_RESULTS) -> list[float]:
        values = self.as_dict()
        return [values[label] for label in labels]

    def predicted_result(self) -> str:
        values = self.as_dict()
        return max(values, key=lambda label: values[label])

    def max_probability(self) -> float:
        values = self.as_dict()
        return max(values.values())

    @classmethod
    def uniform(cls) -> ProbabilityTriple:
        return cls(1 / 3, 1 / 3, 1 / 3)

    @classmethod
    def conservative_prior(cls) -> ProbabilityTriple:
        """Default low-confidence prior used only when stronger sources are absent."""
        return cls(0.43, 0.27, 0.30).normalized()

    @classmethod
    def from_mapping(cls, mapping: Mapping[str, Any]) -> ProbabilityTriple:
        values: dict[str, float] = {}
        for label, aliases in _MAPPING_ALIASES.items():
            value = _first_numeric(mapping, aliases)
            if value is None:
                raise ValueError(f"Missing probability for {label}")
            values[label] = value
        return cls(values["HOME"], values["DRAW"], values["AWAY"]).normalized()

    @classmethod
    def from_vector(
        cls,
        values: Sequence[float],
        labels: Sequence[str] = VALID_RESULTS,
    ) -> ProbabilityTriple:
        if len(values) != len(labels):
            raise ValueError("values and labels must have the same length")
        mapped = dict(zip(labels, values, strict=True))
        return cls(
            float(mapped.get("HOME", 0.0)),
            float(mapped.get("DRAW", 0.0)),
            float(mapped.get("AWAY", 0.0)),
        ).normalized()


def _first_numeric(mapping: Mapping[str, Any], aliases: Sequence[str]) -> float | None:
    for alias in aliases:
        if alias not in mapping:
            continue
        value = mapping[alias]
        if value is None:
            continue
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            continue
        if numeric < 0:
            continue
        return numeric
    return None
