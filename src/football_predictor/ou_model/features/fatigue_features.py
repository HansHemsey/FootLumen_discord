"""Fatigue features for O/U 2.5 prediction."""

from __future__ import annotations

from typing import Any

JsonDict = dict[str, Any]


def build_fatigue_features(base_features: JsonDict) -> JsonDict:
    """Build fatigue and load features from existing 1X2 base features."""
    features: JsonDict = {}
    home_rest = base_features.get("home_team_rest_days") or base_features.get("rest_days_home")
    away_rest = base_features.get("away_team_rest_days") or base_features.get("rest_days_away")
    if home_rest is not None and away_rest is not None:
        features["rest_days_diff"] = float(home_rest) - float(away_rest)
    else:
        features["rest_days_diff"] = None

    home_load = base_features.get("home_team_matches_last_14_days") or base_features.get(
        "matches_last_14_days_home"
    )
    away_load = base_features.get("away_team_matches_last_14_days") or base_features.get(
        "matches_last_14_days_away"
    )
    if home_load is not None and away_load is not None:
        features["combined_matches_last_14_days"] = int(home_load) + int(away_load)
    else:
        features["combined_matches_last_14_days"] = None
    return features
