"""Training pipeline for the OUCompositeModel."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from football_predictor.ou_model.constants import (
    FALLBACK_WEIGHTS,
    FEATURE_VERSION,
    LEAKAGE_FIELDS,
    OU_THRESHOLD,
)
from football_predictor.ou_model.modeling.ou_calibration import CalibrationDecision, calibrate_ou_model
from football_predictor.ou_model.modeling.ou_catboost import fit_ou_catboost
from football_predictor.ou_model.modeling.ou_lightgbm import fit_ou_lightgbm
from football_predictor.ou_model.modeling.ou_logistic import fit_ou_logistic
from football_predictor.ou_model.modeling.ou_model import OUCompositeModel
from football_predictor.ou_model.modeling.ou_stacking import OUStackingConfig, train_meta_model
from football_predictor.ou_model.modeling.ou_xgboost import fit_ou_xgboost

JsonDict = dict[str, Any]

TARGET_COL = "target_ou25"
DATE_COL = "fixture_date"

FORBIDDEN_PATTERNS: tuple[str, ...] = (
    *LEAKAGE_FIELDS,
    "fixture_id",
    "target_fixture_id",
    "prediction_time",
    "feature_version",
    "ou_feature_version",
    "ou_threshold",
    "ou_feature_snapshot_id",
    "ou_market_odd_over",
    "ou_market_odd_under",
    "league_id",
    "season",
    "home_team_id",
    "away_team_id",
    "match_label",
    "competition",
    "match_date",
)


@dataclass(frozen=True)
class OUTrainingConfig:
    model_version: str = "ou-v1"
    threshold: float = OU_THRESHOLD
    train_ratio: float = 0.60
    valid_ratio: float = 0.20
    calibration_ratio: float = 0.10
    test_ratio: float = 0.10
    min_rows_for_meta: int = 80
    feature_min_coverage: float = 0.05
    max_features: int = 120
    random_state: int = 42
    fit_lgbm: bool = True
    fit_xgb: bool = True
    fit_catboost: bool = True


@dataclass
class OUTrainResult:
    model: OUCompositeModel
    model_path: Path
    metrics: JsonDict
    feature_names: list[str]


def _is_forbidden(col: str) -> bool:
    col_lower = col.lower()
    return any(col_lower == f or col_lower.startswith(f) for f in FORBIDDEN_PATTERNS)


def _is_numeric_column(series: "pd.Series") -> bool:  # type: ignore[name-defined]
    """Return True if series contains only scalar numerics (no lists/dicts)."""
    import pandas as pd
    if pd.api.types.is_numeric_dtype(series):
        return True
    if series.dtype == object:
        sample = series.dropna().head(20)
        return all(isinstance(v, (int, float)) for v in sample)
    return False


def select_ou_feature_names(
    frame: pd.DataFrame,
    *,
    min_coverage: float = 0.05,
    max_features: int = 120,
) -> list[str]:
    """Select O/U model features from a training dataset."""
    candidates = [
        col for col in frame.columns
        if col != TARGET_COL and not _is_forbidden(col) and _is_numeric_column(frame[col])
    ]
    n_rows = len(frame)
    if n_rows == 0:
        return candidates[:max_features]

    coverage = {
        col: frame[col].notna().sum() / n_rows
        for col in candidates
    }
    selected = [col for col in candidates if coverage[col] >= min_coverage]

    if len(selected) > max_features:
        if TARGET_COL in frame.columns:
            from sklearn.feature_selection import mutual_info_classif
            from sklearn.impute import SimpleImputer
            imp = SimpleImputer(strategy="median")
            X = imp.fit_transform(frame[selected].fillna(0))
            y = frame[TARGET_COL].values
            mi = mutual_info_classif(X, y, random_state=42)
            ranked = sorted(zip(selected, mi, strict=True), key=lambda x: x[1], reverse=True)
            selected = [col for col, _ in ranked[:max_features]]
        else:
            selected = selected[:max_features]

    if "market_p_over25" not in selected and "market_p_over25" in frame.columns:
        if len(selected) >= max_features:
            selected = selected[:-1]
        selected.append("market_p_over25")

    return selected


def ou_temporal_split(
    frame: pd.DataFrame,
    *,
    train_ratio: float = 0.60,
    valid_ratio: float = 0.20,
    calibration_ratio: float = 0.10,
    test_ratio: float = 0.10,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Four-way strictly temporal split by fixture_date."""
    sorted_frame = frame.sort_values(DATE_COL).reset_index(drop=True)
    n = len(sorted_frame)
    i_train = int(n * train_ratio)
    i_valid = i_train + int(n * valid_ratio)
    i_cal = i_valid + int(n * calibration_ratio)
    return (
        sorted_frame.iloc[:i_train],
        sorted_frame.iloc[i_train:i_valid],
        sorted_frame.iloc[i_valid:i_cal],
        sorted_frame.iloc[i_cal:],
    )


def _compute_metrics(
    y_true: np.ndarray,
    p_over: np.ndarray,
    split_name: str,
) -> JsonDict:
    from sklearn.metrics import log_loss, brier_score_loss
    return {
        "split": split_name,
        "n_rows": int(len(y_true)),
        "brier_score": float(brier_score_loss(y_true, p_over)),
        "log_loss": float(log_loss(y_true, p_over, labels=[0, 1])),
        "over_rate": float(y_true.mean()),
        "mean_p_over": float(p_over.mean()),
    }


def train_ou_model_from_dataset(
    dataset_path: Path,
    output_dir: Path,
    *,
    config: OUTrainingConfig | None = None,
) -> OUTrainResult:
    """Load parquet dataset, split temporally, train OUCompositeModel, save artifacts."""
    resolved_config = config or OUTrainingConfig()

    if dataset_path.suffix in (".parquet", ".pq"):
        frame = pd.read_parquet(dataset_path)
    else:
        frame = pd.read_csv(dataset_path)

    if TARGET_COL not in frame.columns:
        raise ValueError(f"Dataset missing target column '{TARGET_COL}'")
    if DATE_COL not in frame.columns:
        raise ValueError(f"Dataset missing date column '{DATE_COL}'")

    train_frame, valid_frame, cal_frame, test_frame = ou_temporal_split(
        frame,
        train_ratio=resolved_config.train_ratio,
        valid_ratio=resolved_config.valid_ratio,
        calibration_ratio=resolved_config.calibration_ratio,
        test_ratio=resolved_config.test_ratio,
    )

    feature_names = select_ou_feature_names(
        train_frame,
        min_coverage=resolved_config.feature_min_coverage,
        max_features=resolved_config.max_features,
    )

    model, metrics = train_ou_model_from_frames(
        train_frame=train_frame,
        valid_frame=valid_frame,
        cal_frame=cal_frame,
        test_frame=test_frame,
        feature_names=feature_names,
        config=resolved_config,
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    model_path = output_dir / "model.joblib"
    model.save(model_path)

    coverage = {
        col: float(frame[col].notna().sum() / len(frame))
        for col in feature_names
        if col in frame.columns
    }
    (output_dir / "feature_coverage.json").write_text(json.dumps(coverage, indent=2))
    (output_dir / "feature_names.json").write_text(json.dumps(feature_names, indent=2))
    (output_dir / "metrics.json").write_text(json.dumps(metrics, indent=2))
    (output_dir / "metadata.json").write_text(json.dumps({
        "artifact_format": "ou_composite_model_v1",
        "model_version": resolved_config.model_version,
        "threshold": resolved_config.threshold,
        "classes": ["UNDER", "OVER"],
        "training_rows": len(train_frame),
        "validation_rows": len(valid_frame),
        "calibration_rows": len(cal_frame),
        "test_rows": len(test_frame),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "calibration_decision": model.calibration_decision,
        "fallback_weights": model.fallback_weights,
    }, indent=2))

    return OUTrainResult(
        model=model,
        model_path=model_path,
        metrics=metrics,
        feature_names=feature_names,
    )


def train_ou_model_from_frames(
    train_frame: pd.DataFrame,
    valid_frame: pd.DataFrame,
    cal_frame: pd.DataFrame,
    test_frame: pd.DataFrame,
    feature_names: list[str],
    *,
    config: OUTrainingConfig | None = None,
) -> tuple[OUCompositeModel, JsonDict]:
    """Train all layers and return (OUCompositeModel, metrics_dict)."""
    resolved_config = config or OUTrainingConfig()
    rs = resolved_config.random_state

    available_features = [f for f in feature_names if f in train_frame.columns]
    y_train = train_frame[TARGET_COL].values.astype(int)
    X_train = train_frame[available_features].fillna(0)

    logistic_pipe, logistic_features = fit_ou_logistic(X_train, y_train, random_state=rs)

    lgbm_model = None
    if resolved_config.fit_lgbm:
        try:
            lgbm_model = fit_ou_lightgbm(X_train, y_train, available_features, random_state=rs)
        except Exception:
            pass

    xgb_model = None
    if resolved_config.fit_xgb:
        try:
            xgb_model = fit_ou_xgboost(X_train, y_train, available_features, random_state=rs)
        except Exception:
            pass

    catboost_model = None
    if resolved_config.fit_catboost:
        try:
            catboost_model = fit_ou_catboost(X_train, y_train, available_features, random_state=rs)
        except Exception:
            pass

    valid_with_preds = valid_frame.copy()
    expert_names: list[str] = []
    X_valid = valid_frame[available_features].fillna(0)

    # Column names must match the keys used in expert_probabilities_for_row() at inference time.
    valid_with_preds["logistic"] = logistic_pipe.predict_proba(
        X_valid[logistic_features].fillna(0.5)
    )[:, 1]
    expert_names.append("logistic")

    if lgbm_model is not None:
        valid_with_preds["lgbm"] = lgbm_model.predict_proba_over(X_valid)
        expert_names.append("lgbm")
    if xgb_model is not None:
        try:
            valid_with_preds["xgb"] = xgb_model.predict_proba_over(X_valid)
            expert_names.append("xgb")
        except Exception:
            pass
    if catboost_model is not None:
        try:
            valid_with_preds["catboost"] = catboost_model.predict_proba_over(X_valid)
            expert_names.append("catboost")
        except Exception:
            pass

    from football_predictor.ou_model.modeling.ou_poisson import poisson_ou_predict
    valid_with_preds["poisson"] = [
        poisson_ou_predict(row)[0]
        for _, row in valid_frame.iterrows()
    ]
    expert_names.append("poisson")

    stacking_config = OUStackingConfig(
        min_rows_for_meta=resolved_config.min_rows_for_meta,
        random_state=rs,
    )
    meta_model, meta_features_order = train_meta_model(
        valid_with_preds,
        expert_names,
        TARGET_COL,
        config=stacking_config,
    )

    model_stub = OUCompositeModel(
        model_version=resolved_config.model_version,
        threshold=resolved_config.threshold,
        feature_names=available_features,
        poisson_config={},
        logistic_model=logistic_pipe,
        logistic_features=logistic_features,
        lgbm_model=lgbm_model,
        xgb_model=xgb_model,
        catboost_model=catboost_model,
        meta_model=meta_model,
        meta_features_order=meta_features_order,
        fallback_weights=dict(FALLBACK_WEIGHTS),
    )

    cal_p_over = model_stub.predict_proba_over(cal_frame[available_features].fillna(0))
    y_cal = cal_frame[TARGET_COL].values.astype(int)
    calibrator, cal_decision = calibrate_ou_model(cal_p_over, y_cal)

    model_stub.calibration_model = calibrator
    model_stub.calibration_decision = {
        "applied": cal_decision.applied,
        "method": cal_decision.method,
        "rows_used": cal_decision.rows_used,
        "reason": cal_decision.reason,
    }
    model_stub.feature_coverage = {}

    from sklearn.metrics import brier_score_loss, log_loss
    from football_predictor.ou_model.modeling.ou_calibration import apply_calibration_array
    import numpy as np

    metrics: JsonDict = {}
    for split_name, split_frame in [
        ("train", train_frame),
        ("valid", valid_frame),
        ("calibration", cal_frame),
        ("test", test_frame),
    ]:
        if len(split_frame) == 0:
            continue
        p = model_stub.predict_proba_over(split_frame[available_features].fillna(0))
        y = split_frame[TARGET_COL].values.astype(int)
        metrics[split_name] = {
            "n_rows": int(len(y)),
            "brier_score": float(brier_score_loss(y, p)),
            "log_loss": float(log_loss(y, p, labels=[0, 1])),
            "over_rate": float(y.mean()),
            "mean_p_over": float(p.mean()),
        }

    return model_stub, metrics
