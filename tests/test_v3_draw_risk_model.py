from __future__ import annotations

import json

import joblib  # type: ignore[import-untyped]
import numpy as np
import pandas as pd  # type: ignore[import-untyped]

from football_predictor.modeling.v3.draw_risk_model import (
    DrawRiskModel,
    DrawRiskTrainingConfig,
    train_draw_risk_from_dataset,
)
from football_predictor.modeling.v3.features_selection import select_v3_draw_feature_names


def test_v3_draw_feature_selection_excludes_leakage_and_keeps_signals() -> None:
    frame = pd.DataFrame(
        {
            "is_draw": [1, 0, 0],
            "home_wins": [0, 1, 0],
            "target": ["DRAW", "HOME", "AWAY"],
            "outcome": ["DRAW", "HOME", "AWAY"],
            "fixture_id": [-1, -2, -3],
            "fixture_date": ["2026-01-01", "2026-01-02", "2026-01-03"],
            "home_goals": [1, 2, 0],
            "away_goals": [1, 0, 1],
            "payload_json": [{"x": 1}, {"x": 2}, {"x": 3}],
            "p_v2_draw": [0.3, 0.2, 0.25],
            "p_v3_home_no_draw": [0.5, 0.8, 0.2],
            "draw_risk_score": [0.7, 0.2, 0.3],
            "market_draw": [0.32, 0.24, 0.28],
            "p_market_draw": [0.31, 0.23, 0.27],
            "lineup_m30_official_available_flag": [1, 0, 1],
            "official_lineup_available_flag": [1, 0, 1],
            "data_quality_score": [0.95, 0.74, 0.81],
        }
    )

    selected = select_v3_draw_feature_names(frame)

    assert "draw_risk_score" in selected
    assert "market_draw" in selected
    assert "p_market_draw" in selected
    assert "lineup_m30_official_available_flag" in selected
    assert "official_lineup_available_flag" in selected
    assert "data_quality_score" in selected
    assert "is_draw" not in selected
    assert "home_wins" not in selected
    assert "target" not in selected
    assert "outcome" not in selected
    assert "fixture_id" not in selected
    assert "home_goals" not in selected
    assert "away_goals" not in selected
    assert "payload_json" not in selected
    assert "p_v2_draw" not in selected
    assert "p_v3_home_no_draw" not in selected


def test_train_draw_risk_from_dataset_writes_artifacts_and_metrics(tmp_path) -> None:
    dataset_path = tmp_path / "v3_dataset.csv"
    _synthetic_v3_frame(96).to_csv(dataset_path, index=False)

    result = train_draw_risk_from_dataset(
        dataset_path,
        tmp_path / "draw_risk",
        config=DrawRiskTrainingConfig(model_version="test-draw-risk"),
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

    assert metadata["artifact_format"] == "draw_risk_model_v3"
    assert metadata["model_version"] == "test-draw-risk"
    assert metadata["calibration_decision"]["reason"] == "skipped_low_volume"
    assert "is_draw" not in feature_names
    assert metrics["validation"]["log_loss"] is not None
    assert metrics["validation"]["brier_score"] is not None
    assert "roc_auc" in metrics["validation"]
    assert "pr_auc" in metrics["validation"]
    assert "precision_draw" in metrics["validation"]
    assert "recall_draw" in metrics["validation"]
    assert "actual_draw_rate" in metrics["validation"]
    assert "predicted_draw_rate" in metrics["validation"]
    assert metrics["validation"]["baselines"]["prior_draw_rate"] is not None


def test_draw_risk_predict_proba_is_valid_and_handles_missing_columns(tmp_path) -> None:
    dataset_path = tmp_path / "v3_dataset.csv"
    frame = _synthetic_v3_frame(90)
    frame.to_csv(dataset_path, index=False)
    result = train_draw_risk_from_dataset(dataset_path, tmp_path / "draw_risk")

    inference_frame = frame.drop(columns=["draw_risk_parity_score", "p_market_draw"]).head(8)
    draw_probabilities = result.model.predict_draw_proba(inference_frame)
    matrix = result.model.predict_proba(inference_frame)

    assert len(draw_probabilities) == 8
    assert all(0.0 <= probability <= 1.0 for probability in draw_probabilities)
    assert len(matrix) == 8
    for row in matrix:
        assert len(row) == 2
        assert np.isclose(sum(row), 1.0)
        assert all(0.0 <= probability <= 1.0 for probability in row)


def test_low_volume_calibration_is_skipped_and_recorded(tmp_path) -> None:
    dataset_path = tmp_path / "v3_dataset.csv"
    _synthetic_v3_frame(72).to_csv(dataset_path, index=False)

    result = train_draw_risk_from_dataset(dataset_path, tmp_path / "draw_risk")

    assert result.model.calibration_decision["method"] is None
    assert result.model.calibration_decision["reason"] == "skipped_low_volume"
    assert result.metrics["calibration_decision"]["reason"] == "skipped_low_volume"


def test_joblib_loaded_draw_risk_model_preserves_predictions(tmp_path) -> None:
    dataset_path = tmp_path / "v3_dataset.csv"
    frame = _synthetic_v3_frame(88)
    frame.to_csv(dataset_path, index=False)
    result = train_draw_risk_from_dataset(dataset_path, tmp_path / "draw_risk")

    loaded = joblib.load(result.model_path)
    assert isinstance(loaded, DrawRiskModel)

    sample = frame.tail(6)
    np.testing.assert_allclose(
        loaded.predict_draw_proba(sample),
        result.model.predict_draw_proba(sample),
        rtol=1e-12,
        atol=1e-12,
    )


def _synthetic_v3_frame(row_count: int) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    start = pd.Timestamp("2025-01-01T18:00:00Z")
    for index in range(row_count):
        outcome = "DRAW" if index % 4 == 0 else ("HOME" if index % 2 == 0 else "AWAY")
        is_draw = int(outcome == "DRAW")
        fixture_date = start + pd.Timedelta(days=index)
        draw_signal = 0.68 + (index % 3) * 0.015 if is_draw else 0.14 + (index % 5) * 0.02
        market_draw = min(max(draw_signal - 0.04 + (index % 4) * 0.01, 0.05), 0.85)
        rows.append(
            {
                # Negative fixture IDs are explicit synthetic test-only identifiers.
                "fixture_id": -100_000 - index,
                "fixture_date": fixture_date.isoformat(),
                "prediction_time": (fixture_date - pd.Timedelta(minutes=30)).isoformat(),
                "target": outcome,
                "outcome": outcome,
                "is_draw": is_draw,
                "home_wins": 1 if outcome == "HOME" else 0,
                "home_goals": 1 if outcome != "AWAY" else 0,
                "away_goals": 1 if outcome != "HOME" else 0,
                "draw_risk_score": draw_signal,
                "draw_risk_parity_score": 0.82 if is_draw else 0.22 + (index % 6) * 0.04,
                "draw_risk_low_goal_signal": 0.74 if is_draw else 0.32,
                "market_draw": market_draw,
                "p_market_draw": market_draw,
                "p_market_home": 0.45 if outcome == "HOME" else 0.34,
                "p_market_away": 0.45 if outcome == "AWAY" else 0.34,
                "api_pred_draw": market_draw + 0.01,
                "official_lineup_available_flag": int(index % 3 == 0),
                "lineup_m30_official_available_flag": int(index % 3 == 0),
                "data_quality_score": 0.70 + (index % 10) * 0.02,
                "home_team_form_last5": 0.60 if outcome == "HOME" else 0.44,
                "away_team_form_last5": 0.60 if outcome == "AWAY" else 0.44,
                "payload_json": "{}",
            }
        )
    return pd.DataFrame(rows)
