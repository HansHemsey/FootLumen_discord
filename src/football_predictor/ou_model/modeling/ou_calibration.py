"""Platt scaling calibration for O/U 2.5 composite model."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

import numpy as np
import pandas as pd

JsonDict = dict[str, Any]


@dataclass(frozen=True)
class CalibrationDecision:
    applied: bool
    method: str
    rows_used: int
    reason: str


def calibrate_ou_model(
    p_over_train: np.ndarray,
    y_cal: np.ndarray,
    *,
    method: Literal["sigmoid", "isotonic"] = "sigmoid",
    min_rows: int = 60,
    min_slope: float = 0.20,
) -> tuple[Any | None, CalibrationDecision]:
    """Fit a Platt-scaling calibrator on the calibration set.

    Returns (calibrator, decision). calibrator is None if:
    - Insufficient rows, OR
    - Fitted slope < min_slope (near-zero means the model has no signal on this
      calibration set, so applying it would collapse all predictions toward 0.5).
    """
    if len(y_cal) < min_rows:
        return None, CalibrationDecision(
            applied=False,
            method=method,
            rows_used=len(y_cal),
            reason=f"insufficient rows: {len(y_cal)} < {min_rows}",
        )

    from sklearn.linear_model import LogisticRegression

    p_clamped = np.clip(p_over_train, 1e-9, 1 - 1e-9)
    log_odds = np.log(p_clamped / (1 - p_clamped)).reshape(-1, 1)

    base = LogisticRegression(max_iter=2000, C=1.0)
    base.fit(log_odds, y_cal)

    slope = float(base.coef_[0, 0])
    if slope < min_slope:
        return None, CalibrationDecision(
            applied=False,
            method=method,
            rows_used=len(y_cal),
            reason=f"degenerate slope={slope:.4f} < min_slope={min_slope} (no signal on cal set)",
        )

    return base, CalibrationDecision(
        applied=True,
        method=method,
        rows_used=len(y_cal),
        reason=f"ok (slope={slope:.4f})",
    )


def apply_calibration(
    calibrator: Any | None,
    p_over: float,
) -> float:
    """Apply a fitted Platt calibrator to a single probability."""
    if calibrator is None:
        return p_over
    import math
    p_clamped = max(min(p_over, 1 - 1e-9), 1e-9)
    log_odds = math.log(p_clamped / (1 - p_clamped))
    calibrated = calibrator.predict_proba([[log_odds]])[0, 1]
    return float(calibrated)


def apply_calibration_array(
    calibrator: Any | None,
    p_over_arr: np.ndarray,
) -> np.ndarray:
    """Apply calibrator to an array of probabilities."""
    if calibrator is None:
        return p_over_arr
    p_clamped = np.clip(p_over_arr, 1e-9, 1 - 1e-9)
    log_odds = np.log(p_clamped / (1 - p_clamped)).reshape(-1, 1)
    return calibrator.predict_proba(log_odds)[:, 1]
