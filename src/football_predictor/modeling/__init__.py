"""Modeling helpers."""

from football_predictor.modeling.artifacts import ModelArtifact, load_model_artifact
from football_predictor.modeling.baselines import (
    api_prediction_predict,
    api_prediction_probability,
    fallback_prior,
    odds_only_predict,
    odds_only_probability,
    uniform_predict,
)
from football_predictor.modeling.constants import CLASSES
from football_predictor.modeling.multiclass_model import FootballOutcomeModel
from football_predictor.modeling.poisson import (
    estimate_lambda_home_away,
    poisson_baseline_probability,
    poisson_predict,
    score_matrix,
)
from football_predictor.modeling.poisson_v2 import (
    estimate_lambda_home_away_v2,
    poisson_v2_predict,
)
from football_predictor.modeling.preprocessing import (
    PreprocessedDataset,
    features_dict_to_dataframe,
    separate_metadata_target_features,
)
from football_predictor.modeling.probabilities import ProbabilityTriple
from football_predictor.modeling.sport_model import (
    ModelTrainingConfig,
    TrainedSportModel,
    predict_sport_probabilities,
    select_safe_feature_columns,
    train_sport_model,
)
from football_predictor.modeling.stacking import (
    StackingResult,
    StackingWeights,
    stack_probabilities,
    stack_probabilities_with_details,
)
from football_predictor.modeling.train import TrainModelResult, train_model_from_dataset
from football_predictor.modeling.training import train_model_artifact
from football_predictor.modeling.v2_model import FootballOutcomeV2Model, V2TrainingConfig

__all__ = [
    "CLASSES",
    "FootballOutcomeModel",
    "FootballOutcomeV2Model",
    "ModelArtifact",
    "ModelTrainingConfig",
    "PreprocessedDataset",
    "ProbabilityTriple",
    "StackingResult",
    "StackingWeights",
    "TrainModelResult",
    "TrainedSportModel",
    "api_prediction_probability",
    "api_prediction_predict",
    "estimate_lambda_home_away",
    "estimate_lambda_home_away_v2",
    "fallback_prior",
    "features_dict_to_dataframe",
    "load_model_artifact",
    "odds_only_probability",
    "odds_only_predict",
    "poisson_baseline_probability",
    "poisson_predict",
    "poisson_v2_predict",
    "predict_sport_probabilities",
    "score_matrix",
    "select_safe_feature_columns",
    "separate_metadata_target_features",
    "stack_probabilities",
    "stack_probabilities_with_details",
    "train_model_from_dataset",
    "train_model_artifact",
    "train_sport_model",
    "uniform_predict",
    "V2TrainingConfig",
]
