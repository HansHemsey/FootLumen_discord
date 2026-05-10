"""No-Draw Winner derived features from base feature snapshot."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

JsonDict = dict[str, Any]


def build_no_draw_winner_features(features: Mapping[str, Any]) -> JsonDict:
    """Compute no-draw winner features from base features (pure computation, no DB access).

    All inputs come from the already-computed base feature snapshot so point-in-time
    discipline is inherited from the upstream builder.
    """
    home_ppg_home = _f(features, "home_team_home_points_per_match_last10")
    away_ppg_away = _f(features, "away_team_away_points_per_match_last10")
    home_ppg_global = _f(features, "home_team_global_points_per_match_last10")
    away_ppg_global = _f(features, "away_team_global_points_per_match_last10")
    home_ppg_away = _f(features, "home_team_away_points_per_match_last10")

    home_xg_for = _f(
        features,
        "home_team_global_pseudo_xg_for_avg_last10",
        "home_team_global_last10_pseudo_xg_for_avg",
    )
    away_xg_against = _f(
        features,
        "away_team_global_pseudo_xg_against_avg_last10",
        "away_team_global_last10_pseudo_xg_against_avg",
    )
    away_xg_for = _f(
        features,
        "away_team_global_pseudo_xg_for_avg_last10",
        "away_team_global_last10_pseudo_xg_for_avg",
    )
    home_xg_against = _f(
        features,
        "home_team_global_pseudo_xg_against_avg_last10",
        "home_team_global_last10_pseudo_xg_against_avg",
    )

    home_xi_value = _f(features, "home_team_expected_xi_total_value")
    away_xi_value = _f(features, "away_team_expected_xi_total_value")
    home_absence = _f(features, "home_team_absence_impact_score")
    away_absence = _f(features, "away_team_absence_impact_score")

    market_home = _f(features, "market_home")
    market_away = _f(features, "market_away")

    strength_edge = _home_away_strength_edge(home_ppg_home, away_ppg_away)
    attack_defense_edge = _attack_defense_edge(
        home_xg_for, away_xg_against, away_xg_for, home_xg_against
    )
    home_advantage_edge = _home_advantage_edge(home_ppg_home, home_ppg_away)
    xi_value_edge = _xi_value_edge(home_xi_value, away_xi_value)
    absence_edge = _absence_impact_edge(home_absence, away_absence)
    odds_home_prob = _no_draw_home_prob(market_home, market_away)
    odds_away_prob = (1.0 - odds_home_prob) if odds_home_prob is not None else None
    market_confidence = _no_draw_market_confidence(odds_home_prob)

    return {
        "ndw_home_away_strength_edge": strength_edge,
        "ndw_attack_defense_edge": attack_defense_edge,
        "ndw_home_advantage_edge": home_advantage_edge,
        "ndw_xi_value_edge": xi_value_edge,
        "ndw_absence_impact_edge": absence_edge,
        "ndw_odds_home_prob": odds_home_prob,
        "ndw_odds_away_prob": odds_away_prob,
        "ndw_market_no_draw_confidence": market_confidence,
        "ndw_home_ppg_global": home_ppg_global,
        "ndw_away_ppg_global": away_ppg_global,
    }


def _home_away_strength_edge(
    home_ppg_home: float | None,
    away_ppg_away: float | None,
) -> float | None:
    if home_ppg_home is None or away_ppg_away is None:
        return None
    return home_ppg_home - away_ppg_away


def _attack_defense_edge(
    home_xg_for: float | None,
    away_xg_against: float | None,
    away_xg_for: float | None,
    home_xg_against: float | None,
) -> float | None:
    if any(v is None for v in (home_xg_for, away_xg_against, away_xg_for, home_xg_against)):
        return None
    home_net = home_xg_for - away_xg_against  # type: ignore[operator]
    away_net = away_xg_for - home_xg_against  # type: ignore[operator]
    return home_net - away_net


def _home_advantage_edge(
    home_ppg_home: float | None,
    home_ppg_away: float | None,
) -> float | None:
    if home_ppg_home is None or home_ppg_away is None:
        return None
    return home_ppg_home - home_ppg_away


def _xi_value_edge(home_xi: float | None, away_xi: float | None) -> float | None:
    if home_xi is None or away_xi is None:
        return None
    return home_xi - away_xi


def _absence_impact_edge(home_absence: float | None, away_absence: float | None) -> float | None:
    if home_absence is None or away_absence is None:
        return None
    return away_absence - home_absence


def _no_draw_home_prob(
    market_home: float | None,
    market_away: float | None,
) -> float | None:
    """P(Home | No Draw) from margin-free market probabilities."""
    if market_home is None or market_away is None:
        return None
    denom = market_home + market_away
    if denom <= 0:
        return None
    return market_home / denom


def _no_draw_market_confidence(odds_home_prob: float | None) -> float | None:
    """How decisive the no-draw market is: 1 = decisive (near 0 or 1), 0 = balanced."""
    if odds_home_prob is None:
        return None
    return abs(odds_home_prob - 0.5) * 2.0


def _f(features: Mapping[str, Any], *keys: str) -> float | None:
    """Return first non-None float value from the given keys."""
    for key in keys:
        raw = features.get(key)
        if raw is not None:
            try:
                return float(raw)
            except (TypeError, ValueError):
                continue
    return None
