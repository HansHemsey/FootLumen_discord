"""End-to-end V3 training orchestration."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import joblib  # type: ignore[import-untyped]
import numpy as np
import pandas as pd  # type: ignore[import-untyped]

from football_predictor.backtesting.v3_dataset_builder import (
    FIXTURE_ID_COL,
    add_v3_targets,
    build_v3_stacker_dataset,
    chronological_splits,
)
from football_predictor.modeling.v3.composite import FootballOutcomeV3Model
from football_predictor.modeling.v3.constants import (
    DEFAULT_DRAW_RISK_MODEL_VERSION,
    DEFAULT_NO_DRAW_WINNER_MODEL_VERSION,
    DEFAULT_V3_FINAL_MODEL_VERSION,
    DEFAULT_V3_STACKER_MODEL_VERSION,
)
from football_predictor.modeling.v3.draw_risk_model import (
    DrawRiskTrainingConfig,
    train_draw_risk_from_frame,
)
from football_predictor.modeling.v3.no_draw_winner_model import (
    NoDrawWinnerTrainingConfig,
    train_no_draw_winner_from_frame,
)
from football_predictor.modeling.v3.stacker import (
    V3StackerTrainingConfig,
    V3StackerTrainResult,
    train_v3_stacker_from_frame,
)
from football_predictor.utils.time import utc_now

JsonDict = dict[str, Any]


@dataclass(frozen=True)
class V3TrainingConfig:
    """Configuration for full V3 training."""

    model_version: str = DEFAULT_V3_FINAL_MODEL_VERSION
    draw_risk_model_version: str = DEFAULT_DRAW_RISK_MODEL_VERSION
    no_draw_winner_model_version: str = DEFAULT_NO_DRAW_WINNER_MODEL_VERSION
    stacker_model_version: str = DEFAULT_V3_STACKER_MODEL_VERSION
    draw_calibration: str = "isotonic"
    no_draw_winner_calibration: str = "sigmoid"
    train_ratio: float = 0.60
    valid_ratio: float = 0.20
    random_state: int = 42


@dataclass(frozen=True)
class V3TrainResult:
    """Paths and metrics produced by full V3 training."""

    model: FootballOutcomeV3Model
    model_path: Path
    metadata_path: Path
    metrics_path: Path
    draw_risk_model_path: Path
    no_draw_winner_model_path: Path
    stacker_result: V3StackerTrainResult
    metrics: JsonDict


def train_v3_from_dataset(
    dataset_path: Path,
    output_dir: Path,
    *,
    v2_model_dir: Path | None = None,
    config: V3TrainingConfig | None = None,
) -> V3TrainResult:
    """Train Draw Risk, No-Draw Winner and the final V3 stacker."""
    resolved_config = config or V3TrainingConfig()
    frame = add_v3_targets(_load_dataset(dataset_path))
    splits = chronological_splits(
        frame,
        train_ratio=resolved_config.train_ratio,
        valid_ratio=resolved_config.valid_ratio,
    )

    draw_model, draw_metrics = train_draw_risk_from_frame(
        splits.train,
        valid_frame=splits.valid,
        test_frame=splits.test,
        config=DrawRiskTrainingConfig(
            model_version=resolved_config.draw_risk_model_version,
            calibration=resolved_config.draw_calibration,  # type: ignore[arg-type]
            random_state=resolved_config.random_state,
        ),
    )
    ndw_model, ndw_metrics = train_no_draw_winner_from_frame(
        splits.train,
        valid_frame=splits.valid,
        test_frame=splits.test,
        config=NoDrawWinnerTrainingConfig(
            model_version=resolved_config.no_draw_winner_model_version,
            calibration=resolved_config.no_draw_winner_calibration,  # type: ignore[arg-type]
            random_state=resolved_config.random_state,
        ),
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    draw_model_path = _write_component_artifacts(
        output_dir / "draw_risk",
        draw_model,
        draw_metrics,
        extra_metadata={
            "training_rows": len(splits.train),
            "validation_rows": len(splits.valid),
            "test_rows": len(splits.test),
        },
    )
    ndw_model_path = _write_component_artifacts(
        output_dir / "no_draw_winner",
        ndw_model,
        ndw_metrics,
        extra_metadata={
            "training_rows": int((splits.train["outcome"] != "DRAW").sum()),
            "validation_rows": int((splits.valid["outcome"] != "DRAW").sum()),
            "test_rows": int((splits.test["outcome"] != "DRAW").sum()),
        },
    )

    v2_model = _load_optional_model(v2_model_dir)
    valid_stacker_frame = _build_stacker_training_frame(
        splits.valid,
        split_name="valid",
        draw_model=draw_model,
        ndw_model=ndw_model,
        v2_model=v2_model,
    )
    test_stacker_frame = _build_stacker_training_frame(
        splits.test,
        split_name="test",
        draw_model=draw_model,
        ndw_model=ndw_model,
        v2_model=v2_model,
    )
    stacker_result = train_v3_stacker_from_frame(
        valid_stacker_frame,
        output_dir / "stacker",
        eval_frame=test_stacker_frame,
        config=V3StackerTrainingConfig(
            model_version=resolved_config.stacker_model_version,
            random_state=resolved_config.random_state,
        ),
    )
    composite = FootballOutcomeV3Model(
        draw_risk_model=draw_model,
        no_draw_winner_model=ndw_model,
        stacker_model=stacker_result.model,
        v2_model=v2_model,
        model_version=resolved_config.model_version,
    )
    model_path = composite.save(output_dir / "model.joblib")
    metrics = {
        "draw_risk": draw_metrics,
        "no_draw_winner": ndw_metrics,
        "stacker": stacker_result.metrics,
    }
    metadata_path = output_dir / "metadata.json"
    metrics_path = output_dir / "metrics.json"
    metadata_path.write_text(
        json.dumps(
            _json_ready(
                {
                    "artifact_format": "football_outcome_model_v3",
                    "model_version": resolved_config.model_version,
                    "created_at": utc_now().isoformat(),
                    "draw_risk_model_version": draw_model.model_version,
                    "no_draw_winner_model_version": ndw_model.model_version,
                    "stacker_model_version": stacker_result.model.model_version,
                    "v2_model_dir": str(v2_model_dir) if v2_model_dir is not None else None,
                    "training_rows": len(splits.train),
                    "validation_rows": len(splits.valid),
                    "test_rows": len(splits.test),
                    "stacker_training_decision": stacker_result.model.training_decision,
                }
            ),
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    metrics_path.write_text(
        json.dumps(_json_ready(metrics), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return V3TrainResult(
        model=composite,
        model_path=model_path,
        metadata_path=metadata_path,
        metrics_path=metrics_path,
        draw_risk_model_path=draw_model_path,
        no_draw_winner_model_path=ndw_model_path,
        stacker_result=stacker_result,
        metrics=metrics,
    )


def _build_stacker_training_frame(
    frame: pd.DataFrame,
    *,
    split_name: str,
    draw_model: Any,
    ndw_model: Any,
    v2_model: Any | None,
) -> pd.DataFrame:
    if frame.empty:
        return frame.copy()
    base = frame.copy()
    base["split"] = split_name
    fixture_ids = list(base[FIXTURE_ID_COL])
    draw_predictions = pd.DataFrame(
        {
            FIXTURE_ID_COL: fixture_ids,
            "p_v3_draw_risk": draw_model.predict_draw_proba(base),
        }
    )
    home_no_draw = ndw_model.predict_home_no_draw_proba(base)
    ndw_predictions = pd.DataFrame(
        {
            FIXTURE_ID_COL: fixture_ids,
            "p_v3_home_no_draw": home_no_draw,
            "p_v3_away_no_draw": [1.0 - value for value in home_no_draw],
        }
    )
    v2_predictions = _v2_prediction_frame(base, v2_model)
    return build_v3_stacker_dataset(
        base,
        draw_predictions,
        ndw_predictions,
        v2_predictions=v2_predictions,
        split_name=split_name,
    )


def _v2_prediction_frame(frame: pd.DataFrame, v2_model: Any | None) -> pd.DataFrame | None:
    if v2_model is None:
        return None
    try:
        probabilities = v2_model.predict_proba(frame)
    except Exception:
        return None
    return pd.DataFrame(
        {
            FIXTURE_ID_COL: list(frame[FIXTURE_ID_COL]),
            "p_v2_home": [row[0] for row in probabilities],
            "p_v2_draw": [row[1] for row in probabilities],
            "p_v2_away": [row[2] for row in probabilities],
        }
    )


def _write_component_artifacts(
    output_dir: Path,
    model: Any,
    metrics: JsonDict,
    *,
    extra_metadata: JsonDict,
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    model_path = model.save(output_dir / "model.joblib")
    metadata = {
        "artifact_format": model.artifact_format,
        "model_version": model.model_version,
        "created_at": utc_now().isoformat(),
        "classes": model.classes,
        "target_column": model.target_column,
        "estimator_name": model.estimator_name,
        "feature_count": len(model.feature_names),
        "calibration_decision": model.calibration_decision,
        **extra_metadata,
    }
    (output_dir / "metadata.json").write_text(
        json.dumps(_json_ready(metadata), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_dir / "feature_names.json").write_text(
        json.dumps(model.feature_names, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_dir / "feature_coverage.json").write_text(
        json.dumps(_json_ready(model.feature_coverage), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_dir / "metrics.json").write_text(
        json.dumps(_json_ready(metrics), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return model_path


def _load_dataset(dataset_path: Path) -> pd.DataFrame:
    suffix = dataset_path.suffix.casefold()
    if suffix == ".csv":
        return pd.read_csv(dataset_path)
    if suffix in {".parquet", ".pq"}:
        return pd.read_parquet(dataset_path, engine="pyarrow")
    raise ValueError("dataset_path must be .csv or .parquet")


def _load_optional_model(path: Path | None) -> Any | None:
    if path is None:
        return None
    model_path = path / "model.joblib" if path.is_dir() else path
    if not model_path.exists():
        return None
    return joblib.load(model_path)


def _json_ready(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_ready(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [_json_ready(item) for item in value]
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        numeric = float(value)
        return numeric if math.isfinite(numeric) else None
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    return value
