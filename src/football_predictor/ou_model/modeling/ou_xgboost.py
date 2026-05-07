"""XGBoost wrapper for O/U 2.5."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd


@dataclass
class OUXGBoostModel:
    model: Any
    feature_names: list[str]
    model_type: str = "xgboost"

    def predict_proba_over(self, X: pd.DataFrame) -> np.ndarray:
        available = [f for f in self.feature_names if f in X.columns]
        if not available:
            return np.full(len(X), 0.5)
        return self.model.predict_proba(X[available])[:, 1]

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self, path)

    @classmethod
    def load(cls, path: Path) -> OUXGBoostModel:
        return joblib.load(path)


def fit_ou_xgboost(
    X_train: pd.DataFrame,
    y_train: Any,
    feature_names: list[str],
    *,
    random_state: int = 42,
) -> OUXGBoostModel:
    try:
        from xgboost import XGBClassifier
        model = XGBClassifier(
            n_estimators=200,
            learning_rate=0.03,
            max_depth=4,
            subsample=0.80,
            colsample_bytree=0.80,
            eval_metric="logloss",
            random_state=random_state,
            verbosity=0,
        )
    except ImportError:
        from sklearn.ensemble import GradientBoostingClassifier
        model = GradientBoostingClassifier(
            n_estimators=200,
            learning_rate=0.03,
            max_depth=4,
            subsample=0.80,
            random_state=random_state,
        )

    available = [f for f in feature_names if f in X_train.columns]
    model.fit(X_train[available], y_train)
    return OUXGBoostModel(model=model, feature_names=available)
