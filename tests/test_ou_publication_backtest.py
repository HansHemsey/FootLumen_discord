from __future__ import annotations

from pathlib import Path

import pandas as pd

from football_predictor.ou_model.backtesting.ou_evaluator import _fold_splits
from football_predictor.ou_model.backtesting.ou_metrics import expected_calibration_error
from football_predictor.ou_model.backtesting.ou_publication_backtest import (
    EDGE_BUCKETS,
    EV_BUCKETS,
    OUPublicationBacktestConfig,
    build_publication_summary,
    calibration_report_frame,
    evaluate_ou_publication_rows,
    publication_policy_grid_frame,
    recommend_publication_policy,
    roi_by_bucket_frame,
)
from football_predictor.ou_model.backtesting.ou_report_writer import (
    write_ou_v2_backtest_reports,
)


def test_ece_and_calibration_bins_include_model_and_market() -> None:
    frame = evaluate_ou_publication_rows(_rows())
    calibration = calibration_report_frame(frame)

    assert set(calibration["source"]) == {"model", "market"}
    assert calibration[calibration["source"] == "model"]["count"].sum() == len(frame)
    assert expected_calibration_error(
        calibration[calibration["source"] == "model"].to_dict("records")
    ) >= 0


def test_roi_by_edge_and_ev_bucket() -> None:
    frame = evaluate_ou_publication_rows(_rows())

    by_edge = roi_by_bucket_frame(frame, "edge_bucket", EDGE_BUCKETS)
    by_ev = roi_by_bucket_frame(frame, "ev_bucket", EV_BUCKETS)

    assert set(by_edge["bucket"]) == {"0-2 pts", "2-4 pts", "4-6 pts", "6+ pts"}
    assert set(by_ev["bucket"]) == {"0-2 %", "2-4 %", "4-8 %", "8+ %"}
    assert by_edge["total_bets"].sum() >= 1
    assert by_ev["profit_units"].notna().all()


def test_policy_grid_produces_expected_combinations_and_excludes_negative_ev() -> None:
    frame = evaluate_ou_publication_rows(_rows())
    config = OUPublicationBacktestConfig(min_recommended_bets=1)
    grid = publication_policy_grid_frame(frame, config)

    assert len(grid) == 4 * 3 * 4 * 3
    strict = grid[
        (grid["min_edge"] == 0.05)
        & (grid["min_ev"] == 0.05)
        & (grid["min_confidence"] == 70)
        & (grid["min_data_quality"] == 80)
    ].iloc[0]
    assert strict["total_bets"] == 2
    assert pd.isna(frame[frame["fixture_id"] == -3].iloc[0]["value_side"])


def test_missing_market_and_missing_closing_odds_do_not_crash(tmp_path: Path) -> None:
    frame = evaluate_ou_publication_rows([
        {
            "fold": 1,
            "fixture_id": -10,
            "fixture_date": "2026-05-01",
            "target_ou25": 1,
            "p_over": 0.70,
            "p_under": 0.30,
            "market_p_over": None,
            "market_p_under": None,
            "odd_over": None,
            "odd_under": None,
            "data_quality_score": 90,
            "bookmaker_count": None,
        }
    ])
    calibration = calibration_report_frame(frame)
    grid = publication_policy_grid_frame(frame, OUPublicationBacktestConfig(min_recommended_bets=1))
    summary = build_publication_summary(
        frame,
        calibration,
        grid,
        dataset_path=Path("synthetic.parquet"),
        n_folds=1,
        aggregate_backtest={},
        config=OUPublicationBacktestConfig(min_recommended_bets=1),
    )

    assert frame.iloc[0]["publication_decision"] == "no_bet"
    assert summary["closing_line_value"]["closing_odds_coverage"] == 0.0
    assert summary["closing_line_value"]["model_over_clv"] is None

    outputs = write_ou_v2_backtest_reports(
        output_dir=tmp_path,
        summary=summary,
        roi_by_edge_bucket=roi_by_bucket_frame(frame, "edge_bucket", EDGE_BUCKETS),
        roi_by_ev_bucket=roi_by_bucket_frame(frame, "ev_bucket", EV_BUCKETS),
        calibration_bins=calibration,
        publication_policy_grid=grid,
    )
    assert outputs["markdown"].exists()
    assert "Recommandation" in outputs["markdown"].read_text(encoding="utf-8")


def test_recommendation_selects_positive_roi_policy_with_volume() -> None:
    grid = pd.DataFrame([
        {
            "min_edge": 0.03,
            "min_ev": 0.03,
            "min_confidence": 65,
            "min_data_quality": 70,
            "min_bookmaker_count": 2,
            "total_bets": 3,
            "roi": 0.10,
            "profit_units": 0.3,
            "max_drawdown_units": 1.0,
        },
        {
            "min_edge": 0.04,
            "min_ev": 0.05,
            "min_confidence": 70,
            "min_data_quality": 80,
            "min_bookmaker_count": 2,
            "total_bets": 0,
            "roi": 0.0,
            "profit_units": 0.0,
            "max_drawdown_units": 0.0,
        },
    ])

    recommendation = recommend_publication_policy(grid, min_recommended_bets=1)

    assert recommendation["decision"] == "public"
    assert recommendation["min_edge"] == 0.03


def test_fold_splits_are_chronological() -> None:
    frame = pd.DataFrame({
        "fixture_date": pd.date_range("2026-01-01", periods=12, freq="D").astype(str),
        "target_ou25": [0, 1] * 6,
    })

    splits = _fold_splits(frame, n_splits=2, min_train_rows=3)

    assert splits
    for train, test in splits:
        assert train["fixture_date"].max() < test["fixture_date"].min()


def _rows() -> list[dict[str, object]]:
    return [
        {
            "fold": 1,
            "fixture_id": -1,
            "fixture_date": "2026-05-01",
            "league_id": -100,
            "season": 2026,
            "target_ou25": 1,
            "p_over": 0.64,
            "p_under": 0.36,
            "market_p_over": 0.56,
            "market_p_under": 0.44,
            "odd_over": 1.75,
            "odd_under": 2.10,
            "data_quality_score": 90,
            "bookmaker_count": 4,
        },
        {
            "fold": 1,
            "fixture_id": -2,
            "fixture_date": "2026-05-02",
            "league_id": -100,
            "season": 2026,
            "target_ou25": 0,
            "p_over": 0.54,
            "p_under": 0.46,
            "market_p_over": 0.63,
            "market_p_under": 0.37,
            "odd_over": 1.50,
            "odd_under": 2.45,
            "data_quality_score": 90,
            "bookmaker_count": 6,
        },
        {
            "fold": 1,
            "fixture_id": -3,
            "fixture_date": "2026-05-03",
            "league_id": -200,
            "season": 2026,
            "target_ou25": 1,
            "p_over": 0.52,
            "p_under": 0.48,
            "market_p_over": 0.60,
            "market_p_under": 0.40,
            "odd_over": 2.05,
            "odd_under": 1.80,
            "data_quality_score": 90,
            "bookmaker_count": 3,
        },
    ]
