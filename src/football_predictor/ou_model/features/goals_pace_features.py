"""Goals pace features for O/U 2.5 prediction.

Computes rolling total goals averages and Over 2.5 rate from team match history.
Uses the TeamMatch objects already loaded by the 1X2 team feature pipeline.
"""

from __future__ import annotations

from typing import Any

JsonDict = dict[str, Any]

_WINDOWS = (3, 5, 10, 15)
_THRESHOLD = 2.5


def build_goals_pace_features(
    prefix: str,
    matches: list[Any],
    *,
    home_matches: list[Any],
    away_matches: list[Any],
) -> JsonDict:
    """Build goals pace features for one team side.

    Args:
        prefix: "home_team" or "away_team"
        matches: All historical TeamMatch objects for this team (global)
        home_matches: Subset where team played at home
        away_matches: Subset where team played away
    """
    features: JsonDict = {}
    for window in _WINDOWS:
        for scope, scoped in (
            ("global", matches),
            ("home", home_matches),
            ("away", away_matches),
        ):
            selected = scoped[:window]
            key_prefix = f"{prefix}_{scope}"
            if not selected:
                if window in (3, 5, 10, 15):
                    features[f"{key_prefix}_total_goals_avg_last{window}"] = None
                    if scope in ("global",):
                        features[f"{key_prefix}_over25_rate_last{window}"] = None
            else:
                total_goals = [m.goals_for + m.goals_against for m in selected]
                features[f"{key_prefix}_total_goals_avg_last{window}"] = (
                    sum(total_goals) / len(total_goals)
                )
                if scope in ("global", "home", "away"):
                    over25 = [1 if g > _THRESHOLD else 0 for g in total_goals]
                    features[f"{key_prefix}_over25_rate_last{window}"] = (
                        sum(over25) / len(over25)
                    )
    return features


def build_combined_goals_features(
    home_features: JsonDict,
    away_features: JsonDict,
) -> JsonDict:
    """Combine home and away team goals pace into match-level features."""
    features: JsonDict = {}
    for window in (5, 10):
        home_total = home_features.get(f"home_team_global_total_goals_avg_last{window}")
        away_total = away_features.get(f"away_team_global_total_goals_avg_last{window}")
        if home_total is not None and away_total is not None:
            features[f"combined_total_goals_avg_last{window}"] = (home_total + away_total) / 2
        else:
            features[f"combined_total_goals_avg_last{window}"] = None

        home_rate = home_features.get(f"home_team_global_over25_rate_last{window}")
        away_rate = away_features.get(f"away_team_global_over25_rate_last{window}")
        if home_rate is not None and away_rate is not None:
            features[f"combined_over25_rate_last{window}"] = (home_rate + away_rate) / 2
        else:
            features[f"combined_over25_rate_last{window}"] = None
    return features
