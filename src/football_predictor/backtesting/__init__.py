"""Backtesting helpers."""

from football_predictor.backtesting.dataset import (
    build_training_dataset,
    export_dataset,
    parse_prediction_window,
)
from football_predictor.backtesting.dataset_builder import (
    build_training_dataset as build_training_dataset_v1,
)
from football_predictor.backtesting.dataset_builder import (
    create_time_based_split,
)
from football_predictor.backtesting.evaluator import (
    BacktestConfig,
    BacktestResult,
    SplitPeriod,
    compare_models,
    evaluate_predictions,
    run_backtest,
    temporal_split,
)
from football_predictor.backtesting.reports import export_markdown_report, export_metrics_json
from football_predictor.backtesting.v3_dataset_builder import (
    build_v3_draw_risk_dataset,
    build_v3_no_draw_winner_dataset,
    build_v3_stacker_dataset,
)
from football_predictor.backtesting.v3_evaluator import (
    V3BacktestConfig,
    V3BacktestResult,
    run_v3_backtest,
)

__all__ = [
    "BacktestConfig",
    "BacktestResult",
    "SplitPeriod",
    "V3BacktestConfig",
    "V3BacktestResult",
    "compare_models",
    "build_training_dataset",
    "build_training_dataset_v1",
    "build_v3_draw_risk_dataset",
    "build_v3_no_draw_winner_dataset",
    "build_v3_stacker_dataset",
    "create_time_based_split",
    "evaluate_predictions",
    "export_dataset",
    "export_markdown_report",
    "export_metrics_json",
    "parse_prediction_window",
    "run_backtest",
    "run_v3_backtest",
    "temporal_split",
]
