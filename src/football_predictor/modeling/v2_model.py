"""Composite V2 football outcome model."""

from __future__ import annotations

import json
import math
import warnings
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import joblib  # type: ignore[import-untyped]
import pandas as pd  # type: ignore[import-untyped]
from sklearn.ensemble import HistGradientBoostingClassifier  # type: ignore[import-untyped]
from sklearn.impute import SimpleImputer  # type: ignore[import-untyped]
from sklearn.linear_model import LogisticRegression  # type: ignore[import-untyped]
from sklearn.pipeline import Pipeline  # type: ignore[import-untyped]

from football_predictor.modeling.baselines import odds_only_probability
from football_predictor.modeling.constants import CLASSES
from football_predictor.modeling.elo import (
    EloRatingState,
    add_elo_features_to_dataset,
    elo_features_for_row,
    elo_probability_from_diff,
)
from football_predictor.modeling.evaluation import evaluate_probabilities
from football_predictor.modeling.poisson_v2 import (
    estimate_lambda_home_away_v2,
    poisson_v2_probabilities,
)
from football_predictor.modeling.preprocessing import numeric_feature_dataframe
from football_predictor.modeling.probabilities import ProbabilityTriple
from football_predictor.modeling.v2_features import feature_coverage, select_v2_feature_names
from football_predictor.utils.time import utc_now


@dataclass(frozen=True)
class V2TrainingConfig:
    model_version: str = "v2-late"
    min_rows_for_meta: int = 45
    min_rows_for_lightgbm: int = 250
    feature_min_coverage: float = 0.02
    max_features: int = 260
    random_state: int = 42


@dataclass(frozen=True)
class V2TrainResult:
    model: FootballOutcomeV2Model
    model_path: Path
    metadata_path: Path
    feature_names_path: Path
    metrics_path: Path
    feature_coverage_path: Path
    metrics: dict[str, Any]


@dataclass
class FootballOutcomeV2Model:
    model_version: str
    feature_names: list[str]
    tabular_model: Any | None
    market_model: Any | None
    meta_model: Any | None
    elo_state: EloRatingState
    feature_coverage: dict[str, Any]
    source_weights: dict[str, float]
    meta_sources: list[str] = field(
        default_factory=lambda: ["market_calibrated", "poisson_v2", "elo_v2", "tabular_v2"]
    )
    calibration_decision: dict[str, Any] = field(default_factory=dict)
    is_v2_composite: bool = True

    def predict_proba(self, frame: pd.DataFrame) -> list[list[float]]:
        expert_rows = [
            {name: ProbabilityTriple.from_vector(vector) for name, vector in row.items()}
            for row in self.predict_expert_probabilities(frame)
        ]
        if self.meta_model is None:
            return [
                _weighted_log_blend(experts, self.source_weights).to_vector()
                for experts in expert_rows
            ]
        meta_frame = pd.DataFrame(
            [_meta_features(experts, self.meta_sources) for experts in expert_rows]
        )
        raw_matrix = _predict_proba_safely(self.meta_model, meta_frame)
        outputs: list[list[float]] = []
        for raw in raw_matrix:
            values = {label: 0.0 for label in CLASSES}
            for label, probability in zip(self.meta_model.classes_, raw, strict=False):
                if str(label) in values:
                    values[str(label)] = float(probability)
            outputs.append(ProbabilityTriple.from_mapping(values).to_vector())
        return outputs

    def predict_expert_probabilities(self, frame: pd.DataFrame) -> list[dict[str, list[float]]]:
        engineered = _engineer_inference_frame(frame, self.elo_state)
        experts_by_index: dict[Any, dict[str, ProbabilityTriple]] = {}
        for index, row in engineered.iterrows():
            payload = dict(row)
            experts_by_index[index] = {
                "poisson_v2": ProbabilityTriple.from_vector(
                    poisson_v2_probabilities(
                        float(payload["poisson_v2_home_lambda"]),
                        float(payload["poisson_v2_away_lambda"]),
                    ).to_vector()
                ),
                "elo_v2": ProbabilityTriple.from_vector(
                    elo_probability_from_diff(float(payload.get("elo_diff") or 0.0))
                ),
            }
            raw_market = _raw_market_probability(payload)
            if raw_market is not None:
                experts_by_index[index]["market_calibrated"] = raw_market

        _add_batch_market_probabilities(engineered, experts_by_index, self.market_model)
        _add_batch_tabular_probabilities(
            engineered,
            experts_by_index,
            self.tabular_model,
            self.feature_names,
        )
        return [
            {
                name: probability.to_vector()
                for name, probability in experts_by_index[index].items()
            }
            for index in engineered.index
        ]

    def expert_probabilities_for_row(self, row: dict[str, Any]) -> dict[str, ProbabilityTriple]:
        row = _with_inference_elo(row, self.elo_state)
        row.update(_poisson_features(row))
        experts: dict[str, ProbabilityTriple] = {
            "poisson_v2": ProbabilityTriple.from_vector(
                poisson_v2_probabilities(
                    float(row["poisson_v2_home_lambda"]),
                    float(row["poisson_v2_away_lambda"]),
                ).to_vector()
            ),
            "elo_v2": ProbabilityTriple.from_vector(
                elo_probability_from_diff(float(row.get("elo_diff") or 0.0))
            ),
        }
        market = _market_probability(row, self.market_model)
        if market is not None:
            experts["market_calibrated"] = market
        tabular = _tabular_probability(row, self.tabular_model, self.feature_names)
        if tabular is not None:
            experts["tabular_v2"] = tabular
        return experts

    def _final_probability(self, experts: dict[str, ProbabilityTriple]) -> ProbabilityTriple:
        if self.meta_model is not None:
            matrix = pd.DataFrame([_meta_features(experts, self.meta_sources)])
            raw = _predict_proba_safely(self.meta_model, matrix)[0]
            values = {label: 0.0 for label in CLASSES}
            for label, probability in zip(self.meta_model.classes_, raw, strict=False):
                if str(label) in values:
                    values[str(label)] = float(probability)
            return ProbabilityTriple.from_mapping(values)
        return _weighted_log_blend(experts, self.source_weights)

    def save(self, path: Path) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self, path)
        return path


def train_v2_model_from_dataset(
    dataset_path: Path,
    output_dir: Path,
    *,
    config: V2TrainingConfig | None = None,
) -> V2TrainResult:
    config = config or V2TrainingConfig()
    frame = _load_dataset(dataset_path)
    train_frame, valid_frame, _test_frame = _temporal_train_valid_test_split(frame)
    model, metrics = train_v2_model_from_frame(train_frame, valid_frame, config=config)
    output_dir.mkdir(parents=True, exist_ok=True)
    model_path = model.save(output_dir / "model.joblib")
    metadata_path = output_dir / "metadata.json"
    feature_names_path = output_dir / "feature_names.json"
    metrics_path = output_dir / "metrics.json"
    feature_coverage_path = output_dir / "feature_coverage.json"
    metadata_path.write_text(
        json.dumps(
            {
                "artifact_format": "football_outcome_model_v2",
                "model_version": model.model_version,
                "created_at": utc_now().isoformat(),
                "classes": CLASSES,
                "sources": model.meta_sources,
                "source_weights": model.source_weights,
                "calibration_decision": model.calibration_decision,
                "training_rows": len(train_frame),
                "validation_rows": len(valid_frame),
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    feature_names_path.write_text(
        json.dumps(model.feature_names, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    metrics_path.write_text(json.dumps(metrics, indent=2, sort_keys=True), encoding="utf-8")
    feature_coverage_path.write_text(
        json.dumps(model.feature_coverage, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return V2TrainResult(
        model=model,
        model_path=model_path,
        metadata_path=metadata_path,
        feature_names_path=feature_names_path,
        metrics_path=metrics_path,
        feature_coverage_path=feature_coverage_path,
        metrics=metrics,
    )


def train_v2_model_from_frame(
    train_frame: pd.DataFrame,
    valid_frame: pd.DataFrame,
    *,
    config: V2TrainingConfig,
) -> tuple[FootballOutcomeV2Model, dict[str, Any]]:
    if "target" not in train_frame.columns:
        raise ValueError("Dataset must contain target")
    engineered_train, elo_state = _engineer_training_frame(train_frame)
    engineered_valid = _engineer_validation_frame(valid_frame, elo_state)
    feature_names = select_v2_feature_names(
        engineered_train,
        min_coverage=config.feature_min_coverage,
        max_features=config.max_features,
    )
    if not feature_names:
        raise ValueError("No V2 feature columns available for training")
    y_train = list(engineered_train["target"].astype(str))
    y_valid = list(engineered_valid["target"].astype(str)) if not engineered_valid.empty else []
    tabular_model = _fit_tabular_model(
        engineered_train,
        y_train,
        feature_names,
        config=config,
    )
    market_model = _fit_market_model(engineered_train, y_train, config=config)
    provisional = FootballOutcomeV2Model(
        model_version=config.model_version,
        feature_names=feature_names,
        tabular_model=tabular_model,
        market_model=market_model,
        meta_model=None,
        elo_state=elo_state,
        feature_coverage=feature_coverage(engineered_train, feature_names).as_dict(),
        source_weights=_fallback_weights(),
        calibration_decision={"meta_model": "fallback_weights"},
    )
    meta_model = _fit_meta_model(provisional, engineered_valid, y_valid, config=config)
    calibration_decision = (
        {"meta_model": "logistic_regression", "rows": len(engineered_valid)}
        if meta_model is not None
        else {"meta_model": "fallback_weights", "rows": len(engineered_valid)}
    )
    model = FootballOutcomeV2Model(
        model_version=config.model_version,
        feature_names=feature_names,
        tabular_model=tabular_model,
        market_model=market_model,
        meta_model=meta_model,
        elo_state=elo_state,
        feature_coverage=feature_coverage(engineered_train, feature_names).as_dict(),
        source_weights=_fallback_weights(),
        calibration_decision=calibration_decision,
    )
    metrics = {
        "train": _evaluate_v2_frame(model, engineered_train),
        "validation": _evaluate_v2_frame(model, engineered_valid)
        if not engineered_valid.empty
        else None,
    }
    return model, metrics


def _engineer_training_frame(frame: pd.DataFrame) -> tuple[pd.DataFrame, EloRatingState]:
    with_elo, elo_state = add_elo_features_to_dataset(frame)
    return _add_poisson_feature_columns(with_elo), elo_state


def _engineer_validation_frame(frame: pd.DataFrame, elo_state: EloRatingState) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for _, row in frame.iterrows():
        payload = dict(row)
        payload.update(elo_features_for_row(payload, elo_state))
        payload.update(_poisson_features(payload))
        rows.append(payload)
    return pd.DataFrame(rows, index=frame.index)


def _engineer_inference_frame(frame: pd.DataFrame, elo_state: EloRatingState) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for _, row in frame.iterrows():
        payload = _with_inference_elo(dict(row), elo_state)
        payload.update(_poisson_features(payload))
        rows.append(payload)
    return pd.DataFrame(rows, index=frame.index)


def _add_poisson_feature_columns(frame: pd.DataFrame) -> pd.DataFrame:
    rows = [_poisson_features(dict(row)) for _, row in frame.iterrows()]
    return frame.join(pd.DataFrame(rows, index=frame.index))


def _poisson_features(row: dict[str, Any]) -> dict[str, float]:
    home_lambda, away_lambda = estimate_lambda_home_away_v2(row)
    probabilities = poisson_v2_probabilities(home_lambda, away_lambda)
    return {
        "poisson_v2_home_lambda": home_lambda,
        "poisson_v2_away_lambda": away_lambda,
        "poisson_v2_home": probabilities.p_home,
        "poisson_v2_draw": probabilities.p_draw,
        "poisson_v2_away": probabilities.p_away,
    }


def _fit_tabular_model(
    frame: pd.DataFrame,
    y_train: list[str],
    feature_names: list[str],
    *,
    config: V2TrainingConfig,
) -> Any:
    estimator = _lightgbm_estimator(config) or HistGradientBoostingClassifier(
        max_iter=220,
        learning_rate=0.04,
        l2_regularization=0.12,
        random_state=config.random_state,
    )
    prepared = numeric_feature_dataframe(frame[feature_names], impute=True, forbidden_patterns=())
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


def _fit_market_model(
    frame: pd.DataFrame,
    y_train: list[str],
    *,
    config: V2TrainingConfig,
) -> Any | None:
    columns = ["p_market_home", "p_market_draw", "p_market_away"]
    if not all(column in frame.columns for column in columns):
        return None
    prepared = numeric_feature_dataframe(frame[columns], impute=True, forbidden_patterns=())
    if len(set(y_train)) < 3 or len(prepared) < 30:
        return None
    model = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
            (
                "classifier",
                LogisticRegression(
                    max_iter=2000,
                    random_state=config.random_state,
                ),
            ),
        ]
    )
    model.fit(prepared, y_train)
    return model


def _fit_meta_model(
    model: FootballOutcomeV2Model,
    valid_frame: pd.DataFrame,
    y_valid: list[str],
    *,
    config: V2TrainingConfig,
) -> Any | None:
    if len(valid_frame) < config.min_rows_for_meta or len(set(y_valid)) < 3:
        return None
    rows = [
        _meta_features(model.expert_probabilities_for_row(dict(row)), model.meta_sources)
        for _, row in valid_frame.iterrows()
    ]
    meta_frame = pd.DataFrame(rows)
    meta_model = LogisticRegression(max_iter=2000, random_state=config.random_state)
    meta_model.fit(meta_frame, y_valid)
    return meta_model


def _evaluate_v2_frame(model: FootballOutcomeV2Model, frame: pd.DataFrame) -> dict[str, Any]:
    if frame.empty:
        return {"row_count": 0}
    y_true = list(frame["target"].astype(str))
    probabilities = [ProbabilityTriple.from_vector(row) for row in model.predict_proba(frame)]
    metrics = evaluate_probabilities(y_true, probabilities)
    metrics["mean_log_loss_one"] = sum(
        _log_loss_one(prediction, actual)
        for prediction, actual in zip(probabilities, y_true, strict=True)
    ) / len(y_true)
    metrics["mean_brier_one"] = sum(
        _brier_score_one(prediction, actual)
        for prediction, actual in zip(probabilities, y_true, strict=True)
    ) / len(y_true)
    return metrics


def _market_probability(row: dict[str, Any], market_model: Any | None) -> ProbabilityTriple | None:
    raw = _raw_market_probability(row)
    if raw is None:
        return None
    columns = ["p_market_home", "p_market_draw", "p_market_away"]
    if market_model is None or not all(row.get(column) is not None for column in columns):
        return raw
    frame = pd.DataFrame([{column: row.get(column) for column in columns}])
    try:
        raw_prediction = _predict_proba_safely(
            market_model,
            numeric_feature_dataframe(frame, impute=True),
        )
    except Exception:
        return raw
    return _probability_from_estimator_output(market_model, raw_prediction[0])


def _raw_market_probability(row: dict[str, Any]) -> ProbabilityTriple | None:
    if not any(
        key in row and row.get(key) is not None
        for key in (
            "p_market_home",
            "p_market_draw",
            "p_market_away",
            "market_home",
            "market_draw",
            "market_away",
        )
    ):
        return None
    try:
        return odds_only_probability(row)
    except Exception:
        return None


def _tabular_probability(
    row: dict[str, Any],
    tabular_model: Any | None,
    feature_names: list[str],
) -> ProbabilityTriple | None:
    if tabular_model is None:
        return None
    frame = pd.DataFrame([{name: row.get(name) for name in feature_names}])
    prepared = numeric_feature_dataframe(frame, impute=True, forbidden_patterns=())
    try:
        raw = _predict_proba_safely(tabular_model, prepared)[0]
    except Exception:
        return None
    return _probability_from_estimator_output(tabular_model, raw)


def _add_batch_market_probabilities(
    frame: pd.DataFrame,
    experts_by_index: dict[Any, dict[str, ProbabilityTriple]],
    market_model: Any | None,
) -> None:
    columns = ["p_market_home", "p_market_draw", "p_market_away"]
    if market_model is None or not all(column in frame.columns for column in columns):
        return
    mask = frame[columns].notna().all(axis=1)
    if not mask.any():
        return
    prepared = numeric_feature_dataframe(frame.loc[mask, columns], impute=True)
    try:
        raw_matrix = _predict_proba_safely(market_model, prepared)
    except Exception:
        return
    for index, raw in zip(frame.loc[mask].index, raw_matrix, strict=False):
        experts_by_index[index]["market_calibrated"] = _probability_from_estimator_output(
            market_model,
            raw,
        )


def _add_batch_tabular_probabilities(
    frame: pd.DataFrame,
    experts_by_index: dict[Any, dict[str, ProbabilityTriple]],
    tabular_model: Any | None,
    feature_names: list[str],
) -> None:
    if tabular_model is None:
        return
    prepared = numeric_feature_dataframe(
        frame.reindex(columns=feature_names),
        impute=True,
        forbidden_patterns=(),
    )
    try:
        raw_matrix = _predict_proba_safely(tabular_model, prepared)
    except Exception:
        return
    for index, raw in zip(frame.index, raw_matrix, strict=False):
        experts_by_index[index]["tabular_v2"] = _probability_from_estimator_output(
            tabular_model,
            raw,
        )


def _predict_proba_safely(estimator: Any, frame: pd.DataFrame) -> Any:
    with warnings.catch_warnings():
        warnings.filterwarnings(
            "ignore",
            message="X does not have valid feature names.*",
            category=UserWarning,
        )
        warnings.filterwarnings(
            "ignore",
            message="X has feature names.*",
            category=UserWarning,
        )
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


def _meta_features(
    experts: dict[str, ProbabilityTriple],
    sources: list[str],
) -> dict[str, float]:
    features: dict[str, float] = {}
    prior = ProbabilityTriple.conservative_prior()
    for source in sources:
        probability = experts.get(source, prior)
        features[f"{source}_available"] = 1.0 if source in experts else 0.0
        for label, value in probability.as_dict().items():
            features[f"{source}_{label.casefold()}"] = value
    return features


def _weighted_log_blend(
    experts: dict[str, ProbabilityTriple],
    weights: dict[str, float],
) -> ProbabilityTriple:
    available = [
        (source, probability, weights.get(source, 0.0))
        for source, probability in experts.items()
        if weights.get(source, 0.0) > 0
    ]
    if not available:
        return ProbabilityTriple.conservative_prior()
    total_weight = sum(weight for _source, _probability, weight in available)
    logits: list[float] = []
    for index in range(len(CLASSES)):
        logits.append(
            sum(
                (weight / total_weight)
                * math.log(max(probability.to_vector()[index], 1e-12))
                for _source, probability, weight in available
            )
        )
    maximum = max(logits)
    exps = [math.exp(value - maximum) for value in logits]
    total = sum(exps)
    return ProbabilityTriple.from_vector([value / total for value in exps])


def _with_inference_elo(row: dict[str, Any], state: EloRatingState) -> dict[str, Any]:
    if all(key in row for key in ("elo_home_rating", "elo_away_rating", "elo_diff")):
        return row
    return {**row, **elo_features_for_row(row, state)}


def _lightgbm_estimator(config: V2TrainingConfig) -> Any | None:
    try:
        from lightgbm import LGBMClassifier  # type: ignore[import-not-found]
    except Exception:
        return None
    return LGBMClassifier(
        n_estimators=180,
        learning_rate=0.035,
        num_leaves=24,
        subsample=0.85,
        colsample_bytree=0.85,
        objective="multiclass",
        random_state=config.random_state,
        verbose=-1,
    )


def _fallback_weights() -> dict[str, float]:
    return {
        "market_calibrated": 0.35,
        "poisson_v2": 0.25,
        "elo_v2": 0.15,
        "tabular_v2": 0.25,
    }


def _load_dataset(dataset_path: Path) -> pd.DataFrame:
    suffix = dataset_path.suffix.casefold()
    if suffix == ".csv":
        return pd.read_csv(dataset_path)
    if suffix == ".parquet":
        return pd.read_parquet(dataset_path, engine="pyarrow")
    raise ValueError("dataset_path must be .csv or .parquet")


def _log_loss_one(prediction: ProbabilityTriple, actual: str) -> float:
    probability = max(prediction.as_dict().get(actual, 0.0), 1e-15)
    return -math.log(probability)


def _brier_score_one(prediction: ProbabilityTriple, actual: str) -> float:
    values = prediction.as_dict()
    return sum((value - (1.0 if label == actual else 0.0)) ** 2 for label, value in values.items())


def _temporal_train_valid_test_split(
    frame: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    if "fixture_date" not in frame.columns:
        raise ValueError("fixture_date is required for V2 temporal training")
    ordered = (
        frame.assign(__fixture_date_dt=pd.to_datetime(frame["fixture_date"], utc=True))
        .sort_values("__fixture_date_dt")
        .drop(columns=["__fixture_date_dt"])
        .reset_index(drop=True)
    )
    train_end = max(int(len(ordered) * 0.60), 1)
    valid_end = max(int(len(ordered) * 0.80), train_end + 1)
    valid_end = min(valid_end, len(ordered))
    return (
        ordered.iloc[:train_end].copy(),
        ordered.iloc[train_end:valid_end].copy(),
        ordered.iloc[valid_end:].copy(),
    )
