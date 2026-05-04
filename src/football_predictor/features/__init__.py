"""Feature builders and point-in-time safeguards."""

from football_predictor.features.feature_builder import (
    FeatureBuilderResult,
)
from football_predictor.features.feature_builder import (
    build_feature_snapshot as build_feature_snapshot_v1,
)
from football_predictor.features.global_features import (
    GlobalFeatureConfig,
    GlobalFeatureResult,
    build_feature_snapshot,
    build_global_features,
)
from football_predictor.features.team_features import (
    TeamFeatureConfig,
    TeamFeatureResult,
    build_team_features,
    save_team_feature_snapshot,
)
from football_predictor.features.xi_features import (
    PlayerXIConfig,
    PlayerXIResult,
    build_expected_xi,
    build_player_xi_features,
    compute_start_probability,
    infer_probable_formation,
    save_player_xi_feature_snapshot,
    xi_stability_features,
)

__all__ = [
    "GlobalFeatureConfig",
    "GlobalFeatureResult",
    "FeatureBuilderResult",
    "PlayerXIConfig",
    "PlayerXIResult",
    "TeamFeatureConfig",
    "TeamFeatureResult",
    "build_expected_xi",
    "build_feature_snapshot",
    "build_feature_snapshot_v1",
    "build_global_features",
    "build_player_xi_features",
    "build_team_features",
    "compute_start_probability",
    "infer_probable_formation",
    "save_player_xi_feature_snapshot",
    "save_team_feature_snapshot",
    "xi_stability_features",
]
