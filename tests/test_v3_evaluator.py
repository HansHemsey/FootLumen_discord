from __future__ import annotations

import json
from pathlib import Path

import pandas as pd  # type: ignore[import-untyped]
import pytest
from typer.testing import CliRunner

from football_predictor.backtesting.v3_evaluator import (
    V3BacktestConfig,
    run_v3_backtest,
)
from football_predictor.cli import app


def test_run_v3_backtest_retrains_and_writes_comparison_reports(tmp_path: Path) -> None:
    dataset_path = tmp_path / "v3_dataset.csv"
    model_dir = tmp_path / "models" / "v3"
    report_dir = tmp_path / "reports"
    _synthetic_v3_backtest_frame(240, include_v2=True).to_csv(dataset_path, index=False)

    result = run_v3_backtest(
        dataset_path,
        model_dir,
        output_dir=report_dir,
        config=V3BacktestConfig(retrain_v3=True),
    )

    assert result.periods["train"].row_count == 144
    assert result.periods["validation"].row_count == 48
    assert result.periods["test"].row_count == 48
    assert result.report_paths["json"].exists()
    assert result.report_paths["markdown"].exists()
    assert result.report_paths["markdown"].name == "comparison_vs_v2.md"

    metrics = result.metrics_by_model
    assert {
        "odds_only",
        "api_prediction_only",
        "poisson_baseline",
        "v2_existing",
        "v3_draw_risk_only",
        "v3_no_draw_winner_only",
        "v3_deterministic_fusion",
        "v3_stacker_full",
        "v3_blend_v2",
    }.issubset(metrics)
    assert metrics["v3_stacker_full"]["available"] is True
    assert metrics["v3_stacker_full"]["coverage"] == pytest.approx(1.0)
    assert metrics["v3_stacker_full"]["log_loss"] >= 0.0
    assert metrics["v3_stacker_full"]["brier_score"] >= 0.0
    assert "draw_metrics" in metrics["v3_stacker_full"]
    assert "draw_precision" in metrics["v3_stacker_full"]
    assert "draw_recall" in metrics["v3_stacker_full"]
    assert "draw_f1" in metrics["v3_stacker_full"]
    assert "observed_draw_rate" in metrics["v3_stacker_full"]
    assert "mean_predicted_p_draw" in metrics["v3_stacker_full"]
    assert "draw_calibration_bins" in metrics["v3_stacker_full"]
    assert "confusion_matrix_labeled" in metrics["v3_stacker_full"]
    assert metrics["v3_stacker_full"]["confusion_matrix_labeled"]["labels"] == [
        "HOME",
        "DRAW",
        "AWAY",
    ]
    assert "no_draw_metrics" in metrics["v3_stacker_full"]
    assert metrics["v2_existing"]["available"] is True
    assert result.success_criteria["status"] in {"passed", "failed"}
    assert "league_id" in result.group_metrics["test"]
    assert "data_quality_score_bin" in result.group_metrics["test"]
    assert "confidence_label" in result.group_metrics["test"]

    parsed = json.loads(result.report_paths["json"].read_text(encoding="utf-8"))
    assert parsed["success_criteria"]["status"] == result.success_criteria["status"]
    markdown = result.report_paths["markdown"].read_text(encoding="utf-8")
    assert "Backtest V3 - Comparaison" in markdown
    assert "v3_stacker_full" in markdown


def test_v3_success_criteria_are_not_evaluable_without_v2_signal(tmp_path: Path) -> None:
    dataset_path = tmp_path / "v3_dataset.csv"
    model_dir = tmp_path / "models" / "v3"
    _synthetic_v3_backtest_frame(180, include_v2=False).to_csv(dataset_path, index=False)

    result = run_v3_backtest(
        dataset_path,
        model_dir,
        output_dir=tmp_path / "reports",
        config=V3BacktestConfig(retrain_v3=True),
    )

    assert result.metrics_by_model["v2_existing"]["available"] is False
    assert result.success_criteria["status"] == "not_evaluable"
    assert "No V2 baseline available" in result.success_criteria["reason"]


def test_v3_backtest_requires_artifacts_when_retrain_is_disabled(tmp_path: Path) -> None:
    dataset_path = tmp_path / "v3_dataset.csv"
    _synthetic_v3_backtest_frame(90, include_v2=True).to_csv(dataset_path, index=False)

    with pytest.raises(ValueError, match="Train with train-v3"):
        run_v3_backtest(
            dataset_path,
            tmp_path / "missing-v3",
            output_dir=tmp_path / "reports",
            config=V3BacktestConfig(retrain_v3=False),
        )


def test_backtest_v3_cli_smoke_runs_on_synthetic_dataset(tmp_path: Path) -> None:
    dataset_path = tmp_path / "v3_dataset.csv"
    model_dir = tmp_path / "models" / "v3"
    report_dir = tmp_path / "reports"
    _synthetic_v3_backtest_frame(150, include_v2=True).to_csv(dataset_path, index=False)

    result = CliRunner().invoke(
        app,
        [
            "backtest-v3",
            "--dataset",
            str(dataset_path),
            "--model-dir",
            str(model_dir),
            "--output-dir",
            str(report_dir),
            "--retrain-v3",
        ],
    )

    assert result.exit_code == 0, result.stdout
    assert (report_dir / "v3_backtest_report.json").exists()
    assert (report_dir / "comparison_vs_v2.md").exists()
    assert "v3_log_loss" in result.stdout


def _synthetic_v3_backtest_frame(row_count: int, *, include_v2: bool) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    start = pd.Timestamp("2025-01-01T18:00:00Z")
    for index in range(row_count):
        outcome = ["HOME", "DRAW", "AWAY"][index % 3]
        fixture_date = start + pd.Timedelta(days=index)
        is_draw = outcome == "DRAW"
        home_edge = 0.72 if outcome == "HOME" else (-0.72 if outcome == "AWAY" else 0.0)
        draw_signal = 0.70 if is_draw else 0.17 + (index % 5) * 0.01
        market_home = 0.55 if outcome == "HOME" else (0.24 if outcome == "AWAY" else 0.34)
        market_draw = 0.53 if outcome == "DRAW" else 0.22
        market_away = 0.55 if outcome == "AWAY" else (0.24 if outcome == "HOME" else 0.34)
        row: dict[str, object] = {
            # Negative fixture and league IDs are explicit synthetic test-only identifiers.
            "fixture_id": -700_000 - index,
            "fixture_date": fixture_date.isoformat(),
            "prediction_time": (fixture_date - pd.Timedelta(minutes=30)).isoformat(),
            "league_id": -10_000 - (index % 2),
            "season": 2024 + (index % 2),
            "target": outcome,
            "outcome": outcome,
            "home_goals": 2 if outcome == "HOME" else (1 if outcome == "DRAW" else 0),
            "away_goals": 2 if outcome == "AWAY" else (1 if outcome == "DRAW" else 0),
            "draw_risk_score": draw_signal,
            "draw_risk_parity_score": 0.76 if is_draw else 0.22,
            "draw_risk_low_goal_signal": 0.72 if is_draw else 0.28,
            "draw_risk_market_draw_prob": market_draw,
            "ndw_home_away_strength_edge": home_edge,
            "ndw_attack_defense_edge": home_edge * 0.80,
            "ndw_home_advantage_edge": 0.20 if outcome == "HOME" else -0.08,
            "ndw_xi_value_edge": home_edge * 1.10,
            "ndw_absence_impact_edge": 0.20 if outcome == "HOME" else -0.20,
            "ndw_odds_home_prob": market_home / (market_home + market_away),
            "p_market_home": market_home,
            "p_market_draw": market_draw,
            "p_market_away": market_away,
            "market_home": market_home,
            "market_draw": market_draw,
            "market_away": market_away,
            "p_api_home": market_home,
            "p_api_draw": market_draw,
            "p_api_away": market_away,
            "api_pred_home": market_home,
            "api_pred_draw": market_draw,
            "api_pred_away": market_away,
            "market_overround": 0.05,
            "market_dispersion": 0.03,
            "official_lineup_available_flag": int(index % 2 == 0),
            "lineup_m30_official_available_flag": int(index % 2 == 0),
            "home_team_absence_impact_score": 0.12 if outcome == "HOME" else 0.30,
            "away_team_absence_impact_score": 0.30 if outcome == "HOME" else 0.12,
            "data_quality_score": 0.55 + (index % 10) * 0.045,
            "home_team_form_last5": 0.66 if outcome == "HOME" else 0.36,
            "away_team_form_last5": 0.66 if outcome == "AWAY" else 0.36,
            "home_team_global_goals_for_avg_last10": 1.8 if outcome == "HOME" else 1.0,
            "away_team_global_goals_for_avg_last10": 1.8 if outcome == "AWAY" else 1.0,
            "home_team_global_goals_against_avg_last10": 0.9 if outcome == "HOME" else 1.5,
            "away_team_global_goals_against_avg_last10": 0.9 if outcome == "AWAY" else 1.5,
            "payload_json": "{}",
        }
        if include_v2:
            p_v2_home = 0.52 if outcome == "HOME" else (0.24 if outcome == "AWAY" else 0.33)
            p_v2_away = 0.52 if outcome == "AWAY" else (0.24 if outcome == "HOME" else 0.34)
            row.update(
                {
                    "p_v2_home": p_v2_home,
                    "p_v2_draw": 0.49 if outcome == "DRAW" else 0.24,
                    "p_v2_away": p_v2_away,
                }
            )
        rows.append(row)
    return pd.DataFrame(rows)
