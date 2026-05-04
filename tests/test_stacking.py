from __future__ import annotations

import pytest

from football_predictor.modeling.stacking import (
    StackingWeights,
    blend_probabilities,
    stack_probabilities_with_details,
)


def test_blend_probabilities_uses_fixed_class_order_and_normalizes() -> None:
    probabilities = blend_probabilities(
        p_sport=[0.60, 0.25, 0.15],
        p_market=[0.50, 0.30, 0.20],
        p_api=[0.45, 0.30, 0.25],
        weights=StackingWeights(),
    )

    assert len(probabilities) == 3
    assert sum(probabilities) == pytest.approx(1.0)
    assert probabilities[0] > probabilities[2]


def test_blend_probabilities_redistributes_missing_sources() -> None:
    details = stack_probabilities_with_details(
        sport=None,
        market=None,
        api=None,
    )
    probabilities = blend_probabilities(
        p_sport=[0.70, 0.20, 0.10],
        p_market=None,
        p_api=[0.40, 0.30, 0.30],
        weights={"sport": 0.55, "market": 0.35, "api": 0.10},
    )

    assert details.sources_used == []
    assert sum(details.probabilities.to_vector()) == pytest.approx(1.0)
    assert sum(probabilities) == pytest.approx(1.0)
    assert probabilities[0] > probabilities[1]
