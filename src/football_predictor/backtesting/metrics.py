"""Core 1X2 metrics."""

from __future__ import annotations

import math
from collections.abc import Sequence

from football_predictor.modeling.probabilities import ProbabilityTriple


def multiclass_brier_score(
    y_true: Sequence[str],
    proba: Sequence[Sequence[float]],
    classes: Sequence[str],
) -> float:
    _validate_shapes(y_true, proba, classes)
    if not y_true:
        return 0.0
    class_index = {label: index for index, label in enumerate(classes)}
    total = 0.0
    for actual, probabilities in zip(y_true, proba, strict=True):
        if actual not in class_index:
            raise ValueError(f"Unknown actual result: {actual}")
        total += sum(
            (float(probability) - (1.0 if index == class_index[actual] else 0.0)) ** 2
            for index, probability in enumerate(probabilities)
        )
    return total / len(y_true)


def accuracy_score_1x2(
    y_true: Sequence[str],
    proba: Sequence[Sequence[float]],
    classes: Sequence[str] = ("HOME", "DRAW", "AWAY"),
) -> float:
    _validate_shapes(y_true, proba, classes)
    if not y_true:
        return 0.0
    correct = 0
    for actual, probabilities in zip(y_true, proba, strict=True):
        predicted = classes[_argmax(probabilities)]
        correct += int(predicted == actual)
    return correct / len(y_true)


def log_loss_safe(
    y_true: Sequence[str],
    proba: Sequence[Sequence[float]],
    classes: Sequence[str] = ("HOME", "DRAW", "AWAY"),
    epsilon: float = 1e-15,
) -> float:
    _validate_shapes(y_true, proba, classes)
    if not y_true:
        return 0.0
    class_index = {label: index for index, label in enumerate(classes)}
    total = 0.0
    for actual, probabilities in zip(y_true, proba, strict=True):
        if actual not in class_index:
            raise ValueError(f"Unknown actual result: {actual}")
        probability = float(probabilities[class_index[actual]])
        total += -math.log(min(max(probability, epsilon), 1 - epsilon))
    return total / len(y_true)


def confidence_gap(proba: Sequence[float]) -> float:
    if len(proba) < 2:
        raise ValueError("proba must contain at least two classes")
    ordered = sorted((float(value) for value in proba), reverse=True)
    return ordered[0] - ordered[1]


def calibration_bins(
    y_true: Sequence[str],
    proba: Sequence[Sequence[float]],
    classes: Sequence[str] = ("HOME", "DRAW", "AWAY"),
    n_bins: int = 10,
) -> list[dict[str, float | int | None]]:
    _validate_shapes(y_true, proba, classes)
    if n_bins <= 0:
        raise ValueError("n_bins must be positive")
    bins: list[list[tuple[float, bool]]] = [[] for _ in range(n_bins)]
    for actual, probabilities in zip(y_true, proba, strict=True):
        predicted_index = _argmax(probabilities)
        confidence = float(probabilities[predicted_index])
        predicted = classes[predicted_index]
        index = min(int(confidence * n_bins), n_bins - 1)
        bins[index].append((confidence, predicted == actual))

    output: list[dict[str, float | int | None]] = []
    for index, rows in enumerate(bins):
        if not rows:
            output.append(
                {
                    "bin": index,
                    "lower": index / n_bins,
                    "upper": (index + 1) / n_bins,
                    "count": 0,
                    "avg_confidence": None,
                    "accuracy": None,
                }
            )
            continue
        output.append(
            {
                "bin": index,
                "lower": index / n_bins,
                "upper": (index + 1) / n_bins,
                "count": len(rows),
                "avg_confidence": sum(confidence for confidence, _ in rows) / len(rows),
                "accuracy": sum(1.0 for _, correct in rows if correct) / len(rows),
            }
        )
    return output


def log_loss_one(prediction: ProbabilityTriple, actual: str, epsilon: float = 1e-15) -> float:
    probabilities = prediction.as_dict()
    if actual not in probabilities:
        raise ValueError(f"Unknown actual result: {actual}")
    probability = min(max(probabilities[actual], epsilon), 1 - epsilon)
    return -math.log(probability)


def brier_score_one(prediction: ProbabilityTriple, actual: str) -> float:
    probabilities = prediction.as_dict()
    if actual not in probabilities:
        raise ValueError(f"Unknown actual result: {actual}")
    return sum(
        (probabilities[label] - (1.0 if label == actual else 0.0)) ** 2 for label in probabilities
    )


def _validate_shapes(
    y_true: Sequence[str],
    proba: Sequence[Sequence[float]],
    classes: Sequence[str],
) -> None:
    if len(y_true) != len(proba):
        raise ValueError("y_true and proba must have the same length")
    if not classes:
        raise ValueError("classes must not be empty")
    for row in proba:
        if len(row) != len(classes):
            raise ValueError("each probability row must match classes length")
        values = [float(value) for value in row]
        if any(not math.isfinite(value) or value < 0 for value in values):
            raise ValueError("probabilities must be finite and non-negative")
        if sum(values) <= 0:
            raise ValueError("each probability row must have positive mass")


def _argmax(values: Sequence[float]) -> int:
    return max(range(len(values)), key=lambda index: float(values[index]))
