from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from football_predictor.backtesting.dataset import parse_prediction_window
from football_predictor.backtesting.evaluator import BacktestConfig, temporal_split
from football_predictor.modeling.elo import add_elo_features_to_dataset
from football_predictor.modeling.loader import load_prediction_model
from football_predictor.modeling.poisson_v2 import (
    estimate_lambda_home_away_v2,
    poisson_v2_predict,
)
from football_predictor.modeling.train import train_model_from_dataset
from football_predictor.modeling.v2_features import select_v2_feature_names
from football_predictor.modeling.v2_model import V2TrainingConfig, train_v2_model_from_frame


def test_poisson_v2_returns_valid_probabilities_and_reacts_to_edge() -> None:
    home_edge = {
        "home_team_home_goals_for_avg_last10": 2.4,
        "away_team_away_goals_against_avg_last10": 1.9,
        "away_team_away_goals_for_avg_last10": 0.7,
        "home_team_home_goals_against_avg_last10": 0.8,
        "home_team_global_pseudo_xg_for_avg_last10": 2.1,
    }

    home_lambda, away_lambda = estimate_lambda_home_away_v2(home_edge)
    probabilities = poisson_v2_predict(home_edge)

    assert home_lambda > away_lambda
    assert sum(probabilities) == pytest.approx(1.0)
    assert probabilities[0] > probabilities[2]


def test_elo_features_are_point_in_time() -> None:
    frame = _synthetic_v2_dataset(9)
    with_elo, _state = add_elo_features_to_dataset(frame)

    assert with_elo.loc[0, "elo_home_rating"] == pytest.approx(1500.0)
    assert with_elo.loc[6, "elo_home_rating"] != pytest.approx(
        with_elo.loc[0, "elo_home_rating"]
    )


def test_v2_feature_selection_excludes_leakage_columns() -> None:
    frame = _synthetic_v2_dataset(12)
    frame["payload_json"] = "{}"
    frame["status_short"] = "FT"

    selected = select_v2_feature_names(frame)

    assert "p_market_home" in selected
    assert "home_team_global_goals_for_avg_last10" in selected
    assert "fixture_id" not in selected
    assert "home_team_id" not in selected
    assert "target" not in selected
    assert "home_goals" not in selected
    assert "payload_json" not in selected
    assert "status_short" not in selected


def test_train_v2_model_writes_artifacts_and_predicts(tmp_path: Path) -> None:
    dataset_path = tmp_path / "v2_dataset.csv"
    output_dir = tmp_path / "models" / "v2-late"
    _synthetic_v2_dataset(90).to_csv(dataset_path, index=False)

    result = train_model_from_dataset(dataset_path, output_dir, model_version="v2-late-test")
    loaded = load_prediction_model(output_dir)
    probabilities = loaded.predict_proba(_synthetic_v2_dataset(3))

    assert result.model_path.exists()
    assert result.feature_coverage_path is not None
    assert result.feature_coverage_path.exists()
    assert json.loads(result.metadata_path.read_text(encoding="utf-8"))[
        "artifact_format"
    ] == "football_outcome_model_v2"
    assert all(abs(sum(row) - 1.0) < 1e-9 for row in probabilities)


def test_v2_backtest_training_uses_only_train_and_validation_splits() -> None:
    frame = _synthetic_v2_dataset(90)
    train, validation, test = temporal_split(frame, config=BacktestConfig())
    model, metrics = train_v2_model_from_frame(
        train,
        validation,
        config=V2TrainingConfig(model_version="v2-temporal-test"),
    )
    probabilities = model.predict_proba(test)

    assert metrics["train"]["row_count"] == len(train)
    assert metrics["validation"]["row_count"] == len(validation)
    assert len(probabilities) == len(test)


def test_prediction_window_30m_is_supported() -> None:
    assert parse_prediction_window("30m").total_seconds() == 30 * 60
    assert parse_prediction_window("40m").total_seconds() == 40 * 60


def _synthetic_v2_dataset(row_count: int) -> pd.DataFrame:
    labels = ["HOME", "DRAW", "AWAY"]
    rows: list[dict[str, object]] = []
    for index in range(row_count):
        target = labels[index % 3]
        rows.append(
            {
                "target": target,
                "fixture_id": -5000 - index,
                "feature_snapshot_id": -7000 - index,
                "league_id": -100,
                "season": 2099,
                "home_team_id": -10 - (index % 6),
                "away_team_id": -30 - ((index + 2) % 6),
                "home_goals": 2 if target == "HOME" else 1 if target == "DRAW" else 0,
                "away_goals": 2 if target == "AWAY" else 1 if target == "DRAW" else 0,
                "fixture_date": pd.Timestamp("2099-01-01T12:00:00Z")
                + pd.Timedelta(days=index),
                "prediction_time": pd.Timestamp("2099-01-01T11:30:00Z")
                + pd.Timedelta(days=index),
                "home_team_global_goals_for_avg_last10": 2.1 if target == "HOME" else 0.9,
                "away_team_global_goals_for_avg_last10": 2.1 if target == "AWAY" else 0.9,
                "home_team_global_goals_against_avg_last10": 0.8
                if target != "AWAY"
                else 1.8,
                "away_team_global_goals_against_avg_last10": 0.8
                if target != "HOME"
                else 1.8,
                "home_team_global_pseudo_xg_for_avg_last10": 2.0
                if target == "HOME"
                else 1.0,
                "away_team_global_pseudo_xg_for_avg_last10": 2.0
                if target == "AWAY"
                else 1.0,
                "home_team_global_ppg_last10": 2.1 if target == "HOME" else 1.0,
                "away_team_global_ppg_last10": 2.1 if target == "AWAY" else 1.0,
                "home_team_absence_impact_score": 0.1 if target != "HOME" else 0.0,
                "away_team_absence_impact_score": 0.1 if target != "AWAY" else 0.0,
                "home_team_xi_stability_score": 0.8,
                "away_team_xi_stability_score": 0.75,
                "p_market_home": 0.62 if target == "HOME" else 0.22,
                "p_market_draw": 0.54 if target == "DRAW" else 0.24,
                "p_market_away": 0.62 if target == "AWAY" else 0.22,
                "overall_data_quality_score": 75,
            }
        )
    return pd.DataFrame(rows)
