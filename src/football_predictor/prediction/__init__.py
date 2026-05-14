"""Prediction orchestration exports.

Exports are resolved lazily so importing a prediction submodule does not initialize
Discord delivery or automation modules and create circular imports.
"""

__all__ = [
    "AutomationFixtureResult",
    "AutomationRunConfig",
    "AutomationRunSummary",
    "PredictionAutomationService",
    "PredictionOutput",
    "PredictionRequest",
    "PredictionService",
    "PredictionV3Output",
    "PredictionV3Service",
    "PredictionWindow",
    "DailyFixtureResult",
    "DailyPredictionSummary",
    "DailyPredictionWindow",
    "get_fixtures_to_predict",
    "prediction_time_for_fixture",
    "predict_fixture",
    "run_daily_predictions",
    "run_daily_predictions_v3",
]


def __getattr__(name: str):
    if name in {
        "AutomationFixtureResult",
        "AutomationRunConfig",
        "AutomationRunSummary",
        "PredictionAutomationService",
        "PredictionWindow",
    }:
        from football_predictor.prediction.automation import (
            AutomationFixtureResult,
            AutomationRunConfig,
            AutomationRunSummary,
            PredictionAutomationService,
            PredictionWindow,
        )

        return {
            "AutomationFixtureResult": AutomationFixtureResult,
            "AutomationRunConfig": AutomationRunConfig,
            "AutomationRunSummary": AutomationRunSummary,
            "PredictionAutomationService": PredictionAutomationService,
            "PredictionWindow": PredictionWindow,
        }[name]
    if name == "predict_fixture":
        from football_predictor.prediction.predict_fixture import predict_fixture

        return predict_fixture
    if name in {
        "DailyFixtureResult",
        "DailyPredictionSummary",
        "get_fixtures_to_predict",
        "run_daily_predictions",
        "run_daily_predictions_v3",
    }:
        from football_predictor.prediction.run_daily import (
            DailyFixtureResult,
            DailyPredictionSummary,
            get_fixtures_to_predict,
            run_daily_predictions,
            run_daily_predictions_v3,
        )

        return {
            "DailyFixtureResult": DailyFixtureResult,
            "DailyPredictionSummary": DailyPredictionSummary,
            "get_fixtures_to_predict": get_fixtures_to_predict,
            "run_daily_predictions": run_daily_predictions,
            "run_daily_predictions_v3": run_daily_predictions_v3,
        }[name]
    if name in {"DailyPredictionWindow", "prediction_time_for_fixture"}:
        from football_predictor.prediction.scheduler import (
            DailyPredictionWindow,
            prediction_time_for_fixture,
        )

        return {
            "DailyPredictionWindow": DailyPredictionWindow,
            "prediction_time_for_fixture": prediction_time_for_fixture,
        }[name]
    if name in {"PredictionOutput", "PredictionRequest", "PredictionService"}:
        from football_predictor.prediction.service import (
            PredictionOutput,
            PredictionRequest,
            PredictionService,
        )

        return {
            "PredictionOutput": PredictionOutput,
            "PredictionRequest": PredictionRequest,
            "PredictionService": PredictionService,
        }[name]
    if name in {"PredictionV3Output", "PredictionV3Service"}:
        from football_predictor.prediction.v3_service import (
            PredictionV3Output,
            PredictionV3Service,
        )

        return {
            "PredictionV3Output": PredictionV3Output,
            "PredictionV3Service": PredictionV3Service,
        }[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
