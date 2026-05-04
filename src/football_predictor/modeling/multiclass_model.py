"""Serializable multiclass football outcome model."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import joblib  # type: ignore[import-untyped]
import pandas as pd  # type: ignore[import-untyped]
from sklearn.ensemble import HistGradientBoostingClassifier  # type: ignore[import-untyped]
from sklearn.impute import SimpleImputer  # type: ignore[import-untyped]
from sklearn.linear_model import LogisticRegression  # type: ignore[import-untyped]
from sklearn.pipeline import Pipeline  # type: ignore[import-untyped]
from sklearn.preprocessing import StandardScaler  # type: ignore[import-untyped]

from football_predictor.modeling.constants import CLASSES
from football_predictor.modeling.preprocessing import (
    numeric_feature_dataframe,
    select_numeric_feature_names,
)


class FootballOutcomeModel:
    """Sklearn-backed 1X2 model with safe feature preprocessing."""

    def __init__(
        self,
        *,
        model_version: str = "v1",
        estimator: Any | None = None,
        feature_names: list[str] | None = None,
        random_state: int = 42,
    ) -> None:
        self.model_version = model_version
        self.estimator = estimator or HistGradientBoostingClassifier(random_state=random_state)
        self.feature_names = feature_names or []
        self.random_state = random_state
        self.classes_ = list(CLASSES)

    def fit(self, x: pd.DataFrame, y: pd.Series | list[str]) -> FootballOutcomeModel:
        frame = x.copy()
        self.feature_names = self.feature_names or select_numeric_feature_names(frame)
        if not self.feature_names:
            raise ValueError("No safe numeric feature columns available for training")
        prepared = numeric_feature_dataframe(frame[self.feature_names], impute=True)
        try:
            self.estimator.fit(prepared, y)
        except ValueError:
            self.estimator = self._logistic_fallback()
            self.estimator.fit(prepared, y)
        if hasattr(self.estimator, "classes_"):
            self.classes_ = [str(label) for label in self.estimator.classes_]
        return self

    def predict_proba(self, x: pd.DataFrame) -> list[list[float]]:
        if not self.feature_names:
            raise ValueError("Model has no feature_names; fit or load a model first")
        prepared = _frame_for_features(x, self.feature_names)
        raw = self.estimator.predict_proba(prepared)
        output: list[list[float]] = []
        for row in raw:
            values = {label: 0.0 for label in CLASSES}
            for label, probability in zip(self.classes_, row, strict=False):
                if label in values:
                    values[label] = float(probability)
            total = sum(values.values())
            if total <= 0:
                output.append([1.0 / len(CLASSES)] * len(CLASSES))
            else:
                output.append([values[label] / total for label in CLASSES])
        return output

    def save(self, path: Path) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self, path)
        return path

    @classmethod
    def load(cls, path: Path) -> FootballOutcomeModel:
        model = joblib.load(path)
        if not isinstance(model, cls):
            raise TypeError(f"Unexpected model type: {type(model)!r}")
        return model

    def _logistic_fallback(self) -> Pipeline:
        return Pipeline(
            steps=[
                ("imputer", SimpleImputer(strategy="median")),
                ("scaler", StandardScaler()),
                (
                    "classifier",
                    LogisticRegression(
                        max_iter=2000,
                        class_weight="balanced",
                        random_state=self.random_state,
                    ),
                ),
            ]
        )


def _frame_for_features(frame: pd.DataFrame, feature_names: list[str]) -> pd.DataFrame:
    prepared = pd.DataFrame(
        {
            name: frame[name] if name in frame.columns else float("nan")
            for name in feature_names
        },
        index=frame.index,
    )
    return numeric_feature_dataframe(prepared[feature_names], impute=True, forbidden_patterns=())
