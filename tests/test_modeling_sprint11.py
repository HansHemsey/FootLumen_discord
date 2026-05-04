from __future__ import annotations

from pathlib import Path

import pandas as pd  # type: ignore[import-untyped]
import pytest
from typer.testing import CliRunner

from football_predictor.cli import app
from football_predictor.modeling.artifacts import load_model_artifact
from football_predictor.modeling.baselines import (
    api_prediction_probability,
    odds_only_probability,
)
from football_predictor.modeling.evaluation import evaluate_probabilities
from football_predictor.modeling.poisson import poisson_baseline_probability
from football_predictor.modeling.probabilities import VALID_RESULTS, ProbabilityTriple
from football_predictor.modeling.sport_model import (
    ModelTrainingConfig,
    predict_sport_probabilities,
    prepare_feature_frame,
    select_safe_feature_columns,
    train_sport_model,
)
from football_predictor.modeling.stacking import (
    stack_probabilities,
    stack_probabilities_with_details,
)
from football_predictor.modeling.training import train_model_artifact


def test_probability_helpers_preserve_class_order() -> None:
    probabilities = ProbabilityTriple.from_mapping({"HOME": 2, "DRAW": 1, "AWAY": 1})

    assert probabilities.to_vector() == [0.5, 0.25, 0.25]
    assert tuple(VALID_RESULTS) == ("HOME", "DRAW", "AWAY")


def test_odds_and_api_baselines_handle_missing_or_invalid_values() -> None:
    row = {
        "market_home": 0.50,
        "market_draw": 0.25,
        "market_away": 0.25,
        "api_pred_home": 45,
        "api_pred_draw": 25,
        "api_pred_away": 30,
    }

    assert odds_only_probability(row).as_dict()["HOME"] == pytest.approx(0.50)
    assert api_prediction_probability(row).as_dict()["HOME"] == pytest.approx(0.45)
    assert odds_only_probability({"market_home": "bad"}).as_dict() == (
        ProbabilityTriple.conservative_prior().as_dict()
    )


def test_poisson_baseline_is_finite_and_directional() -> None:
    home_favored = poisson_baseline_probability(
        {
            "home_team_global_goals_for_avg_last10": 2.1,
            "away_team_global_goals_against_avg_last10": 1.8,
            "away_team_global_goals_for_avg_last10": 0.8,
            "home_team_global_goals_against_avg_last10": 0.7,
        }
    )

    values = home_favored.as_dict()
    assert sum(values.values()) == pytest.approx(1.0)
    assert values["HOME"] > values["AWAY"]


def test_stacking_details_renormalize_missing_sources() -> None:
    result = stack_probabilities_with_details(
        sport=ProbabilityTriple(0.60, 0.20, 0.20),
        market=None,
        api=ProbabilityTriple(0.30, 0.30, 0.40),
    )

    assert result.probabilities.as_dict() == stack_probabilities(
        sport=ProbabilityTriple(0.60, 0.20, 0.20),
        market=None,
        api=ProbabilityTriple(0.30, 0.30, 0.40),
    ).as_dict()
    assert set(result.normalized_weights) == {"sport", "api"}
    assert sum(result.normalized_weights.values()) == pytest.approx(1.0)


def test_safe_feature_selector_excludes_target_leakage_columns() -> None:
    frame = _synthetic_dataset(9)

    columns = select_safe_feature_columns(frame)

    assert "target" not in columns
    assert "fixture_id" not in columns
    assert "target_fixture_id" not in columns
    assert "home_team_id" not in columns
    assert "away_team_id" not in columns
    assert "league_id" not in columns
    assert "season" not in columns
    assert "home_goals" not in columns
    assert "away_goals" not in columns
    assert "fixture_date" not in columns
    assert "prediction_time" not in columns
    assert "home_team_expected_xi_json" not in columns
    assert "market_home" in columns
    assert "home_team_global_goals_for_avg_last10" in columns


def test_sport_model_trains_predicts_and_calibrates_with_missing_values() -> None:
    frame = _synthetic_dataset(60)
    config = ModelTrainingConfig(model_version="synthetic-v1", min_rows_for_calibration=30)

    model = train_sport_model(frame, config=config)
    predictions = predict_sport_probabilities(model, frame.head(5))

    assert model.model_version == "synthetic-v1"
    assert model.calibration_method == "sigmoid"
    assert len(predictions) == 5
    assert all(
        sum(prediction.as_dict().values()) == pytest.approx(1.0)
        for prediction in predictions
    )


def test_prepare_feature_frame_preserves_missing_model_columns() -> None:
    frame = pd.DataFrame({"feature_a": [1.0, 2.0]})

    prepared = prepare_feature_frame(frame, ["feature_a", "data_quality_score"])

    assert list(prepared.columns) == ["feature_a", "data_quality_score"]
    assert prepared["data_quality_score"].isna().all()


def test_calibration_is_skipped_when_dataset_is_too_small() -> None:
    config = ModelTrainingConfig(model_version="small-v1", min_rows_for_calibration=30)

    model = train_sport_model(_synthetic_dataset(9), config=config)

    assert model.calibration_method is None
    assert model.calibration_skipped_reason is not None


def test_model_artifact_roundtrip(tmp_path: Path) -> None:
    frame = _synthetic_dataset(45)

    artifact = train_model_artifact(
        frame,
        tmp_path,
        "artifact-v1",
        config=ModelTrainingConfig(model_version="artifact-v1", min_rows_for_calibration=30),
    )
    loaded = load_model_artifact(tmp_path)

    assert (tmp_path / "model.joblib").exists()
    assert (tmp_path / "metadata.json").exists()
    assert loaded.model_version == artifact.model_version
    assert loaded.feature_columns == artifact.feature_columns
    assert loaded.sport_model.predict_probabilities(frame.head(3))[0].as_dict() == (
        artifact.sport_model.predict_probabilities(frame.head(3))[0].as_dict()
    )


def test_evaluation_metrics_are_json_serializable_shapes() -> None:
    metrics = evaluate_probabilities(
        ["HOME", "DRAW", "AWAY"],
        [
            ProbabilityTriple(0.7, 0.2, 0.1),
            ProbabilityTriple(0.2, 0.6, 0.2),
            ProbabilityTriple(0.1, 0.3, 0.6),
        ],
        calibration_bins=5,
    )

    assert metrics["accuracy"] == pytest.approx(1.0)
    assert metrics["log_loss"] >= 0.0
    assert metrics["brier_score"] >= 0.0
    assert len(metrics["confusion_matrix"]) == 3
    assert len(metrics["calibration_bins"]) == 5


def test_train_cli_writes_artifact_without_network(tmp_path: Path) -> None:
    dataset = tmp_path / "training.csv"
    output_dir = tmp_path / "model"
    _synthetic_dataset(45).to_csv(dataset, index=False)

    result = CliRunner().invoke(
        app,
        [
            "train",
            "--dataset",
            str(dataset),
            "--output-dir",
            str(output_dir),
            "--model-version",
            "cli-v1",
            "--calibration",
            "sigmoid",
        ],
    )

    assert result.exit_code == 0, result.stdout
    assert (output_dir / "model.joblib").exists()
    assert (output_dir / "metadata.json").exists()
    assert "cli-v1" in result.stdout


def _synthetic_dataset(row_count: int) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    labels = ["HOME", "DRAW", "AWAY"]
    for index in range(row_count):
        target = labels[index % len(labels)]
        home_strength = 2.2 if target == "HOME" else 1.2 if target == "DRAW" else 0.7
        away_strength = 2.1 if target == "AWAY" else 1.1 if target == "DRAW" else 0.8
        draw_signal = 1.0 if target == "DRAW" else 0.0
        rows.append(
            {
                "target": target,
                "fixture_id": -10_000 - index,
                "target_fixture_id": -20_000 - index,
                "feature_snapshot_id": index,
                "league_id": -1,
                "season": 2099,
                "home_team_id": -100,
                "away_team_id": -200,
                "fixture_date": f"2099-01-{(index % 28) + 1:02d}T12:00:00+00:00",
                "prediction_time": f"2099-01-{(index % 28) + 1:02d}T00:00:00+00:00",
                "home_goals": 2 if target == "HOME" else 1,
                "away_goals": 2 if target == "AWAY" else 1,
                "home_team_expected_xi_json": "[]",
                "home_team_global_goals_for_avg_last10": home_strength,
                "away_team_global_goals_for_avg_last10": away_strength,
                "home_team_global_goals_against_avg_last10": away_strength / 2,
                "away_team_global_goals_against_avg_last10": home_strength / 2,
                "home_team_global_points_per_match_last10": home_strength,
                "away_team_global_points_per_match_last10": away_strength,
                "rank_diff": -home_strength + away_strength,
                "draw_pressure": draw_signal,
                "market_home": 0.62 if target == "HOME" else 0.25,
                "market_draw": 0.55 if target == "DRAW" else 0.20,
                "market_away": 0.60 if target == "AWAY" else 0.20,
                "api_pred_home": 0.58 if target == "HOME" else 0.22,
                "api_pred_draw": 0.52 if target == "DRAW" else 0.20,
                "api_pred_away": 0.57 if target == "AWAY" else 0.21,
                "player_stats_available_rate": None if index % 7 == 0 else 0.8,
            }
        )
    return pd.DataFrame(rows)
