from __future__ import annotations

import pytest

from football_predictor.modeling.probabilities import ProbabilityTriple
from football_predictor.modeling.stacking import stack_probabilities


def test_stacking_renormalizes_available_sources() -> None:
    probabilities = stack_probabilities(
        sport=ProbabilityTriple(0.5, 0.25, 0.25),
        market=None,
        api=ProbabilityTriple(0.2, 0.3, 0.5),
    )

    assert sum(probabilities.as_dict().values()) == pytest.approx(1.0)
    assert probabilities.predicted_result() in {"HOME", "DRAW", "AWAY"}
