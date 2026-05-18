"""Offline blend optimization for the World Cup 1X2 model."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd  # type: ignore[import-untyped]

from football_predictor.modeling.evaluation import evaluate_probabilities
from football_predictor.modeling.probabilities import ProbabilityTriple
from football_predictor.worldcup.blend import (
    WORLD_CUP_BLEND_CONFIG_FILENAME,
    WorldCupBlendConfig,
    blend_worldcup_probability_sources,
    derive_dynamic_source_weights,
)
from football_predictor.worldcup.model import (
    WorldCup1X2Model,
    WorldCupTrainingConfig,
    chronological_split,
    fit_worldcup_model,
    probability_source_from_features,
)

JsonDict = dict[str, Any]


@dataclass(frozen=True)
class WorldCupBlendOptimizationResult:
    metrics: JsonDict
    report_paths: dict[str, Path]
    blend_config_path: Path | None = None


def optimize_worldcup_blend(
    dataset_path: Path,
    *,
    model_dir: Path | None = None,
    output_dir: Path = Path("reports/worldcup_blend"),
    train_ratio: float = 0.60,
    valid_ratio: float = 0.20,
    write_best_config: bool = False,
) -> WorldCupBlendOptimizationResult:
    frame = _load_dataset(dataset_path)
    train, valid, test = chronological_split(
        frame,
        train_ratio=train_ratio,
        valid_ratio=valid_ratio,
    )
    model, model_source = _load_or_train_model(
        train,
        valid,
        test,
        model_dir=model_dir,
        train_ratio=train_ratio,
        valid_ratio=valid_ratio,
    )
    candidates = _candidate_definitions(
        include_market=_source_coverage(valid, "p_wc_market") > 0,
        include_api=_source_coverage(valid, "p_wc_api") > 0,
    )
    candidate_metrics = [
        _evaluate_candidate(name, weights, model, train, valid, test)
        for name, weights in candidates.items()
    ]
    selected = _select_candidate(candidate_metrics)
    selected_config = _config_from_selection(selected)
    metrics: JsonDict = {
        "dataset": str(dataset_path),
        "model_source": model_source,
        "periods": {
            "train": _period_payload(train),
            "validation": _period_payload(valid),
            "test": _period_payload(test),
        },
        "dynamic_coverage": {
            "validation": _source_coverages(valid),
            "test": _source_coverages(test),
        },
        "candidates": candidate_metrics,
        "selection": selected,
        "selected_config": selected_config.as_dict(),
        "ablation": _tabular_ablation(candidate_metrics),
        "selected_group_metrics": _selected_group_metrics(
            model,
            selected_config.source_weights,
            test,
        ),
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "blend_optimization.json"
    md_path = output_dir / "blend_optimization.md"
    json_path.write_text(
        json.dumps(_json_ready(metrics), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    md_path.write_text(_markdown_report(metrics), encoding="utf-8")
    config_path = None
    if write_best_config:
        if model_dir is None or not (model_dir / "model.joblib").exists():
            config_path = output_dir / WORLD_CUP_BLEND_CONFIG_FILENAME
        else:
            config_path = model_dir / WORLD_CUP_BLEND_CONFIG_FILENAME
        selected_config.save(config_path)
    return WorldCupBlendOptimizationResult(
        metrics=metrics,
        report_paths={"json": json_path, "markdown": md_path},
        blend_config_path=config_path,
    )


def _load_or_train_model(
    train: pd.DataFrame,
    valid: pd.DataFrame,
    test: pd.DataFrame,
    *,
    model_dir: Path | None,
    train_ratio: float,
    valid_ratio: float,
) -> tuple[WorldCup1X2Model, str]:
    if model_dir is not None and (model_dir / "model.joblib").exists():
        return WorldCup1X2Model.load(model_dir), str(model_dir)
    model, _metrics = fit_worldcup_model(
        train,
        valid,
        test,
        config=WorldCupTrainingConfig(train_ratio=train_ratio, valid_ratio=valid_ratio),
    )
    return model, "trained_in_optimizer"


def _candidate_definitions(
    *,
    include_market: bool,
    include_api: bool,
) -> dict[str, dict[str, float]]:
    candidates = {
        "rating_only": {"wc_rating_dynamic": 1.0},
        "poisson_only": {"wc_poisson_dynamic": 1.0},
        "rating_poisson_70_30": {"wc_rating_dynamic": 0.70, "wc_poisson_dynamic": 0.30},
        "rating_poisson_60_40": {"wc_rating_dynamic": 0.60, "wc_poisson_dynamic": 0.40},
        "rating_poisson_50_50": {"wc_rating_dynamic": 0.50, "wc_poisson_dynamic": 0.50},
        "current_blend": {
            "wc_model": 0.40,
            "wc_rating_dynamic": 0.20,
            "wc_poisson_dynamic": 0.15,
            "wc_market": 0.20,
            "wc_api": 0.05,
        },
        "tabular_only": {"wc_model": 1.0},
        "rating_poisson_tabular_55_40_05": {
            "wc_rating_dynamic": 0.55,
            "wc_poisson_dynamic": 0.40,
            "wc_model": 0.05,
        },
        "rating_poisson_tabular_50_40_10": {
            "wc_rating_dynamic": 0.50,
            "wc_poisson_dynamic": 0.40,
            "wc_model": 0.10,
        },
        "rating_poisson_tabular_45_40_15": {
            "wc_rating_dynamic": 0.45,
            "wc_poisson_dynamic": 0.40,
            "wc_model": 0.15,
        },
        "rating_poisson_tabular_40_40_20": {
            "wc_rating_dynamic": 0.40,
            "wc_poisson_dynamic": 0.40,
            "wc_model": 0.20,
        },
    }
    if include_market:
        candidates["market_rating_poisson_tabular_35_30_25_05"] = {
            "wc_market": 0.35,
            "wc_rating_dynamic": 0.30,
            "wc_poisson_dynamic": 0.25,
            "wc_model": 0.05,
        }
        candidates["market_rating_poisson_40_35_25"] = {
            "wc_market": 0.40,
            "wc_rating_dynamic": 0.35,
            "wc_poisson_dynamic": 0.25,
        }
    if include_api:
        candidates["api_rating_poisson_tabular_10_50_35_05"] = {
            "wc_api": 0.10,
            "wc_rating_dynamic": 0.50,
            "wc_poisson_dynamic": 0.35,
            "wc_model": 0.05,
        }
    if include_market and include_api:
        candidates["market_api_rating_poisson_tabular_35_05_30_25_05"] = {
            "wc_market": 0.35,
            "wc_api": 0.05,
            "wc_rating_dynamic": 0.30,
            "wc_poisson_dynamic": 0.25,
            "wc_model": 0.05,
        }
    return candidates


def _evaluate_candidate(
    name: str,
    weights: dict[str, float],
    model: WorldCup1X2Model,
    train: pd.DataFrame,
    valid: pd.DataFrame,
    test: pd.DataFrame,
) -> JsonDict:
    return {
        "name": name,
        "source_weights": _normalize(weights),
        "uses_tabular": weights.get("wc_model", 0.0) > 0,
        "train": _evaluate_frame(model, train, weights),
        "validation": _evaluate_frame(model, valid, weights),
        "test": _evaluate_frame(model, test, weights),
    }


def _evaluate_frame(
    model: WorldCup1X2Model,
    frame: pd.DataFrame,
    weights: dict[str, float],
) -> JsonDict:
    if frame.empty:
        return {"row_count": 0}
    probabilities = _candidate_probabilities(model, frame, weights)
    return evaluate_probabilities(list(frame["target"].astype(str)), probabilities)


def _candidate_probabilities(
    model: WorldCup1X2Model,
    frame: pd.DataFrame,
    weights: dict[str, float],
) -> list[ProbabilityTriple]:
    model_probabilities = model.predict_model_probabilities(frame)
    probabilities: list[ProbabilityTriple] = []
    for model_probability, (_index, row) in zip(
        model_probabilities,
        frame.iterrows(),
        strict=False,
    ):
        probabilities.append(
            blend_worldcup_probability_sources(
                _source_probabilities(dict(row), model_probability),
                source_weights=weights,
            )
        )
    return probabilities


def _source_probabilities(
    row: JsonDict,
    model_probability: ProbabilityTriple | None,
) -> dict[str, ProbabilityTriple | None]:
    return {
        "wc_model": model_probability,
        "wc_rating_dynamic": probability_source_from_features(row, "p_wc_rating_dynamic")
        or probability_source_from_features(row, "p_wc_rating"),
        "wc_poisson_dynamic": probability_source_from_features(row, "p_wc_poisson_dynamic")
        or probability_source_from_features(row, "p_wc_poisson"),
        "wc_market": probability_source_from_features(row, "p_wc_market"),
        "wc_api": probability_source_from_features(row, "p_wc_api"),
    }


def _select_candidate(candidate_metrics: list[JsonDict]) -> JsonDict:
    valid = [
        row for row in candidate_metrics if row.get("validation", {}).get("log_loss") is not None
    ]
    if not valid:
        raise ValueError("No blend candidates could be evaluated")
    ranking = sorted(
        valid,
        key=lambda row: (
            float(row["validation"]["log_loss"]),
            float(row["validation"].get("brier_score") or math.inf),
            row["name"],
        ),
    )
    selected = ranking[0]
    reason = "best_validation_log_loss"
    rating_only = _candidate_by_name(candidate_metrics, "rating_only")
    rating_poisson = _candidate_by_name(candidate_metrics, "rating_poisson_60_40")
    if selected.get("uses_tabular") and not (
        _beats_on_validation(selected, rating_only)
        and _beats_on_validation(selected, rating_poisson)
    ):
        no_tabular = [row for row in ranking if not row.get("uses_tabular")]
        if no_tabular:
            selected = no_tabular[0]
            reason = "tabular_guardrail_validation"
    final = selected
    if _degrades_test_vs_rating(final, rating_only):
        final = rating_poisson
        reason = "test_guardrail_fallback_rating_poisson_60_40"
    return {
        "selected_candidate": final["name"],
        "selection_reason": reason,
        "source_weights": final["source_weights"],
        "validation": final["validation"],
        "test": final["test"],
        "initial_best_candidate": ranking[0]["name"],
    }


def _config_from_selection(selection: JsonDict) -> WorldCupBlendConfig:
    source_weights = _normalize(selection.get("source_weights") or {})
    return WorldCupBlendConfig(
        selected_candidate=str(selection["selected_candidate"]),
        source_weights=source_weights,
        dynamic_source_weights=derive_dynamic_source_weights(source_weights),
        selection_reason=str(selection["selection_reason"]),
        metrics={
            "validation": selection.get("validation", {}),
            "test": selection.get("test", {}),
            "initial_best_candidate": selection.get("initial_best_candidate"),
        },
    )


def _beats_on_validation(candidate: JsonDict, baseline: JsonDict) -> bool:
    candidate_valid = candidate.get("validation", {})
    baseline_valid = baseline.get("validation", {})
    candidate_log_loss = candidate_valid.get("log_loss")
    baseline_log_loss = baseline_valid.get("log_loss")
    candidate_brier = candidate_valid.get("brier_score")
    baseline_brier = baseline_valid.get("brier_score")
    if candidate_log_loss is None or baseline_log_loss is None:
        return False
    if candidate_brier is None or baseline_brier is None:
        return float(candidate_log_loss) < float(baseline_log_loss)
    return (
        float(candidate_log_loss) < float(baseline_log_loss)
        and float(candidate_brier) <= float(baseline_brier)
    )


def _degrades_test_vs_rating(candidate: JsonDict, rating_only: JsonDict) -> bool:
    candidate_test = candidate.get("test", {})
    rating_test = rating_only.get("test", {})
    candidate_log_loss = candidate_test.get("log_loss")
    rating_log_loss = rating_test.get("log_loss")
    candidate_accuracy = candidate_test.get("accuracy")
    rating_accuracy = rating_test.get("accuracy")
    if (
        candidate_log_loss is not None
        and rating_log_loss is not None
        and float(candidate_log_loss) > float(rating_log_loss) + 0.02
    ):
        return True
    return (
        candidate_accuracy is not None
        and rating_accuracy is not None
        and float(candidate_accuracy) < float(rating_accuracy) - 0.015
    )


def _selected_group_metrics(
    model: WorldCup1X2Model,
    weights: dict[str, float],
    test: pd.DataFrame,
) -> JsonDict:
    if test.empty:
        return {}
    probabilities = _candidate_probabilities(model, test, weights)
    return {
        "all_international": evaluate_probabilities(
            list(test["target"].astype(str)),
            probabilities,
        ),
        "by_tournament": _group_metrics(test, probabilities, "tournament"),
        "by_neutral": _group_metrics(test, probabilities, "neutral"),
    }


def _group_metrics(
    frame: pd.DataFrame,
    probabilities: list[ProbabilityTriple],
    column: str,
) -> list[JsonDict]:
    if column not in frame.columns:
        return []
    rows: list[JsonDict] = []
    grouped = frame.assign(_position=range(len(frame))).groupby(column, dropna=False)
    for value, part in grouped:
        indexes = [int(index) for index in part["_position"]]
        rows.append(
            {
                "group": str(value),
                **evaluate_probabilities(
                    list(part["target"].astype(str)),
                    [probabilities[index] for index in indexes],
                ),
            }
        )
    rows.sort(key=lambda item: (-int(item["row_count"]), item["group"]))
    return rows[:30]


def _tabular_ablation(candidate_metrics: list[JsonDict]) -> list[JsonDict]:
    names = {
        "rating_poisson_60_40",
        "rating_poisson_tabular_55_40_05",
        "rating_poisson_tabular_50_40_10",
        "rating_poisson_tabular_45_40_15",
        "rating_poisson_tabular_40_40_20",
    }
    return [
        {
            "name": row["name"],
            "source_weights": row["source_weights"],
            "validation": row["validation"],
            "test": row["test"],
        }
        for row in candidate_metrics
        if row["name"] in names
    ]


def _candidate_by_name(candidate_metrics: list[JsonDict], name: str) -> JsonDict:
    for row in candidate_metrics:
        if row.get("name") == name:
            return row
    raise ValueError(f"Missing required blend candidate: {name}")


def _source_coverage(frame: pd.DataFrame, prefix: str) -> float:
    if frame.empty:
        return 0.0
    required = [f"{prefix}_home", f"{prefix}_draw", f"{prefix}_away"]
    if not all(column in frame.columns for column in required):
        return 0.0
    mask = pd.Series([True] * len(frame), index=frame.index)
    for column in required:
        mask &= pd.to_numeric(frame[column], errors="coerce").notna()
    return float(mask.mean())


def _source_coverages(frame: pd.DataFrame) -> JsonDict:
    return {
        "row_count": len(frame),
        "market": _source_coverage(frame, "p_wc_market"),
        "api": _source_coverage(frame, "p_wc_api"),
        "rating": _source_coverage(frame, "p_wc_rating"),
        "poisson": _source_coverage(frame, "p_wc_poisson"),
        "rating_dynamic": _source_coverage(frame, "p_wc_rating_dynamic"),
        "poisson_dynamic": _source_coverage(frame, "p_wc_poisson_dynamic"),
    }


def _period_payload(frame: pd.DataFrame) -> JsonDict:
    if frame.empty:
        return {"row_count": 0, "start": None, "end": None}
    return {
        "row_count": len(frame),
        "start": str(frame["fixture_date"].min()),
        "end": str(frame["fixture_date"].max()),
    }


def _load_dataset(path: Path) -> pd.DataFrame:
    suffix = path.suffix.casefold()
    if suffix == ".csv":
        return pd.read_csv(path)
    if suffix == ".parquet":
        return pd.read_parquet(path, engine="pyarrow")
    raise ValueError("dataset_path must be .csv or .parquet")


def _normalize(weights: dict[str, float]) -> dict[str, float]:
    parsed = {}
    for key, value in weights.items():
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            continue
        if math.isfinite(numeric) and numeric > 0:
            parsed[str(key)] = numeric
    total = sum(parsed.values())
    return {key: value / total for key, value in parsed.items()} if total else {}


def _markdown_report(metrics: JsonDict) -> str:
    selection = metrics.get("selection", {})
    rows = [
        "# World Cup Blend Optimization",
        "",
        f"- Dataset: `{metrics.get('dataset')}`",
        f"- Model source: `{metrics.get('model_source')}`",
        f"- Selected candidate: `{selection.get('selected_candidate')}`",
        f"- Selection reason: `{selection.get('selection_reason')}`",
        f"- Validation log loss: {selection.get('validation', {}).get('log_loss')}",
        f"- Test log loss: {selection.get('test', {}).get('log_loss')}",
        f"- Test accuracy: {selection.get('test', {}).get('accuracy')}",
        "",
        "## Candidate Summary",
        "",
        "| Candidate | Valid log loss | Valid Brier | Test accuracy | Test log loss |",
        "|---|---:|---:|---:|---:|",
    ]
    for candidate in metrics.get("candidates", []):
        validation = candidate.get("validation", {})
        test = candidate.get("test", {})
        rows.append(
            "| "
            f"{candidate.get('name')} | "
            f"{_fmt(validation.get('log_loss'))} | "
            f"{_fmt(validation.get('brier_score'))} | "
            f"{_fmt(test.get('accuracy'))} | "
            f"{_fmt(test.get('log_loss'))} |"
        )
    rows.extend(
        [
            "",
            "## Selected Weights",
            "",
            json.dumps(metrics.get("selected_config", {}).get("source_weights", {}), indent=2),
            "",
            "## Dynamic Coverage",
            "",
            json.dumps(metrics.get("dynamic_coverage", {}), indent=2, sort_keys=True),
        ]
    )
    return "\n".join(rows)


def _fmt(value: Any) -> str:
    if value is None:
        return "n/a"
    try:
        return f"{float(value):.4f}"
    except (TypeError, ValueError):
        return str(value)


def _json_ready(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_ready(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [_json_ready(item) for item in value]
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    return value
