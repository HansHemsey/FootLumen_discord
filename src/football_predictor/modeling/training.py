"""Training orchestration for Sprint 11 model artifacts."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Any

import pandas as pd  # type: ignore[import-untyped]

from football_predictor.modeling.artifacts import ModelArtifact, save_model_artifact
from football_predictor.modeling.evaluation import evaluate_probabilities
from football_predictor.modeling.sport_model import (
    ModelTrainingConfig,
    TrainedSportModel,
    predict_sport_probabilities,
    train_sport_model,
)


def train_model_artifact(
    train_df: pd.DataFrame,
    output_dir: Path,
    model_version: str,
    valid_df: pd.DataFrame | None = None,
    config: ModelTrainingConfig | None = None,
) -> ModelArtifact:
    config = replace(config, model_version=model_version) if config else ModelTrainingConfig(
        model_version=model_version
    )
    sport_model = train_sport_model(train_df, config=config)
    metrics = _evaluate_train_valid(sport_model, train_df, valid_df)
    sport_model.metrics = metrics
    artifact = ModelArtifact(
        model_version=model_version,
        sport_model=sport_model,
        metrics=metrics,
        metadata={
            "artifact_format": "football_predictor_model_v1",
            "training_rows": len(train_df),
            "validation_rows": 0 if valid_df is None else len(valid_df),
        },
    )
    save_model_artifact(artifact, output_dir)
    return artifact


def load_training_frame(path: Path) -> pd.DataFrame:
    suffix = path.suffix.casefold()
    if suffix == ".csv":
        return pd.read_csv(path)
    if suffix == ".parquet":
        return pd.read_parquet(path, engine="pyarrow")
    raise ValueError("Training dataset must be .csv or .parquet")


def split_training_validation(
    frame: pd.DataFrame,
    *,
    valid_until: str | None = None,
    test_until: str | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame | None, pd.DataFrame | None]:
    """Create chronological train/validation/test splits from fixture_date.

    If no cutoffs are provided, all rows are used for training. With `valid_until`,
    rows up to that date train the model and later rows validate it. With both cutoffs,
    rows after `valid_until` and up to `test_until` are validation, and rows after
    `test_until` are held out as test metadata.
    """
    if valid_until is None and test_until is None:
        return frame.copy(), None, None
    if "fixture_date" not in frame.columns:
        raise ValueError("fixture_date is required for time-based training splits")

    ordered = frame.sort_values("fixture_date").reset_index(drop=True)
    dates = pd.to_datetime(ordered["fixture_date"], utc=True)
    if valid_until is not None:
        valid_cutoff = _utc_timestamp(valid_until)
        train = ordered.loc[dates <= valid_cutoff].copy()
        later = ordered.loc[dates > valid_cutoff].copy()
        later_dates = dates.loc[dates > valid_cutoff]
    else:
        if test_until is None:
            raise ValueError("test_until is required when valid_until is omitted")
        test_cutoff = _utc_timestamp(test_until)
        train = ordered.loc[dates <= test_cutoff].copy()
        later = ordered.loc[dates > test_cutoff].copy()
        later_dates = dates.loc[dates > test_cutoff]

    if test_until is None:
        return train, later if not later.empty else None, None

    test_cutoff = _utc_timestamp(test_until)
    valid = later.loc[later_dates <= test_cutoff].copy()
    test = later.loc[later_dates > test_cutoff].copy()
    return train, valid if not valid.empty else None, test if not test.empty else None


def _utc_timestamp(value: str) -> pd.Timestamp:
    timestamp = pd.Timestamp(value)
    if timestamp.tzinfo is None:
        return timestamp.tz_localize("UTC")
    return timestamp.tz_convert("UTC")


def _evaluate_train_valid(
    model: TrainedSportModel,
    train_df: pd.DataFrame,
    valid_df: pd.DataFrame | None,
) -> dict[str, Any]:
    metrics: dict[str, Any] = {
        "train": evaluate_probabilities(
            list(train_df["target"].astype(str)),
            predict_sport_probabilities(model, train_df),
        )
    }
    if valid_df is not None and not valid_df.empty:
        metrics["validation"] = evaluate_probabilities(
            list(valid_df["target"].astype(str)),
            predict_sport_probabilities(model, valid_df),
        )
    return metrics
