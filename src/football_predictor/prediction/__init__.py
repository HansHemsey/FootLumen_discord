"""Prediction orchestration."""

from football_predictor.prediction.automation import (
    AutomationFixtureResult,
    AutomationRunConfig,
    AutomationRunSummary,
    PredictionAutomationService,
    PredictionWindow,
)
from football_predictor.prediction.predict_fixture import predict_fixture
from football_predictor.prediction.run_daily import (
    DailyFixtureResult,
    DailyPredictionSummary,
    get_fixtures_to_predict,
    run_daily_predictions,
)
from football_predictor.prediction.scheduler import (
    DailyPredictionWindow,
    prediction_time_for_fixture,
)
from football_predictor.prediction.service import (
    PredictionOutput,
    PredictionRequest,
    PredictionService,
)

__all__ = [
    "AutomationFixtureResult",
    "AutomationRunConfig",
    "AutomationRunSummary",
    "PredictionAutomationService",
    "PredictionOutput",
    "PredictionRequest",
    "PredictionService",
    "PredictionWindow",
    "DailyFixtureResult",
    "DailyPredictionSummary",
    "DailyPredictionWindow",
    "get_fixtures_to_predict",
    "prediction_time_for_fixture",
    "predict_fixture",
    "run_daily_predictions",
]
