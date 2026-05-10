from __future__ import annotations

import json

import joblib  # type: ignore[import-untyped]
import numpy as np
import pandas as pd  # type: ignore[import-untyped]

from football_predictor.modeling.v3.features_selection import (
    select_v3_no_draw_winner_feature_names,
)
from football_predictor.modeling.v3.no_draw_winner_model import (
    NoDrawWinnerModel,
    NoDrawWinnerTrainingConfig,
    train_no_draw_winner_from_dataset,
)


def test_v3_no_draw_winner_feature_selection_excludes_leakage_and_keeps_signals() -> None:
    frame = pd.DataFrame(
        {
            "is_draw": [0, 0, 1],
            "home_wins": [1, 0, None],
            "target": ["HOME", "AWAY", "DRAW"],
            "outcome": ["HOME", "AWAY", "DRAW"],
            "fixture_id": [-1, -2, -3],
            "fixture_date": ["2026-01-01", "2026-01-02", "2026-01-03"],
            "home_goals": [2, 0, 1],
            "away_goals": [0, 1, 1],
            "payload_json": [{"x": 1}, {"x": 2}, {"x": 3}],
            "p_v2_home": [0.5, 0.2, 0.33],
            "p_v3_draw_risk": [0.2, 0.3, 0.6],
            "draw_risk_score": [0.2, 0.3, 0.7],
            "ndw_home_away_strength_edge": [0.4, -0.3, 0.0],
            "ndw_attack_defense_edge": [0.5, -0.4, 0.1],
            "ndw_odds_home_prob": [0.68, 0.36, 0.50],
            "market_home": [0.52, 0.25, 0.35],
            "market_draw": [0.24, 0.25, 0.30],
            "market_away": [0.24, 0.50, 0.35],
            "p_market_home": [0.53, 0.26, 0.34],
            "p_market_draw": [0.22, 0.23, 0.32],
            "p_market_away": [0.25, 0.51, 0.34],
            "api_pred_home": [0.54, 0.28, 0.33],
            "api_pred_draw": [0.22, 0.24, 0.34],
            "api_pred_away": [0.24, 0.50, 0.33],
            "official_lineup_available_flag": [1, 0, 1],
            "home_team_absence_impact_score": [0.1, 0.3, 0.2],
            "away_team_absence_impact_score": [0.3, 0.1, 0.2],
            "data_quality_score": [0.95, 0.74, 0.81],
        }
    )

    selected = select_v3_no_draw_winner_feature_names(frame)

    assert "ndw_home_away_strength_edge" in selected
    assert "ndw_attack_defense_edge" in selected
    assert "ndw_odds_home_prob" in selected
    assert "market_home" in selected
    assert "market_away" in selected
    assert "p_market_home" in selected
    assert "p_market_away" in selected
    assert "api_pred_home" in selected
    assert "api_pred_away" in selected
    assert "official_lineup_available_flag" in selected
    assert "home_team_absence_impact_score" in selected
    assert "data_quality_score" in selected
    assert "is_draw" not in selected
    assert "home_wins" not in selected
    assert "target" not in selected
    assert "outcome" not in selected
    assert "fixture_id" not in selected
    assert "home_goals" not in selected
    assert "away_goals" not in selected
    assert "payload_json" not in selected
    assert "p_v2_home" not in selected
    assert "p_v3_draw_risk" not in selected
    assert "draw_risk_score" not in selected
    assert "market_draw" not in selected
    assert "p_market_draw" not in selected
    assert "api_pred_draw" not in selected


def test_train_no_draw_winner_from_dataset_filters_draws_and_writes_artifacts(tmp_path) -> None:
    dataset_path = tmp_path / "v3_dataset.csv"
    frame = _synthetic_v3_frame(120)
    frame.to_csv(dataset_path, index=False)

    result = train_no_draw_winner_from_dataset(
        dataset_path,
        tmp_path / "no_draw_winner",
        config=NoDrawWinnerTrainingConfig(model_version="test-no-draw-winner"),
    )

    for artifact_path in (
        result.model_path,
        result.metadata_path,
        result.feature_names_path,
        result.metrics_path,
        result.feature_coverage_path,
    ):
        assert artifact_path.exists()

    metadata = json.loads(result.metadata_path.read_text(encoding="utf-8"))
    metrics = json.loads(result.metrics_path.read_text(encoding="utf-8"))
    feature_names = json.loads(result.feature_names_path.read_text(encoding="utf-8"))
    non_draw_rows = int((frame["target"] != "DRAW").sum())

    assert metadata["artifact_format"] == "no_draw_winner_model_v3"
    assert metadata["model_version"] == "test-no-draw-winner"
    assert metadata["training_rows"] + metadata["validation_rows"] + metadata["test_rows"] == (
        non_draw_rows
    )
    assert metadata["calibration_decision"]["reason"] == "skipped_low_volume"
    assert "home_wins" not in feature_names
    assert metrics["validation"]["log_loss"] is not None
    assert metrics["validation"]["brier_score"] is not None
    assert "roc_auc" in metrics["validation"]
    assert "pr_auc" in metrics["validation"]
    assert metrics["validation"]["baselines"]["market_home_no_draw_probability"] is not None


def test_no_draw_winner_predict_proba_is_valid_and_handles_missing_columns(tmp_path) -> None:
    dataset_path = tmp_path / "v3_dataset.csv"
    frame = _synthetic_v3_frame(108)
    frame.to_csv(dataset_path, index=False)
    result = train_no_draw_winner_from_dataset(dataset_path, tmp_path / "no_draw_winner")

    inference_frame = frame.drop(columns=["ndw_attack_defense_edge", "p_market_home"]).head(9)
    home_probabilities = result.model.predict_home_no_draw_proba(inference_frame)
    matrix = result.model.predict_proba(inference_frame)

    assert len(home_probabilities) == 9
    assert all(0.0 <= probability <= 1.0 for probability in home_probabilities)
    assert len(matrix) == 9
    for row in matrix:
        assert len(row) == 2
        assert np.isclose(sum(row), 1.0)
        assert all(0.0 <= probability <= 1.0 for probability in row)


def test_low_volume_sigmoid_calibration_is_skipped_and_recorded(tmp_path) -> None:
    dataset_path = tmp_path / "v3_dataset.csv"
    _synthetic_v3_frame(72).to_csv(dataset_path, index=False)

    result = train_no_draw_winner_from_dataset(dataset_path, tmp_path / "no_draw_winner")

    assert result.model.calibration_decision["method"] is None
    assert result.model.calibration_decision["reason"] == "skipped_low_volume"
    assert result.metrics["calibration_decision"]["reason"] == "skipped_low_volume"


def test_joblib_loaded_no_draw_winner_model_preserves_predictions(tmp_path) -> None:
    dataset_path = tmp_path / "v3_dataset.csv"
    frame = _synthetic_v3_frame(112)
    frame.to_csv(dataset_path, index=False)
    result = train_no_draw_winner_from_dataset(dataset_path, tmp_path / "no_draw_winner")

    loaded = joblib.load(result.model_path)
    assert isinstance(loaded, NoDrawWinnerModel)

    sample = frame.tail(6)
    np.testing.assert_allclose(
        loaded.predict_home_no_draw_proba(sample),
        result.model.predict_home_no_draw_proba(sample),
        rtol=1e-12,
        atol=1e-12,
    )


def _synthetic_v3_frame(row_count: int) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    start = pd.Timestamp("2025-01-01T18:00:00Z")
    for index in range(row_count):
        outcome = "DRAW" if index % 5 == 0 else ("HOME" if index % 2 == 0 else "AWAY")
        home_wins = 1 if outcome == "HOME" else 0
        fixture_date = start + pd.Timedelta(days=index)
        home_edge = 0.55 + (index % 4) * 0.03 if home_wins else -0.55 - (index % 4) * 0.03
        market_home = 0.56 if home_wins else 0.26
        market_away = 0.26 if home_wins else 0.56
        if outcome == "DRAW":
            home_edge = 0.0
            market_home = 0.34
            market_away = 0.34
        rows.append(
            {
                # Negative fixture IDs are explicit synthetic test-only identifiers.
                "fixture_id": -200_000 - index,
                "fixture_date": fixture_date.isoformat(),
                "prediction_time": (fixture_date - pd.Timedelta(minutes=30)).isoformat(),
                "target": outcome,
                "outcome": outcome,
                "is_draw": int(outcome == "DRAW"),
                "home_wins": None if outcome == "DRAW" else home_wins,
                "home_goals": 1 if outcome != "AWAY" else 0,
                "away_goals": 1 if outcome != "HOME" else 0,
                "draw_risk_score": 0.70 if outcome == "DRAW" else 0.18,
                "ndw_home_away_strength_edge": home_edge,
                "ndw_attack_defense_edge": home_edge * 0.8,
                "ndw_home_advantage_edge": 0.20 if home_wins else -0.10,
                "ndw_xi_value_edge": home_edge * 1.3,
                "ndw_absence_impact_edge": 0.20 if home_wins else -0.20,
                "ndw_odds_home_prob": market_home / (market_home + market_away),
                "market_home": market_home,
                "market_away": market_away,
                "p_market_home": market_home,
                "p_market_away": market_away,
                "api_pred_home": market_home + 0.01,
                "api_pred_away": market_away - 0.01,
                "official_lineup_available_flag": int(index % 3 == 0),
                "lineup_m30_official_available_flag": int(index % 3 == 0),
                "home_team_absence_impact_score": 0.10 if home_wins else 0.32,
                "away_team_absence_impact_score": 0.32 if home_wins else 0.10,
                "data_quality_score": 0.72 + (index % 10) * 0.02,
                "home_team_form_last5": 0.62 if home_wins else 0.38,
                "away_team_form_last5": 0.38 if home_wins else 0.62,
                "payload_json": "{}",
            }
        )
    return pd.DataFrame(rows)
