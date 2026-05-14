"""Data quality flags and scoring."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from football_predictor.utils.time import ensure_aware_utc

JsonDict = dict[str, Any]

DATA_QUALITY_VERSION = "dq_v2"


@dataclass(frozen=True)
class DataQuality:
    odds_available: bool = False
    injuries_available: bool = False
    official_lineups_available: bool = False
    player_stats_available: bool = False
    standings_available: bool = False
    api_prediction_available: bool = False

    def score(self) -> int:
        weighted = {
            "odds_available": 25,
            "injuries_available": 12,
            "official_lineups_available": 18,
            "player_stats_available": 20,
            "standings_available": 15,
            "api_prediction_available": 10,
        }
        return sum(points for flag, points in weighted.items() if getattr(self, flag))

    def label(self) -> str:
        score = self.score()
        if score >= 75:
            return "High"
        if score >= 50:
            return "Medium"
        if score >= 25:
            return "Low"
        return "Uncertain"

    def as_dict(self) -> dict[str, bool | int | str]:
        return {
            "score": self.score(),
            "label": self.label(),
            "odds_available": self.odds_available,
            "injuries_available": self.injuries_available,
            "official_lineups_available": self.official_lineups_available,
            "player_stats_available": self.player_stats_available,
            "standings_available": self.standings_available,
            "api_prediction_available": self.api_prediction_available,
        }


def bounded_quality_score(score: int | float) -> int:
    """Clamp feature quality score to the public 0..100 scale."""
    return max(0, min(100, int(round(score))))


def quality_label(score: int | float) -> str:
    bounded = bounded_quality_score(score)
    if bounded >= 75:
        return "High"
    if bounded >= 50:
        return "Medium"
    if bounded >= 25:
        return "Low"
    return "Uncertain"


def count_quality_ratio(count: int, *, full_count: int, partial_count: int = 1) -> float:
    """Return a simple 0/0.5/1 ratio for count-based source coverage."""
    if count >= full_count:
        return 1.0
    if count >= partial_count:
        return 0.5
    return 0.0


def source_quality_payload(
    *,
    available: bool,
    checked: bool,
    count: int,
    weight: float,
    prediction_time: datetime | None = None,
    latest_fetched_at: datetime | None = None,
    fresh_minutes: int | None = None,
    partial_minutes: int | None = None,
    base_ratio: float | None = None,
    warnings: list[str] | None = None,
) -> JsonDict:
    """Build a JSON-safe dq_v2 source block and its weighted score contribution."""
    resolved_warnings = list(warnings or [])
    resolved_available = bool(available)
    resolved_checked = bool(checked)
    resolved_count = int(count)
    ratio = _bounded_ratio(base_ratio if base_ratio is not None else (1.0 if available else 0.0))
    freshness_ratio = 1.0
    fresh = resolved_checked
    age_minutes: float | None = None
    latest_iso: str | None = None

    if latest_fetched_at is not None:
        latest = ensure_aware_utc(latest_fetched_at)
        latest_iso = latest.isoformat()
        if prediction_time is not None:
            cutoff = ensure_aware_utc(prediction_time)
            age_minutes = round((cutoff - latest).total_seconds() / 60, 2)
            if age_minutes < 0:
                resolved_available = False
                resolved_checked = False
                resolved_count = 0
                freshness_ratio = 0.0
                fresh = False
                resolved_warnings.append("future_snapshot_ignored")
            elif fresh_minutes is not None and age_minutes > fresh_minutes:
                fresh = False
                partial_limit = partial_minutes if partial_minutes is not None else fresh_minutes
                freshness_ratio = 0.5 if age_minutes <= partial_limit else 0.0
                resolved_warnings.append("source_stale")
            else:
                fresh = bool(checked)
    elif fresh_minutes is not None and checked:
        freshness_ratio = 0.0
        fresh = False
        resolved_warnings.append("freshness_timestamp_missing")
    elif not checked:
        fresh = False

    score = bounded_quality_score(weight * ratio * freshness_ratio)
    return {
        "available": resolved_available,
        "checked": resolved_checked,
        "fresh": bool(fresh),
        "latest_fetched_at": latest_iso,
        "age_minutes": age_minutes,
        "age_hours": round(age_minutes / 60, 2) if age_minutes is not None else None,
        "count": resolved_count,
        "score": score,
        "warnings": resolved_warnings,
    }


def publication_quality_payload(
    source_quality_json: dict[str, JsonDict],
    *,
    blockers: list[str] | None = None,
) -> JsonDict:
    """Return the dq_v2 aggregate publication quality contract."""
    source_scores = [
        float(source.get("score") or 0)
        for source in source_quality_json.values()
        if isinstance(source, dict)
    ]
    score = bounded_quality_score(sum(source_scores))
    resolved_blockers = list(blockers or [])
    for source_name, source in source_quality_json.items():
        if not isinstance(source, dict):
            continue
        warnings = source.get("warnings") if isinstance(source.get("warnings"), list) else []
        if "future_snapshot_ignored" in warnings:
            resolved_blockers.append(f"{source_name}_future_snapshot")
    return {
        "data_quality_version": DATA_QUALITY_VERSION,
        "publication_data_quality_score": score,
        "publication_data_quality_label": quality_label(score),
        "publication_blockers": sorted(set(resolved_blockers)),
        "source_quality_json": source_quality_json,
    }


def _bounded_ratio(value: float) -> float:
    return max(0.0, min(float(value), 1.0))


def compute_feature_quality_score(
    *,
    historical_matches_home_count: int,
    historical_matches_away_count: int,
    team_stats_available_rate: float,
    player_stats_available_rate: float,
    lineups_available_flag: bool,
    injuries_available_flag: bool,
    odds_available_flag: bool,
    api_prediction_available_flag: bool,
    reference_docs_available_flag: bool,
    standings_available_flag: bool,
) -> int:
    """Compute Sprint 10 feature-builder data quality on a 0..100 scale."""
    score = 0.0
    if historical_matches_home_count > 0 and historical_matches_away_count > 0:
        score += 20
    score += 15 * max(0.0, min(team_stats_available_rate, 1.0))
    score += 15 * max(0.0, min(player_stats_available_rate, 1.0))
    score += 10 if lineups_available_flag else 0
    score += 5 if injuries_available_flag else 0
    score += 20 if odds_available_flag else 0
    score += 10 if api_prediction_available_flag else 0
    score += 3 if reference_docs_available_flag else 0
    score += 2 if standings_available_flag else 0
    return bounded_quality_score(score)


def feature_quality_payload(
    *,
    historical_matches_home_count: int,
    historical_matches_away_count: int,
    team_stats_available_rate: float,
    player_stats_available_rate: float,
    lineups_available_flag: bool,
    injuries_available_flag: bool,
    odds_available_flag: bool,
    api_prediction_available_flag: bool,
    reference_docs_available_flag: bool,
    standings_available_flag: bool,
    warnings: list[str] | None = None,
) -> JsonDict:
    """Return the Sprint 10 feature-builder data quality contract."""
    score = compute_feature_quality_score(
        historical_matches_home_count=historical_matches_home_count,
        historical_matches_away_count=historical_matches_away_count,
        team_stats_available_rate=team_stats_available_rate,
        player_stats_available_rate=player_stats_available_rate,
        lineups_available_flag=lineups_available_flag,
        injuries_available_flag=injuries_available_flag,
        odds_available_flag=odds_available_flag,
        api_prediction_available_flag=api_prediction_available_flag,
        reference_docs_available_flag=reference_docs_available_flag,
        standings_available_flag=standings_available_flag,
    )
    return {
        "historical_matches_home_count": historical_matches_home_count,
        "historical_matches_away_count": historical_matches_away_count,
        "team_stats_available_rate": team_stats_available_rate,
        "player_stats_available_rate": player_stats_available_rate,
        "lineups_available_flag": lineups_available_flag,
        "injuries_available_flag": injuries_available_flag,
        "odds_available_flag": odds_available_flag,
        "api_prediction_available_flag": api_prediction_available_flag,
        "reference_docs_available_flag": reference_docs_available_flag,
        "standings_available_flag": standings_available_flag,
        "overall_data_quality_score": score,
        "warnings": warnings or [],
    }


def observability_quality_score(
    *,
    historical_home_available: bool,
    historical_away_available: bool,
    match_statistics_available: bool,
    lineups_available: bool,
    player_stats_available: bool,
    injuries_available: bool,
    odds_available: bool,
    api_prediction_available: bool,
    reference_docs_available: bool,
    standings_available: bool,
) -> int:
    """Score local data coverage for diagnostics without recalculating features."""
    score = 0
    score += 10 if historical_home_available else 0
    score += 10 if historical_away_available else 0
    score += 15 if match_statistics_available else 0
    score += 10 if lineups_available else 0
    score += 15 if player_stats_available else 0
    score += 5 if injuries_available else 0
    score += 20 if odds_available else 0
    score += 5 if api_prediction_available else 0
    score += 5 if reference_docs_available else 0
    score += 5 if standings_available else 0
    return bounded_quality_score(score)


def observability_quality_payload(
    *,
    historical_home_count: int,
    historical_away_count: int,
    match_statistics_count: int,
    lineups_count: int,
    player_stats_count: int,
    injuries_count: int,
    odds_count: int,
    api_prediction_count: int,
    reference_docs_available: bool,
    standings_count: int,
) -> JsonDict:
    """Return explicit source-availability flags for `football-predictor data-quality`."""
    flags = {
        "historical_home_available": historical_home_count > 0,
        "historical_away_available": historical_away_count > 0,
        "match_statistics_available": match_statistics_count > 0,
        "lineups_available": lineups_count > 0,
        "player_stats_available": player_stats_count > 0,
        "injuries_available": injuries_count > 0,
        "odds_available": odds_count > 0,
        "api_prediction_available": api_prediction_count > 0,
        "reference_docs_available": reference_docs_available,
        "standings_available": standings_count > 0,
    }
    return {
        **flags,
        "historical_home_count": historical_home_count,
        "historical_away_count": historical_away_count,
        "overall_data_quality_score": observability_quality_score(**flags),
    }
