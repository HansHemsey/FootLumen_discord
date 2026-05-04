from __future__ import annotations

import pytest

from football_predictor.backtesting.metrics import (
    accuracy_score_1x2,
    calibration_bins,
    confidence_gap,
    log_loss_safe,
    multiclass_brier_score,
)

CLASSES = ["HOME", "DRAW", "AWAY"]


def test_log_loss_safe_is_stable_with_extreme_probabilities() -> None:
    loss = log_loss_safe(["HOME", "AWAY"], [[1.0, 0.0, 0.0], [0.0, 0.0, 1.0]], CLASSES)

    assert loss >= 0.0
    assert loss < 1e-6


def test_brier_score_is_bounded_for_multiclass() -> None:
    perfect = multiclass_brier_score(["HOME"], [[1.0, 0.0, 0.0]], CLASSES)
    wrong = multiclass_brier_score(["HOME"], [[0.0, 0.0, 1.0]], CLASSES)

    assert perfect == pytest.approx(0.0)
    assert 0.0 <= wrong <= 2.0


def test_accuracy_score_1x2_uses_probability_argmax() -> None:
    accuracy = accuracy_score_1x2(
        ["HOME", "DRAW", "AWAY"],
        [[0.7, 0.2, 0.1], [0.1, 0.8, 0.1], [0.4, 0.5, 0.1]],
        CLASSES,
    )

    assert accuracy == pytest.approx(2 / 3)


def test_confidence_gap_is_top_probability_minus_second_best() -> None:
    assert confidence_gap([0.55, 0.30, 0.15]) == pytest.approx(0.25)


def test_calibration_bins_return_counts_and_accuracy() -> None:
    bins = calibration_bins(
        ["HOME", "DRAW", "AWAY"],
        [[0.7, 0.2, 0.1], [0.1, 0.8, 0.1], [0.4, 0.5, 0.1]],
        CLASSES,
        n_bins=5,
    )

    assert len(bins) == 5
    assert sum(int(item["count"] or 0) for item in bins) == 3
    assert any(item["accuracy"] is not None for item in bins)
