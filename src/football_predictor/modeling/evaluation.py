"""Evaluation metrics for 1X2 probability models."""

from __future__ import annotations

import math
from collections.abc import Sequence
from typing import Any

from sklearn.metrics import accuracy_score, confusion_matrix  # type: ignore[import-untyped]

from football_predictor.modeling.probabilities import VALID_RESULTS, ProbabilityTriple


def evaluate_probabilities(
    y_true: Sequence[str],
    predictions: Sequence[ProbabilityTriple],
    *,
    calibration_bins: int = 10,
) -> dict[str, Any]:
    if len(y_true) != len(predictions):
        raise ValueError("y_true and predictions must have the same length")
    if not y_true:
        return {
            "row_count": 0,
            "accuracy": None,
            "log_loss": None,
            "brier_score": None,
            "confusion_matrix": [],
            "calibration_bins": [],
        }
    invalid = set(y_true).difference(VALID_RESULTS)
    if invalid:
        raise ValueError(f"Unknown labels: {sorted(invalid)}")

    predicted_labels = [prediction.predicted_result() for prediction in predictions]
    return {
        "row_count": len(y_true),
        "accuracy": float(accuracy_score(y_true, predicted_labels)),
        "log_loss": float(_log_loss_multiclass(y_true, predictions)),
        "brier_score": float(_brier_score_multiclass(y_true, predictions)),
        "confusion_matrix": confusion_matrix(
            y_true,
            predicted_labels,
            labels=list(VALID_RESULTS),
        ).tolist(),
        "calibration_bins": _calibration_bins(y_true, predictions, n_bins=calibration_bins),
    }


def _log_loss_multiclass(
    y_true: Sequence[str],
    predictions: Sequence[ProbabilityTriple],
    *,
    epsilon: float = 1e-15,
) -> float:
    total = 0.0
    for actual, prediction in zip(y_true, predictions, strict=True):
        probability = prediction.as_dict()[actual]
        total += -math.log(min(max(probability, epsilon), 1 - epsilon))
    return total / len(y_true)


def _brier_score_multiclass(
    y_true: Sequence[str],
    predictions: Sequence[ProbabilityTriple],
) -> float:
    total = 0.0
    for actual, prediction in zip(y_true, predictions, strict=True):
        values = prediction.as_dict()
        total += sum(
            (values[label] - (1.0 if label == actual else 0.0)) ** 2
            for label in VALID_RESULTS
        )
    return total / len(y_true)


def _calibration_bins(
    y_true: Sequence[str],
    predictions: Sequence[ProbabilityTriple],
    *,
    n_bins: int,
) -> list[dict[str, float | int | None]]:
    bins: list[list[tuple[float, bool]]] = [[] for _ in range(n_bins)]
    for actual, prediction in zip(y_true, predictions, strict=True):
        confidence = prediction.max_probability()
        predicted = prediction.predicted_result()
        index = min(int(confidence * n_bins), n_bins - 1)
        bins[index].append((confidence, predicted == actual))

    output: list[dict[str, float | int | None]] = []
    for index, rows in enumerate(bins):
        lower = index / n_bins
        upper = (index + 1) / n_bins
        if not rows:
            output.append(
                {
                    "bin": index,
                    "lower": lower,
                    "upper": upper,
                    "count": 0,
                    "avg_confidence": None,
                    "accuracy": None,
                }
            )
            continue
        output.append(
            {
                "bin": index,
                "lower": lower,
                "upper": upper,
                "count": len(rows),
                "avg_confidence": sum(confidence for confidence, _ in rows) / len(rows),
                "accuracy": sum(1.0 for _, correct in rows if correct) / len(rows),
            }
        )
    return output
