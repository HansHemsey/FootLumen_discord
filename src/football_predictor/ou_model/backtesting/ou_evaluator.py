"""Walk-forward backtesting for the O/U 2.5 model."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from football_predictor.ou_model.backtesting.ou_metrics import (
    binary_brier_score,
    binary_log_loss,
    calibration_bins_binary,
    roi_simulation,
)
from football_predictor.ou_model.modeling.ou_train import (
    OUTrainingConfig,
    select_ou_feature_names,
    train_ou_model_from_frames,
)

logger = logging.getLogger(__name__)

JsonDict = dict[str, Any]

TARGET_COL = "target_ou25"
DATE_COL = "fixture_date"

BASELINES = ("poisson", "logistic", "lgbm", "xgb", "catboost", "ensemble", "market")


@dataclass(frozen=True)
class OUBacktestConfig:
    n_splits: int = 5
    min_train_rows: int = 300
    edge_thresholds: tuple[float, ...] = (0.02, 0.03, 0.05)
    kelly_fraction: float = 0.25
    train_ratio: float = 0.60
    valid_ratio: float = 0.20
    calibration_ratio: float = 0.10
    feature_min_coverage: float = 0.05
    max_features: int = 120
    random_state: int = 42
    fit_lgbm: bool = True
    fit_xgb: bool = True
    fit_catboost: bool = True


@dataclass
class OUFoldResult:
    fold: int
    n_train: int
    n_test: int
    test_date_start: str
    test_date_end: str
    metrics_per_model: dict[str, JsonDict]
    roi_per_model: dict[str, dict[str, JsonDict]]  # model -> edge_threshold -> roi_dict
    calibration_bins: list[JsonDict]
    prediction_rows: list[JsonDict] = field(default_factory=list)


@dataclass
class OUBacktestResult:
    config: OUBacktestConfig
    folds: list[OUFoldResult]
    aggregate: JsonDict
    dataset_path: str | None = None
    output_dir: str | None = None


def _fold_splits(
    frame: pd.DataFrame,
    n_splits: int,
    min_train_rows: int,
) -> list[tuple[pd.DataFrame, pd.DataFrame]]:
    """Return list of (train_df, test_df) for walk-forward folds."""
    sorted_frame = frame.sort_values(DATE_COL).reset_index(drop=True)
    n = len(sorted_frame)
    fold_size = n // (n_splits + 1)

    splits: list[tuple[pd.DataFrame, pd.DataFrame]] = []
    for k in range(1, n_splits + 1):
        train_end = k * fold_size
        test_end = min((k + 1) * fold_size, n)
        if train_end < min_train_rows or test_end <= train_end:
            continue
        train_df = sorted_frame.iloc[:train_end].copy()
        test_df = sorted_frame.iloc[train_end:test_end].copy()
        splits.append((train_df, test_df))

    return splits


def _metrics_for_predictions(
    y_true: np.ndarray,
    p_over: np.ndarray,
    odd_over: list[float | None],
    odd_under: list[float | None],
    *,
    edge_thresholds: tuple[float, ...],
    kelly_fraction: float,
) -> tuple[JsonDict, dict[str, JsonDict]]:
    """Return (base_metrics, roi_per_threshold)."""
    base: JsonDict = {
        "brier_score": binary_brier_score(list(y_true), list(p_over)),
        "log_loss": binary_log_loss(list(y_true), list(p_over)),
        "over_rate": float(y_true.mean()),
        "mean_p_over": float(p_over.mean()),
        "n_rows": int(len(y_true)),
    }
    roi_per_threshold: dict[str, JsonDict] = {}
    for et in edge_thresholds:
        roi_per_threshold[f"edge_{et:.2f}"] = roi_simulation(
            list(y_true),
            list(p_over),
            odd_over,
            odd_under,
            edge_threshold=et,
            kelly_fraction=kelly_fraction,
        )
    return base, roi_per_threshold


def _market_p_over(
    odd_over: float,
    odd_under: float,
) -> float:
    q_o = 1 / odd_over
    q_u = 1 / odd_under
    return q_o / (q_o + q_u)


def _run_single_fold(
    fold_idx: int,
    train_df: pd.DataFrame,
    test_df: pd.DataFrame,
    config: OUBacktestConfig,
) -> OUFoldResult:
    logger.info(
        "Fold %d: train=%d rows, test=%d rows",
        fold_idx, len(train_df), len(test_df),
    )

    n = len(train_df)
    i_valid = int(n * config.train_ratio)
    i_cal = i_valid + int(n * config.valid_ratio)

    pure_train = train_df.iloc[:i_valid]
    valid_df = train_df.iloc[i_valid:i_cal]
    cal_df = train_df.iloc[i_cal:]

    feature_names = select_ou_feature_names(
        pure_train,
        min_coverage=config.feature_min_coverage,
        max_features=config.max_features,
    )
    available = [f for f in feature_names if f in pure_train.columns]

    training_config = OUTrainingConfig(
        train_ratio=config.train_ratio,
        valid_ratio=config.valid_ratio,
        calibration_ratio=config.calibration_ratio,
        test_ratio=0.0,
        min_rows_for_meta=80,
        feature_min_coverage=config.feature_min_coverage,
        max_features=config.max_features,
        random_state=config.random_state,
        fit_lgbm=config.fit_lgbm,
        fit_xgb=config.fit_xgb,
        fit_catboost=config.fit_catboost,
    )

    try:
        model, _ = train_ou_model_from_frames(
            train_frame=pure_train,
            valid_frame=valid_df if len(valid_df) > 0 else pure_train.iloc[-10:],
            cal_frame=cal_df if len(cal_df) > 0 else pure_train.iloc[-5:],
            test_frame=test_df,
            feature_names=available,
            config=training_config,
        )
    except Exception as exc:
        logger.warning("Fold %d training failed: %s", fold_idx, exc)
        return OUFoldResult(
            fold=fold_idx,
            n_train=len(train_df),
            n_test=len(test_df),
            test_date_start=str(test_df[DATE_COL].min()),
            test_date_end=str(test_df[DATE_COL].max()),
            metrics_per_model={},
            roi_per_model={},
            calibration_bins=[],
            prediction_rows=[],
        )

    y_test = test_df[TARGET_COL].values.astype(int)
    X_test = test_df[available].fillna(0)

    odd_over_col = test_df.get("ou_market_odd_over", pd.Series([None] * len(test_df)))
    odd_under_col = test_df.get("ou_market_odd_under", pd.Series([None] * len(test_df)))
    odd_over_list: list[float | None] = [
        float(v) if pd.notna(v) else None for v in odd_over_col
    ]
    odd_under_list: list[float | None] = [
        float(v) if pd.notna(v) else None for v in odd_under_col
    ]

    metrics_per_model: dict[str, JsonDict] = {}
    roi_per_model: dict[str, dict[str, JsonDict]] = {}

    # Ensemble
    p_ensemble = model.predict_proba_over(X_test)
    m, r = _metrics_for_predictions(
        y_test, p_ensemble, odd_over_list, odd_under_list,
        edge_thresholds=config.edge_thresholds,
        kelly_fraction=config.kelly_fraction,
    )
    metrics_per_model["ensemble"] = m
    roi_per_model["ensemble"] = r

    # Expert breakdowns
    expert_preds: dict[str, list[float]] = {
        "poisson": [], "logistic": [], "lgbm": [], "xgb": [], "catboost": [],
    }
    for _, row in test_df.iterrows():
        ep = model.expert_probabilities_for_row(row)
        for k in expert_preds:
            expert_preds[k].append(ep.get(k, 0.5))

    for model_name, p_list in expert_preds.items():
        p_arr = np.array(p_list, dtype=float)
        m, r = _metrics_for_predictions(
            y_test, p_arr, odd_over_list, odd_under_list,
            edge_thresholds=config.edge_thresholds,
            kelly_fraction=config.kelly_fraction,
        )
        metrics_per_model[model_name] = m
        roi_per_model[model_name] = r

    # Market-only baseline
    market_p_list: list[float] = []
    for oo, ou in zip(odd_over_list, odd_under_list, strict=True):
        if oo is not None and ou is not None and oo > 1 and ou > 1:
            market_p_list.append(_market_p_over(oo, ou))
        else:
            market_p_list.append(0.5)
    p_market = np.array(market_p_list, dtype=float)
    m, r = _metrics_for_predictions(
        y_test, p_market, odd_over_list, odd_under_list,
        edge_thresholds=config.edge_thresholds,
        kelly_fraction=config.kelly_fraction,
    )
    metrics_per_model["market"] = m
    roi_per_model["market"] = r

    cal_bins = calibration_bins_binary(list(y_test), list(p_ensemble), n_bins=10)
    prediction_rows = _prediction_rows_for_fold(
        fold_idx,
        test_df,
        y_test,
        p_ensemble,
        p_market,
        odd_over_list,
        odd_under_list,
    )

    return OUFoldResult(
        fold=fold_idx,
        n_train=len(train_df),
        n_test=len(test_df),
        test_date_start=str(test_df[DATE_COL].min()),
        test_date_end=str(test_df[DATE_COL].max()),
        metrics_per_model=metrics_per_model,
        roi_per_model=roi_per_model,
        calibration_bins=cal_bins,
        prediction_rows=prediction_rows,
    )


def _prediction_rows_for_fold(
    fold_idx: int,
    test_df: pd.DataFrame,
    y_true: np.ndarray,
    p_ensemble: np.ndarray,
    p_market: np.ndarray,
    odd_over_list: list[float | None],
    odd_under_list: list[float | None],
) -> list[JsonDict]:
    rows: list[JsonDict] = []
    for row_idx, (_, row) in enumerate(test_df.iterrows()):
        closing_odd_over = _first_numeric(
            row,
            (
                "closing_ou_market_odd_over",
                "ou_closing_odd_over",
                "closing_market_odd_over25",
                "market_closing_odd_over25",
            ),
        )
        closing_odd_under = _first_numeric(
            row,
            (
                "closing_ou_market_odd_under",
                "ou_closing_odd_under",
                "closing_market_odd_under25",
                "market_closing_odd_under25",
            ),
        )
        rows.append({
            "fold": fold_idx,
            "row_index": row_idx,
            "fixture_id": _json_scalar(row.get("fixture_id")),
            "fixture_date": _json_scalar(row.get(DATE_COL)),
            "league_id": _json_scalar(row.get("league_id")),
            "season": _json_scalar(row.get("season")),
            "target_ou25": int(y_true[row_idx]),
            "p_over": float(p_ensemble[row_idx]),
            "p_under": float(1.0 - p_ensemble[row_idx]),
            "market_p_over": (
                float(p_market[row_idx])
                if odd_over_list[row_idx] is not None and odd_under_list[row_idx] is not None
                else None
            ),
            "market_p_under": (
                float(1.0 - p_market[row_idx])
                if odd_over_list[row_idx] is not None and odd_under_list[row_idx] is not None
                else None
            ),
            "odd_over": odd_over_list[row_idx],
            "odd_under": odd_under_list[row_idx],
            "closing_odd_over": closing_odd_over,
            "closing_odd_under": closing_odd_under,
            "data_quality_score": _first_numeric(
                row,
                (
                    "ou_data_quality_score",
                    "overall_data_quality_score",
                    "publication_data_quality_score",
                    "data_quality_score",
                ),
            ),
            "bookmaker_count": _first_numeric(
                row,
                (
                    "market_ou_bookmaker_count",
                    "ou_market_bookmaker_count",
                    "market_bookmaker_count",
                    "bookmaker_count",
                ),
            ),
        })
    return rows


def _first_numeric(row: pd.Series, keys: tuple[str, ...]) -> float | None:
    for key in keys:
        if key not in row:
            continue
        value = row.get(key)
        if pd.isna(value):
            continue
        try:
            return float(value)
        except (TypeError, ValueError):
            continue
    return None


def _json_scalar(value: Any) -> Any:
    if pd.isna(value):
        return None
    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:
            return value
    return value


def _aggregate_fold_results(folds: list[OUFoldResult]) -> JsonDict:
    """Average metrics across folds for each model."""
    if not folds:
        return {}

    all_models = set()
    for fold in folds:
        all_models.update(fold.metrics_per_model.keys())

    agg: JsonDict = {}
    for model_name in sorted(all_models):
        fold_metrics = [
            f.metrics_per_model[model_name]
            for f in folds
            if model_name in f.metrics_per_model
        ]
        if not fold_metrics:
            continue
        keys = [k for k in fold_metrics[0] if isinstance(fold_metrics[0][k], (int, float))]
        agg[model_name] = {
            k: float(np.mean([fm[k] for fm in fold_metrics if k in fm]))
            for k in keys
        }
        agg[model_name]["n_folds"] = len(fold_metrics)

    return agg


def run_ou_backtest(
    dataset_path: Path,
    *,
    output_dir: Path | None = None,
    config: OUBacktestConfig | None = None,
) -> OUBacktestResult:
    """Walk-forward O/U backtest over the full dataset.

    Trains a fresh model on each fold's train portion, evaluates on held-out
    test portion, then aggregates metrics across folds.
    """
    resolved_config = config or OUBacktestConfig()

    if dataset_path.suffix in (".parquet", ".pq"):
        frame = pd.read_parquet(dataset_path)
    else:
        frame = pd.read_csv(dataset_path)

    if TARGET_COL not in frame.columns:
        raise ValueError(f"Dataset missing target column '{TARGET_COL}'")
    if DATE_COL not in frame.columns:
        raise ValueError(f"Dataset missing date column '{DATE_COL}'")

    frame = frame.sort_values(DATE_COL).reset_index(drop=True)
    logger.info(
        "Running O/U backtest: %d total rows, %d splits",
        len(frame),
        resolved_config.n_splits,
    )

    fold_splits = _fold_splits(frame, resolved_config.n_splits, resolved_config.min_train_rows)
    if not fold_splits:
        raise ValueError(
            f"Not enough rows for {resolved_config.n_splits} folds "
            f"(min_train_rows={resolved_config.min_train_rows})"
        )

    folds: list[OUFoldResult] = []
    for i, (train_df, test_df) in enumerate(fold_splits, start=1):
        fold_result = _run_single_fold(i, train_df, test_df, resolved_config)
        folds.append(fold_result)

    aggregate = _aggregate_fold_results(folds)

    result = OUBacktestResult(
        config=resolved_config,
        folds=folds,
        aggregate=aggregate,
        dataset_path=str(dataset_path),
        output_dir=str(output_dir) if output_dir else None,
    )

    if output_dir is not None:
        output_dir.mkdir(parents=True, exist_ok=True)
        _save_backtest_results(result, output_dir)

    return result


def _save_backtest_results(result: OUBacktestResult, output_dir: Path) -> None:
    summary: JsonDict = {
        "n_folds": len(result.folds),
        "aggregate": result.aggregate,
        "folds": [
            {
                "fold": f.fold,
                "n_train": f.n_train,
                "n_test": f.n_test,
                "test_date_start": f.test_date_start,
                "test_date_end": f.test_date_end,
                "metrics": f.metrics_per_model,
                "roi": f.roi_per_model,
                "prediction_rows": f.prediction_rows,
            }
            for f in result.folds
        ],
        "dataset_path": result.dataset_path,
    }
    (output_dir / "backtest_results.json").write_text(json.dumps(summary, indent=2, default=str))
    logger.info("Saved backtest results to %s", output_dir / "backtest_results.json")
