"""V3 backtesting and comparison against V2 and baseline sources."""

from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Literal

import joblib  # type: ignore[import-untyped]
import numpy as np
import pandas as pd  # type: ignore[import-untyped]
from sklearn.metrics import (  # type: ignore[import-untyped]
    average_precision_score,
    precision_recall_fscore_support,
    roc_auc_score,
)

from football_predictor.backtesting.metrics import confidence_gap
from football_predictor.backtesting.v3_dataset_builder import (
    OUTCOME_COL,
    add_v3_targets,
    chronological_splits,
)
from football_predictor.modeling.constants import CLASSES
from football_predictor.modeling.evaluation import evaluate_probabilities
from football_predictor.modeling.poisson import poisson_baseline_probability
from football_predictor.modeling.probabilities import ProbabilityTriple
from football_predictor.modeling.v3.composite import FootballOutcomeV3Model
from football_predictor.modeling.v3.fusion import (
    api_probability_from_row,
    deterministic_v3_fusion,
    market_probability_from_row,
    v2_probability_from_row,
)
from football_predictor.modeling.v3.training import V3TrainingConfig, train_v3_from_dataset
from football_predictor.utils.time import utc_now

ReportFormat = Literal["json", "markdown", "both"]
JsonDict = dict[str, Any]

V3_PRIMARY_MODEL_NAME = "v3_stacker_full"
V2_MODEL_NAME = "v2_existing"


@dataclass(frozen=True)
class V3BacktestConfig:
    """Configuration for V3 comparison reports."""

    train_ratio: float = 0.60
    valid_ratio: float = 0.20
    calibration_bins: int = 10
    report_format: ReportFormat = "both"
    retrain_v3: bool = False
    model_version: str = "v3.0-final"
    draw_calibration: str = "isotonic"
    no_draw_winner_calibration: str = "sigmoid"


@dataclass(frozen=True)
class V3SplitPeriod:
    """Temporal split metadata for reports."""

    name: str
    row_count: int
    start: str | None
    end: str | None


@dataclass(frozen=True)
class V3BacktestResult:
    """Result payload and report paths for a V3 backtest."""

    periods: dict[str, V3SplitPeriod]
    metrics_by_model: dict[str, Any]
    group_metrics: dict[str, Any]
    success_criteria: dict[str, Any]
    report_paths: dict[str, Path]
    payload: dict[str, Any] = field(default_factory=dict)


def run_v3_backtest(
    dataset_path: Path,
    model_dir: Path,
    *,
    v2_model_dir: Path | None = None,
    output_dir: Path | None = None,
    config: V3BacktestConfig | None = None,
) -> V3BacktestResult:
    """Evaluate the V3 composite model, V2 and baseline sources on the test fold."""
    resolved_config = config or V3BacktestConfig()
    _validate_config(resolved_config)
    frame = add_v3_targets(_load_dataset(dataset_path))
    _validate_dataset(frame)
    splits = chronological_splits(
        frame,
        train_ratio=resolved_config.train_ratio,
        valid_ratio=resolved_config.valid_ratio,
    )
    if splits.test.empty:
        raise ValueError("Temporal split produced an empty test set")

    model = _resolve_v3_model(
        dataset_path=dataset_path,
        model_dir=model_dir,
        v2_model_dir=v2_model_dir,
        config=resolved_config,
    )
    v2_model = _load_optional_model(v2_model_dir)

    periods = {
        "train": _period_for("train", splits.train),
        "validation": _period_for("validation", splits.valid),
        "test": _period_for("test", splits.test),
    }
    validation_predictions = _build_prediction_sets(splits.valid, model=model, v2_model=v2_model)
    test_predictions = _build_prediction_sets(splits.test, model=model, v2_model=v2_model)
    validation_metrics = _metrics_for_prediction_sets(
        splits.valid,
        validation_predictions,
        config=resolved_config,
    )
    test_metrics = _metrics_for_prediction_sets(
        splits.test,
        test_predictions,
        config=resolved_config,
    )
    group_metrics = {
        "validation": _group_metrics(
            splits.valid,
            validation_predictions,
            config=resolved_config,
        ),
        "test": _group_metrics(splits.test, test_predictions, config=resolved_config),
    }
    success = _success_criteria(test_metrics, group_metrics.get("test", {}))

    payload: JsonDict = {
        "dataset_path": str(dataset_path),
        "model_dir": str(model_dir),
        "v2_model_dir": str(v2_model_dir) if v2_model_dir is not None else None,
        "generated_at": utc_now().isoformat(),
        "config": asdict(resolved_config),
        "periods": {name: asdict(period) for name, period in periods.items()},
        "metrics": {
            "validation": validation_metrics,
            "test": test_metrics,
        },
        "group_metrics": group_metrics,
        "success_criteria": success,
        "leakage": {
            "evaluation_scope": "test fold only",
            "training_scope": (
                "V3 retrained chronologically from train/validation folds"
                if resolved_config.retrain_v3
                else "pretrained V3 artifact evaluated on chronological test fold"
            ),
            "uses_target_as_feature": False,
        },
    }
    paths = _write_reports(
        payload,
        output_dir or Path("reports/v3"),
        report_format=resolved_config.report_format,
    )
    return V3BacktestResult(
        periods=periods,
        metrics_by_model=test_metrics,
        group_metrics=group_metrics,
        success_criteria=success,
        report_paths=paths,
        payload=payload,
    )


def _resolve_v3_model(
    *,
    dataset_path: Path,
    model_dir: Path,
    v2_model_dir: Path | None,
    config: V3BacktestConfig,
) -> FootballOutcomeV3Model:
    if config.retrain_v3:
        result = train_v3_from_dataset(
            dataset_path,
            model_dir,
            v2_model_dir=v2_model_dir,
            config=V3TrainingConfig(
                model_version=config.model_version,
                draw_calibration=config.draw_calibration,
                no_draw_winner_calibration=config.no_draw_winner_calibration,
                train_ratio=config.train_ratio,
                valid_ratio=config.valid_ratio,
            ),
        )
        return result.model
    if not _v3_artifacts_exist(model_dir):
        raise ValueError(
            "V3 artifacts not found. Train with train-v3 first or pass --retrain-v3."
        )
    return FootballOutcomeV3Model.load(model_dir, v2_model_dir=v2_model_dir)


def _build_prediction_sets(
    frame: pd.DataFrame,
    *,
    model: FootballOutcomeV3Model,
    v2_model: Any | None,
) -> dict[str, list[ProbabilityTriple | None]]:
    if frame.empty:
        return {}
    rows = list(_rows(frame))
    component_frame = model.predict_component_frame(frame)
    if v2_model is None and {"p_v2_home", "p_v2_draw", "p_v2_away"}.issubset(frame.columns):
        for column in ("p_v2_home", "p_v2_draw", "p_v2_away"):
            component_frame[column] = frame[column].to_numpy()
    v3_predictions = model.predict_probability_triples(frame)
    v2_predictions = _v2_predictions(frame, v2_model)
    deterministic = [
        deterministic_v3_fusion(
            draw_probability=_float_or_default(row.get("p_v3_draw_risk"), 1.0 / 3.0),
            home_no_draw_probability=_float_or_default(row.get("p_v3_home_no_draw"), 0.5),
            v2_probability=v2_probability_from_row(row),
            market_probability=market_probability_from_row(row),
        )
        for _, row in component_frame.iterrows()
    ]
    draw_only = [
        ProbabilityTriple(
            0.5 * (1.0 - _float_or_default(value, 1.0 / 3.0)),
            _float_or_default(value, 1.0 / 3.0),
            0.5 * (1.0 - _float_or_default(value, 1.0 / 3.0)),
        ).normalized()
        for value in component_frame["p_v3_draw_risk"]
    ]
    ndw_only = [
        ProbabilityTriple(
            _float_or_default(value, 0.5),
            0.0,
            1.0 - _float_or_default(value, 0.5),
        ).normalized()
        for value in component_frame["p_v3_home_no_draw"]
    ]
    output: dict[str, list[ProbabilityTriple | None]] = {
        "odds_only": [market_probability_from_row(row) for row in rows],
        "api_prediction_only": [api_probability_from_row(row) for row in rows],
        "poisson_baseline": [poisson_baseline_probability(row) for row in rows],
        V2_MODEL_NAME: v2_predictions,
        "v3_draw_risk_only": draw_only,
        "v3_no_draw_winner_only": ndw_only,
        "v3_deterministic_fusion": deterministic,
        V3_PRIMARY_MODEL_NAME: v3_predictions,
        "v3_blend_v2": _blend_predictions(v3_predictions, v2_predictions),
    }
    return output


def _metrics_for_prediction_sets(
    frame: pd.DataFrame,
    predictions_by_model: dict[str, list[ProbabilityTriple | None]],
    *,
    config: V3BacktestConfig,
) -> dict[str, JsonDict]:
    y_true = list(frame[OUTCOME_COL].astype(str))
    output: dict[str, JsonDict] = {}
    for name, predictions in predictions_by_model.items():
        if name == "v3_no_draw_winner_only":
            output[name] = _no_draw_winner_report(frame, predictions_by_model)
            continue
        output[name] = _metrics_for_predictions(y_true, predictions, config=config)
    return output


def _metrics_for_predictions(
    y_true: list[str],
    predictions: list[ProbabilityTriple | None],
    *,
    config: V3BacktestConfig,
) -> JsonDict:
    covered_true: list[str] = []
    covered_predictions: list[ProbabilityTriple] = []
    for actual, prediction in zip(y_true, predictions, strict=True):
        if prediction is None:
            continue
        covered_true.append(actual)
        covered_predictions.append(prediction)
    if not covered_predictions:
        return {
            "available": False,
            "row_count": 0,
            "coverage": 0.0,
            "missing_predictions": len(y_true),
            "reason": "no usable predictions",
        }
    metrics = evaluate_probabilities(
        covered_true,
        covered_predictions,
        calibration_bins=config.calibration_bins,
    )
    metrics["available"] = True
    metrics["coverage"] = len(covered_predictions) / len(y_true) if y_true else 0.0
    metrics["missing_predictions"] = len(y_true) - len(covered_predictions)
    metrics["avg_confidence_gap"] = _average_confidence_gap(covered_predictions)
    draw_metrics = _draw_metrics(covered_true, covered_predictions, config=config)
    metrics["draw_metrics"] = draw_metrics
    metrics["draw_ece"] = draw_metrics.get("ece")
    metrics["no_draw_metrics"] = _no_draw_metrics(covered_true, covered_predictions)
    return metrics


def _no_draw_winner_report(
    frame: pd.DataFrame,
    predictions_by_model: dict[str, list[ProbabilityTriple | None]],
) -> JsonDict:
    ndw_predictions = predictions_by_model.get("v3_no_draw_winner_only", [])
    no_draw = [
        (actual, prediction)
        for actual, prediction in zip(
            list(frame[OUTCOME_COL].astype(str)),
            ndw_predictions,
            strict=True,
        )
        if actual != "DRAW" and prediction is not None
    ]
    if not no_draw:
        return {
            "available": False,
            "row_count": 0,
            "reason": "No non-draw rows available for reporter metrics",
        }
    y_true = [actual for actual, _prediction in no_draw]
    predictions = [prediction for _actual, prediction in no_draw]
    return {
        "available": True,
        "row_count": len(no_draw),
        "coverage": len(no_draw) / len(frame) if len(frame) else 0.0,
        "reason": "Reporter only: No-Draw Winner is conditional and not a 3-class baseline",
        "no_draw_metrics": _no_draw_metrics(y_true, predictions),
    }


def _draw_metrics(
    y_true: list[str],
    predictions: list[ProbabilityTriple],
    *,
    config: V3BacktestConfig,
) -> JsonDict:
    y_binary = [1 if label == "DRAW" else 0 for label in y_true]
    p_draw = [prediction.as_dict()["DRAW"] for prediction in predictions]
    predicted_draw = [
        1 if prediction.predicted_result() == "DRAW" else 0 for prediction in predictions
    ]
    precision, recall, f1, _support = precision_recall_fscore_support(
        y_binary,
        predicted_draw,
        average="binary",
        zero_division=0,
    )
    return {
        "row_count": len(y_binary),
        "positive_rate": sum(y_binary) / len(y_binary) if y_binary else None,
        "precision": float(precision),
        "recall": float(recall),
        "f1": float(f1),
        "roc_auc": _binary_auc(y_binary, p_draw),
        "pr_auc": _binary_pr_auc(y_binary, p_draw),
        "calibration_bins": _binary_calibration_bins(
            y_binary,
            p_draw,
            n_bins=config.calibration_bins,
        ),
        "ece": _binary_ece(y_binary, p_draw, n_bins=config.calibration_bins),
    }


def _no_draw_metrics(y_true: list[str], predictions: list[ProbabilityTriple]) -> JsonDict:
    labels: list[int] = []
    probabilities: list[float] = []
    for actual, prediction in zip(y_true, predictions, strict=True):
        if actual == "DRAW":
            continue
        values = prediction.as_dict()
        total = values["HOME"] + values["AWAY"]
        if total <= 0:
            continue
        labels.append(1 if actual == "HOME" else 0)
        probabilities.append(values["HOME"] / total)
    if not labels:
        return {"row_count": 0}
    predicted = [1 if probability >= 0.5 else 0 for probability in probabilities]
    correct = sum(
        int(label == prediction) for label, prediction in zip(labels, predicted, strict=True)
    )
    return {
        "row_count": len(labels),
        "home_rate": sum(labels) / len(labels),
        "accuracy": correct / len(labels),
        "roc_auc": _binary_auc(labels, probabilities),
    }


def _group_metrics(
    frame: pd.DataFrame,
    predictions_by_model: dict[str, list[ProbabilityTriple | None]],
    *,
    config: V3BacktestConfig,
) -> JsonDict:
    if frame.empty:
        return {}
    groups: JsonDict = {}
    for column in ("league_id", "season", "official_lineup_available_flag"):
        if column in frame.columns:
            groups[column] = _group_by_indexes(
                frame,
                _indexes_by_column(frame, column),
                predictions_by_model,
                config=config,
            )
    if {"league_id", "season"}.issubset(frame.columns):
        key = frame["league_id"].astype(str) + "_" + frame["season"].astype(str)
        groups["league_season"] = _group_by_indexes(
            frame,
            _indexes_by_values(key),
            predictions_by_model,
            config=config,
        )
    quality_indexes = _data_quality_indexes(frame)
    if quality_indexes:
        groups["data_quality_score_bin"] = _group_by_indexes(
            frame,
            quality_indexes,
            predictions_by_model,
            config=config,
        )
    confidence_indexes = _confidence_label_indexes(
        predictions_by_model.get(V3_PRIMARY_MODEL_NAME, [])
    )
    if confidence_indexes:
        groups["confidence_label"] = _group_by_indexes(
            frame,
            confidence_indexes,
            predictions_by_model,
            config=config,
        )
    return groups


def _group_by_indexes(
    frame: pd.DataFrame,
    indexes_by_group: dict[str, list[int]],
    predictions_by_model: dict[str, list[ProbabilityTriple | None]],
    *,
    config: V3BacktestConfig,
) -> JsonDict:
    output: JsonDict = {}
    y_true = list(frame[OUTCOME_COL].astype(str))
    for group_name, indexes in indexes_by_group.items():
        if not indexes:
            continue
        subset_predictions = {
            name: [predictions[index] for index in indexes]
            for name, predictions in predictions_by_model.items()
            if len(predictions) == len(frame) and name != "v3_no_draw_winner_only"
        }
        subset_true = [y_true[index] for index in indexes]
        output[group_name] = {
            "row_count": len(indexes),
            "metrics": {
                name: _metrics_for_predictions(subset_true, predictions, config=config)
                for name, predictions in subset_predictions.items()
            },
        }
    return output


def _success_criteria(test_metrics: JsonDict, test_groups: JsonDict) -> JsonDict:
    v3 = test_metrics.get(V3_PRIMARY_MODEL_NAME, {})
    v2 = test_metrics.get(V2_MODEL_NAME, {})
    if not v3.get("available"):
        return {
            "status": "not_evaluable",
            "reason": "V3 primary model did not produce usable predictions",
            "checks": {},
        }
    if not v2.get("available"):
        return {
            "status": "not_evaluable",
            "reason": "No V2 baseline available; provide --v2-model-dir or p_v2_* columns",
            "checks": {},
        }

    checks = {
        "log_loss_improvement": _threshold_check(
            _delta(v3.get("log_loss"), v2.get("log_loss")),
            threshold=-0.005,
            comparator="<=",
            description="log_loss V3 <= log_loss V2 - 0.005",
        ),
        "brier_improvement": _threshold_check(
            _delta(v3.get("brier_score"), v2.get("brier_score")),
            threshold=-0.003,
            comparator="<=",
            description="Brier V3 <= Brier V2 - 0.003",
        ),
        "draw_ece_improvement": _threshold_check(
            _delta(v3.get("draw_ece"), v2.get("draw_ece")),
            threshold=-0.01,
            comparator="<=",
            description="ECE Draw V3 <= ECE Draw V2 - 0.01",
        ),
        "confidence_gap_no_regression": _threshold_check(
            _delta(v3.get("avg_confidence_gap"), v2.get("avg_confidence_gap")),
            threshold=0.0,
            comparator=">=",
            description="Average confidence gap V3 >= V2",
        ),
        "league_log_loss_no_regression": _league_regression_check(test_groups),
    }
    evaluable = all(check["evaluable"] for check in checks.values())
    passed = evaluable and all(check["passed"] for check in checks.values())
    return {
        "status": "passed" if passed else "failed" if evaluable else "not_evaluable",
        "checks": checks,
    }


def _league_regression_check(test_groups: JsonDict) -> JsonDict:
    regressions: list[JsonDict] = []
    for league_id, payload in test_groups.get("league_id", {}).items():
        row_count = int(payload.get("row_count", 0))
        if row_count < 100:
            continue
        metrics = payload.get("metrics", {})
        v3 = metrics.get(V3_PRIMARY_MODEL_NAME, {})
        v2 = metrics.get(V2_MODEL_NAME, {})
        delta = _delta(v3.get("log_loss"), v2.get("log_loss"))
        if delta is None:
            continue
        if delta > 0.005:
            regressions.append(
                {
                    "league_id": league_id,
                    "row_count": row_count,
                    "log_loss_delta_v3_minus_v2": delta,
                }
            )
    return {
        "evaluable": True,
        "passed": not regressions,
        "description": "No league with >=100 test matches regresses by >0.005 log_loss",
        "regressions": regressions,
    }


def _write_reports(
    payload: JsonDict,
    output_dir: Path,
    *,
    report_format: ReportFormat,
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}
    if report_format in {"json", "both"}:
        paths["json"] = output_dir / "v3_backtest_report.json"
        paths["json"].write_text(
            json.dumps(_json_ready(payload), indent=2, sort_keys=True),
            encoding="utf-8",
        )
    if report_format in {"markdown", "both"}:
        paths["markdown"] = output_dir / "comparison_vs_v2.md"
        paths["markdown"].write_text(_markdown_report(payload), encoding="utf-8")
    return paths


def _markdown_report(payload: JsonDict) -> str:
    lines = [
        "# Backtest V3 - Comparaison",
        "",
        f"- Dataset: `{payload.get('dataset_path', '')}`",
        f"- Model dir: `{payload.get('model_dir', '')}`",
        f"- V2 model dir: `{payload.get('v2_model_dir') or 'not provided'}`",
        f"- Generated at: `{payload.get('generated_at', '')}`",
        "",
        "## Splits",
        "",
        "| Split | Rows | Start | End |",
        "| --- | ---: | --- | --- |",
    ]
    for name, period in payload.get("periods", {}).items():
        lines.append(
            f"| {name} | {period.get('row_count', 0)} | {period.get('start') or ''} | "
            f"{period.get('end') or ''} |"
        )
    lines.extend(
        [
            "",
            "## Comparatif Test",
            "",
            "| Modèle | Rows | Coverage | Accuracy | Log loss | Brier | "
            "Draw F1 | Draw AUC | Draw ECE | Conf. gap |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for name, metrics in payload.get("metrics", {}).get("test", {}).items():
        draw = metrics.get("draw_metrics", {})
        lines.append(
            f"| {name} | {metrics.get('row_count', 0)} | {_fmt(metrics.get('coverage'))} | "
            f"{_fmt(metrics.get('accuracy'))} | {_fmt(metrics.get('log_loss'))} | "
            f"{_fmt(metrics.get('brier_score'))} | {_fmt(draw.get('f1'))} | "
            f"{_fmt(draw.get('roc_auc'))} | {_fmt(metrics.get('draw_ece'))} | "
            f"{_fmt(metrics.get('avg_confidence_gap'))} |"
        )
    lines.extend(["", "## Critères V3", ""])
    success = payload.get("success_criteria", {})
    lines.append(f"Statut: `{success.get('status', 'not_evaluable')}`")
    if success.get("reason"):
        lines.append(f"Raison: {success['reason']}")
    checks = success.get("checks", {})
    if checks:
        lines.extend(
            [
                "",
                "| Critère | Passed | Delta | Seuil |",
                "| --- | --- | ---: | ---: |",
            ]
        )
        for name, check in checks.items():
            if name == "league_log_loss_no_regression":
                lines.append(
                    f"| {name} | {check.get('passed')} | "
                    f"{len(check.get('regressions', []))} regression(s) | 0 |"
                )
            else:
                lines.append(
                    f"| {name} | {check.get('passed')} | "
                    f"{_fmt(check.get('delta'))} | {_fmt(check.get('threshold'))} |"
                )
    lines.extend(["", "## Groupes Test", ""])
    for group_name, groups in payload.get("group_metrics", {}).get("test", {}).items():
        lines.append(f"### {group_name}")
        lines.append("")
        if not groups:
            lines.append("_Non disponible._")
            lines.append("")
            continue
        lines.append("| Groupe | Rows |")
        lines.append("| --- | ---: |")
        for value, group_payload in groups.items():
            lines.append(f"| `{value}` | {group_payload.get('row_count', 0)} |")
        lines.append("")
    lines.extend(
        [
            "## Note",
            "",
            "Le rapport évalue le fold test chronologique. Si les critères V3 sont `failed` "
            "ou `not_evaluable`, la V3 reste candidate et la V2 reste le chemin de production.",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def _load_dataset(path: Path) -> pd.DataFrame:
    suffix = path.suffix.casefold()
    if suffix == ".csv":
        return pd.read_csv(path)
    if suffix in {".parquet", ".pq"}:
        return pd.read_parquet(path, engine="pyarrow")
    raise ValueError("dataset_path must be .csv or .parquet")


def _validate_config(config: V3BacktestConfig) -> None:
    if config.train_ratio <= 0 or config.valid_ratio <= 0:
        raise ValueError("train_ratio and valid_ratio must be positive")
    if config.train_ratio + config.valid_ratio >= 1:
        raise ValueError("train_ratio + valid_ratio must be less than 1")
    if config.calibration_bins <= 0:
        raise ValueError("calibration_bins must be positive")
    if config.report_format not in {"json", "markdown", "both"}:
        raise ValueError("report_format must be json, markdown, or both")


def _validate_dataset(frame: pd.DataFrame) -> None:
    if frame.empty:
        raise ValueError("V3 backtest dataset is empty")
    if "fixture_date" not in frame.columns:
        raise ValueError("fixture_date is required for V3 backtesting")
    invalid_dates = pd.to_datetime(frame["fixture_date"], utc=True, errors="coerce").isna()
    if invalid_dates.any():
        raise ValueError("fixture_date contains invalid datetime values")
    labels = set(frame[OUTCOME_COL].astype(str))
    invalid = labels.difference(CLASSES)
    if invalid:
        raise ValueError(f"Unknown target labels: {sorted(invalid)}")


def _v3_artifacts_exist(model_dir: Path) -> bool:
    return all(
        path.exists()
        for path in (
            model_dir / "draw_risk" / "model.joblib",
            model_dir / "no_draw_winner" / "model.joblib",
        )
    )


def _load_optional_model(path: Path | None) -> Any | None:
    if path is None:
        return None
    model_path = path / "model.joblib" if path.is_dir() else path
    if not model_path.exists():
        return None
    return joblib.load(model_path)


def _v2_predictions(frame: pd.DataFrame, v2_model: Any | None) -> list[ProbabilityTriple | None]:
    if v2_model is not None:
        try:
            return [ProbabilityTriple.from_vector(row) for row in v2_model.predict_proba(frame)]
        except Exception:
            return [None for _ in range(len(frame))]
    output: list[ProbabilityTriple | None] = []
    for row in _rows(frame):
        output.append(v2_probability_from_row(row))
    return output


def _blend_predictions(
    left: list[ProbabilityTriple | None],
    right: list[ProbabilityTriple | None],
) -> list[ProbabilityTriple | None]:
    output: list[ProbabilityTriple | None] = []
    for left_item, right_item in zip(left, right, strict=True):
        if left_item is None or right_item is None:
            output.append(None)
            continue
        left_values = left_item.as_dict()
        right_values = right_item.as_dict()
        output.append(
            ProbabilityTriple.from_mapping(
                {
                    label: 0.5 * left_values[label] + 0.5 * right_values[label]
                    for label in CLASSES
                }
            )
        )
    return output


def _average_confidence_gap(predictions: list[ProbabilityTriple]) -> float | None:
    if not predictions:
        return None
    return sum(confidence_gap(prediction.to_vector()) for prediction in predictions) / len(
        predictions
    )


def _binary_auc(labels: list[int], probabilities: list[float]) -> float | None:
    if len(set(labels)) < 2:
        return None
    return float(roc_auc_score(labels, probabilities))


def _binary_pr_auc(labels: list[int], probabilities: list[float]) -> float | None:
    if len(set(labels)) < 2 or sum(labels) == 0:
        return None
    return float(average_precision_score(labels, probabilities))


def _binary_calibration_bins(
    labels: list[int],
    probabilities: list[float],
    *,
    n_bins: int,
) -> list[JsonDict]:
    bins: list[list[tuple[float, int]]] = [[] for _ in range(n_bins)]
    for label, probability in zip(labels, probabilities, strict=True):
        index = min(int(float(probability) * n_bins), n_bins - 1)
        bins[index].append((float(probability), int(label)))
    output: list[JsonDict] = []
    for index, rows in enumerate(bins):
        lower = index / n_bins
        upper = (index + 1) / n_bins
        if not rows:
            output.append(
                {
                    "bin": index,
                    "lower": lower,
                    "upper": upper,
                    "count": 0,
                    "avg_probability": None,
                    "event_rate": None,
                }
            )
            continue
        output.append(
            {
                "bin": index,
                "lower": lower,
                "upper": upper,
                "count": len(rows),
                "avg_probability": sum(probability for probability, _label in rows) / len(rows),
                "event_rate": sum(label for _probability, label in rows) / len(rows),
            }
        )
    return output


def _binary_ece(labels: list[int], probabilities: list[float], *, n_bins: int) -> float | None:
    if not labels:
        return None
    total = len(labels)
    ece = 0.0
    for item in _binary_calibration_bins(labels, probabilities, n_bins=n_bins):
        count = int(item["count"])
        if count == 0:
            continue
        avg_probability = float(item["avg_probability"])
        event_rate = float(item["event_rate"])
        ece += (count / total) * abs(avg_probability - event_rate)
    return ece


def _indexes_by_column(frame: pd.DataFrame, column: str) -> dict[str, list[int]]:
    return _indexes_by_values(frame[column].astype(str))


def _indexes_by_values(values: pd.Series) -> dict[str, list[int]]:
    output: dict[str, list[int]] = {}
    for index, value in enumerate(values):
        output.setdefault(str(value), []).append(index)
    return output


def _data_quality_indexes(frame: pd.DataFrame) -> dict[str, list[int]]:
    column = "data_quality_score" if "data_quality_score" in frame.columns else None
    if column is None and "overall_data_quality_score" in frame.columns:
        column = "overall_data_quality_score"
    if column is None:
        return {}
    values = pd.to_numeric(frame[column], errors="coerce")
    scale = 100.0 if values.max(skipna=True) <= 1.0 else 1.0
    buckets: dict[str, list[int]] = {
        "0_25": [],
        "25_50": [],
        "50_75": [],
        "75_100": [],
        "missing": [],
    }
    for index, value in enumerate(values):
        if pd.isna(value):
            buckets["missing"].append(index)
            continue
        score = float(value) * scale
        if score < 25:
            buckets["0_25"].append(index)
        elif score < 50:
            buckets["25_50"].append(index)
        elif score < 75:
            buckets["50_75"].append(index)
        else:
            buckets["75_100"].append(index)
    return {name: indexes for name, indexes in buckets.items() if indexes}


def _confidence_label_indexes(
    predictions: list[ProbabilityTriple | None],
) -> dict[str, list[int]]:
    buckets: dict[str, list[int]] = {
        "uncertain_<0.40": [],
        "low_0.40_0.50": [],
        "medium_0.50_0.70": [],
        "high_>=0.70": [],
    }
    for index, prediction in enumerate(predictions):
        if prediction is None:
            continue
        confidence = prediction.max_probability()
        if confidence < 0.40:
            buckets["uncertain_<0.40"].append(index)
        elif confidence < 0.50:
            buckets["low_0.40_0.50"].append(index)
        elif confidence < 0.70:
            buckets["medium_0.50_0.70"].append(index)
        else:
            buckets["high_>=0.70"].append(index)
    return {name: indexes for name, indexes in buckets.items() if indexes}


def _threshold_check(
    delta: float | None,
    *,
    threshold: float,
    comparator: Literal["<=", ">="],
    description: str,
) -> JsonDict:
    if delta is None:
        return {
            "evaluable": False,
            "passed": False,
            "delta": None,
            "threshold": threshold,
            "description": description,
        }
    passed = delta <= threshold if comparator == "<=" else delta >= threshold
    return {
        "evaluable": True,
        "passed": passed,
        "delta": delta,
        "threshold": threshold,
        "description": description,
    }


def _delta(left: Any, right: Any) -> float | None:
    try:
        left_value = float(left)
        right_value = float(right)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(left_value) or not math.isfinite(right_value):
        return None
    return left_value - right_value


def _period_for(name: str, frame: pd.DataFrame) -> V3SplitPeriod:
    if frame.empty:
        return V3SplitPeriod(name=name, row_count=0, start=None, end=None)
    dates = pd.to_datetime(frame["fixture_date"], utc=True)
    return V3SplitPeriod(
        name=name,
        row_count=len(frame),
        start=dates.min().isoformat(),
        end=dates.max().isoformat(),
    )


def _rows(frame: pd.DataFrame) -> list[dict[str, Any]]:
    return [row.to_dict() for _, row in frame.iterrows()]


def _float_or_default(value: Any, default: float) -> float:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return default
    if not math.isfinite(numeric):
        return default
    return min(max(numeric, 1e-15), 1.0 - 1e-15)


def _fmt(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return str(value)
    try:
        return f"{float(value):.4f}"
    except (TypeError, ValueError):
        return str(value)


def _json_ready(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_ready(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [_json_ready(item) for item in value]
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        numeric = float(value)
        return numeric if math.isfinite(numeric) else None
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    return value
