"""World Cup 1X2 model training and inference."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import joblib  # type: ignore[import-untyped]
import pandas as pd  # type: ignore[import-untyped]
from sklearn.ensemble import HistGradientBoostingClassifier  # type: ignore[import-untyped]
from sklearn.impute import SimpleImputer  # type: ignore[import-untyped]
from sklearn.linear_model import LogisticRegression  # type: ignore[import-untyped]
from sklearn.pipeline import Pipeline  # type: ignore[import-untyped]

from football_predictor.modeling.constants import CLASSES
from football_predictor.modeling.draw_metrics import evaluate_draw_metrics
from football_predictor.modeling.evaluation import evaluate_probabilities
from football_predictor.modeling.preprocessing import (
    is_forbidden_feature,
    numeric_feature_dataframe,
)
from football_predictor.modeling.probabilities import ProbabilityTriple
from football_predictor.utils.time import utc_now
from football_predictor.worldcup.blend import (
    WorldCupBlendConfig,
    load_worldcup_blend_config,
)
from football_predictor.worldcup.features import (
    blend_worldcup_probabilities,
    poisson_probabilities,
    probability_from_rating_diff,
)

JsonDict = dict[str, Any]


@dataclass(frozen=True)
class WorldCupTrainingConfig:
    model_version: str = "worldcup-1x2-v1"
    train_ratio: float = 0.60
    valid_ratio: float = 0.20
    min_rows_for_calibration: int = 200
    feature_min_coverage: float = 0.02
    max_features: int = 280
    random_state: int = 42


@dataclass(frozen=True)
class WorldCupTrainResult:
    model: WorldCup1X2Model
    model_path: Path
    metadata_path: Path
    feature_names_path: Path
    metrics_path: Path
    reference_coverage_path: Path
    metrics: JsonDict


@dataclass
class WorldCup1X2Model:
    model_version: str
    feature_names: list[str]
    estimator: Any
    calibrator: Any | None
    calibration_decision: JsonDict = field(default_factory=dict)
    feature_coverage: JsonDict = field(default_factory=dict)
    blend_config: WorldCupBlendConfig | None = None
    is_worldcup_1x2: bool = True

    def predict_proba(
        self,
        frame: pd.DataFrame,
        *,
        include_dynamic: bool = True,
    ) -> list[list[float]]:
        model_probabilities = self.predict_model_probabilities(
            frame,
            include_dynamic=include_dynamic,
        )
        scoring_frame = frame if include_dynamic else _strip_dynamic_columns(frame)
        outputs: list[list[float]] = []
        for position, (_index, row) in enumerate(scoring_frame.iterrows()):
            model_probability = model_probabilities[position]
            outputs.append(
                final_probability_from_row(
                    dict(row),
                    model_probability=model_probability,
                    include_dynamic=include_dynamic,
                    blend_config=getattr(self, "blend_config", None),
                ).to_vector()
            )
        return outputs

    def predict_model_probabilities(
        self,
        frame: pd.DataFrame,
        *,
        include_dynamic: bool = True,
    ) -> list[ProbabilityTriple]:
        scoring_frame = frame if include_dynamic else _strip_dynamic_columns(frame)
        prepared = _prepare_features(scoring_frame, self.feature_names)
        raw = _predict_proba_safely(self.estimator, prepared)
        model_probabilities = [
            _probability_from_estimator_output(self.estimator, row) for row in raw
        ]
        if self.calibrator is not None:
            calibration_frame = pd.DataFrame(
                [probability.as_dict() for probability in model_probabilities]
            )
            calibrated_raw = _predict_proba_safely(self.calibrator, calibration_frame)
            model_probabilities = [
                _probability_from_estimator_output(self.calibrator, row)
                for row in calibrated_raw
            ]
        return model_probabilities

    def save(self, path: Path) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self, path)
        return path

    @classmethod
    def load(cls, path: Path) -> WorldCup1X2Model:
        model_path = path / "model.joblib" if path.is_dir() else path
        obj = joblib.load(model_path)
        if not isinstance(obj, cls):
            raise TypeError(f"Expected WorldCup1X2Model at {model_path}, got {type(obj)}")
        obj.blend_config = load_worldcup_blend_config(path if path.is_dir() else model_path)
        return obj


def train_worldcup_model_from_dataset(
    dataset_path: Path,
    output_dir: Path,
    *,
    config: WorldCupTrainingConfig | None = None,
    reference_coverage: JsonDict | None = None,
) -> WorldCupTrainResult:
    frame = _load_dataset(dataset_path)
    return train_worldcup_model_from_frame(
        frame,
        output_dir,
        config=config,
        reference_coverage=reference_coverage,
    )


def train_worldcup_model_from_frame(
    frame: pd.DataFrame,
    output_dir: Path,
    *,
    config: WorldCupTrainingConfig | None = None,
    reference_coverage: JsonDict | None = None,
) -> WorldCupTrainResult:
    resolved = config or WorldCupTrainingConfig()
    train, valid, test = chronological_split(
        frame,
        train_ratio=resolved.train_ratio,
        valid_ratio=resolved.valid_ratio,
    )
    model, metrics = fit_worldcup_model(train, valid, test, config=resolved)
    output_dir.mkdir(parents=True, exist_ok=True)
    model_path = model.save(output_dir / "model.joblib")
    metadata_path = output_dir / "metadata.json"
    feature_names_path = output_dir / "feature_names.json"
    metrics_path = output_dir / "metrics.json"
    reference_coverage_path = output_dir / "reference_coverage.json"
    metadata = {
        "artifact_format": "worldcup_1x2_model",
        "model_version": model.model_version,
        "created_at": utc_now().isoformat(),
        "classes": CLASSES,
        "feature_count": len(model.feature_names),
        "training_rows": len(train),
        "validation_rows": len(valid),
        "test_rows": len(test),
        "calibration_decision": model.calibration_decision,
    }
    metadata_path.write_text(
        json.dumps(_json_ready(metadata), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    feature_names_path.write_text(
        json.dumps(model.feature_names, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    metrics_path.write_text(
        json.dumps(_json_ready(metrics), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    reference_coverage_path.write_text(
        json.dumps(_json_ready(reference_coverage or {}), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return WorldCupTrainResult(
        model=model,
        model_path=model_path,
        metadata_path=metadata_path,
        feature_names_path=feature_names_path,
        metrics_path=metrics_path,
        reference_coverage_path=reference_coverage_path,
        metrics=metrics,
    )


def fit_worldcup_model(
    train: pd.DataFrame,
    valid: pd.DataFrame,
    test: pd.DataFrame,
    *,
    config: WorldCupTrainingConfig,
) -> tuple[WorldCup1X2Model, JsonDict]:
    if "target" not in train.columns:
        raise ValueError("World Cup dataset must contain target")
    feature_names = select_worldcup_feature_names(
        train,
        min_coverage=config.feature_min_coverage,
        max_features=config.max_features,
    )
    if not feature_names:
        raise ValueError("No World Cup feature columns available for training")
    y_train = list(train["target"].astype(str))
    estimator = _fit_estimator(train, y_train, feature_names, config=config)
    provisional = WorldCup1X2Model(
        model_version=config.model_version,
        feature_names=feature_names,
        estimator=estimator,
        calibrator=None,
        calibration_decision={"method": "none", "reason": "not_attempted"},
        feature_coverage=_feature_coverage(train, feature_names),
    )
    calibrator, calibration_decision = _fit_calibrator(provisional, valid, config=config)
    model = WorldCup1X2Model(
        model_version=config.model_version,
        feature_names=feature_names,
        estimator=estimator,
        calibrator=calibrator,
        calibration_decision=calibration_decision,
        feature_coverage=_feature_coverage(train, feature_names),
    )
    metrics = {
        "model_version": model.model_version,
        "feature_count": len(feature_names),
        "calibration_decision": calibration_decision,
        "train": evaluate_worldcup_frame(model, train),
        "validation": evaluate_worldcup_frame(model, valid),
        "test": evaluate_worldcup_frame(model, test),
        "baselines": {
            "validation": evaluate_worldcup_baselines(valid),
            "test": evaluate_worldcup_baselines(test),
        },
    }
    return model, metrics


def final_probability_from_row(
    row: JsonDict,
    *,
    model_probability: ProbabilityTriple | None,
    include_dynamic: bool = True,
    blend_config: WorldCupBlendConfig | None = None,
    source_weights: dict[str, float] | None = None,
) -> ProbabilityTriple:
    rating = _probability_from_prefix(
        row,
        "p_wc_rating_dynamic" if include_dynamic else "p_wc_rating",
    ) or _probability_from_prefix(row, "p_wc_rating") or ProbabilityTriple(1 / 3, 1 / 3, 1 / 3)
    poisson = _probability_from_prefix(
        row,
        "p_wc_poisson_dynamic" if include_dynamic else "p_wc_poisson",
    ) or _probability_from_prefix(row, "p_wc_poisson") or ProbabilityTriple(1 / 3, 1 / 3, 1 / 3)
    market = _probability_from_prefix(row, "p_wc_market") if include_dynamic else None
    api = _probability_from_prefix(row, "p_wc_api") if include_dynamic else None
    return blend_worldcup_probabilities(
        model_probability=model_probability,
        rating_probability=rating,
        poisson_probability=poisson,
        market_probability=market,
        api_probability=api,
        blend_config=blend_config,
        source_weights=source_weights,
    )


def fallback_probability_from_features(
    features: JsonDict,
    *,
    blend_config: WorldCupBlendConfig | None = None,
) -> ProbabilityTriple:
    if all(
        key in features
        for key in (
            "p_wc_rating_dynamic_home",
            "p_wc_rating_dynamic_draw",
            "p_wc_rating_dynamic_away",
        )
    ):
        rating = ProbabilityTriple(
            float(features["p_wc_rating_dynamic_home"]),
            float(features["p_wc_rating_dynamic_draw"]),
            float(features["p_wc_rating_dynamic_away"]),
        )
    elif all(
        key in features for key in ("p_wc_rating_home", "p_wc_rating_draw", "p_wc_rating_away")
    ):
        rating = ProbabilityTriple(
            float(features["p_wc_rating_home"]),
            float(features["p_wc_rating_draw"]),
            float(features["p_wc_rating_away"]),
        )
    else:
        rating = probability_from_rating_diff(float(features.get("wc_internal_elo_diff") or 0.0))
    if all(
        key in features
        for key in (
            "p_wc_poisson_dynamic_home",
            "p_wc_poisson_dynamic_draw",
            "p_wc_poisson_dynamic_away",
        )
    ):
        poisson = ProbabilityTriple(
            float(features["p_wc_poisson_dynamic_home"]),
            float(features["p_wc_poisson_dynamic_draw"]),
            float(features["p_wc_poisson_dynamic_away"]),
        )
    elif all(
        key in features
        for key in ("p_wc_poisson_home", "p_wc_poisson_draw", "p_wc_poisson_away")
    ):
        poisson = ProbabilityTriple(
            float(features["p_wc_poisson_home"]),
            float(features["p_wc_poisson_draw"]),
            float(features["p_wc_poisson_away"]),
        )
    else:
        poisson = poisson_probabilities(
            float(features.get("wc_expected_home_goals") or 1.35),
            float(features.get("wc_expected_away_goals") or 1.10),
        )
    return blend_worldcup_probabilities(
        model_probability=None,
        rating_probability=rating,
        poisson_probability=poisson,
        market_probability=_probability_from_prefix(features, "p_wc_market"),
        api_probability=_probability_from_prefix(features, "p_wc_api"),
        blend_config=blend_config,
    )


def evaluate_worldcup_frame(
    model: WorldCup1X2Model,
    frame: pd.DataFrame,
    *,
    include_dynamic: bool = True,
) -> JsonDict:
    if frame.empty:
        return {"row_count": 0}
    y_true = list(frame["target"].astype(str))
    probabilities = [
        ProbabilityTriple.from_vector(row)
        for row in model.predict_proba(frame, include_dynamic=include_dynamic)
    ]
    metrics = evaluate_probabilities(y_true, probabilities)
    metrics.update(evaluate_draw_metrics(y_true, probabilities))
    return metrics


def evaluate_worldcup_baselines(frame: pd.DataFrame) -> JsonDict:
    if frame.empty:
        return {"row_count": 0}
    y_true = list(frame["target"].astype(str))
    rating = [_probability_from_prefix(row, "p_wc_rating") for _, row in frame.iterrows()]
    poisson = [_probability_from_prefix(row, "p_wc_poisson") for _, row in frame.iterrows()]
    market = [_probability_from_prefix(row, "p_wc_market") for _, row in frame.iterrows()]
    api = [_probability_from_prefix(row, "p_wc_api") for _, row in frame.iterrows()]
    return {
        "row_count": len(frame),
        "wc_rating": _evaluate_available(y_true, rating),
        "wc_poisson": _evaluate_available(y_true, poisson),
        "market": _evaluate_available(y_true, market),
        "api": _evaluate_available(y_true, api),
    }


def worldcup_blend_weights(
    *,
    has_model: bool,
    has_market: bool,
    has_api: bool,
    blend_config: WorldCupBlendConfig | None = None,
) -> dict[str, float]:
    available = {"wc_rating_dynamic", "wc_poisson_dynamic"}
    if has_model:
        available.add("wc_model")
    if has_market:
        available.add("wc_market")
    if has_api:
        available.add("wc_api")
    return (blend_config or WorldCupBlendConfig.default()).weights_for_sources(available)


def probability_source_from_features(row: JsonDict, prefix: str) -> ProbabilityTriple | None:
    return _probability_from_prefix(row, prefix)


def chronological_split(
    frame: pd.DataFrame,
    *,
    train_ratio: float = 0.60,
    valid_ratio: float = 0.20,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    if "fixture_date" not in frame.columns:
        raise ValueError("World Cup dataset must contain fixture_date")
    ordered = frame.sort_values("fixture_date").reset_index(drop=True)
    train_end = max(int(len(ordered) * train_ratio), 1)
    valid_end = max(int(len(ordered) * (train_ratio + valid_ratio)), train_end + 1)
    return (
        ordered.iloc[:train_end].copy(),
        ordered.iloc[train_end:valid_end].copy(),
        ordered.iloc[valid_end:].copy(),
    )


def select_worldcup_feature_names(
    frame: pd.DataFrame,
    *,
    min_coverage: float,
    max_features: int,
) -> list[str]:
    candidates: list[tuple[str, float]] = []
    for column in frame.columns:
        name = str(column)
        if is_forbidden_feature(name):
            continue
        if not (name.startswith("wc_") or name.startswith("p_wc_")):
            continue
        numeric = pd.to_numeric(frame[column], errors="coerce")
        coverage = float(numeric.notna().mean()) if len(numeric) else 0.0
        if numeric.notna().any() and coverage >= min_coverage:
            candidates.append((name, coverage))
    candidates.sort(key=lambda item: (-item[1], item[0]))
    return [name for name, _coverage in candidates[:max_features]]


def _fit_estimator(
    frame: pd.DataFrame,
    y_train: list[str],
    feature_names: list[str],
    *,
    config: WorldCupTrainingConfig,
) -> Any:
    prepared = _prepare_features(frame, feature_names)
    estimator = HistGradientBoostingClassifier(
        max_iter=240,
        learning_rate=0.035,
        l2_regularization=0.12,
        random_state=config.random_state,
    )
    try:
        estimator.fit(prepared, y_train)
        return estimator
    except ValueError:
        fallback = Pipeline(
            steps=[
                ("imputer", SimpleImputer(strategy="median")),
                (
                    "classifier",
                    LogisticRegression(
                        max_iter=2000,
                        class_weight="balanced",
                        random_state=config.random_state,
                    ),
                ),
            ]
        )
        fallback.fit(prepared, y_train)
        return fallback


def _fit_calibrator(
    model: WorldCup1X2Model,
    valid: pd.DataFrame,
    *,
    config: WorldCupTrainingConfig,
) -> tuple[Any | None, JsonDict]:
    if valid.empty or len(valid) < config.min_rows_for_calibration:
        return None, {
            "method": "none",
            "reason": "insufficient_validation_rows",
            "rows": len(valid),
        }
    y_valid = list(valid["target"].astype(str))
    if set(y_valid) != set(CLASSES):
        return None, {"method": "none", "reason": "missing_validation_class", "rows": len(valid)}
    raw = _predict_proba_safely(model.estimator, _prepare_features(valid, model.feature_names))
    probability_frame = pd.DataFrame(
        [ProbabilityTriple.from_vector(row).as_dict() for row in raw]
    )
    calibrator = LogisticRegression(max_iter=2000, random_state=config.random_state)
    calibrator.fit(probability_frame, y_valid)
    return calibrator, {"method": "multiclass_sigmoid", "rows": len(valid)}


def _prepare_features(frame: pd.DataFrame, feature_names: list[str]) -> pd.DataFrame:
    for name in feature_names:
        if name not in frame.columns:
            frame = frame.assign(**{name: pd.NA})
    return numeric_feature_dataframe(frame[feature_names], impute=True, forbidden_patterns=())


def _predict_proba_safely(estimator: Any, frame: pd.DataFrame) -> Any:
    return estimator.predict_proba(frame)


def _probability_from_estimator_output(estimator: Any, raw: Any) -> ProbabilityTriple:
    classes = [str(label) for label in getattr(estimator, "classes_", CLASSES)]
    if not hasattr(estimator, "classes_") and hasattr(estimator, "named_steps"):
        classifier = estimator.named_steps.get("classifier")
        classes = [str(label) for label in getattr(classifier, "classes_", CLASSES)]
    values = {label: 0.0 for label in CLASSES}
    for label, probability in zip(classes, raw, strict=False):
        if label in values:
            values[label] = float(probability)
    return ProbabilityTriple.from_mapping(values)


def _feature_coverage(frame: pd.DataFrame, feature_names: list[str]) -> JsonDict:
    row_count = len(frame)
    return {
        name: float(pd.to_numeric(frame[name], errors="coerce").notna().sum() / row_count)
        if row_count and name in frame.columns
        else 0.0
        for name in feature_names
    }


def _probability_from_prefix(row: Any, prefix: str) -> ProbabilityTriple | None:
    home = _optional_float(_row_value(row, f"{prefix}_home"))
    draw = _optional_float(_row_value(row, f"{prefix}_draw"))
    away = _optional_float(_row_value(row, f"{prefix}_away"))
    if home is None or draw is None or away is None:
        return None
    total = home + draw + away
    if total <= 0:
        return None
    return ProbabilityTriple(home / total, draw / total, away / total).normalized()


def _evaluate_available(
    y_true: list[str],
    probabilities: list[ProbabilityTriple | None],
) -> JsonDict:
    pairs = [
        (target, probability)
        for target, probability in zip(y_true, probabilities, strict=False)
        if probability
    ]
    if not pairs:
        return {"row_count": 0, "coverage": 0.0}
    targets = [target for target, _probability in pairs]
    available = [probability for _target, probability in pairs]
    metrics = evaluate_probabilities(targets, available)
    metrics.update(evaluate_draw_metrics(targets, available))
    metrics["coverage"] = len(pairs) / len(y_true) if y_true else 0.0
    return metrics


def _strip_dynamic_columns(frame: pd.DataFrame) -> pd.DataFrame:
    dynamic_prefixes = (
        "wc_market_",
        "p_wc_market_",
        "wc_api_pred_",
        "p_wc_api_",
        "wc_official_lineup_",
        "wc_home_absence_",
        "wc_away_absence_",
        "wc_home_dynamic_",
        "wc_away_dynamic_",
        "wc_dynamic_",
        "p_wc_rating_dynamic_",
        "p_wc_poisson_dynamic_",
    )
    return frame.drop(
        columns=[name for name in frame.columns if str(name).startswith(dynamic_prefixes)],
        errors="ignore",
    )


def _row_value(row: Any, key: str) -> Any:
    if isinstance(row, dict):
        return row.get(key)
    return row.get(key, None)


def _optional_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if math.isfinite(parsed) else None


def _load_dataset(dataset_path: Path) -> pd.DataFrame:
    suffix = dataset_path.suffix.casefold()
    if suffix == ".csv":
        return pd.read_csv(dataset_path)
    if suffix == ".parquet":
        return pd.read_parquet(dataset_path, engine="pyarrow")
    raise ValueError("dataset_path must be .csv or .parquet")


def _json_ready(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_ready(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [_json_ready(item) for item in value]
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    return value
