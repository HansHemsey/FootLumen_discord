"""Model artifact persistence."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import joblib  # type: ignore[import-untyped]

from football_predictor.modeling.sport_model import TrainedSportModel
from football_predictor.utils.time import utc_now

MODEL_FILENAME = "model.joblib"
METADATA_FILENAME = "metadata.json"


@dataclass
class ModelArtifact:
    model_version: str
    sport_model: TrainedSportModel
    created_at: datetime = field(default_factory=utc_now)
    metrics: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def feature_columns(self) -> list[str]:
        return list(self.sport_model.feature_columns)


def save_model_artifact(artifact: ModelArtifact, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    model_path = output_dir / MODEL_FILENAME
    joblib.dump(artifact, model_path)
    (output_dir / METADATA_FILENAME).write_text(
        json.dumps(_metadata_payload(artifact), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return model_path


def load_model_artifact(path: Path) -> ModelArtifact:
    model_path = path / MODEL_FILENAME if path.is_dir() else path
    artifact = joblib.load(model_path)
    if not isinstance(artifact, ModelArtifact):
        raise TypeError(f"Unexpected artifact type: {type(artifact)!r}")
    return artifact


def _metadata_payload(artifact: ModelArtifact) -> dict[str, Any]:
    return {
        "model_version": artifact.model_version,
        "created_at": artifact.created_at.isoformat(),
        "feature_columns": artifact.feature_columns,
        "calibration_method": artifact.sport_model.calibration_method,
        "calibration_skipped_reason": artifact.sport_model.calibration_skipped_reason,
        "config": asdict(artifact.sport_model.config),
        "metrics": artifact.metrics,
        "metadata": artifact.metadata,
    }
