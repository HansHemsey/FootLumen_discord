"""Logistic Regression baseline for O/U 2.5."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

LOGISTIC_FEATURES = [
    "combined_total_goals_avg_last5",
    "combined_total_goals_avg_last10",
    "combined_over25_rate_last5",
    "combined_over25_rate_last10",
    "home_team_global_over25_rate_last5",
    "away_team_global_over25_rate_last5",
    "home_team_global_total_goals_avg_last5",
    "away_team_global_total_goals_avg_last5",
    "combined_pseudo_xg_total_avg_last5",
    "market_p_over25",
    "home_team_rest_days",
    "away_team_rest_days",
    "combined_corners_avg_last5",
    "h2h_total_goals_avg_last5",
    "h2h_over25_rate_last5",
]


def build_logistic_pipeline(random_state: int = 42) -> Pipeline:
    return Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler", StandardScaler()),
        ("clf", LogisticRegression(max_iter=2000, C=1.0, random_state=random_state)),
    ])


def fit_ou_logistic(
    X_train: pd.DataFrame,
    y_train: Any,
    *,
    feature_names: list[str] | None = None,
    random_state: int = 42,
) -> tuple[Pipeline, list[str]]:
    """Fit logistic regression on available LOGISTIC_FEATURES subset."""
    available = [f for f in LOGISTIC_FEATURES if f in X_train.columns]
    if not available:
        available = list(X_train.columns)[:10]
    pipe = build_logistic_pipeline(random_state)
    pipe.fit(X_train[available], y_train)
    return pipe, available


def predict_proba_over_logistic(pipe: Pipeline, X: pd.DataFrame, features: list[str]) -> np.ndarray:
    available = [f for f in features if f in X.columns]
    if not available:
        return np.full(len(X), 0.5)
    return pipe.predict_proba(X[available])[:, 1]


def save_logistic(pipe: Pipeline, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({"pipeline": pipe}, path)


def load_logistic(path: Path) -> Pipeline:
    data = joblib.load(path)
    return data["pipeline"]
