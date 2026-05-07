"""Shot intensity features for O/U 2.5 prediction.

Combines shot metrics from both teams to estimate match tempo/goal pace.
"""

from __future__ import annotations

from typing import Any

JsonDict = dict[str, Any]

_WINDOWS = (5, 10)


def build_combined_shot_features(base_features: JsonDict) -> JsonDict:
    """Build combined shot intensity features from existing 1X2 base features.

    Reads already-computed per-team shot averages and creates match-level combined signals.
    """
    features: JsonDict = {}
    for window in _WINDOWS:
        home_shots = base_features.get(f"home_team_global_shots_for_avg_last{window}")
        away_shots = base_features.get(f"away_team_global_shots_for_avg_last{window}")
        if home_shots is not None and away_shots is not None:
            features[f"combined_shots_avg_last{window}"] = home_shots + away_shots
        else:
            features[f"combined_shots_avg_last{window}"] = None

        home_sog = base_features.get(f"home_team_global_shots_on_goal_for_avg_last{window}")
        away_sog = base_features.get(f"away_team_global_shots_on_goal_for_avg_last{window}")
        if home_sog is not None and away_sog is not None:
            features[f"combined_shots_on_goal_avg_last{window}"] = home_sog + away_sog
        else:
            features[f"combined_shots_on_goal_avg_last{window}"] = None

        home_xg = base_features.get(f"home_team_global_pseudo_xg_for_avg_last{window}")
        away_xg = base_features.get(f"away_team_global_pseudo_xg_for_avg_last{window}")
        if home_xg is not None and away_xg is not None:
            features[f"combined_pseudo_xg_total_avg_last{window}"] = home_xg + away_xg
        else:
            features[f"combined_pseudo_xg_total_avg_last{window}"] = None
    return features
