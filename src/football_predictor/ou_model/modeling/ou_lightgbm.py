"""LightGBM wrapper for O/U 2.5."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd


@dataclass
class OULightGBMModel:
    model: Any
    feature_names: list[str]
    model_type: str = "lightgbm"

    def predict_proba_over(self, X: pd.DataFrame) -> np.ndarray:
        available = [f for f in self.feature_names if f in X.columns]
        if not available:
            return np.full(len(X), 0.5)
        return self.model.predict_proba(X[available])[:, 1]

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self, path)

    @classmethod
    def load(cls, path: Path) -> OULightGBMModel:
        return joblib.load(path)


def fit_ou_lightgbm(
    X_train: pd.DataFrame,
    y_train: Any,
    feature_names: list[str],
    *,
    random_state: int = 42,
) -> OULightGBMModel:
    try:
        from lightgbm import LGBMClassifier
        model = LGBMClassifier(
            n_estimators=300,
            learning_rate=0.02,
            num_leaves=8,           # shallow trees — anti-overfit
            min_child_samples=40,   # at least 40 samples per leaf
            subsample=0.70,
            colsample_bytree=0.50,  # use half the features per tree
            reg_alpha=0.5,          # L1
            reg_lambda=2.0,         # L2
            objective="binary",
            random_state=random_state,
            verbose=-1,
        )
    except ImportError:
        from sklearn.ensemble import HistGradientBoostingClassifier
        model = HistGradientBoostingClassifier(
            max_leaf_nodes=8,
            min_samples_leaf=40,
            l2_regularization=2.0,
            random_state=random_state,
        )

    available = [f for f in feature_names if f in X_train.columns]
    model.fit(X_train[available], y_train)
    return OULightGBMModel(model=model, feature_names=available)
