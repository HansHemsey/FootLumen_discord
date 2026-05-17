"""V3 final stacker model and training helpers."""

from __future__ import annotations

import json
import math
import warnings
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import joblib  # type: ignore[import-untyped]
import numpy as np
import pandas as pd  # type: ignore[import-untyped]
from sklearn.linear_model import LogisticRegression  # type: ignore[import-untyped]

from football_predictor.modeling.constants import CLASSES
from football_predictor.modeling.evaluation import evaluate_probabilities
from football_predictor.modeling.probabilities import ProbabilityTriple
from football_predictor.modeling.v3.constants import (
    DEFAULT_V3_STACKER_MODEL_VERSION,
    OUTCOME_COLUMN,
)
from football_predictor.modeling.v3.fusion import (
    V3FusionWeights,
    deterministic_v3_fusion,
    market_probability_from_row,
    v2_probability_from_row,
)
from football_predictor.utils.time import utc_now

JsonDict = dict[str, Any]

ARTIFACT_FORMAT = "v3_stacker_model"
TARGET_COL = "target"
STACKER_FEATURE_NAMES = [
    "p_v3_draw_risk",
    "p_v3_home_no_draw",
    "p_v3_away_no_draw",
    "p_v2_home",
    "p_v2_draw",
    "p_v2_away",
    "p_market_home",
    "p_market_draw",
    "p_market_away",
    "p_market_home_no_draw",
    "p_market_away_no_draw",
    "market_overround",
    "market_dispersion",
    "p_api_home",
    "p_api_draw",
    "p_api_away",
    "data_quality_score",
    "official_lineup_available_flag",
    "has_v2_signal",
    "has_market_signal",
    "has_api_signal",
]


@dataclass(frozen=True)
class V3StackerTrainingConfig:
    """Training options for the V3 final stacker."""

    model_version: str = DEFAULT_V3_STACKER_MODEL_VERSION
    min_rows_for_stacker: int = 45
    random_state: int = 42


@dataclass(frozen=True)
class V3StackerTrainResult:
    """Paths and metrics produced by V3 stacker training."""

    model: V3StackerModel
    model_path: Path
    metadata_path: Path
    metrics_path: Path
    metrics: JsonDict


@dataclass
class V3StackerModel:
    """Final V3 1X2 stacker with deterministic fallback."""

    model_version: str
    estimator: Any | None
    feature_names: list[str]
    training_decision: JsonDict
    source_weights: V3FusionWeights = field(default_factory=V3FusionWeights)
    classes: list[str] = field(default_factory=lambda: list(CLASSES))
    artifact_format: str = ARTIFACT_FORMAT

    def predict_proba(self, frame: pd.DataFrame) -> list[list[float]]:
        """Return final V3 probabilities ordered as HOME, DRAW, AWAY."""
        if self.estimator is None:
            return [self._fallback_for_row(row).to_vector() for _, row in frame.iterrows()]
        prepared = build_stacker_feature_frame(frame, feature_names=self.feature_names)
        raw_matrix = _predict_proba_safely(self.estimator, prepared)
        return [
            _probability_from_estimator_output(self.estimator, raw).to_vector()
            for raw in raw_matrix
        ]

    def predict_probability_triples(self, frame: pd.DataFrame) -> list[ProbabilityTriple]:
        return [ProbabilityTriple.from_vector(row) for row in self.predict_proba(frame)]

    def _fallback_for_row(self, row: pd.Series) -> ProbabilityTriple:
        return deterministic_v3_fusion(
            draw_probability=_first_float(row, "p_v3_draw_risk", default=1.0 / 3.0),
            home_no_draw_probability=_first_float(
                row,
                "p_v3_home_no_draw",
                default=0.5,
            ),
            v2_probability=v2_probability_from_row(row),
            market_probability=market_probability_from_row(row),
            weights=self.source_weights,
        )

    def save(self, path: Path) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self, path)
        return path

    @classmethod
    def load(cls, path: Path) -> V3StackerModel:
        model_path = path / "model.joblib" if path.is_dir() else path
        obj = joblib.load(model_path)
        if not isinstance(obj, cls):
            raise TypeError(f"Expected V3StackerModel at {model_path}, got {type(obj)}")
        return obj


def train_v3_stacker_from_frame(
    frame: pd.DataFrame,
    output_dir: Path,
    *,
    eval_frame: pd.DataFrame | None = None,
    config: V3StackerTrainingConfig | None = None,
) -> V3StackerTrainResult:
    """Train the final V3 stacker on an already-built validation fold."""
    resolved_config = config or V3StackerTrainingConfig()
    train = _ensure_outcome(frame)
    evaluation = _ensure_outcome(eval_frame) if eval_frame is not None else pd.DataFrame()
    estimator: Any | None
    training_decision: JsonDict

    y_train = list(train[OUTCOME_COLUMN].astype(str)) if not train.empty else []
    skip_reason = _stacker_skip_reason(y_train, resolved_config)
    if skip_reason is not None:
        estimator = None
        training_decision = {
            "method": "deterministic_fallback",
            "reason": skip_reason,
            "rows": len(train),
            "class_counts": _class_counts(y_train),
        }
    else:
        prepared = build_stacker_feature_frame(train)
        estimator = LogisticRegression(max_iter=2000, random_state=resolved_config.random_state)
        estimator.fit(prepared, y_train)
        training_decision = {
            "method": "logistic_regression",
            "rows": len(train),
            "class_counts": _class_counts(y_train),
        }

    model = V3StackerModel(
        model_version=resolved_config.model_version,
        estimator=estimator,
        feature_names=list(STACKER_FEATURE_NAMES),
        training_decision=training_decision,
    )
    metrics = {
        "model_version": model.model_version,
        "classes": model.classes,
        "training_decision": training_decision,
        "train": evaluate_v3_stacker_frame(model, train),
        "test": evaluate_v3_stacker_frame(model, evaluation) if not evaluation.empty else None,
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    model_path = model.save(output_dir / "model.joblib")
    metadata_path = output_dir / "metadata.json"
    metrics_path = output_dir / "metrics.json"
    metadata_path.write_text(
        json.dumps(
            _json_ready(
                {
                    "artifact_format": model.artifact_format,
                    "model_version": model.model_version,
                    "created_at": utc_now().isoformat(),
                    "classes": model.classes,
                    "feature_names": model.feature_names,
                    "training_rows": len(train),
                    "test_rows": len(evaluation),
                    "training_decision": model.training_decision,
                    "source_weights": model.source_weights.as_dict(),
                }
            ),
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    metrics_path.write_text(
        json.dumps(_json_ready(metrics), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return V3StackerTrainResult(
        model=model,
        model_path=model_path,
        metadata_path=metadata_path,
        metrics_path=metrics_path,
        metrics=metrics,
    )


def evaluate_v3_stacker_frame(model: V3StackerModel, frame: pd.DataFrame) -> JsonDict:
    prepared = _ensure_outcome(frame)
    if prepared.empty:
        return {"row_count": 0}
    y_true = list(prepared[OUTCOME_COLUMN].astype(str))
    predictions = model.predict_probability_triples(prepared)
    return evaluate_probabilities(y_true, predictions)


def build_stacker_feature_frame(
    frame: pd.DataFrame,
    *,
    feature_names: list[str] | None = None,
) -> pd.DataFrame:
    """Build a dense numeric stacker input matrix with source availability flags."""
    result = pd.DataFrame(index=frame.index)
    result["p_v3_draw_risk"] = _series(frame, "p_v3_draw_risk", default=1.0 / 3.0)
    result["p_v3_home_no_draw"] = _series(frame, "p_v3_home_no_draw", default=0.5)
    if "p_v3_away_no_draw" in frame.columns:
        result["p_v3_away_no_draw"] = _series(frame, "p_v3_away_no_draw", default=0.5)
    else:
        result["p_v3_away_no_draw"] = 1.0 - result["p_v3_home_no_draw"]

    has_v2 = _all_columns_available(frame, ["p_v2_home", "p_v2_draw", "p_v2_away"])
    result["p_v2_home"] = _series(frame, "p_v2_home", default=1.0 / 3.0)
    result["p_v2_draw"] = _series(frame, "p_v2_draw", default=1.0 / 3.0)
    result["p_v2_away"] = _series(frame, "p_v2_away", default=1.0 / 3.0)

    result["p_market_home"] = _first_series(frame, ["p_market_home", "market_home"], 1.0 / 3.0)
    result["p_market_draw"] = _first_series(frame, ["p_market_draw", "market_draw"], 1.0 / 3.0)
    result["p_market_away"] = _first_series(frame, ["p_market_away", "market_away"], 1.0 / 3.0)
    has_market = _any_column_group_available(
        frame,
        [
            ["p_market_home", "p_market_draw", "p_market_away"],
            ["market_home", "market_draw", "market_away"],
        ],
    )
    market_total = result["p_market_home"] + result["p_market_away"]
    result["p_market_home_no_draw"] = (result["p_market_home"] / market_total).where(
        market_total > 0,
        0.5,
    )
    result["p_market_away_no_draw"] = 1.0 - result["p_market_home_no_draw"]
    result["market_overround"] = _series(frame, "market_overround", default=0.0)
    result["market_dispersion"] = _first_series(
        frame,
        ["market_dispersion", "bookmaker_dispersion_draw"],
        0.0,
    )

    result["p_api_home"] = _first_series(frame, ["p_api_home", "api_pred_home"], 1.0 / 3.0)
    result["p_api_draw"] = _first_series(frame, ["p_api_draw", "api_pred_draw"], 1.0 / 3.0)
    result["p_api_away"] = _first_series(frame, ["p_api_away", "api_pred_away"], 1.0 / 3.0)
    has_api = _any_column_group_available(
        frame,
        [
            ["p_api_home", "p_api_draw", "p_api_away"],
            ["api_pred_home", "api_pred_draw", "api_pred_away"],
        ],
    )

    result["data_quality_score"] = _first_series(
        frame,
        ["data_quality_score", "overall_data_quality_score"],
        0.0,
    )
    result["official_lineup_available_flag"] = _series(
        frame,
        "official_lineup_available_flag",
        default=0.0,
    )
    result["has_v2_signal"] = has_v2.astype(float)
    result["has_market_signal"] = has_market.astype(float)
    result["has_api_signal"] = has_api.astype(float)
    result = result.loc[:, feature_names or STACKER_FEATURE_NAMES]
    return result.fillna(
        {
            "p_v3_draw_risk": 1.0 / 3.0,
            "p_v3_home_no_draw": 0.5,
            "p_v3_away_no_draw": 0.5,
            "p_v2_home": 1.0 / 3.0,
            "p_v2_draw": 1.0 / 3.0,
            "p_v2_away": 1.0 / 3.0,
            "p_market_home": 1.0 / 3.0,
            "p_market_draw": 1.0 / 3.0,
            "p_market_away": 1.0 / 3.0,
            "p_market_home_no_draw": 0.5,
            "p_market_away_no_draw": 0.5,
            "market_overround": 0.0,
            "market_dispersion": 0.0,
            "p_api_home": 1.0 / 3.0,
            "p_api_draw": 1.0 / 3.0,
            "p_api_away": 1.0 / 3.0,
            "data_quality_score": 0.0,
            "official_lineup_available_flag": 0.0,
            "has_v2_signal": 0.0,
            "has_market_signal": 0.0,
            "has_api_signal": 0.0,
        }
    )


def _stacker_skip_reason(y_train: list[str], config: V3StackerTrainingConfig) -> str | None:
    if len(y_train) < config.min_rows_for_stacker:
        return "skipped_low_volume"
    if set(y_train) != set(CLASSES):
        return "skipped_missing_class"
    return None


def _ensure_outcome(frame: pd.DataFrame | None) -> pd.DataFrame:
    if frame is None:
        return pd.DataFrame()
    result = frame.copy()
    if result.empty:
        if OUTCOME_COLUMN not in result.columns:
            result[OUTCOME_COLUMN] = pd.Series(dtype="object")
        return result
    if OUTCOME_COLUMN not in result.columns and TARGET_COL in result.columns:
        result[OUTCOME_COLUMN] = result[TARGET_COL].astype(str)
    if OUTCOME_COLUMN not in result.columns:
        raise ValueError("V3 stacker frames require outcome or target")
    invalid = set(result[OUTCOME_COLUMN].dropna().astype(str)) - set(CLASSES)
    if invalid:
        raise ValueError(f"Unknown 1X2 outcome values: {sorted(invalid)}")
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


def _probability_from_estimator_output(estimator: Any, raw: Any) -> ProbabilityTriple:
    classes = [str(label) for label in getattr(estimator, "classes_", CLASSES)]
    values = {label: 0.0 for label in CLASSES}
    for label, probability in zip(classes, raw, strict=False):
        if label in values:
            values[label] = float(probability)
    return ProbabilityTriple.from_mapping(values)


def _all_columns_available(frame: pd.DataFrame, columns: list[str]) -> pd.Series:
    if not all(column in frame.columns for column in columns):
        return pd.Series([False] * len(frame), index=frame.index)
    return frame[columns].notna().all(axis=1)


def _any_column_group_available(
    frame: pd.DataFrame,
    column_groups: list[list[str]],
) -> pd.Series:
    result = pd.Series([False] * len(frame), index=frame.index)
    for columns in column_groups:
        result = result | _all_columns_available(frame, columns)
    return result


def _series(frame: pd.DataFrame, column: str, *, default: float) -> pd.Series:
    if column not in frame.columns:
        return pd.Series([default] * len(frame), index=frame.index, dtype=float)
    return pd.to_numeric(frame[column], errors="coerce")


def _first_series(frame: pd.DataFrame, columns: list[str], default: float) -> pd.Series:
    result = pd.Series([pd.NA] * len(frame), index=frame.index, dtype="Float64")
    for column in columns:
        if column in frame.columns:
            result = result.combine_first(pd.to_numeric(frame[column], errors="coerce"))
    return result.astype(float).fillna(default)


def _first_float(row: pd.Series, column: str, *, default: float) -> float:
    if column not in row:
        return default
    try:
        value = float(row[column])
    except (TypeError, ValueError):
        return default
    if not math.isfinite(value):
        return default
    return value


def _class_counts(y_train: list[str]) -> dict[str, int]:
    return {label: y_train.count(label) for label in CLASSES}


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
