from __future__ import annotations

import json
import warnings
from pathlib import Path

import pandas as pd  # type: ignore[import-untyped]
from pandas.errors import PerformanceWarning  # type: ignore[import-untyped]

from football_predictor.modeling.multiclass_model import FootballOutcomeModel
from football_predictor.modeling.preprocessing import (
    numeric_feature_dataframe,
    separate_metadata_target_features,
)
from football_predictor.modeling.train import train_model_from_dataset


def test_preprocessing_excludes_target_leakage_and_handles_booleans() -> None:
    frame = pd.DataFrame(
        [
            {
                "target": "HOME",
                "home_goals": 2,
                "away_goals": 1,
                "fixture_id": -1,
                "league_id": -2,
                "home_team_id": -3,
                "status_short": "FT",
                "fixture_date": "2099-01-01T12:00:00+00:00",
                "feature_a": 1.5,
                "feature_bool": True,
                "payload_json": "{}",
            },
            {
                "target": "AWAY",
                "home_goals": 0,
                "away_goals": 1,
                "fixture_id": -4,
                "league_id": -2,
                "home_team_id": -5,
                "status_short": "FT",
                "fixture_date": "2099-01-02T12:00:00+00:00",
                "feature_a": None,
                "feature_bool": False,
                "payload_json": "{}",
            },
        ]
    )

    data = separate_metadata_target_features(frame)

    assert data.feature_names == ["feature_a", "feature_bool"]
    assert data.features["feature_a"].isna().sum() == 0
    assert data.features["feature_bool"].tolist() == [1.0, 0.0]
    assert "home_goals" in data.metadata.columns
    assert "fixture_id" in data.metadata.columns


def test_numeric_feature_dataframe_does_not_fragment_many_columns() -> None:
    frame = pd.DataFrame(
        [
            {f"feature_{index}": float(index) for index in range(180)},
            {f"feature_{index}": None if index % 7 == 0 else float(index) for index in range(180)},
        ]
    )

    with warnings.catch_warnings():
        warnings.simplefilter("error", PerformanceWarning)
        output = numeric_feature_dataframe(frame)

    assert output.shape == (2, 180)
    assert output.isna().sum().sum() == 0


def test_football_outcome_model_save_load_roundtrip(tmp_path: Path) -> None:
    frame = _synthetic_dataset(30)
    data = separate_metadata_target_features(frame)
    model_path = tmp_path / "model.joblib"

    model = FootballOutcomeModel(model_version="synthetic-v1")
    model.fit(data.features, list(data.target.astype(str)))  # type: ignore[union-attr]
    model.save(model_path)
    loaded = FootballOutcomeModel.load(model_path)

    probabilities = loaded.predict_proba(data.features.head(3))
    assert loaded.model_version == "synthetic-v1"
    assert loaded.feature_names == model.feature_names
    assert len(probabilities) == 3
    assert all(abs(sum(row) - 1.0) < 1e-9 for row in probabilities)


def test_football_outcome_model_predicts_with_missing_trained_feature() -> None:
    frame = _synthetic_dataset(30)
    data = separate_metadata_target_features(frame)
    model = FootballOutcomeModel(model_version="synthetic-missing-feature")
    model.fit(data.features, list(data.target.astype(str)))  # type: ignore[union-attr]
    assert "p_market_home" in model.feature_names

    predict_frame = data.features.drop(columns=["p_market_home"])
    probabilities = model.predict_proba(predict_frame.head(3))

    assert len(probabilities) == 3
    assert all(abs(sum(row) - 1.0) < 1e-9 for row in probabilities)


def test_train_model_from_dataset_writes_expected_artifacts(tmp_path: Path) -> None:
    dataset_path = tmp_path / "training.csv"
    output_dir = tmp_path / "models" / "v1"
    _synthetic_dataset(45).to_csv(dataset_path, index=False)

    result = train_model_from_dataset(dataset_path, output_dir, model_version="v1-test")

    assert result.model_path.exists()
    assert result.metadata_path.exists()
    assert result.feature_names_path.exists()
    assert result.metrics_path.exists()
    feature_names = json.loads(result.feature_names_path.read_text(encoding="utf-8"))
    metrics = json.loads(result.metrics_path.read_text(encoding="utf-8"))
    metadata = json.loads(result.metadata_path.read_text(encoding="utf-8"))
    assert "fixture_id" not in feature_names
    assert "home_goals" not in feature_names
    assert "target" not in feature_names
    assert metrics["train"]["row_count"] > 0
    assert metadata["model_version"] == "v1-test"


def _synthetic_dataset(row_count: int) -> pd.DataFrame:
    labels = ["HOME", "DRAW", "AWAY"]
    rows: list[dict[str, object]] = []
    for index in range(row_count):
        target = labels[index % 3]
        rows.append(
            {
                "target": target,
                "fixture_id": -1000 - index,
                "league_id": -1,
                "season": 2099,
                "home_team_id": -10,
                "away_team_id": -20,
                "home_goals": 2 if target == "HOME" else 1,
                "away_goals": 2 if target == "AWAY" else 1,
                "fixture_date": f"2099-01-{(index % 28) + 1:02d}T12:00:00+00:00",
                "prediction_time": f"2099-01-{(index % 28) + 1:02d}T00:00:00+00:00",
                "home_team_global_goals_for_avg_last10": 2.0 if target == "HOME" else 0.8,
                "away_team_global_goals_for_avg_last10": 2.0 if target == "AWAY" else 0.8,
                "draw_signal": 1.0 if target == "DRAW" else 0.0,
                "p_market_home": 0.60 if target == "HOME" else 0.20,
                "p_market_draw": 0.55 if target == "DRAW" else 0.25,
                "p_market_away": 0.60 if target == "AWAY" else 0.20,
                "lineups_available_flag": index % 2 == 0,
                "home_team_expected_xi_json": "[]",
            }
        )
    return pd.DataFrame(rows)
