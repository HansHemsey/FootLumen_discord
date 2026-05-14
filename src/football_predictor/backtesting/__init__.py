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

_LAZY_EXPORTS = {
    "ProductionLikeBacktestConfig": (
        "football_predictor.backtesting.production_like",
        "ProductionLikeBacktestConfig",
    ),
    "ProductionLikeBacktestResult": (
        "football_predictor.backtesting.production_like",
        "ProductionLikeBacktestResult",
    ),
    "production_like_prediction_time": (
        "football_predictor.backtesting.production_like",
        "production_like_prediction_time",
    ),
    "run_production_like_backtest": (
        "football_predictor.backtesting.production_like",
        "run_production_like_backtest",
    ),
    "SeasonConfidenceBacktestConfig": (
        "football_predictor.backtesting.season_confidence",
        "SeasonConfidenceBacktestConfig",
    ),
    "SeasonConfidenceBacktestResult": (
        "football_predictor.backtesting.season_confidence",
        "SeasonConfidenceBacktestResult",
    ),
    "run_season_confidence_backtest": (
        "football_predictor.backtesting.season_confidence",
        "run_season_confidence_backtest",
    ),
    "V3BacktestConfig": (
        "football_predictor.backtesting.v3_evaluator",
        "V3BacktestConfig",
    ),
    "V3BacktestResult": (
        "football_predictor.backtesting.v3_evaluator",
        "V3BacktestResult",
    ),
    "run_v3_backtest": (
        "football_predictor.backtesting.v3_evaluator",
        "run_v3_backtest",
    ),
}

__all__ = [
    "BacktestConfig",
    "BacktestResult",
    "SplitPeriod",
    "V3BacktestConfig",
    "V3BacktestResult",
    "ProductionLikeBacktestConfig",
    "ProductionLikeBacktestResult",
    "SeasonConfidenceBacktestConfig",
    "SeasonConfidenceBacktestResult",
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
    "production_like_prediction_time",
    "run_backtest",
    "run_production_like_backtest",
    "run_season_confidence_backtest",
    "run_v3_backtest",
    "temporal_split",
]


def __getattr__(name: str) -> object:
    """Load heavy backtesting exports lazily to avoid V3 model import cycles."""
    if name not in _LAZY_EXPORTS:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module_name, attribute_name = _LAZY_EXPORTS[name]
    from importlib import import_module

    value = getattr(import_module(module_name), attribute_name)
    globals()[name] = value
    return value
