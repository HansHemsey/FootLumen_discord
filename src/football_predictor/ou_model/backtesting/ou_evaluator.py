"""Walk-forward backtesting for the O/U 2.5 model."""

from __future__ import annotations

import json
import logging
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from football_predictor.backtesting.confidence_calibration import (
    THRESHOLD_VERSION,
    ConfidenceThresholdConfig,
    build_confidence_threshold_artifact,
)
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
from football_predictor.ou_model.prediction.ou_service import _ou_confidence_score

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
    confidence_thresholds: JsonDict = field(default_factory=dict)


@dataclass
class OUBacktestResult:
    config: OUBacktestConfig
    folds: list[OUFoldResult]
    aggregate: JsonDict
    dataset_path: str | None = None
    output_dir: str | None = None
    confidence_thresholds: JsonDict = field(default_factory=dict)


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
    p_over_array = np.asarray(p_over, dtype=float)
    base: JsonDict = {
        "brier_score": binary_brier_score(list(y_true), list(p_over_array)),
        "log_loss": binary_log_loss(list(y_true), list(p_over_array)),
        "over_rate": float(y_true.mean()),
        "mean_p_over": float(p_over_array.mean()),
        "n_rows": int(len(y_true)),
    }
    roi_per_threshold: dict[str, JsonDict] = {}
    for et in edge_thresholds:
        roi_per_threshold[f"edge_{et:.2f}"] = roi_simulation(
            list(y_true),
            list(p_over_array),
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
    threshold_calibration_frame = cal_df if len(cal_df) > 0 else valid_df
    confidence_thresholds = build_confidence_threshold_artifact(
        validation_records=_ou_confidence_records(model, threshold_calibration_frame, available),
        test_records=_ou_confidence_records(model, test_df, available),
        config=ConfidenceThresholdConfig(model_family="ou25"),
        periods={
            "validation": _period_payload(threshold_calibration_frame),
            "test": _period_payload(test_df),
        },
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
        confidence_thresholds=confidence_thresholds,
    )


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


def _ou_confidence_records(
    model: Any,
    frame: pd.DataFrame,
    feature_names: list[str],
) -> list[JsonDict]:
    if frame.empty:
        return []
    X = frame[feature_names].fillna(0) if feature_names else pd.DataFrame(index=frame.index)
    p_over_values = model.predict_proba_over(X)
    quality_scale = _quality_score_scale(frame)
    records: list[JsonDict] = []
    for index, (_, row) in enumerate(frame.iterrows()):
        p_over = float(p_over_values[index])
        p_over = max(0.0, min(1.0, p_over))
        actual = int(row[TARGET_COL])
        odd_over = _optional_float(row.get("ou_market_odd_over"))
        odd_under = _optional_float(row.get("ou_market_odd_under"))
        market_p = _market_probability_or_default(odd_over, odd_under)
        edge_over = p_over - market_p
        quality_score = _row_quality_score(row, scale=quality_scale)
        data_quality = _publication_quality_payload(row, quality_score)
        stake, profit = _flat_stake_profit(
            actual=actual,
            p_over=p_over,
            market_p_over=market_p,
            odd_over=odd_over,
            odd_under=odd_under,
        )
        records.append(
            {
                "fixture_id": _json_value(row.get("fixture_id")),
                "league_id": _json_value(row.get("league_id")),
                "season": _json_value(row.get("season")),
                "actual": actual,
                "predicted": 1 if p_over >= 0.5 else 0,
                "correct": (1 if p_over >= 0.5 else 0) == actual,
                "confidence_score": _row_confidence_score(row, p_over, edge_over),
                "data_quality": data_quality,
                "p_over": p_over,
                "p_max": max(p_over, 1.0 - p_over),
                "edge_abs": abs(edge_over),
                "gap": abs(p_over - 0.5) * 2,
                "log_loss": _binary_loss(actual, p_over),
                "brier_score": (p_over - actual) ** 2,
                "baseline_predicted": 1 if market_p >= 0.5 else 0,
                "baseline_correct": (1 if market_p >= 0.5 else 0) == actual,
                "baseline_log_loss": _binary_loss(actual, market_p),
                "baseline_brier_score": (market_p - actual) ** 2,
                "stake": stake,
                "profit": profit,
            }
        )
    return records


def _aggregate_confidence_thresholds(folds: list[OUFoldResult]) -> JsonDict:
    artifacts = [fold.confidence_thresholds for fold in folds if fold.confidence_thresholds]
    highs = [
        _optional_float(item.get("thresholds", {}).get("global", {}).get("high"))
        for item in artifacts
    ]
    very_highs = [
        _optional_float(item.get("thresholds", {}).get("global", {}).get("very_high"))
        for item in artifacts
    ]
    highs = [item for item in highs if item is not None]
    very_highs = [item for item in very_highs if item is not None]
    return {
        "threshold_version": THRESHOLD_VERSION,
        "model_family": "ou25",
        "production_approved": bool(artifacts) and all(
            item.get("production_approved") is True for item in artifacts
        ),
        "thresholds": {
            "global": {
                "high": float(np.median(highs)) if highs else None,
                "very_high": float(np.median(very_highs)) if very_highs else None,
            }
        },
        "folds": artifacts,
    }


def _period_payload(frame: pd.DataFrame) -> JsonDict:
    if frame.empty:
        return {"row_count": 0, "start": None, "end": None}
    dates = pd.to_datetime(frame[DATE_COL], utc=True)
    return {
        "row_count": int(len(frame)),
        "start": dates.min().isoformat(),
        "end": dates.max().isoformat(),
    }


def _row_confidence_score(row: pd.Series, p_over: float, edge_over: float) -> float:
    existing = _optional_float(row.get("confidence_score"))
    if existing is not None:
        return existing
    return _ou_confidence_score(p_over, edge_over)


def _publication_quality_payload(row: pd.Series, score: float | None) -> JsonDict:
    payload: JsonDict = {}
    if score is not None:
        payload["publication_data_quality_score"] = score
    blockers = _parse_blockers(row.get("publication_blockers"))
    if blockers:
        payload["publication_blockers"] = blockers
    return payload


def _row_quality_score(row: pd.Series, *, scale: float) -> float | None:
    for key in (
        "publication_data_quality_score",
        "ou_data_quality_score",
        "overall_data_quality_score",
        "data_quality_score",
    ):
        value = _optional_float(row.get(key))
        if value is not None:
            return max(0.0, min(100.0, value * scale))
    return None


def _quality_score_scale(frame: pd.DataFrame) -> float:
    values: list[float] = []
    for key in (
        "publication_data_quality_score",
        "ou_data_quality_score",
        "overall_data_quality_score",
        "data_quality_score",
    ):
        if key not in frame.columns:
            continue
        values.extend(
            value
            for value in (_optional_float(item) for item in frame[key].tolist())
            if value is not None
        )
    return 100.0 if values and max(values) <= 1.0 else 1.0


def _parse_blockers(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list | tuple | set):
        return [str(item) for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return [value]
        if isinstance(parsed, list):
            return [str(item) for item in parsed if str(item).strip()]
    return []


def _flat_stake_profit(
    *,
    actual: int,
    p_over: float,
    market_p_over: float,
    odd_over: float | None,
    odd_under: float | None,
) -> tuple[float | None, float | None]:
    if odd_over is None or odd_under is None or odd_over <= 1 or odd_under <= 1:
        return None, None
    edge_over = p_over - market_p_over
    edge_under = market_p_over - p_over
    if edge_over <= 0 and edge_under <= 0:
        return None, None
    if edge_over >= edge_under:
        won = actual == 1
        odd = odd_over
    else:
        won = actual == 0
        odd = odd_under
    return 1.0, (odd - 1.0) if won else -1.0


def _market_probability_or_default(
    odd_over: float | None,
    odd_under: float | None,
) -> float:
    if odd_over is not None and odd_under is not None and odd_over > 1 and odd_under > 1:
        return _market_p_over(odd_over, odd_under)
    return 0.5


def _binary_loss(actual: int, probability: float) -> float:
    p = min(max(float(probability), 1e-15), 1 - 1e-15)
    return -(actual * math.log(p) + (1 - actual) * math.log(1 - p))


def _json_value(value: Any) -> Any:
    if pd.isna(value):
        return None
    if isinstance(value, np.generic):
        return value.item()
    return value


def _optional_float(value: Any) -> float | None:
    try:
        resolved = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(resolved):
        return None
    return resolved


def _published_only_report_from_thresholds(confidence_thresholds: JsonDict) -> JsonDict:
    folds = confidence_thresholds.get("folds", [])
    fold_reports: list[JsonDict] = []
    if isinstance(folds, list):
        for index, artifact in enumerate(folds, start=1):
            if not isinstance(artifact, dict):
                continue
            test_metrics = artifact.get("metrics", {}).get("test", {})
            fold_reports.append(
                {
                    "fold": index,
                    "production_approved": artifact.get("production_approved"),
                    "scopes": {
                        "internal_all": _ou_scope_metrics(
                            test_metrics.get("internal_all", {}),
                            test_metrics.get("baseline_internal_all", {}),
                        ),
                        "published_only": _ou_scope_metrics(
                            test_metrics.get("published_only", {}),
                            test_metrics.get("baseline_on_published", {}),
                        ),
                    },
                    "groups": {
                        "league": _ou_group_metrics(test_metrics.get("by_league", {})),
                        "season": _ou_group_metrics(test_metrics.get("by_season", {})),
                        "confidence_label": {
                            label: _ou_scope_metrics(metrics, {})
                            for label, metrics in test_metrics.get("labels", {}).items()
                            if isinstance(metrics, dict)
                        },
                        "data_quality": _ou_group_metrics(
                            test_metrics.get("by_data_quality_bin", {})
                        ),
                    },
                }
            )
    return {
        "model_family": "ou25",
        "policy": {
            "threshold_version": confidence_thresholds.get("threshold_version"),
            "thresholds": confidence_thresholds.get("thresholds", {}).get("global", {}),
            "production_approved": confidence_thresholds.get("production_approved"),
        },
        "aggregate": {
            "fold_count": len(fold_reports),
            "published_rows": sum(
                int(
                    report.get("scopes", {})
                    .get("published_only", {})
                    .get("ensemble", {})
                    .get("row_count")
                    or 0
                )
                for report in fold_reports
            ),
        },
        "folds": fold_reports,
    }


def _ou_scope_metrics(ensemble: JsonDict, market: JsonDict) -> JsonDict:
    return {
        "ensemble": ensemble if isinstance(ensemble, dict) else {},
        "market": market if isinstance(market, dict) else {},
        "comparison": {
            "log_loss_delta_ensemble_minus_market": _delta(
                ensemble.get("log_loss") if isinstance(ensemble, dict) else None,
                market.get("log_loss") if isinstance(market, dict) else None,
            ),
            "brier_delta_ensemble_minus_market": _delta(
                ensemble.get("brier_score") if isinstance(ensemble, dict) else None,
                market.get("brier_score") if isinstance(market, dict) else None,
            ),
            "accuracy_delta_ensemble_minus_market": _delta(
                ensemble.get("accuracy") if isinstance(ensemble, dict) else None,
                market.get("accuracy") if isinstance(market, dict) else None,
            ),
            "roi_ensemble": ensemble.get("roi") if isinstance(ensemble, dict) else None,
        },
    }


def _ou_group_metrics(groups: JsonDict) -> JsonDict:
    if not isinstance(groups, dict):
        return {}
    output: JsonDict = {}
    for value, payload in groups.items():
        if not isinstance(payload, dict):
            continue
        output[str(value)] = {
            "row_count": payload.get("row_count"),
            "metrics": _ou_scope_metrics(
                payload.get("published_only", {}),
                payload.get("baseline_on_published", {}),
            ),
        }
    return output


def _delta(left: Any, right: Any) -> float | None:
    left_value = _optional_float(left)
    right_value = _optional_float(right)
    if left_value is None or right_value is None:
        return None
    return left_value - right_value


def _published_only_markdown(report: JsonDict) -> str:
    lines = [
        "# Backtest Published-Only O/U 2.5",
        "",
        "## Policy",
        "",
        f"- Model family: `{report.get('model_family')}`",
        f"- Threshold version: `{report.get('policy', {}).get('threshold_version')}`",
        f"- Production approved: `{report.get('policy', {}).get('production_approved')}`",
        "",
        "## Folds",
        "",
        "| Fold | Scope | Rows | Ensemble log loss | Market log loss | Ensemble ROI |",
        "| ---: | --- | ---: | ---: | ---: | ---: |",
    ]
    for fold in report.get("folds", []):
        for scope_name, payload in fold.get("scopes", {}).items():
            ensemble = payload.get("ensemble", {})
            market = payload.get("market", {})
            lines.append(
                f"| {fold.get('fold')} | {scope_name} | {ensemble.get('row_count', 0)} | "
                f"{_fmt(ensemble.get('log_loss'))} | {_fmt(market.get('log_loss'))} | "
                f"{_fmt(ensemble.get('roi'))} |"
            )
    return "\n".join(lines).rstrip() + "\n"


def _fmt(value: Any) -> str:
    if value is None:
        return ""
    try:
        return f"{float(value):.4f}"
    except (TypeError, ValueError):
        return str(value)


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
    confidence_thresholds = _aggregate_confidence_thresholds(folds)
    published_only_report = _published_only_report_from_thresholds(confidence_thresholds)
    aggregate["confidence_thresholds"] = {
        "production_approved": confidence_thresholds.get("production_approved"),
        "global": confidence_thresholds.get("thresholds", {}).get("global", {}),
        "fold_count": len(confidence_thresholds.get("folds", [])),
    }
    aggregate["published_only"] = published_only_report.get("aggregate", {})

    result = OUBacktestResult(
        config=resolved_config,
        folds=folds,
        aggregate=aggregate,
        dataset_path=str(dataset_path),
        output_dir=str(output_dir) if output_dir else None,
        confidence_thresholds=confidence_thresholds,
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
                "confidence_thresholds": f.confidence_thresholds,
            }
            for f in result.folds
        ],
        "dataset_path": result.dataset_path,
        "confidence_thresholds": result.confidence_thresholds,
        "published_only_report": _published_only_report_from_thresholds(
            result.confidence_thresholds
        ),
    }
    (output_dir / "backtest_results.json").write_text(json.dumps(summary, indent=2, default=str))
    (output_dir / "confidence_thresholds.json").write_text(
        json.dumps(result.confidence_thresholds, indent=2, default=str)
    )
    published_report = summary["published_only_report"]
    (output_dir / "published_only_report.json").write_text(
        json.dumps(published_report, indent=2, default=str)
    )
    (output_dir / "published_only_report.md").write_text(
        _published_only_markdown(published_report)
    )
    logger.info("Saved backtest results to %s", output_dir / "backtest_results.json")
