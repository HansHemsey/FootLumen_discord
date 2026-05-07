"""CatBoost wrapper for O/U 2.5."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd


@dataclass
class OUCatBoostModel:
    model: Any
    feature_names: list[str]
    model_type: str = "catboost"

    def predict_proba_over(self, X: pd.DataFrame) -> np.ndarray:
        available = [f for f in self.feature_names if f in X.columns]
        if not available:
            return np.full(len(X), 0.5)
        return self.model.predict_proba(X[available])[:, 1]

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self, path)

    @classmethod
    def load(cls, path: Path) -> OUCatBoostModel:
        return joblib.load(path)


def fit_ou_catboost(
    X_train: pd.DataFrame,
    y_train: Any,
    feature_names: list[str],
    *,
    random_state: int = 42,
) -> OUCatBoostModel:
    try:
        from catboost import CatBoostClassifier
        model = CatBoostClassifier(
            iterations=300,
            learning_rate=0.02,
            depth=4,                # shallower trees
            min_data_in_leaf=30,    # anti-overfit
            l2_leaf_reg=5.0,        # L2 regularization
            subsample=0.70,
            colsample_bylevel=0.50,
            loss_function="Logloss",
            eval_metric="Logloss",
            random_seed=random_state,
            verbose=0,
        )
    except ImportError:
        from sklearn.ensemble import ExtraTreesClassifier
        model = ExtraTreesClassifier(
            n_estimators=300,
            min_samples_leaf=40,
            max_features=0.5,
            random_state=random_state,
        )

    available = [f for f in feature_names if f in X_train.columns]
    model.fit(X_train[available], y_train)
    return OUCatBoostModel(model=model, feature_names=available)
