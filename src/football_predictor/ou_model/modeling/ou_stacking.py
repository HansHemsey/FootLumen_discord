"""Stacking ensemble for O/U 2.5 predictions.

Level 1: Poisson, Logistic, LightGBM, XGBoost, CatBoost → each produces a scalar p_over.
Level 2: LogisticRegression meta-model trained on out-of-fold level-1 predictions.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd

from football_predictor.ou_model.constants import FALLBACK_WEIGHTS

JsonDict = dict[str, Any]


@dataclass(frozen=True)
class OUStackingResult:
    p_over: float
    p_under: float
    expert_probabilities: dict[str, float]
    meta_available: bool


@dataclass(frozen=True)
class OUStackingConfig:
    min_rows_for_meta: int = 80
    random_state: int = 42


def blend_ou_probabilities(
    experts: dict[str, float],
    *,
    weights: dict[str, float] | None = None,
    meta_model: Any | None = None,
    meta_features_order: list[str] | None = None,
) -> OUStackingResult:
    """Blend expert O/U probabilities.

    Uses meta_model if available, otherwise weighted geometric mean.
    The market expert (key="market") receives the highest fallback weight.
    """
    resolved_weights = weights or FALLBACK_WEIGHTS
    if meta_model is not None and meta_features_order is not None:
        row = [experts.get(k, 0.5) for k in meta_features_order]
        p_over = float(meta_model.predict_proba([row])[0, 1])
    else:
        log_sum = 0.0
        total_weight = 0.0
        for name, p in experts.items():
            w = resolved_weights.get(name, 0.1)
            p_clamped = max(min(float(p), 1 - 1e-9), 1e-9)
            log_sum += w * math.log(p_clamped / (1 - p_clamped))
            total_weight += w
        if total_weight > 0:
            log_odds = log_sum / total_weight
            p_over = 1 / (1 + math.exp(-log_odds))
        else:
            p_over = 0.5

    p_over = max(min(p_over, 1 - 1e-6), 1e-6)
    return OUStackingResult(
        p_over=p_over,
        p_under=1.0 - p_over,
        expert_probabilities={k: float(v) for k, v in experts.items()},
        meta_available=meta_model is not None,
    )


def train_meta_model(
    valid_frame: pd.DataFrame,
    expert_names: list[str],
    target_col: str = "target_ou25",
    *,
    config: OUStackingConfig | None = None,
) -> tuple[Any, list[str]] | tuple[None, list[str]]:
    """Train a LogisticRegression meta-model on expert out-of-fold predictions.

    Returns (meta_model, expert_names) or (None, expert_names) if not enough rows.
    """
    resolved = config or OUStackingConfig()
    available_experts = [e for e in expert_names if e in valid_frame.columns]
    y = valid_frame[target_col].values
    if len(y) < resolved.min_rows_for_meta or len(available_experts) < 2:
        return None, available_experts

    from sklearn.linear_model import LogisticRegression

    X = valid_frame[available_experts].fillna(0.5).values
    meta = LogisticRegression(max_iter=2000, C=0.5, random_state=resolved.random_state)
    meta.fit(X, y)
    return meta, available_experts
