"""Backtesting reports for the World Cup 1X2 model."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd  # type: ignore[import-untyped]

from football_predictor.modeling.probabilities import ProbabilityTriple
from football_predictor.worldcup.features import (
    is_continental,
    is_world_cup,
    is_world_cup_qualification,
)
from football_predictor.worldcup.model import (
    WorldCup1X2Model,
    WorldCupTrainingConfig,
    chronological_split,
    evaluate_worldcup_baselines,
    evaluate_worldcup_frame,
    fit_worldcup_model,
)

JsonDict = dict[str, Any]


@dataclass(frozen=True)
class WorldCupBacktestResult:
    metrics: JsonDict
    report_paths: dict[str, Path]


def run_worldcup_backtest(
    dataset_path: Path,
    *,
    model_dir: Path | None = None,
    output_dir: Path = Path("reports/worldcup"),
    train_ratio: float = 0.60,
    valid_ratio: float = 0.20,
) -> WorldCupBacktestResult:
    frame = _load_dataset(dataset_path)
    train, valid, test = chronological_split(
        frame,
        train_ratio=train_ratio,
        valid_ratio=valid_ratio,
    )
    if model_dir is not None and (model_dir / "model.joblib").exists():
        model = WorldCup1X2Model.load(model_dir)
        model_source = str(model_dir)
    else:
        model, _metrics = fit_worldcup_model(
            train,
            valid,
            test,
            config=WorldCupTrainingConfig(train_ratio=train_ratio, valid_ratio=valid_ratio),
        )
        model_source = "trained_in_backtest"
    metrics: JsonDict = {
        "dataset": str(dataset_path),
        "model_source": model_source,
        "periods": {
            "train": _period_payload(train),
            "validation": _period_payload(valid),
            "test": _period_payload(test),
        },
        "metrics_by_model": {
            "worldcup_1x2": {
                "validation": evaluate_worldcup_frame(model, valid),
                "test": evaluate_worldcup_frame(model, test),
            },
            "worldcup_1x2_static": {
                "validation": evaluate_worldcup_frame(model, valid, include_dynamic=False),
                "test": evaluate_worldcup_frame(model, test, include_dynamic=False),
            },
            "worldcup_1x2_dynamic_available": {
                "validation": evaluate_worldcup_frame(model, _dynamic_available(valid)),
                "test": evaluate_worldcup_frame(model, _dynamic_available(test)),
            },
            "baselines": {
                "validation": evaluate_worldcup_baselines(valid),
                "test": evaluate_worldcup_baselines(test),
            },
        },
        "dynamic_coverage": {
            "validation": _dynamic_coverage(valid),
            "test": _dynamic_coverage(test),
        },
        "group_metrics": {
            "all_international": evaluate_worldcup_frame(model, test),
            "world_cup_tournament": evaluate_worldcup_frame(model, _tournament_subset(test, "wc")),
            "world_cup_qualifiers": evaluate_worldcup_frame(
                model,
                _tournament_subset(test, "qualifiers"),
            ),
            "continental": evaluate_worldcup_frame(model, _tournament_subset(test, "continental")),
            "test_by_tournament": _group_accuracy(model, test, "tournament"),
            "test_by_neutral": _group_accuracy(model, test, "neutral"),
        },
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "worldcup_backtest_report.json"
    md_path = output_dir / "worldcup_backtest_report.md"
    json_path.write_text(json.dumps(metrics, indent=2, sort_keys=True), encoding="utf-8")
    md_path.write_text(_markdown_report(metrics), encoding="utf-8")
    return WorldCupBacktestResult(
        metrics=metrics,
        report_paths={"json": json_path, "markdown": md_path},
    )


def _load_dataset(path: Path) -> pd.DataFrame:
    suffix = path.suffix.casefold()
    if suffix == ".csv":
        return pd.read_csv(path)
    if suffix == ".parquet":
        return pd.read_parquet(path, engine="pyarrow")
    raise ValueError("dataset_path must be .csv or .parquet")


def _period_payload(frame: pd.DataFrame) -> JsonDict:
    if frame.empty:
        return {"row_count": 0, "start": None, "end": None}
    return {
        "row_count": len(frame),
        "start": str(frame["fixture_date"].min()),
        "end": str(frame["fixture_date"].max()),
    }


def _group_accuracy(model: WorldCup1X2Model, frame: pd.DataFrame, column: str) -> list[JsonDict]:
    if frame.empty or column not in frame.columns:
        return []
    probabilities = [ProbabilityTriple.from_vector(row) for row in model.predict_proba(frame)]
    result = frame.copy()
    result["predicted"] = [probability.predicted_result() for probability in probabilities]
    rows: list[JsonDict] = []
    for value, part in result.groupby(column, dropna=False):
        rows.append(
            {
                "group": str(value),
                "row_count": len(part),
                "accuracy": float((part["predicted"] == part["target"]).mean()),
            }
        )
    rows.sort(key=lambda item: (-int(item["row_count"]), item["group"]))
    return rows[:30]


def _dynamic_available(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty or "wc_dynamic_any_source_available_flag" not in frame.columns:
        return frame.iloc[0:0].copy()
    mask = pd.to_numeric(frame["wc_dynamic_any_source_available_flag"], errors="coerce").fillna(0)
    return frame.loc[mask > 0].copy()


def _dynamic_coverage(frame: pd.DataFrame) -> JsonDict:
    row_count = len(frame)
    if row_count == 0:
        return {"row_count": 0}
    fields = {
        "market": "wc_dynamic_market_available_flag",
        "api_prediction": "wc_dynamic_api_prediction_available_flag",
        "lineups": "wc_dynamic_lineups_available_flag",
        "injuries": "wc_dynamic_injuries_available_flag",
        "any": "wc_dynamic_any_source_available_flag",
    }
    payload: JsonDict = {"row_count": row_count}
    for label, column in fields.items():
        if column not in frame.columns:
            payload[label] = {"count": 0, "coverage": 0.0}
            continue
        count = int((pd.to_numeric(frame[column], errors="coerce").fillna(0) > 0).sum())
        payload[label] = {"count": count, "coverage": count / row_count}
    return payload


def _tournament_subset(frame: pd.DataFrame, kind: str) -> pd.DataFrame:
    if frame.empty or "tournament" not in frame.columns:
        return frame.iloc[0:0].copy()
    if kind == "wc":
        mask = frame["tournament"].astype(str).map(is_world_cup)
    elif kind == "qualifiers":
        mask = frame["tournament"].astype(str).map(is_world_cup_qualification)
    elif kind == "continental":
        mask = frame["tournament"].astype(str).map(is_continental)
    else:
        mask = pd.Series([False] * len(frame), index=frame.index)
    return frame.loc[mask].copy()


def _markdown_report(metrics: JsonDict) -> str:
    test = (
        metrics.get("metrics_by_model", {})
        .get("worldcup_1x2", {})
        .get("test", {})
    )
    baselines = (
        metrics.get("metrics_by_model", {})
        .get("baselines", {})
        .get("test", {})
    )
    rating = baselines.get("wc_rating", {}) if isinstance(baselines, dict) else {}
    poisson = baselines.get("wc_poisson", {}) if isinstance(baselines, dict) else {}
    dynamic = metrics.get("dynamic_coverage", {}).get("test", {})
    return "\n".join(
        [
            "# World Cup 1X2 Backtest",
            "",
            f"- Dataset: `{metrics.get('dataset')}`",
            f"- Model source: `{metrics.get('model_source')}`",
            f"- Test rows: {test.get('row_count')}",
            f"- WorldCup 1X2 accuracy: {test.get('accuracy')}",
            f"- WorldCup 1X2 log_loss: {test.get('log_loss')}",
            f"- Rating baseline accuracy: {rating.get('accuracy')}",
            f"- Poisson baseline accuracy: {poisson.get('accuracy')}",
            f"- Dynamic source coverage: {json.dumps(dynamic, sort_keys=True)}",
            "",
            "## Periods",
            "",
            json.dumps(metrics.get("periods", {}), indent=2, sort_keys=True),
        ]
    )
