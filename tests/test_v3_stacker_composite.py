from __future__ import annotations

import json

import pandas as pd  # type: ignore[import-untyped]
import pytest

from football_predictor.modeling.v3.composite import FootballOutcomeV3Model
from football_predictor.modeling.v3.fusion import deterministic_v3_fusion
from football_predictor.modeling.v3.stacker import (
    V3StackerTrainingConfig,
    train_v3_stacker_from_frame,
)
from football_predictor.modeling.v3.training import train_v3_from_dataset


def test_deterministic_v3_fusion_returns_normalized_1x2_probabilities() -> None:
    probability = deterministic_v3_fusion(
        draw_probability=0.22,
        home_no_draw_probability=0.70,
        v2_probability=[0.50, 0.25, 0.25],
        market_probability=[0.48, 0.24, 0.28],
    )

    values = probability.to_vector()
    assert len(values) == 3
    assert all(0.0 <= value <= 1.0 for value in values)
    assert sum(values) == pytest.approx(1.0)
    assert probability.predicted_result() == "HOME"


def test_v3_stacker_training_writes_artifact_and_predicts_valid_probabilities(tmp_path) -> None:
    frame = _synthetic_stacker_frame(72)

    result = train_v3_stacker_from_frame(
        frame,
        tmp_path / "stacker",
        config=V3StackerTrainingConfig(min_rows_for_stacker=12),
    )

    assert result.model_path.exists()
    assert result.metadata_path.exists()
    assert result.metrics_path.exists()
    assert result.model.training_decision["method"] == "logistic_regression"
    probabilities = result.model.predict_proba(frame.head(9))
    assert len(probabilities) == 9
    for row in probabilities:
        assert len(row) == 3
        assert all(0.0 <= value <= 1.0 for value in row)
        assert sum(row) == pytest.approx(1.0)

    metrics = json.loads(result.metrics_path.read_text(encoding="utf-8"))
    assert metrics["train"]["log_loss"] is not None
    assert metrics["train"]["brier_score"] is not None


def test_train_v3_from_dataset_writes_components_and_loaded_composite_predicts(tmp_path) -> None:
    dataset_path = tmp_path / "v3_dataset.csv"
    frame = _synthetic_v3_frame(240)
    frame.to_csv(dataset_path, index=False)

    result = train_v3_from_dataset(dataset_path, tmp_path / "v3")

    assert result.model_path.exists()
    assert result.metadata_path.exists()
    assert result.metrics_path.exists()
    assert result.draw_risk_model_path.exists()
    assert result.no_draw_winner_model_path.exists()
    assert result.stacker_result.model_path.exists()
    assert result.stacker_result.model.training_decision["method"] == "logistic_regression"

    loaded = FootballOutcomeV3Model.load(tmp_path / "v3")
    probabilities = loaded.predict_proba(frame.head(12))
    assert len(probabilities) == 12
    for row in probabilities:
        assert len(row) == 3
        assert all(0.0 <= value <= 1.0 for value in row)
        assert sum(row) == pytest.approx(1.0)

    metadata = json.loads(result.metadata_path.read_text(encoding="utf-8"))
    assert metadata["artifact_format"] == "football_outcome_model_v3"
    assert metadata["stacker_training_decision"]["method"] == "logistic_regression"


def test_loaded_composite_uses_deterministic_fallback_without_stacker(tmp_path) -> None:
    dataset_path = tmp_path / "v3_dataset.csv"
    frame = _synthetic_v3_frame(90)
    frame.to_csv(dataset_path, index=False)
    result = train_v3_from_dataset(dataset_path, tmp_path / "v3")

    result.stacker_result.model_path.unlink()
    loaded = FootballOutcomeV3Model.load(tmp_path / "v3")
    probabilities = loaded.predict_proba(frame.tail(5))

    assert loaded.stacker_model is None
    for row in probabilities:
        assert len(row) == 3
        assert all(0.0 <= value <= 1.0 for value in row)
        assert sum(row) == pytest.approx(1.0)


def _synthetic_stacker_frame(row_count: int) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for index in range(row_count):
        outcome = ["HOME", "DRAW", "AWAY"][index % 3]
        p_draw = 0.64 if outcome == "DRAW" else 0.16
        home_no_draw = 0.76 if outcome == "HOME" else 0.24
        rows.append(
            {
                "fixture_id": -300_000 - index,
                "target": outcome,
                "outcome": outcome,
                "p_v3_draw_risk": p_draw,
                "p_v3_home_no_draw": home_no_draw,
                "p_v3_away_no_draw": 1.0 - home_no_draw,
                "p_v2_home": 0.58 if outcome == "HOME" else 0.22,
                "p_v2_draw": 0.56 if outcome == "DRAW" else 0.20,
                "p_v2_away": 0.58 if outcome == "AWAY" else 0.22,
                "p_market_home": 0.55 if outcome == "HOME" else 0.24,
                "p_market_draw": 0.52 if outcome == "DRAW" else 0.22,
                "p_market_away": 0.55 if outcome == "AWAY" else 0.24,
                "p_api_home": 0.54 if outcome == "HOME" else 0.23,
                "p_api_draw": 0.51 if outcome == "DRAW" else 0.23,
                "p_api_away": 0.54 if outcome == "AWAY" else 0.23,
                "market_overround": 0.06,
                "market_dispersion": 0.03,
                "data_quality_score": 0.80,
                "official_lineup_available_flag": int(index % 2 == 0),
            }
        )
    return pd.DataFrame(rows)


def _synthetic_v3_frame(row_count: int) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    start = pd.Timestamp("2025-01-01T18:00:00Z")
    for index in range(row_count):
        outcome = ["HOME", "DRAW", "AWAY"][index % 3]
        fixture_date = start + pd.Timedelta(days=index)
        is_draw = int(outcome == "DRAW")
        home_wins = int(outcome == "HOME")
        draw_signal = 0.68 if is_draw else 0.16 + (index % 4) * 0.01
        home_edge = 0.60 if outcome == "HOME" else (-0.60 if outcome == "AWAY" else 0.0)
        market_home = 0.55 if outcome == "HOME" else (0.24 if outcome == "AWAY" else 0.34)
        market_draw = 0.54 if outcome == "DRAW" else 0.22
        market_away = 0.55 if outcome == "AWAY" else (0.24 if outcome == "HOME" else 0.34)
        rows.append(
            {
                # Negative fixture IDs are explicit synthetic test-only identifiers.
                "fixture_id": -400_000 - index,
                "fixture_date": fixture_date.isoformat(),
                "prediction_time": (fixture_date - pd.Timedelta(minutes=30)).isoformat(),
                "target": outcome,
                "outcome": outcome,
                "is_draw": is_draw,
                "home_wins": None if outcome == "DRAW" else home_wins,
                "home_goals": 1 if outcome != "AWAY" else 0,
                "away_goals": 1 if outcome != "HOME" else 0,
                "draw_risk_score": draw_signal,
                "draw_risk_parity_score": 0.75 if is_draw else 0.24,
                "draw_risk_low_goal_signal": 0.70 if is_draw else 0.30,
                "ndw_home_away_strength_edge": home_edge,
                "ndw_attack_defense_edge": home_edge * 0.8,
                "ndw_home_advantage_edge": 0.20 if outcome == "HOME" else -0.08,
                "ndw_xi_value_edge": home_edge * 1.2,
                "ndw_absence_impact_edge": 0.18 if outcome == "HOME" else -0.18,
                "ndw_odds_home_prob": market_home / (market_home + market_away),
                "market_home": market_home,
                "market_draw": market_draw,
                "market_away": market_away,
                "p_market_home": market_home,
                "p_market_draw": market_draw,
                "p_market_away": market_away,
                "api_pred_home": market_home,
                "api_pred_draw": market_draw,
                "api_pred_away": market_away,
                "market_overround": 0.05,
                "market_dispersion": 0.03,
                "official_lineup_available_flag": int(index % 3 == 0),
                "lineup_m30_official_available_flag": int(index % 3 == 0),
                "home_team_absence_impact_score": 0.10 if outcome == "HOME" else 0.30,
                "away_team_absence_impact_score": 0.30 if outcome == "HOME" else 0.10,
                "data_quality_score": 0.74 + (index % 10) * 0.02,
                "home_team_form_last5": 0.62 if outcome == "HOME" else 0.38,
                "away_team_form_last5": 0.62 if outcome == "AWAY" else 0.38,
                "payload_json": "{}",
            }
        )
    return pd.DataFrame(rows)
