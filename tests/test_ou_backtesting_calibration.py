from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from football_predictor.ou_model.backtesting.ou_evaluator import (
    OUBacktestConfig,
    run_ou_backtest,
)


def test_ou_backtest_writes_confidence_threshold_artifact(
    tmp_path: Path,
    monkeypatch,
) -> None:
    dataset_path = tmp_path / "ou_dataset.csv"
    output_dir = tmp_path / "reports"
    _synthetic_ou_frame(18).to_csv(dataset_path, index=False)

    monkeypatch.setattr(
        "football_predictor.ou_model.backtesting.ou_evaluator.select_ou_feature_names",
        lambda *_args, **_kwargs: ["signal"],
    )
    monkeypatch.setattr(
        "football_predictor.ou_model.backtesting.ou_evaluator.train_ou_model_from_frames",
        lambda **_kwargs: (_FakeOUModel(), {}),
    )

    result = run_ou_backtest(
        dataset_path,
        output_dir=output_dir,
        config=OUBacktestConfig(n_splits=1, min_train_rows=6),
    )

    assert result.confidence_thresholds["model_family"] == "ou25"
    assert result.aggregate["confidence_thresholds"]["fold_count"] == 1
    assert result.aggregate["published_only"]["fold_count"] == 1
    assert (output_dir / "confidence_thresholds.json").exists()
    assert (output_dir / "backtest_results.json").exists()
    assert (output_dir / "published_only_report.json").exists()
    assert (output_dir / "published_only_report.md").exists()
    report = json.loads((output_dir / "published_only_report.json").read_text())
    assert report["folds"][0]["scopes"]["published_only"]["ensemble"]["row_count"] <= (
        report["folds"][0]["scopes"]["internal_all"]["ensemble"]["row_count"]
    )
    assert "market" in report["folds"][0]["scopes"]["published_only"]
    assert "confidence_label" in report["folds"][0]["groups"]
    assert "data_quality" in report["folds"][0]["groups"]


class _FakeOUModel:
    model_version = "synthetic-ou"

    def predict_proba_over(self, frame: pd.DataFrame) -> list[float]:
        return [float(value) for value in frame["signal"].tolist()]

    def expert_probabilities_for_row(self, row: pd.Series) -> dict[str, float]:
        value = float(row.get("signal", 0.5))
        return {
            "poisson": value,
            "logistic": value,
            "lgbm": value,
            "xgb": value,
            "catboost": value,
        }


def _synthetic_ou_frame(row_count: int) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    start = pd.Timestamp("2025-01-01T18:00:00Z")
    for index in range(row_count):
        target = int(index % 2 == 0)
        signal = 0.82 if target else 0.18
        rows.append(
            {
                "fixture_id": -800_000 - index,
                "fixture_date": (start + pd.Timedelta(days=index)).isoformat(),
                "league_id": -25,
                "season": 2026,
                "target_ou25": target,
                "signal": signal,
                "ou_market_odd_over": 2.2 if target else 1.8,
                "ou_market_odd_under": 1.8 if target else 2.2,
                "publication_data_quality_score": 85,
            }
        )
    return pd.DataFrame(rows)
