"""V3 multi-model components."""

from football_predictor.modeling.v3.composite import FootballOutcomeV3Model
from football_predictor.modeling.v3.draw_risk_model import (
    DrawRiskModel,
    DrawRiskTrainingConfig,
    DrawRiskTrainResult,
    train_draw_risk_from_dataset,
    train_draw_risk_from_frame,
)
from football_predictor.modeling.v3.no_draw_winner_model import (
    NoDrawWinnerModel,
    NoDrawWinnerTrainingConfig,
    NoDrawWinnerTrainResult,
    train_no_draw_winner_from_dataset,
    train_no_draw_winner_from_frame,
)
from football_predictor.modeling.v3.stacker import (
    V3StackerModel,
    V3StackerTrainingConfig,
    V3StackerTrainResult,
    train_v3_stacker_from_frame,
)
from football_predictor.modeling.v3.training import (
    V3TrainingConfig,
    V3TrainResult,
    train_v3_from_dataset,
)

__all__ = [
    "DrawRiskModel",
    "DrawRiskTrainingConfig",
    "DrawRiskTrainResult",
    "FootballOutcomeV3Model",
    "NoDrawWinnerModel",
    "NoDrawWinnerTrainingConfig",
    "NoDrawWinnerTrainResult",
    "V3StackerModel",
    "V3StackerTrainingConfig",
    "V3StackerTrainResult",
    "V3TrainingConfig",
    "V3TrainResult",
    "train_draw_risk_from_dataset",
    "train_draw_risk_from_frame",
    "train_no_draw_winner_from_dataset",
    "train_no_draw_winner_from_frame",
    "train_v3_from_dataset",
    "train_v3_stacker_from_frame",
]
