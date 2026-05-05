"""Temporal backtesting and reporting for trained models and baselines."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Literal

import pandas as pd  # type: ignore[import-untyped]

from football_predictor.backtesting.metrics import (
    accuracy_score_1x2,
    calibration_bins,
    confidence_gap,
    log_loss_safe,
    multiclass_brier_score,
)
from football_predictor.backtesting.reports import export_markdown_report, export_metrics_json
from football_predictor.modeling.baselines import (
    api_prediction_predict,
    odds_only_predict,
)
from football_predictor.modeling.constants import CLASSES
from football_predictor.modeling.evaluation import evaluate_probabilities
from football_predictor.modeling.loader import PredictionModel, load_prediction_model
from football_predictor.modeling.poisson import poisson_predict
from football_predictor.modeling.preprocessing import (
    is_forbidden_feature,
    separate_metadata_target_features,
)
from football_predictor.modeling.probabilities import ProbabilityTriple
from football_predictor.modeling.stacking import blend_probabilities
from football_predictor.modeling.v2_model import V2TrainingConfig, train_v2_model_from_frame
from football_predictor.utils.time import utc_now

ReportFormat = Literal["json", "markdown", "both"]


@dataclass(frozen=True)
class BacktestConfig:
    train_ratio: float = 0.60
    valid_ratio: float = 0.20
    test_ratio: float = 0.20
    confidence_thresholds: tuple[float, ...] = (0.40, 0.50, 0.60, 0.70, 0.80)
    calibration_bins: int = 10
    report_format: ReportFormat = "both"
    retrain_v2_model_version: str | None = None


@dataclass(frozen=True)
class SplitPeriod:
    name: str
    row_count: int
    start: str | None
    end: str | None


@dataclass(frozen=True)
class BacktestResult:
    periods: dict[str, SplitPeriod]
    metrics_by_model: dict[str, Any]
    group_metrics: dict[str, Any]
    report_paths: dict[str, Path]
    payload: dict[str, Any] = field(default_factory=dict)


def evaluate_predictions(
    df: pd.DataFrame,
    y_true: list[str] | pd.Series,
    proba_columns: tuple[str, str, str] | list[str],
    *,
    classes: list[str] | tuple[str, ...] = tuple(CLASSES),
    n_bins: int = 10,
) -> dict[str, Any]:
    """Evaluate point-in-time probability columns without reading leakage columns."""
    missing = [column for column in proba_columns if column not in df.columns]
    if missing:
        raise ValueError(f"Missing probability columns: {missing}")
    labels = list(pd.Series(y_true).astype(str))
    probabilities = _probability_rows(df, proba_columns)
    return {
        "row_count": len(labels),
        "accuracy": accuracy_score_1x2(labels, probabilities, classes),
        "log_loss": log_loss_safe(labels, probabilities, classes),
        "brier_score": multiclass_brier_score(labels, probabilities, classes),
        "calibration_bins": calibration_bins(labels, probabilities, classes, n_bins=n_bins),
        "avg_confidence_gap": sum(confidence_gap(row) for row in probabilities)
        / len(probabilities)
        if probabilities
        else None,
    }


def compare_models(
    df: pd.DataFrame,
    *,
    final_model_columns: tuple[str, str, str] | None = None,
    config: BacktestConfig | None = None,
) -> dict[str, Any]:
    """Compare final_model, odds_only, poisson and api_prediction probabilities."""
    config = config or BacktestConfig()
    _validate_dataset(df)
    predictions: dict[str, list[ProbabilityTriple | None]] = {
        "odds_only": [_optional_triple(odds_only_predict(row)) for row in _rows(df)],
        "poisson": [_optional_triple(poisson_predict(row)) for row in _rows(df)],
        "api_prediction": [_optional_triple(api_prediction_predict(row)) for row in _rows(df)],
    }
    if final_model_columns is not None:
        probabilities = _probability_rows(df, final_model_columns)
        predictions["final_model"] = [ProbabilityTriple.from_vector(row) for row in probabilities]
    y_true = list(df["target"].astype(str))
    return {
        name: _metrics_for_optional_predictions(y_true, model_predictions, config=config)
        for name, model_predictions in predictions.items()
    }


def run_backtest(
    dataset_path: Path,
    model_dir: Path | None = None,
    output_dir: Path | None = None,
    config: BacktestConfig | None = None,
) -> BacktestResult:
    config = config or BacktestConfig()
    _validate_config(config)
    frame = _load_dataset(dataset_path)
    _validate_dataset(frame)
    train_frame, valid_frame, test_frame = temporal_split(frame, config=config)
    model = (
        _train_v2_for_backtest(train_frame, valid_frame, config.retrain_v2_model_version)
        if config.retrain_v2_model_version
        else _load_model(model_dir)
        if model_dir is not None
        else None
    )

    periods = {
        "train": _period_for("train", train_frame),
        "validation": _period_for("validation", valid_frame),
        "test": _period_for("test", test_frame),
    }
    validation_results = _evaluate_frame(valid_frame, model=model, config=config)
    test_results = _evaluate_frame(test_frame, model=model, config=config)
    comparisons = _comparisons_against_model(test_results)
    group_metrics = {
        "test": _group_metrics(test_frame, model=model, config=config),
        "validation": _group_metrics(valid_frame, model=model, config=config),
    }
    leakage = _leakage_report(test_frame)

    payload: dict[str, Any] = {
        "dataset_path": str(dataset_path),
        "model_dir": str(model_dir) if model_dir is not None else None,
        "generated_at": utc_now().isoformat(),
        "config": asdict(config),
        "periods": {name: asdict(period) for name, period in periods.items()},
        "metrics": {
            "validation": validation_results,
            "test": test_results,
        },
        "comparisons": {"test": comparisons},
        "group_metrics": group_metrics,
        "leakage": leakage,
    }
    resolved_output_dir = output_dir or _default_output_dir()
    report_paths = _write_reports(payload, resolved_output_dir, config.report_format)
    return BacktestResult(
        periods=periods,
        metrics_by_model=test_results,
        group_metrics=group_metrics,
        report_paths=report_paths,
        payload=payload,
    )


def temporal_split(
    frame: pd.DataFrame,
    *,
    config: BacktestConfig,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    _validate_dataset(frame)
    ordered = (
        frame.assign(__fixture_date_dt=pd.to_datetime(frame["fixture_date"], utc=True))
        .sort_values("__fixture_date_dt")
        .drop(columns=["__fixture_date_dt"])
        .reset_index(drop=True)
    )
    total_rows = len(ordered)
    train_end = max(int(total_rows * config.train_ratio), 1)
    valid_end = max(int(total_rows * (config.train_ratio + config.valid_ratio)), train_end + 1)
    valid_end = min(valid_end, total_rows)
    train = ordered.iloc[:train_end].copy()
    validation = ordered.iloc[train_end:valid_end].copy()
    test = ordered.iloc[valid_end:].copy()
    if test.empty and not validation.empty:
        test = validation.tail(1).copy()
        validation = validation.iloc[:-1].copy()
    if test.empty:
        raise ValueError("Temporal split produced an empty test set")
    return train, validation, test


def _evaluate_frame(
    frame: pd.DataFrame,
    *,
    model: PredictionModel | None,
    config: BacktestConfig,
) -> dict[str, Any]:
    if frame.empty:
        return {}
    y_true = list(frame["target"].astype(str))
    predictions: dict[str, list[ProbabilityTriple | None]] = {
        "odds_only": [_optional_triple(odds_only_predict(row)) for row in _rows(frame)],
        "poisson": [_optional_triple(poisson_predict(row)) for row in _rows(frame)],
        "api_prediction_only": [
            _optional_triple(api_prediction_predict(row)) for row in _rows(frame)
        ],
    }
    if model is not None:
        predict_frame = frame if getattr(model, "is_v2_composite", False) else None
        data = (
            separate_metadata_target_features(frame, impute=True)
            if predict_frame is None
            else None
        )
        sport_predictions = [
            _optional_triple(row)
            for row in model.predict_proba(
                predict_frame if predict_frame is not None else data.features  # type: ignore[union-attr]
            )
        ]
        predictions["model_final"] = sport_predictions
        if getattr(model, "is_v2_composite", False) and hasattr(
            model,
            "predict_expert_probabilities",
        ):
            expert_rows = model.predict_expert_probabilities(frame)
            for source in ("market_calibrated", "poisson_v2", "elo_v2", "tabular_v2"):
                predictions[source] = [
                    _optional_triple(experts.get(source)) for experts in expert_rows
                ]
            predictions["stacking_v2"] = sport_predictions
        else:
            predictions["stacking_final"] = [
                _stack_row(sport, row)
                for sport, row in zip(sport_predictions, _rows(frame), strict=True)
            ]

    results: dict[str, Any] = {}
    for name, model_predictions in predictions.items():
        results[name] = _metrics_for_optional_predictions(
            y_true,
            model_predictions,
            config=config,
        )
    return results


def _metrics_for_optional_predictions(
    y_true: list[str],
    predictions: list[ProbabilityTriple | None],
    *,
    config: BacktestConfig,
) -> dict[str, Any]:
    covered_true: list[str] = []
    covered_predictions: list[ProbabilityTriple] = []
    for actual, prediction in zip(y_true, predictions, strict=True):
        if prediction is None:
            continue
        covered_true.append(actual)
        covered_predictions.append(prediction)
    coverage = len(covered_predictions) / len(y_true) if y_true else 0.0
    metrics = evaluate_probabilities(
        covered_true,
        covered_predictions,
        calibration_bins=config.calibration_bins,
    )
    metrics["coverage"] = coverage
    metrics["missing_predictions"] = len(y_true) - len(covered_predictions)
    metrics["confidence_thresholds"] = _confidence_threshold_metrics(
        covered_true,
        covered_predictions,
        thresholds=config.confidence_thresholds,
        denominator=len(y_true),
    )
    return metrics


def _confidence_threshold_metrics(
    y_true: list[str],
    predictions: list[ProbabilityTriple],
    *,
    thresholds: tuple[float, ...],
    denominator: int,
) -> list[dict[str, float | int | None]]:
    output: list[dict[str, float | int | None]] = []
    for threshold in thresholds:
        selected = [
            (actual, prediction)
            for actual, prediction in zip(y_true, predictions, strict=True)
            if prediction.max_probability() >= threshold
        ]
        correct = sum(
            1 for actual, prediction in selected if prediction.predicted_result() == actual
        )
        output.append(
            {
                "threshold": threshold,
                "row_count": len(selected),
                "coverage": len(selected) / denominator if denominator else 0.0,
                "accuracy": correct / len(selected) if selected else None,
            }
        )
    return output


def _group_metrics(
    frame: pd.DataFrame,
    *,
    model: PredictionModel | None,
    config: BacktestConfig,
) -> dict[str, Any]:
    groups: dict[str, Any] = {}
    for column in ("league_id", "season"):
        if column not in frame.columns or frame.empty:
            continue
        column_groups: dict[str, Any] = {}
        for value, group in frame.groupby(column, sort=True):
            column_groups[str(value)] = {
                "row_count": len(group),
                "metrics": _evaluate_frame(group.copy(), model=model, config=config),
            }
        groups[column] = column_groups
    confidence_groups = _confidence_bucket_metrics(frame, model=model, config=config)
    if confidence_groups:
        groups["confidence_bucket"] = confidence_groups
    quality_groups = _data_quality_bucket_metrics(frame, model=model, config=config)
    if quality_groups:
        groups["data_quality_bucket"] = quality_groups
    return groups


def _comparisons_against_model(results: dict[str, Any]) -> dict[str, Any]:
    model_metrics = results.get("model_final")
    if not model_metrics:
        return {}
    comparisons: dict[str, Any] = {}
    for name, metrics in results.items():
        if name == "model_final":
            continue
        comparisons[name] = {
            "accuracy_delta_model_minus_baseline": _delta(
                model_metrics.get("accuracy"), metrics.get("accuracy")
            ),
            "log_loss_delta_baseline_minus_model": _delta(
                metrics.get("log_loss"), model_metrics.get("log_loss")
            ),
            "brier_delta_baseline_minus_model": _delta(
                metrics.get("brier_score"), model_metrics.get("brier_score")
            ),
        }
    return comparisons


def _confidence_bucket_metrics(
    frame: pd.DataFrame,
    *,
    model: PredictionModel | None,
    config: BacktestConfig,
) -> dict[str, Any]:
    evaluation = _evaluate_frame(frame, model=model, config=config)
    output: dict[str, Any] = {}
    for model_name in evaluation:
        predictions = _predictions_for_model(frame, model_name, model=model)
        buckets: dict[str, list[int]] = {
            "low_<0.50": [],
            "medium_0.50_0.70": [],
            "high_>=0.70": [],
        }
        for index, prediction in enumerate(predictions):
            if prediction is None:
                continue
            confidence = prediction.max_probability()
            if confidence < 0.50:
                buckets["low_<0.50"].append(index)
            elif confidence < 0.70:
                buckets["medium_0.50_0.70"].append(index)
            else:
                buckets["high_>=0.70"].append(index)
        output[model_name] = {
            bucket: _evaluate_index_subset(frame, indexes, model=model, config=config).get(
                model_name,
                {},
            )
            for bucket, indexes in buckets.items()
            if indexes
        }
    return output


def _data_quality_bucket_metrics(
    frame: pd.DataFrame,
    *,
    model: PredictionModel | None,
    config: BacktestConfig,
) -> dict[str, Any]:
    quality_column = _quality_column(frame)
    if quality_column is None:
        return {}
    buckets: dict[str, list[int]] = {
        "low_<40": [],
        "medium_40_70": [],
        "high_>=70": [],
    }
    values = pd.to_numeric(frame[quality_column], errors="coerce")
    for index, value in enumerate(values):
        if pd.isna(value) or float(value) < 40:
            buckets["low_<40"].append(index)
        elif float(value) < 70:
            buckets["medium_40_70"].append(index)
        else:
            buckets["high_>=70"].append(index)
    return {
        bucket: {
            "row_count": len(indexes),
            "metrics": _evaluate_index_subset(frame, indexes, model=model, config=config),
        }
        for bucket, indexes in buckets.items()
        if indexes
    }


def _evaluate_index_subset(
    frame: pd.DataFrame,
    indexes: list[int],
    *,
    model: PredictionModel | None,
    config: BacktestConfig,
) -> dict[str, Any]:
    subset = frame.iloc[indexes].copy()
    return _evaluate_frame(subset, model=model, config=config)


def _predictions_for_model(
    frame: pd.DataFrame,
    model_name: str,
    *,
    model: PredictionModel | None,
) -> list[ProbabilityTriple | None]:
    rows = _rows(frame)
    if model_name == "odds_only":
        return [_optional_triple(odds_only_predict(row)) for row in rows]
    if model_name == "poisson":
        return [_optional_triple(poisson_predict(row)) for row in rows]
    if model_name in {"api_prediction", "api_prediction_only"}:
        return [_optional_triple(api_prediction_predict(row)) for row in rows]
    if model is None:
        return [None for _ in rows]
    if getattr(model, "is_v2_composite", False):
        sport = [_optional_triple(row) for row in model.predict_proba(frame)]
    else:
        data = separate_metadata_target_features(frame, impute=True)
        sport = [_optional_triple(row) for row in model.predict_proba(data.features)]
    if model_name == "model_final":
        return sport
    if getattr(model, "is_v2_composite", False) and hasattr(model, "predict_expert_probabilities"):
        if model_name == "stacking_v2":
            return sport
        expert_rows = model.predict_expert_probabilities(frame)
        if model_name in {"market_calibrated", "poisson_v2", "elo_v2", "tabular_v2"}:
            return [_optional_triple(experts.get(model_name)) for experts in expert_rows]
    if model_name == "stacking_final":
        return [_stack_row(prediction, row) for prediction, row in zip(sport, rows, strict=True)]
    return [None for _ in rows]


def _write_reports(
    payload: dict[str, Any],
    output_dir: Path,
    report_format: ReportFormat,
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}
    if report_format in {"json", "both"}:
        paths["json"] = export_metrics_json(payload, output_dir / "backtest_report.json")
    if report_format in {"markdown", "both"}:
        paths["markdown"] = export_markdown_report(payload, output_dir / "backtest_report.md")
    return paths


def _markdown_report(payload: dict[str, Any]) -> str:
    lines = [
        "# Backtest Football Predictor",
        "",
        f"- Dataset: `{payload['dataset_path']}`",
        f"- Model dir: `{payload['model_dir']}`",
        f"- Generated at: `{payload['generated_at']}`",
        "",
        "## Periods",
        "",
        "| Split | Rows | Start | End |",
        "| --- | ---: | --- | --- |",
    ]
    for name, period in payload["periods"].items():
        lines.append(
            f"| {name} | {period['row_count']} | {period['start'] or ''} | "
            f"{period['end'] or ''} |"
        )
    lines.extend(
        ["", "## Test Metrics", "", "| Model | Rows | Coverage | Accuracy | Log loss | Brier |"]
    )
    lines.append("| --- | ---: | ---: | ---: | ---: | ---: |")
    for model_name, metrics in payload["metrics"].get("test", {}).items():
        lines.append(
            f"| {model_name} | {metrics.get('row_count', 0)} | "
            f"{_fmt(metrics.get('coverage'))} | {_fmt(metrics.get('accuracy'))} | "
            f"{_fmt(metrics.get('log_loss'))} | {_fmt(metrics.get('brier_score'))} |"
        )
    lines.extend(["", "## Confidence Thresholds", ""])
    for model_name, metrics in payload["metrics"].get("test", {}).items():
        lines.append(f"### {model_name}")
        lines.append("")
        lines.append("| Threshold | Rows | Coverage | Accuracy |")
        lines.append("| ---: | ---: | ---: | ---: |")
        for item in metrics.get("confidence_thresholds", []):
            lines.append(
                f"| {item['threshold']} | {item['row_count']} | "
                f"{_fmt(item['coverage'])} | {_fmt(item['accuracy'])} |"
            )
        lines.append("")
    lines.extend(["## Group Metrics", ""])
    for group_name, groups in payload.get("group_metrics", {}).get("test", {}).items():
        lines.append(f"### {group_name}")
        lines.append("")
        for value, group_payload in groups.items():
            lines.append(f"- `{value}`: {group_payload['row_count']} rows")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _load_dataset(path: Path) -> pd.DataFrame:
    suffix = path.suffix.casefold()
    if suffix == ".csv":
        return pd.read_csv(path)
    if suffix == ".parquet":
        return pd.read_parquet(path, engine="pyarrow")
    raise ValueError("dataset_path must be .csv or .parquet")


def _probability_rows(
    frame: pd.DataFrame,
    proba_columns: tuple[str, str, str] | list[str],
) -> list[list[float]]:
    rows: list[list[float]] = []
    for _, row in frame.iterrows():
        rows.append([float(row[column]) for column in proba_columns])
    return rows


def _quality_column(frame: pd.DataFrame) -> str | None:
    for column in ("data_quality_score", "overall_data_quality_score"):
        if column in frame.columns:
            return column
    return None


def _load_model(model_dir: Path) -> PredictionModel:
    model_path = model_dir / "model.joblib" if model_dir.is_dir() else model_dir
    return load_prediction_model(model_path)


def _train_v2_for_backtest(
    train_frame: pd.DataFrame,
    valid_frame: pd.DataFrame,
    model_version: str,
) -> PredictionModel:
    model, _metrics = train_v2_model_from_frame(
        train_frame,
        valid_frame,
        config=V2TrainingConfig(model_version=model_version),
    )
    return model


def _validate_dataset(frame: pd.DataFrame) -> None:
    if frame.empty:
        raise ValueError("Backtest dataset is empty")
    if "fixture_date" not in frame.columns:
        raise ValueError("fixture_date is required for temporal backtesting")
    if "target" not in frame.columns:
        raise ValueError("target is required for backtesting")
    dates = pd.to_datetime(frame["fixture_date"], utc=True, errors="coerce")
    if dates.isna().any():
        raise ValueError("fixture_date contains invalid datetime values")
    labels = set(frame["target"].astype(str))
    invalid = labels.difference(CLASSES)
    if invalid:
        raise ValueError(f"Unknown target labels: {sorted(invalid)}")


def _validate_config(config: BacktestConfig) -> None:
    ratios = (config.train_ratio, config.valid_ratio, config.test_ratio)
    if any(ratio < 0 for ratio in ratios):
        raise ValueError("Split ratios must be non-negative")
    if abs(sum(ratios) - 1.0) > 1e-9:
        raise ValueError("Split ratios must sum to 1.0")
    if config.report_format not in {"json", "markdown", "both"}:
        raise ValueError("report_format must be json, markdown, or both")


def _period_for(name: str, frame: pd.DataFrame) -> SplitPeriod:
    if frame.empty:
        return SplitPeriod(name=name, row_count=0, start=None, end=None)
    dates = pd.to_datetime(frame["fixture_date"], utc=True)
    return SplitPeriod(
        name=name,
        row_count=len(frame),
        start=dates.min().isoformat(),
        end=dates.max().isoformat(),
    )


def _rows(frame: pd.DataFrame) -> list[dict[str, Any]]:
    return [dict(row) for row in frame.to_dict(orient="records")]


def _optional_triple(values: list[float] | None) -> ProbabilityTriple | None:
    if values is None:
        return None
    return ProbabilityTriple.from_vector(values)


def _stack_row(sport: ProbabilityTriple | None, row: dict[str, Any]) -> ProbabilityTriple | None:
    if sport is None:
        return None
    market = _market_probability_if_present(row)
    api = _optional_triple(api_prediction_predict(row))
    if market is None and api is None:
        return None
    return ProbabilityTriple.from_vector(blend_probabilities(sport, market, api))


def _market_probability_if_present(row: dict[str, Any]) -> ProbabilityTriple | None:
    for keys in (
        ("p_market_home", "p_market_draw", "p_market_away"),
        ("market_home", "market_draw", "market_away"),
    ):
        values: list[float] = []
        for key in keys:
            value = row.get(key)
            if value is None:
                values = []
                break
            try:
                values.append(float(value))
            except (TypeError, ValueError):
                values = []
                break
        if values:
            return ProbabilityTriple.from_vector(values)
    return None


def _leakage_report(frame: pd.DataFrame) -> dict[str, Any]:
    data = separate_metadata_target_features(frame, impute=True)
    forbidden_in_features = [
        name for name in data.feature_names if is_forbidden_feature(name)
    ]
    return {
        "feature_count": len(data.feature_names),
        "forbidden_columns_in_features": forbidden_in_features,
        "metadata_columns": list(data.metadata.columns),
    }


def _delta(left: Any, right: Any) -> float | None:
    if left is None or right is None:
        return None
    return float(left) - float(right)


def _fmt(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, int):
        return str(value)
    try:
        return f"{float(value):.4f}"
    except (TypeError, ValueError):
        return str(value)


def _default_output_dir() -> Path:
    stamp = utc_now().strftime("%Y%m%dT%H%M%SZ")
    return Path("data/processed/backtests") / stamp
