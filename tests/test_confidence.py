from __future__ import annotations

import pytest

from football_predictor.features.data_quality import DataQuality
from football_predictor.modeling.probabilities import ProbabilityTriple
from football_predictor.prediction.confidence import (
    confidence_gap,
    confidence_label,
    confidence_score,
)


def test_confidence_gap_is_max_minus_second_best() -> None:
    assert confidence_gap(ProbabilityTriple(0.60, 0.25, 0.15)) == pytest.approx(0.35)


def test_confidence_label_marks_weak_probability_or_gap_uncertain() -> None:
    assert confidence_label(ProbabilityTriple(0.42, 0.31, 0.27)) == "Uncertain"
    assert confidence_label(ProbabilityTriple(0.45, 0.40, 0.15)) == "Uncertain"


def test_confidence_label_supports_full_scale() -> None:
    assert confidence_label(ProbabilityTriple(0.72, 0.18, 0.10)) == "Very High"
    assert confidence_label(ProbabilityTriple(0.60, 0.24, 0.16)) == "High"
    assert confidence_label(ProbabilityTriple(0.52, 0.30, 0.18)) == "Medium"
    assert confidence_label(ProbabilityTriple(0.46, 0.34, 0.20)) == "Low"


def test_confidence_score_stays_bounded() -> None:
    score = confidence_score(ProbabilityTriple(0.60, 0.25, 0.15), DataQuality(odds_available=True))

    assert 0 <= score <= 100
