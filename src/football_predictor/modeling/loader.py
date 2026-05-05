"""Model loading helpers for V1 and V2 artifacts."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import joblib  # type: ignore[import-untyped]

from football_predictor.modeling.multiclass_model import FootballOutcomeModel
from football_predictor.modeling.v2_model import FootballOutcomeV2Model

PredictionModel = FootballOutcomeModel | FootballOutcomeV2Model


def load_prediction_model(path: Path) -> PredictionModel:
    model_path = path / "model.joblib" if path.is_dir() else path
    model: Any = joblib.load(model_path)
    if isinstance(model, FootballOutcomeModel | FootballOutcomeV2Model):
        return model
    raise TypeError(f"Unexpected model type: {type(model)!r}")
