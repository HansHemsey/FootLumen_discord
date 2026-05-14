"""Training and inference for the V3 Draw Risk binary model."""

from __future__ import annotations

import json
import math
import warnings
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

import joblib  # type: ignore[import-untyped]
import numpy as np
import pandas as pd  # type: ignore[import-untyped]
from sklearn.calibration import CalibratedClassifierCV  # type: ignore[import-untyped]
from sklearn.ensemble import HistGradientBoostingClassifier  # type: ignore[import-untyped]
from sklearn.impute import SimpleImputer  # type: ignore[import-untyped]
from sklearn.linear_model import LogisticRegression  # type: ignore[import-untyped]
from sklearn.metrics import (  # type: ignore[import-untyped]
    accuracy_score,
    average_precision_score,
    brier_score_loss,
    log_loss,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.pipeline import Pipeline  # type: ignore[import-untyped]

from football_predictor.backtesting.v3_dataset_builder import chronological_splits
from football_predictor.modeling.preprocessing import numeric_feature_dataframe
from football_predictor.modeling.v3.constants import (
    DEFAULT_DRAW_RISK_MODEL_VERSION,
    DRAW_CLASS,
    DRAW_RISK_CLASSES,
    DRAW_RISK_TARGET,
    NOT_DRAW_CLASS,
    OUTCOME_COLUMN,
)
from football_predictor.modeling.v3.features_selection import (
    feature_coverage,
    select_v3_draw_feature_names,
)
from football_predictor.utils.time import utc_now

JsonDict = dict[str, Any]
CalibrationMode = Literal["isotonic", "none"]

ARTIFACT_FORMAT = "draw_risk_model_v3"
DATE_COL = "fixture_date"
TARGET_COL = "target"
EPSILON = 1e-15


@dataclass(frozen=True)
class DrawRiskTrainingConfig:
    """Training options for the V3 Draw Risk model."""

    model_version: str = DEFAULT_DRAW_RISK_MODEL_VERSION
    calibration: CalibrationMode = "isotonic"
    train_ratio: float = 0.60
    valid_ratio: float = 0.20
    min_rows_for_calibration: int = 200
    calibration_cv: int = 3
    feature_min_coverage: float = 0.02
    max_features: int = 260
    random_state: int = 42


@dataclass(frozen=True)
class DrawRiskTrainResult:
    """Paths and metrics produced by Draw Risk training."""

    model: DrawRiskModel
    model_path: Path
    metadata_path: Path
    feature_names_path: Path
    metrics_path: Path
    feature_coverage_path: Path
    metrics: JsonDict


@dataclass
class DrawRiskModel:
    """Binary model returning P(Draw) for V3."""

    model_version: str
    feature_names: list[str]
    estimator: Any
    feature_coverage: JsonDict
    calibration_decision: JsonDict
    estimator_name: str
    target_column: str = DRAW_RISK_TARGET
    artifact_format: str = ARTIFACT_FORMAT
    classes: list[str] = field(default_factory=lambda: list(DRAW_RISK_CLASSES))

    def predict_draw_proba(self, frame: pd.DataFrame) -> list[float]:
        """Return P(Draw) for each row."""
        if not self.feature_names:
            raise ValueError("DrawRiskModel has no feature_names")
        prepared = _prepare_features(frame, self.feature_names)
        raw_matrix = _predict_proba_safely(self.estimator, prepared)
        return [
            _clip_probability(probability)
            for probability in _draw_probabilities_from_raw(self.estimator, raw_matrix)
        ]

    def predict_proba(self, frame: pd.DataFrame) -> list[list[float]]:
        """Return probabilities ordered as [P(NotDraw), P(Draw)]."""
        return [[1.0 - probability, probability] for probability in self.predict_draw_proba(frame)]

    def save(self, path: Path) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self, path)
        return path

    @classmethod
    def load(cls, path: Path) -> DrawRiskModel:
        obj = joblib.load(path)
        if not isinstance(obj, cls):
            raise TypeError(f"Expected DrawRiskModel at {path}, got {type(obj)}")
        return obj


def train_draw_risk_from_dataset(
    dataset_path: Path,
    output_dir: Path,
    *,
    config: DrawRiskTrainingConfig | None = None,
) -> DrawRiskTrainResult:
    """Load a V3 dataset, split chronologically, train and write Draw Risk artifacts."""
    resolved_config = config or DrawRiskTrainingConfig()
    frame = _ensure_draw_target(_load_dataset(dataset_path))
    if DATE_COL not in frame.columns:
        raise ValueError(f"Dataset must contain {DATE_COL} for chronological V3 training")

    splits = chronological_splits(
        frame,
        train_ratio=resolved_config.train_ratio,
        valid_ratio=resolved_config.valid_ratio,
        date_col=DATE_COL,
    )
    model, metrics = train_draw_risk_from_frame(
        splits.train,
        valid_frame=splits.valid,
        test_frame=splits.test,
        config=resolved_config,
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    model_path = model.save(output_dir / "model.joblib")
    metadata_path = output_dir / "metadata.json"
    feature_names_path = output_dir / "feature_names.json"
    metrics_path = output_dir / "metrics.json"
    feature_coverage_path = output_dir / "feature_coverage.json"

    metadata = {
        "artifact_format": model.artifact_format,
        "model_version": model.model_version,
        "created_at": utc_now().isoformat(),
        "classes": model.classes,
        "target_column": model.target_column,
        "estimator_name": model.estimator_name,
        "feature_count": len(model.feature_names),
        "training_rows": len(splits.train),
        "validation_rows": len(splits.valid),
        "test_rows": len(splits.test),
        "train_ratio": resolved_config.train_ratio,
        "valid_ratio": resolved_config.valid_ratio,
        "calibration_decision": model.calibration_decision,
    }
    metadata_path.write_text(
        json.dumps(_json_ready(metadata), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    feature_names_path.write_text(
        json.dumps(model.feature_names, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    metrics_path.write_text(
        json.dumps(_json_ready(metrics), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    feature_coverage_path.write_text(
        json.dumps(_json_ready(model.feature_coverage), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return DrawRiskTrainResult(
        model=model,
        model_path=model_path,
        metadata_path=metadata_path,
        feature_names_path=feature_names_path,
        metrics_path=metrics_path,
        feature_coverage_path=feature_coverage_path,
        metrics=metrics,
    )


def train_draw_risk_from_frame(
    train_frame: pd.DataFrame,
    *,
    valid_frame: pd.DataFrame | None = None,
    test_frame: pd.DataFrame | None = None,
    config: DrawRiskTrainingConfig | None = None,
) -> tuple[DrawRiskModel, JsonDict]:
    """Train a Draw Risk model from already-split V3 frames."""
    resolved_config = config or DrawRiskTrainingConfig()
    train = _ensure_draw_target(train_frame)
    valid = _ensure_draw_target(valid_frame) if valid_frame is not None else pd.DataFrame()
    test = _ensure_draw_target(test_frame) if test_frame is not None else pd.DataFrame()

    if train.empty:
        raise ValueError("Draw Risk training requires at least one row")
    y_train = pd.to_numeric(train[DRAW_RISK_TARGET], errors="raise").astype(int).to_numpy()
    if len(set(y_train.tolist())) < 2:
        raise ValueError("Draw Risk training requires both DRAW and NOT_DRAW rows")

    feature_names = select_v3_draw_feature_names(
        train,
        min_coverage=resolved_config.feature_min_coverage,
        max_features=resolved_config.max_features,
    )
    if not feature_names:
        raise ValueError("No V3 Draw Risk feature columns available for training")

    prepared = _prepare_features(train, feature_names)
    estimator, estimator_name, calibration_decision = _fit_estimator(
        prepared,
        y_train,
        config=resolved_config,
    )
    model = DrawRiskModel(
        model_version=resolved_config.model_version,
        feature_names=feature_names,
        estimator=estimator,
        feature_coverage=feature_coverage(train, feature_names),
        calibration_decision=calibration_decision,
        estimator_name=estimator_name,
    )
    prior_draw_rate = float(np.mean(y_train))
    metrics = {
        "model_version": resolved_config.model_version,
        "target_column": DRAW_RISK_TARGET,
        "classes": DRAW_RISK_CLASSES,
        "feature_count": len(feature_names),
        "calibration_decision": calibration_decision,
        "train": evaluate_draw_risk_frame(model, train, prior_draw_rate=prior_draw_rate),
        "validation": evaluate_draw_risk_frame(model, valid, prior_draw_rate=prior_draw_rate)
        if not valid.empty
        else None,
        "test": evaluate_draw_risk_frame(model, test, prior_draw_rate=prior_draw_rate)
        if not test.empty
        else None,
    }
    return model, metrics


def evaluate_draw_risk_frame(
    model: DrawRiskModel,
    frame: pd.DataFrame,
    *,
    prior_draw_rate: float | None = None,
) -> JsonDict:
    """Evaluate Draw Risk probabilities on one split."""
    prepared = _ensure_draw_target(frame)
    if prepared.empty:
        return {"row_count": 0}

    y_true = pd.to_numeric(prepared[DRAW_RISK_TARGET], errors="raise").astype(int).to_numpy()
    probabilities = np.asarray(model.predict_draw_proba(prepared), dtype=float)
    predictions = (probabilities >= 0.5).astype(int)
    prior = _clip_probability(
        float(prior_draw_rate) if prior_draw_rate is not None else float(np.mean(y_true))
    )

    result: JsonDict = {
        "row_count": int(len(y_true)),
        "class_balance": _class_balance(y_true),
        "accuracy": float(accuracy_score(y_true, predictions)),
        "log_loss": _binary_log_loss(y_true, probabilities),
        "brier_score": float(brier_score_loss(y_true, probabilities)),
        "roc_auc": _roc_auc(y_true, probabilities),
        "pr_auc": _pr_auc(y_true, probabilities),
        "precision_draw": float(precision_score(y_true, predictions, zero_division=0)),
        "recall_draw": float(recall_score(y_true, predictions, zero_division=0)),
        "actual_draw_rate": float(np.mean(y_true)),
        "predicted_draw_rate": float(np.mean(predictions)),
        "mean_predicted_draw": float(np.mean(probabilities)),
    }
    bins, ece = _calibration_bins(y_true, probabilities)
    result["calibration_bins"] = bins
    result["ece"] = ece
    result["baselines"] = _baseline_metrics(prepared, y_true, probabilities, prior)
    return result


def _fit_estimator(
    prepared: pd.DataFrame,
    y_train: np.ndarray,
    *,
    config: DrawRiskTrainingConfig,
) -> tuple[Any, str, JsonDict]:
    skip_reason = _calibration_skip_reason(y_train, config)
    if config.calibration == "none":
        estimator, estimator_name, fit_decision = _fit_base_estimator(
            prepared,
            y_train,
            config=config,
        )
        return estimator, estimator_name, {
            "method": None,
            "reason": "disabled",
            **fit_decision,
        }
    if skip_reason is not None:
        estimator, estimator_name, fit_decision = _fit_base_estimator(
            prepared,
            y_train,
            config=config,
        )
        return estimator, estimator_name, {
            "method": None,
            "reason": skip_reason,
            "rows": int(len(y_train)),
            "class_counts": _class_counts(y_train),
            **fit_decision,
        }

    base = _hist_gradient_boosting_estimator(config)
    calibrated = CalibratedClassifierCV(
        estimator=base,
        method="isotonic",
        cv=config.calibration_cv,
    )
    try:
        calibrated.fit(prepared, y_train)
        return calibrated, "hist_gradient_boosting_calibrated", {
            "method": "isotonic",
            "rows": int(len(y_train)),
            "cv": config.calibration_cv,
            "class_counts": _class_counts(y_train),
            "base_estimator": "hist_gradient_boosting",
        }
    except Exception as exc:
        estimator, estimator_name, fit_decision = _fit_base_estimator(
            prepared,
            y_train,
            config=config,
        )
        return estimator, estimator_name, {
            "method": None,
            "reason": "calibration_fit_failed",
            "error": str(exc),
            **fit_decision,
        }


def _fit_base_estimator(
    prepared: pd.DataFrame,
    y_train: np.ndarray,
    *,
    config: DrawRiskTrainingConfig,
) -> tuple[Any, str, JsonDict]:
    estimator = _hist_gradient_boosting_estimator(config)
    try:
        estimator.fit(prepared, y_train)
        return estimator, "hist_gradient_boosting", {
            "base_estimator": "hist_gradient_boosting",
        }
    except Exception as exc:
        fallback = Pipeline(
            steps=[
                ("imputer", SimpleImputer(strategy="median")),
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
        fallback.fit(prepared, y_train)
        return fallback, "logistic_regression_fallback", {
            "base_estimator": "logistic_regression_fallback",
            "fallback_reason": str(exc),
        }


def _hist_gradient_boosting_estimator(
    config: DrawRiskTrainingConfig,
) -> HistGradientBoostingClassifier:
    try:
        return HistGradientBoostingClassifier(
            max_iter=220,
            learning_rate=0.04,
            l2_regularization=0.12,
            min_samples_leaf=20,
            class_weight="balanced",
            random_state=config.random_state,
        )
    except TypeError:
        return HistGradientBoostingClassifier(
            max_iter=220,
            learning_rate=0.04,
            l2_regularization=0.12,
            min_samples_leaf=20,
            random_state=config.random_state,
        )


def _calibration_skip_reason(
    y_train: np.ndarray,
    config: DrawRiskTrainingConfig,
) -> str | None:
    if len(y_train) < config.min_rows_for_calibration:
        return "skipped_low_volume"
    counts = _class_counts(y_train)
    if len(counts) < 2:
        return "skipped_single_class"
    if min(counts.values()) < config.calibration_cv:
        return "skipped_class_too_rare"
    return None


def _prepare_features(frame: pd.DataFrame, feature_names: list[str]) -> pd.DataFrame:
    return numeric_feature_dataframe(
        frame.reindex(columns=feature_names),
        impute=True,
        forbidden_patterns=(),
    )


def _load_dataset(dataset_path: Path) -> pd.DataFrame:
    suffix = dataset_path.suffix.casefold()
    if suffix == ".csv":
        return pd.read_csv(dataset_path)
    if suffix in {".parquet", ".pq"}:
        return pd.read_parquet(dataset_path, engine="pyarrow")
    raise ValueError("dataset_path must be .csv or .parquet")


def _ensure_draw_target(frame: pd.DataFrame | None) -> pd.DataFrame:
    if frame is None:
        return pd.DataFrame()
    result = frame.copy()
    if result.empty:
        if DRAW_RISK_TARGET not in result.columns:
            result[DRAW_RISK_TARGET] = pd.Series(dtype="int64")
        return result

    if DRAW_RISK_TARGET in result.columns:
        values = pd.to_numeric(result[DRAW_RISK_TARGET], errors="raise")
        invalid = set(values.dropna().astype(int).unique()) - {NOT_DRAW_CLASS, DRAW_CLASS}
        if invalid:
            raise ValueError(f"{DRAW_RISK_TARGET} must contain only 0/1 values")
        result[DRAW_RISK_TARGET] = values.astype(int)
        return result

    if TARGET_COL not in result.columns and OUTCOME_COLUMN in result.columns:
        result[TARGET_COL] = result[OUTCOME_COLUMN]
    if TARGET_COL not in result.columns:
        raise ValueError(f"Dataset must contain {DRAW_RISK_TARGET}, {TARGET_COL}, or outcome")

    invalid_targets = set(result[TARGET_COL].dropna().astype(str)) - {"HOME", "DRAW", "AWAY"}
    if invalid_targets:
        raise ValueError(f"Unknown 1X2 target values: {sorted(invalid_targets)}")
    result[OUTCOME_COLUMN] = result[TARGET_COL].astype(str)
    result[DRAW_RISK_TARGET] = (result[OUTCOME_COLUMN] == "DRAW").astype(int)
    return result


def _predict_proba_safely(estimator: Any, frame: pd.DataFrame) -> Any:
    with warnings.catch_warnings():
        warnings.filterwarnings(
            "ignore",
            message="X does not have valid feature names.*",
            category=UserWarning,
        )
        warnings.filterwarnings(
            "ignore",
            message="X has feature names.*",
            category=UserWarning,
        )
        return estimator.predict_proba(frame)


def _draw_probabilities_from_raw(estimator: Any, raw_matrix: Any) -> list[float]:
    matrix = np.asarray(raw_matrix, dtype=float)
    if matrix.ndim == 1:
        return [float(value) for value in matrix]
    classes = _estimator_classes(estimator)
    if not classes:
        return [float(row[-1]) for row in matrix]
    class_labels = [str(label).casefold() for label in classes]
    if str(DRAW_CLASS) in class_labels:
        index = class_labels.index(str(DRAW_CLASS))
        return [float(row[index]) for row in matrix]
    if "draw" in class_labels:
        index = class_labels.index("draw")
        return [float(row[index]) for row in matrix]
    return [float(row[-1]) for row in matrix]


def _estimator_classes(estimator: Any) -> list[Any]:
    classes = getattr(estimator, "classes_", None)
    if classes is not None:
        return list(classes)
    if hasattr(estimator, "named_steps"):
        classifier = estimator.named_steps.get("classifier")
        classes = getattr(classifier, "classes_", None)
        if classes is not None:
            return list(classes)
    return []


def _class_balance(y_true: np.ndarray) -> JsonDict:
    draw_rate = float(np.mean(y_true)) if len(y_true) else 0.0
    return {
        "draw": draw_rate,
        "not_draw": 1.0 - draw_rate,
        "draw_count": int(np.sum(y_true == DRAW_CLASS)),
        "not_draw_count": int(np.sum(y_true == NOT_DRAW_CLASS)),
    }


def _class_counts(y_true: np.ndarray) -> dict[int, int]:
    return {
        int(label): int(count)
        for label, count in zip(*np.unique(y_true.astype(int), return_counts=True), strict=True)
    }


def _binary_log_loss(y_true: np.ndarray, probabilities: np.ndarray) -> float:
    matrix = np.column_stack([1.0 - probabilities, probabilities])
    return float(log_loss(y_true, matrix, labels=[NOT_DRAW_CLASS, DRAW_CLASS]))


def _roc_auc(y_true: np.ndarray, probabilities: np.ndarray) -> float | None:
    if len(set(y_true.tolist())) < 2:
        return None
    try:
        return float(roc_auc_score(y_true, probabilities))
    except ValueError:
        return None


def _pr_auc(y_true: np.ndarray, probabilities: np.ndarray) -> float | None:
    if len(set(y_true.tolist())) < 2:
        return None
    try:
        return float(average_precision_score(y_true, probabilities))
    except ValueError:
        return None


def _calibration_bins(
    y_true: np.ndarray,
    probabilities: np.ndarray,
    *,
    n_bins: int = 10,
) -> tuple[list[JsonDict], float]:
    buckets: list[list[tuple[float, int]]] = [[] for _ in range(n_bins)]
    for actual, probability in zip(y_true, probabilities, strict=True):
        index = min(int(float(probability) * n_bins), n_bins - 1)
        buckets[index].append((float(probability), int(actual)))

    bins: list[JsonDict] = []
    ece = 0.0
    total = max(len(y_true), 1)
    for index, values in enumerate(buckets):
        lower = index / n_bins
        upper = (index + 1) / n_bins
        if not values:
            bins.append(
                {
                    "bin_lower": lower,
                    "bin_upper": upper,
                    "count": 0,
                    "mean_predicted": None,
                    "actual_fraction": None,
                }
            )
            continue
        mean_predicted = sum(probability for probability, _actual in values) / len(values)
        actual_fraction = sum(actual for _probability, actual in values) / len(values)
        ece += (len(values) / total) * abs(mean_predicted - actual_fraction)
        bins.append(
            {
                "bin_lower": lower,
                "bin_upper": upper,
                "count": len(values),
                "mean_predicted": mean_predicted,
                "actual_fraction": actual_fraction,
            }
        )
    return bins, float(ece)


def _baseline_metrics(
    frame: pd.DataFrame,
    y_true: np.ndarray,
    probabilities: np.ndarray,
    prior_draw_rate: float,
) -> JsonDict:
    prior_values = np.full(len(y_true), _clip_probability(prior_draw_rate), dtype=float)
    model_log_loss = _binary_log_loss(y_true, probabilities)
    model_brier = float(brier_score_loss(y_true, probabilities))
    baselines: JsonDict = {
        "prior_draw_rate": float(prior_values[0]) if len(prior_values) else None,
        "prior_log_loss": _binary_log_loss(y_true, prior_values),
        "prior_brier_score": float(brier_score_loss(y_true, prior_values)),
        "log_loss_delta_vs_prior": model_log_loss - _binary_log_loss(y_true, prior_values),
        "brier_delta_vs_prior": model_brier - float(brier_score_loss(y_true, prior_values)),
    }

    market = _market_draw_probability(frame)
    if market is None:
        baselines["market_draw_probability"] = None
        return baselines

    mask = market.notna().to_numpy()
    if not mask.any():
        baselines["market_draw_probability"] = {"row_count": 0}
        return baselines

    market_values = market.loc[mask].to_numpy(dtype=float)
    y_market = y_true[mask]
    market_log_loss = _binary_log_loss(y_market, market_values)
    market_brier = float(brier_score_loss(y_market, market_values))
    baselines["market_draw_probability"] = {
        "row_count": int(mask.sum()),
        "mean_market_draw": float(np.mean(market_values)),
        "log_loss": market_log_loss,
        "brier_score": market_brier,
        "log_loss_delta_vs_market": _binary_log_loss(y_market, probabilities[mask])
        - market_log_loss,
        "brier_delta_vs_market": float(brier_score_loss(y_market, probabilities[mask]))
        - market_brier,
    }
    return baselines


def _market_draw_probability(frame: pd.DataFrame) -> pd.Series | None:
    for column in (
        "p_market_draw",
        "market_draw",
        "draw_risk_market_prob",
        "market_p_draw",
    ):
        if column not in frame.columns:
            continue
        values = pd.to_numeric(frame[column], errors="coerce")
        return values.where((values >= 0.0) & (values <= 1.0))
    return None


def _clip_probability(value: float) -> float:
    if not math.isfinite(float(value)):
        return 0.5
    return max(min(float(value), 1.0 - EPSILON), EPSILON)


def _json_ready(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_ready(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [_json_ready(item) for item in value]
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        numeric = float(value)
        return numeric if math.isfinite(numeric) else None
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    return value
