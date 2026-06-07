from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pandas as pd  # type: ignore[import-untyped]
import pytest
from typer.testing import CliRunner

from football_predictor.backtesting.evaluator import (
    BacktestConfig,
    compare_models,
    evaluate_predictions,
    run_backtest,
    temporal_split,
)
from football_predictor.backtesting.reports import export_markdown_report, export_metrics_json
from football_predictor.cli import app
from football_predictor.modeling.train import train_model_from_dataset


def test_temporal_split_is_ordered_and_uses_ratios() -> None:
    frame = _synthetic_dataset(30).sample(frac=1.0, random_state=42).reset_index(drop=True)

    train, validation, test = temporal_split(frame, config=BacktestConfig())

    assert len(train) == 18
    assert len(validation) == 6
    assert len(test) == 6
    assert pd.to_datetime(train["fixture_date"], utc=True).max() < pd.to_datetime(
        validation["fixture_date"],
        utc=True,
    ).min()
    assert pd.to_datetime(validation["fixture_date"], utc=True).max() < pd.to_datetime(
        test["fixture_date"],
        utc=True,
    ).min()


def test_run_backtest_baselines_exports_reports_and_leakage_report(tmp_path: Path) -> None:
    dataset_path = tmp_path / "dataset.csv"
    output_dir = tmp_path / "reports"
    _synthetic_dataset(45, missing_api_every=3).to_csv(dataset_path, index=False)

    result = run_backtest(dataset_path, output_dir=output_dir)

    assert result.periods["train"].row_count == 27
    assert result.periods["validation"].row_count == 9
    assert result.periods["test"].row_count == 9
    assert "odds_only" in result.metrics_by_model
    assert "poisson" in result.metrics_by_model
    assert "api_prediction_only" in result.metrics_by_model
    assert "model_final" not in result.metrics_by_model
    assert result.metrics_by_model["api_prediction_only"]["coverage"] < 1.0
    assert result.payload["leakage"]["forbidden_columns_in_features"] == []
    assert "league_id" in result.payload["group_metrics"]["test"]
    assert "season" in result.payload["group_metrics"]["test"]
    assert result.report_paths["json"].exists()
    assert result.report_paths["markdown"].exists()
    parsed = json.loads(result.report_paths["json"].read_text(encoding="utf-8"))
    assert parsed["periods"]["test"]["row_count"] == 9
    assert "Backtest FootLumen" in result.report_paths["markdown"].read_text(
        encoding="utf-8"
    )
    assert "confidence_bucket" in result.payload["group_metrics"]["test"]
    assert "data_quality_bucket" in result.payload["group_metrics"]["test"]


def test_run_backtest_with_model_and_stacking_comparisons(tmp_path: Path) -> None:
    dataset_path = tmp_path / "dataset.csv"
    model_dir = tmp_path / "model"
    output_dir = tmp_path / "reports"
    frame = _synthetic_dataset(60)
    frame.to_csv(dataset_path, index=False)
    train_model_from_dataset(dataset_path, model_dir, model_version="synthetic-backtest")

    result = run_backtest(dataset_path, model_dir=model_dir, output_dir=output_dir)

    assert "model_final" in result.metrics_by_model
    assert "stacking_final" in result.metrics_by_model
    assert result.metrics_by_model["model_final"]["coverage"] == pytest.approx(1.0)
    assert result.metrics_by_model["stacking_final"]["coverage"] == pytest.approx(1.0)
    assert "odds_only" in result.payload["comparisons"]["test"]
    assert result.payload["group_metrics"]["test"]["league_id"]
    assert result.report_paths["json"].exists()


def test_backtest_cli_runs_on_synthetic_dataset_and_model(tmp_path: Path) -> None:
    dataset_path = tmp_path / "dataset.csv"
    model_dir = tmp_path / "model"
    output_dir = tmp_path / "reports"
    _synthetic_dataset(45).to_csv(dataset_path, index=False)
    train_model_from_dataset(dataset_path, model_dir, model_version="cli-backtest")

    result = CliRunner().invoke(
        app,
        [
            "backtest",
            "--dataset",
            str(dataset_path),
            "--model-dir",
            str(model_dir),
            "--output-dir",
            str(output_dir),
            "--format",
            "both",
        ],
    )

    assert result.exit_code == 0, result.stdout
    assert (output_dir / "backtest_report.json").exists()
    assert (output_dir / "backtest_report.md").exists()
    assert "model_final" in result.stdout


def test_backtest_requires_fixture_date_and_target(tmp_path: Path) -> None:
    dataset_path = tmp_path / "bad.csv"
    pd.DataFrame([{"feature": 1.0, "target": "HOME"}]).to_csv(dataset_path, index=False)

    with pytest.raises(ValueError, match="fixture_date"):
        run_backtest(dataset_path, output_dir=tmp_path / "reports")


def test_evaluate_predictions_returns_core_metrics() -> None:
    frame = pd.DataFrame(
        [
            {"target": "HOME", "p_home": 0.70, "p_draw": 0.20, "p_away": 0.10},
            {"target": "DRAW", "p_home": 0.20, "p_draw": 0.60, "p_away": 0.20},
            {"target": "AWAY", "p_home": 0.20, "p_draw": 0.30, "p_away": 0.50},
        ]
    )

    metrics = evaluate_predictions(
        frame,
        frame["target"],
        ("p_home", "p_draw", "p_away"),
        n_bins=4,
    )

    assert metrics["row_count"] == 3
    assert metrics["accuracy"] == pytest.approx(1.0)
    assert metrics["log_loss"] >= 0.0
    assert 0.0 <= metrics["brier_score"] <= 2.0
    assert metrics["avg_confidence_gap"] > 0.0
    assert len(metrics["calibration_bins"]) == 4


def test_compare_models_includes_requested_baselines_and_final_columns() -> None:
    frame = _synthetic_dataset(12)
    frame["final_home"] = frame["p_market_home"]
    frame["final_draw"] = frame["p_market_draw"]
    frame["final_away"] = frame["p_market_away"]

    metrics = compare_models(
        frame,
        final_model_columns=("final_home", "final_draw", "final_away"),
    )

    assert set(metrics) == {"odds_only", "poisson", "api_prediction", "final_model"}
    assert metrics["final_model"]["coverage"] == pytest.approx(1.0)
    assert metrics["odds_only"]["row_count"] == 12


def test_report_exporters_write_json_and_markdown(tmp_path: Path) -> None:
    payload = {
        "dataset_path": "synthetic.csv",
        "model_dir": "synthetic-model",
        "generated_at": "2099-01-01T00:00:00+00:00",
        "periods": {
            "test": {
                "row_count": 3,
                "start": "2099-01-01T00:00:00+00:00",
                "end": "2099-01-03T00:00:00+00:00",
            }
        },
        "metrics": {
            "test": {
                "odds_only": {
                    "row_count": 3,
                    "coverage": 1.0,
                    "accuracy": 0.67,
                    "log_loss": 0.8,
                    "brier_score": 0.4,
                    "calibration_bins": [],
                    "confidence_thresholds": [],
                }
            }
        },
        "group_metrics": {
            "test": {
                "league_id": {"synthetic": {"row_count": 3, "metrics": {"odds_only": {}}}},
                "data_quality_bucket": {"low_<40": {"row_count": 1, "metrics": {}}},
            }
        },
    }

    json_path = export_metrics_json(payload, tmp_path / "metrics.json")
    markdown_path = export_markdown_report(payload, tmp_path / "report.md")

    assert json.loads(json_path.read_text(encoding="utf-8"))["dataset_path"] == "synthetic.csv"
    markdown = markdown_path.read_text(encoding="utf-8")
    assert "Résumé Global" in markdown
    assert "Performance Par Ligue" in markdown
    assert "Avertissement Qualité Des Données" in markdown


def _synthetic_dataset(row_count: int, *, missing_api_every: int | None = None) -> pd.DataFrame:
    labels = ["HOME", "DRAW", "AWAY"]
    rows: list[dict[str, object]] = []
    start = datetime(2099, 1, 1, 12, tzinfo=UTC)
    for index in range(row_count):
        target = labels[index % len(labels)]
        league_id = -1 if index % 2 == 0 else -2
        api_missing = missing_api_every is not None and index % missing_api_every == 0
        fixture_date = start + timedelta(days=index)
        prediction_time = fixture_date - timedelta(hours=12)
        rows.append(
            {
                "target": target,
                "fixture_id": -10_000 - index,
                "target_fixture_id": -20_000 - index,
                "feature_snapshot_id": index,
                "league_id": league_id,
                "season": 2099 + (index % 2),
                "home_team_id": -100,
                "away_team_id": -200,
                "home_goals": 2 if target == "HOME" else 1,
                "away_goals": 2 if target == "AWAY" else 1,
                "status_short": "FT",
                "fixture_date": fixture_date.isoformat(),
                "prediction_time": prediction_time.isoformat(),
                "home_team_global_goals_for_avg_last10": 2.2
                if target == "HOME"
                else 0.9,
                "away_team_global_goals_for_avg_last10": 2.2
                if target == "AWAY"
                else 0.9,
                "home_team_global_goals_against_avg_last10": 0.8
                if target == "HOME"
                else 1.5,
                "away_team_global_goals_against_avg_last10": 0.8
                if target == "AWAY"
                else 1.5,
                "draw_signal": 1.0 if target == "DRAW" else 0.0,
                "p_market_home": 0.62 if target == "HOME" else 0.22,
                "p_market_draw": 0.58 if target == "DRAW" else 0.20,
                "p_market_away": 0.62 if target == "AWAY" else 0.22,
                "api_pred_home": None if api_missing else 0.60 if target == "HOME" else 0.20,
                "api_pred_draw": None if api_missing else 0.56 if target == "DRAW" else 0.22,
                "api_pred_away": None if api_missing else 0.60 if target == "AWAY" else 0.20,
                "overall_data_quality_score": 35.0 if index % 5 == 0 else 82.0,
                "home_team_expected_xi_json": "[]",
                "payload_json": "{}",
            }
        )
    return pd.DataFrame(rows)
