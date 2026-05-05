"""V2 feature selection and coverage reporting."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd  # type: ignore[import-untyped]

from football_predictor.modeling.preprocessing import is_forbidden_feature

V2_PREFIXES = (
    "market_",
    "p_market_",
    "odds_",
    "api_pred_",
    "elo_",
    "poisson_v2_",
)

V2_SUBSTRINGS = (
    "ppg",
    "points_per_game",
    "win_rate",
    "draw_rate",
    "loss_rate",
    "goals_for",
    "goals_against",
    "goal_diff",
    "clean_sheet",
    "failed_to_score",
    "shots",
    "pseudo_xg",
    "adj_goals",
    "adj_shots",
    "rank",
    "points_diff",
    "goals_diff",
    "rest_days",
    "matches_last",
    "expected_xi_avg_value",
    "expected_xi_total_value",
    "bench_depth",
    "xi_stability",
    "formation_stability",
    "absence_impact",
    "availability",
    "replacement_quality",
    "starter_missing_count",
    "lineups_available",
    "player_stats_available",
    "injuries_available",
    "standings_available",
    "data_quality",
)


@dataclass(frozen=True)
class FeatureCoverage:
    row_count: int
    selected_feature_count: int
    coverage_by_feature: dict[str, float]

    def as_dict(self) -> dict[str, object]:
        return {
            "row_count": self.row_count,
            "selected_feature_count": self.selected_feature_count,
            "coverage_by_feature": self.coverage_by_feature,
        }


def select_v2_feature_names(
    frame: pd.DataFrame,
    *,
    min_coverage: float = 0.02,
    max_features: int = 260,
) -> list[str]:
    candidates: list[tuple[str, float]] = []
    for column in frame.columns:
        name = str(column)
        if is_forbidden_feature(name):
            continue
        if not _is_v2_candidate(name):
            continue
        numeric = pd.to_numeric(frame[column], errors="coerce")
        coverage = float(numeric.notna().mean()) if len(numeric) else 0.0
        if numeric.notna().any() and coverage >= min_coverage:
            candidates.append((name, coverage))
    candidates.sort(key=lambda item: (-item[1], item[0]))
    return [name for name, _coverage in candidates[:max_features]]


def feature_coverage(frame: pd.DataFrame, feature_names: list[str]) -> FeatureCoverage:
    coverage = {
        name: float(pd.to_numeric(frame[name], errors="coerce").notna().mean())
        if name in frame.columns and len(frame)
        else 0.0
        for name in feature_names
    }
    return FeatureCoverage(
        row_count=len(frame),
        selected_feature_count=len(feature_names),
        coverage_by_feature=coverage,
    )


def _is_v2_candidate(name: str) -> bool:
    normalized = name.casefold()
    if normalized.startswith(V2_PREFIXES):
        return True
    if normalized.startswith(("home_team_", "away_team_")):
        return any(part in normalized for part in V2_SUBSTRINGS)
    return normalized in {
        "overall_data_quality_score",
        "data_quality_score",
        "team_stats_available_rate",
        "player_stats_available_rate",
        "historical_player_stats_available_rate",
    }
