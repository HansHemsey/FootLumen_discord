"""Calibration helpers for scikit-learn probability estimators."""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Literal

import pandas as pd  # type: ignore[import-untyped]
from sklearn.calibration import CalibratedClassifierCV  # type: ignore[import-untyped]

CalibrationMethod = Literal["sigmoid", "isotonic"]


@dataclass(frozen=True)
class CalibrationDecision:
    method_used: str | None
    skipped_reason: str | None


def calibrate_probabilities(
    probabilities: Sequence[float],
    *,
    temperature: float = 1.0,
) -> list[float]:
    """Apply simple temperature scaling to one probability vector."""
    if temperature <= 0 or not math.isfinite(temperature):
        raise ValueError("temperature must be a positive finite value")
    clipped = [max(float(value), 1e-12) for value in probabilities]
    logits = [math.log(value) / temperature for value in clipped]
    maximum = max(logits)
    exps = [math.exp(value - maximum) for value in logits]
    total = sum(exps)
    return [value / total for value in exps]


def maybe_calibrate_estimator(
    estimator: Any,
    x_train: pd.DataFrame,
    y_train: Sequence[str],
    *,
    method: CalibrationMethod | None,
    min_rows: int,
    cv: int = 3,
) -> tuple[Any, CalibrationDecision]:
    """Fit either a calibrated estimator or the base estimator.

    Calibration is cross-validated on the training set only. It is skipped when
    the sample is too small or any class lacks enough rows for the requested CV.
    """
    if method is None:
        estimator.fit(x_train, y_train)
        return estimator, CalibrationDecision(method_used=None, skipped_reason="disabled")

    skipped_reason = _calibration_skip_reason(y_train, min_rows=min_rows, cv=cv)
    if skipped_reason is not None:
        estimator.fit(x_train, y_train)
        return estimator, CalibrationDecision(method_used=None, skipped_reason=skipped_reason)

    calibrated = CalibratedClassifierCV(estimator=estimator, method=method, cv=cv)
    calibrated.fit(x_train, y_train)
    return calibrated, CalibrationDecision(method_used=method, skipped_reason=None)


def _calibration_skip_reason(
    y_train: Sequence[str],
    *,
    min_rows: int,
    cv: int,
) -> str | None:
    if len(y_train) < min_rows:
        return f"requires at least {min_rows} rows"
    counts = {label: 0 for label in set(y_train)}
    for label in y_train:
        counts[label] += 1
    if len(counts) < 3:
        return "requires all HOME/DRAW/AWAY classes"
    if min(counts.values()) < cv:
        return f"requires at least {cv} rows per class"
    return None
