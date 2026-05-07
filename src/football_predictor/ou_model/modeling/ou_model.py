"""OUCompositeModel — save/load + inference for O/U 2.5."""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd

from football_predictor.ou_model.constants import (
    DEFAULT_AWAY_LAMBDA,
    DEFAULT_HOME_LAMBDA,
    FALLBACK_WEIGHTS,
    OU_THRESHOLD,
)
from football_predictor.ou_model.modeling.ou_calibration import apply_calibration
from football_predictor.ou_model.modeling.ou_poisson import extract_lambdas, ou_poisson_probability
from football_predictor.ou_model.modeling.ou_stacking import blend_ou_probabilities

JsonRow = Mapping[str, Any]
JsonDict = dict[str, Any]


@dataclass
class OUCompositeModel:
    model_version: str
    threshold: float = OU_THRESHOLD
    feature_names: list[str] = field(default_factory=list)
    poisson_config: JsonDict = field(default_factory=dict)
    logistic_model: Any | None = None
    logistic_features: list[str] = field(default_factory=list)
    lgbm_model: Any | None = None
    xgb_model: Any | None = None
    catboost_model: Any | None = None
    meta_model: Any | None = None
    meta_features_order: list[str] = field(default_factory=list)
    calibration_model: Any | None = None
    fallback_weights: dict[str, float] = field(default_factory=lambda: dict(FALLBACK_WEIGHTS))
    feature_coverage: dict[str, float] = field(default_factory=dict)
    calibration_decision: JsonDict = field(default_factory=dict)
    is_ou_composite: bool = True

    def predict_ou(self, row: JsonRow) -> tuple[float, float]:
        """Return (p_over, p_under) for a single feature row."""
        experts = self.expert_probabilities_for_row(row)
        market_p = None
        if isinstance(row, dict):
            market_p = row.get("market_p_over25")
        if market_p is not None and isinstance(market_p, (int, float)) and math.isfinite(float(market_p)):
            experts["market"] = float(market_p)

        result = blend_ou_probabilities(
            experts,
            weights=self.fallback_weights,
            meta_model=self.meta_model,
            meta_features_order=self.meta_features_order or None,
        )
        p_over = apply_calibration(self.calibration_model, result.p_over)
        p_over = max(min(p_over, 1 - 1e-6), 1e-6)
        return p_over, 1.0 - p_over

    def predict_proba_over(self, frame: pd.DataFrame) -> np.ndarray:
        """Return P(Over) for each row in a DataFrame."""
        return np.array([self.predict_ou(row)[0] for _, row in frame.iterrows()])

    def expert_probabilities_for_row(self, row: JsonRow) -> dict[str, float]:
        """Return each expert's p_over estimate."""
        experts: dict[str, float] = {}

        try:
            home_lambda, away_lambda = extract_lambdas(row)
            p_over_poisson, _ = ou_poisson_probability(
                home_lambda, away_lambda, self.threshold,
                **self.poisson_config,
            )
            experts["poisson"] = p_over_poisson
        except Exception:
            experts["poisson"] = 0.5

        if self.logistic_model is not None and self.logistic_features:
            try:
                X_row = pd.DataFrame([dict(row)])[self.logistic_features]
                experts["logistic"] = float(
                    self.logistic_model.predict_proba(X_row.fillna(0.5))[0, 1]
                )
            except Exception:
                pass

        if self.lgbm_model is not None:
            try:
                X_row = pd.DataFrame([dict(row)])
                experts["lgbm"] = float(self.lgbm_model.predict_proba_over(X_row)[0])
            except Exception:
                pass

        if self.xgb_model is not None:
            try:
                X_row = pd.DataFrame([dict(row)])
                experts["xgb"] = float(self.xgb_model.predict_proba_over(X_row)[0])
            except Exception:
                pass

        if self.catboost_model is not None:
            try:
                X_row = pd.DataFrame([dict(row)])
                experts["catboost"] = float(self.catboost_model.predict_proba_over(X_row)[0])
            except Exception:
                pass

        return experts

    def save(self, path: Path) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self, path)
        return path

    @classmethod
    def load(cls, path: Path) -> OUCompositeModel:
        obj = joblib.load(path)
        if not isinstance(obj, cls):
            raise TypeError(f"Expected OUCompositeModel at {path}, got {type(obj)}")
        return obj
