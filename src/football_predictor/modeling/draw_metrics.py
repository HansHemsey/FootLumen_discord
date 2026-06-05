"""DRAW-specific metrics for 1X2 probability models."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from football_predictor.modeling.constants import CLASSES
from football_predictor.modeling.probabilities import ProbabilityTriple

JsonDict = dict[str, Any]


def evaluate_draw_metrics(
    y_true: Sequence[str],
    predictions: Sequence[ProbabilityTriple],
    *,
    calibration_bins: int = 10,
) -> JsonDict:
    """Return explicit DRAW metrics without changing multiclass metrics."""
    if len(y_true) != len(predictions):
        raise ValueError("y_true and predictions must have the same length")
    if calibration_bins <= 0:
        raise ValueError("calibration_bins must be positive")

    row_count = len(y_true)
    if row_count == 0:
        return {
            "row_count": 0,
            "draw_precision": None,
            "draw_recall": None,
            "draw_f1": None,
            "observed_draw_rate": None,
            "mean_predicted_p_draw": None,
            "draw_calibration_bins": [],
            "draw_ece": None,
            "confusion_matrix_labeled": _empty_confusion_matrix(),
        }

    actual_draw = [str(label).upper() == "DRAW" for label in y_true]
    predicted_labels = [prediction.predicted_result() for prediction in predictions]
    predicted_draw = [label == "DRAW" for label in predicted_labels]
    p_draw = [prediction.as_dict()["DRAW"] for prediction in predictions]

    tp = sum(
        1
        for actual, predicted in zip(actual_draw, predicted_draw, strict=True)
        if actual and predicted
    )
    fp = sum(
        1
        for actual, predicted in zip(actual_draw, predicted_draw, strict=True)
        if not actual and predicted
    )
    fn = sum(
        1
        for actual, predicted in zip(actual_draw, predicted_draw, strict=True)
        if actual and not predicted
    )
    precision = _safe_divide(tp, tp + fp)
    recall = _safe_divide(tp, tp + fn)
    f1 = _safe_divide(2 * precision * recall, precision + recall)
    bins = _draw_calibration_bins(actual_draw, p_draw, n_bins=calibration_bins)

    return {
        "row_count": row_count,
        "draw_precision": precision,
        "draw_recall": recall,
        "draw_f1": f1,
        "observed_draw_rate": sum(1 for value in actual_draw if value) / row_count,
        "mean_predicted_p_draw": sum(p_draw) / row_count,
        "draw_calibration_bins": bins,
        "draw_ece": _draw_ece(bins, row_count=row_count),
        "confusion_matrix_labeled": _confusion_matrix_labeled(y_true, predicted_labels),
    }


def legacy_v3_draw_metrics(metrics: JsonDict) -> JsonDict:
    """Map shared draw metrics to the historical V3 nested key names."""
    return {
        "row_count": metrics.get("row_count"),
        "positive_rate": metrics.get("observed_draw_rate"),
        "precision": metrics.get("draw_precision"),
        "recall": metrics.get("draw_recall"),
        "f1": metrics.get("draw_f1"),
        "calibration_bins": metrics.get("draw_calibration_bins", []),
        "ece": metrics.get("draw_ece"),
    }


def _draw_calibration_bins(
    actual_draw: Sequence[bool],
    probabilities: Sequence[float],
    *,
    n_bins: int,
) -> list[JsonDict]:
    bins: list[list[tuple[float, int]]] = [[] for _ in range(n_bins)]
    for actual, probability in zip(actual_draw, probabilities, strict=True):
        clipped = max(0.0, min(float(probability), 1.0))
        index = min(int(clipped * n_bins), n_bins - 1)
        bins[index].append((clipped, int(actual)))

    output: list[JsonDict] = []
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
                    "avg_probability": None,
                    "event_rate": None,
                }
            )
            continue
        output.append(
            {
                "bin": index,
                "lower": lower,
                "upper": upper,
                "count": len(rows),
                "avg_probability": sum(probability for probability, _ in rows) / len(rows),
                "event_rate": sum(actual for _probability, actual in rows) / len(rows),
            }
        )
    return output


def _draw_ece(bins: Sequence[JsonDict], *, row_count: int) -> float | None:
    if row_count <= 0:
        return None
    ece = 0.0
    for item in bins:
        count = int(item.get("count") or 0)
        if count <= 0:
            continue
        avg_probability = item.get("avg_probability")
        event_rate = item.get("event_rate")
        if avg_probability is None or event_rate is None:
            continue
        ece += (count / row_count) * abs(float(avg_probability) - float(event_rate))
    return ece


def _confusion_matrix_labeled(
    y_true: Sequence[str],
    predicted_labels: Sequence[str],
) -> JsonDict:
    matrix = {actual: {predicted: 0 for predicted in CLASSES} for actual in CLASSES}
    for actual, predicted in zip(y_true, predicted_labels, strict=True):
        actual_key = str(actual).upper()
        predicted_key = str(predicted).upper()
        if actual_key in matrix and predicted_key in matrix[actual_key]:
            matrix[actual_key][predicted_key] += 1
    return {
        "labels": list(CLASSES),
        "matrix": [[matrix[actual][predicted] for predicted in CLASSES] for actual in CLASSES],
        "rows": [
            {"actual": actual, "predicted": dict(matrix[actual])}
            for actual in CLASSES
        ],
    }


def _empty_confusion_matrix() -> JsonDict:
    return {
        "labels": list(CLASSES),
        "matrix": [[0 for _predicted in CLASSES] for _actual in CLASSES],
        "rows": [
            {"actual": actual, "predicted": {predicted: 0 for predicted in CLASSES}}
            for actual in CLASSES
        ],
    }


def _safe_divide(numerator: float, denominator: float) -> float:
    return 0.0 if denominator <= 0 else numerator / denominator
