"""Sport model training and prediction with leakage-aware feature selection."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any, Literal

import pandas as pd  # type: ignore[import-untyped]
from sklearn.impute import SimpleImputer  # type: ignore[import-untyped]
from sklearn.linear_model import LogisticRegression  # type: ignore[import-untyped]
from sklearn.pipeline import Pipeline  # type: ignore[import-untyped]
from sklearn.preprocessing import StandardScaler  # type: ignore[import-untyped]

from football_predictor.modeling.calibration import maybe_calibrate_estimator
from football_predictor.modeling.preprocessing import (
    FORBIDDEN_FEATURE_PATTERNS,
    numeric_feature_dataframe,
    select_numeric_feature_names,
)
from football_predictor.modeling.probabilities import VALID_RESULTS, ProbabilityTriple
from football_predictor.modeling.stacking import StackingWeights

CalibrationConfig = Literal["sigmoid", "isotonic"]

DEFAULT_FORBIDDEN_FEATURE_PATTERNS = FORBIDDEN_FEATURE_PATTERNS


@dataclass(frozen=True)
class ModelTrainingConfig:
    model_version: str = "v1"
    calibration_method: CalibrationConfig | None = "sigmoid"
    min_rows_for_calibration: int = 30
    forbidden_feature_patterns: tuple[str, ...] = DEFAULT_FORBIDDEN_FEATURE_PATTERNS
    stacking_weights: StackingWeights = StackingWeights()
    random_state: int = 42


@dataclass
class TrainedSportModel:
    model_version: str
    estimator: Any
    feature_columns: list[str]
    calibration_method: str | None
    calibration_skipped_reason: str | None
    config: ModelTrainingConfig = field(default_factory=ModelTrainingConfig)
    metrics: dict[str, Any] = field(default_factory=dict)

    def predict_probabilities(self, frame: pd.DataFrame) -> list[ProbabilityTriple]:
        return predict_sport_probabilities(self, frame)


def train_sport_model(
    frame: pd.DataFrame,
    config: ModelTrainingConfig | None = None,
) -> TrainedSportModel:
    config = config or ModelTrainingConfig()
    _validate_training_targets(frame)
    feature_columns = select_safe_feature_columns(frame, config=config)
    if not feature_columns:
        raise ValueError("No safe numeric feature columns available for training")

    x_train = prepare_feature_frame(frame, feature_columns)
    y_train = list(frame["target"].astype(str))
    estimator, decision = maybe_calibrate_estimator(
        _build_base_estimator(config),
        x_train,
        y_train,
        method=config.calibration_method,
        min_rows=config.min_rows_for_calibration,
    )
    return TrainedSportModel(
        model_version=config.model_version,
        estimator=estimator,
        feature_columns=feature_columns,
        calibration_method=decision.method_used,
        calibration_skipped_reason=decision.skipped_reason,
        config=config,
    )


def predict_sport_probabilities(
    model: TrainedSportModel,
    frame: pd.DataFrame,
) -> list[ProbabilityTriple]:
    x_frame = prepare_feature_frame(frame, model.feature_columns)
    raw_probabilities = model.estimator.predict_proba(x_frame)
    classes = [str(label) for label in model.estimator.classes_]
    predictions: list[ProbabilityTriple] = []
    for row in raw_probabilities:
        values = {label: 0.0 for label in VALID_RESULTS}
        for label, probability in zip(classes, row, strict=False):
            if label in values:
                values[label] = float(probability)
        predictions.append(ProbabilityTriple.from_mapping(values))
    return predictions


def select_safe_feature_columns(
    frame: pd.DataFrame,
    config: ModelTrainingConfig | None = None,
) -> list[str]:
    config = config or ModelTrainingConfig()
    return select_numeric_feature_names(
        frame,
        forbidden_patterns=config.forbidden_feature_patterns,
    )


def prepare_feature_frame(frame: pd.DataFrame, feature_columns: Sequence[str]) -> pd.DataFrame:
    prepared = pd.DataFrame(
        {
            column: frame[column] if column in frame.columns else float("nan")
            for column in feature_columns
        },
        index=frame.index,
    )
    return numeric_feature_dataframe(
        prepared[list(feature_columns)],
        impute=False,
        forbidden_patterns=(),
    )


def _build_base_estimator(config: ModelTrainingConfig) -> Pipeline:
    return Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
            (
                "classifier",
                LogisticRegression(
                    max_iter=2000,
                    class_weight="balanced",
                    random_state=config.random_state,
                ),
            ),
        ]
    )


def _validate_training_targets(frame: pd.DataFrame) -> None:
    if "target" not in frame.columns:
        raise ValueError("Training frame must contain a target column")
    labels = set(frame["target"].astype(str))
    invalid = labels.difference(VALID_RESULTS)
    if invalid:
        raise ValueError(f"Unknown target labels: {sorted(invalid)}")
    missing = set(VALID_RESULTS).difference(labels)
    if missing:
        raise ValueError(
            f"Training requires all HOME/DRAW/AWAY classes, missing: {sorted(missing)}"
        )
