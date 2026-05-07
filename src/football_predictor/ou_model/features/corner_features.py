"""Corner intensity features for O/U 2.5 prediction."""

from __future__ import annotations

from typing import Any

JsonDict = dict[str, Any]

_WINDOWS = (5, 10)


def build_combined_corner_features(base_features: JsonDict) -> JsonDict:
    """Combine corner averages from both teams into match-level signals."""
    features: JsonDict = {}
    for window in _WINDOWS:
        home_corners = base_features.get(f"home_team_global_corners_for_avg_last{window}")
        away_corners = base_features.get(f"away_team_global_corners_for_avg_last{window}")
        if home_corners is not None and away_corners is not None:
            features[f"combined_corners_avg_last{window}"] = home_corners + away_corners
        else:
            features[f"combined_corners_avg_last{window}"] = None
    return features
