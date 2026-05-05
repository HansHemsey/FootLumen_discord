"""Dataset-to-artifact training entrypoints."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd  # type: ignore[import-untyped]

from football_predictor.modeling.constants import CLASSES
from football_predictor.modeling.evaluation import evaluate_probabilities
from football_predictor.modeling.multiclass_model import FootballOutcomeModel
from football_predictor.modeling.preprocessing import separate_metadata_target_features
from football_predictor.modeling.probabilities import ProbabilityTriple
from football_predictor.modeling.v2_model import (
    V2TrainingConfig,
    train_v2_model_from_dataset,
)
from football_predictor.utils.time import utc_now


@dataclass(frozen=True)
class TrainModelResult:
    model: Any
    model_path: Path
    metadata_path: Path
    feature_names_path: Path
    metrics_path: Path
    metrics: dict[str, Any]
    feature_coverage_path: Path | None = None


def train_model_from_dataset(
    dataset_path: Path,
    output_dir: Path,
    *,
    model_version: str = "v1",
) -> TrainModelResult:
    if model_version.startswith("v2"):
        result = train_v2_model_from_dataset(
            dataset_path,
            output_dir,
            config=V2TrainingConfig(model_version=model_version),
        )
        return TrainModelResult(
            model=result.model,
            model_path=result.model_path,
            metadata_path=result.metadata_path,
            feature_names_path=result.feature_names_path,
            metrics_path=result.metrics_path,
            metrics=result.metrics,
            feature_coverage_path=result.feature_coverage_path,
        )
    frame = _load_dataset(dataset_path)
    train_frame, valid_frame = _time_based_train_valid_split(frame)
    train_data = separate_metadata_target_features(train_frame, impute=True)
    if train_data.target is None:
        raise ValueError("Dataset must contain target")

    model = FootballOutcomeModel(model_version=model_version)
    model.fit(train_data.features, list(train_data.target.astype(str)))

    metrics = {
        "train": _evaluate_frame(model, train_frame),
        "validation": None if valid_frame is None else _evaluate_frame(model, valid_frame),
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    model_path = model.save(output_dir / "model.joblib")
    metadata_path = output_dir / "metadata.json"
    feature_names_path = output_dir / "feature_names.json"
    metrics_path = output_dir / "metrics.json"
    metadata = {
        "model_version": model.model_version,
        "created_at": utc_now().isoformat(),
        "classes": CLASSES,
        "training_rows": len(train_frame),
        "validation_rows": 0 if valid_frame is None else len(valid_frame),
        "artifact_format": "football_outcome_model_v1",
    }
    metadata_path.write_text(json.dumps(metadata, indent=2, sort_keys=True), encoding="utf-8")
    feature_names_path.write_text(
        json.dumps(model.feature_names, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    metrics_path.write_text(json.dumps(metrics, indent=2, sort_keys=True), encoding="utf-8")
    return TrainModelResult(
        model=model,
        model_path=model_path,
        metadata_path=metadata_path,
        feature_names_path=feature_names_path,
        metrics_path=metrics_path,
        metrics=metrics,
    )


def _load_dataset(dataset_path: Path) -> pd.DataFrame:
    suffix = dataset_path.suffix.casefold()
    if suffix == ".csv":
        return pd.read_csv(dataset_path)
    if suffix == ".parquet":
        return pd.read_parquet(dataset_path, engine="pyarrow")
    raise ValueError("dataset_path must be .csv or .parquet")


def _time_based_train_valid_split(frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame | None]:
    if "fixture_date" not in frame.columns or len(frame) < 10:
        return frame.copy(), None
    ordered = frame.sort_values("fixture_date").reset_index(drop=True)
    split_index = max(int(len(ordered) * 0.8), 1)
    train = ordered.iloc[:split_index].copy()
    valid = ordered.iloc[split_index:].copy()
    return train, None if valid.empty else valid


def _evaluate_frame(model: FootballOutcomeModel, frame: pd.DataFrame) -> dict[str, Any]:
    data = separate_metadata_target_features(frame, impute=True)
    if data.target is None:
        raise ValueError("Dataset must contain target")
    probabilities = [
        ProbabilityTriple.from_vector(row)
        for row in model.predict_proba(data.features)
    ]
    return evaluate_probabilities(list(data.target.astype(str)), probabilities)
