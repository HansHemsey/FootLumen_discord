"""Point-in-time team feature builder."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from football_predictor.db import models
from football_predictor.db.repositories import upsert_by_fields
from football_predictor.features.context_features import (
    extract_round_number,
    matches_in_last_days,
    rest_days,
)
from football_predictor.features.stat_parsing import parse_fixture_statistics
from football_predictor.utils.exceptions import DataQualityError
from football_predictor.utils.time import ensure_aware_utc

JsonDict = dict[str, Any]

FINISHED_STATUSES = {"FT", "AET", "PEN"}
PERFORMANCE_METRICS = (
    "total_shots",
    "shots_total",
    "shots_on_goal",
    "shots_off_goal",
    "shots_inside_box",
    "shots_insidebox",
    "shots_outsidebox",
    "blocked_shots",
    "possession",
    "passes_total",
    "passes_accurate",
    "passes_percentage",
    "pass_accuracy",
    "corners",
    "fouls",
    "offsides",
    "cards",
    "yellow_cards",
    "red_cards",
    "goalkeeper_saves",
    "pseudo_xg",
)
SHOOTING_METRICS = ("total_shots", "shots_total", "shots_on_goal", "shots_insidebox")
FOR_AGAINST_METRICS = (
    "shots",
    "shots_on_goal",
    "corners",
    "pseudo_xg",
)


@dataclass(frozen=True)
class TeamFeatureConfig:
    windows: tuple[int, ...] = (3, 5, 10, 15)
    ewma_alpha: float = 0.35
    ewma_window: int = 15
    feature_version: str = "team_features_v1"


@dataclass(frozen=True)
class TeamFeatureResult:
    features_json: JsonDict
    data_quality_json: JsonDict


@dataclass(frozen=True)
class TeamMatch:
    fixture: models.Fixture
    team_id: int
    opponent_id: int
    side: str
    goals_for: int
    goals_against: int
    points: int

    @property
    def goal_diff(self) -> int:
        return self.goals_for - self.goals_against


@dataclass(frozen=True)
class SideFeatureContext:
    features: JsonDict
    history_count: int
    stats_covered: int
    events_covered: int
    pseudo_xg_available: bool
    standing_available: bool
    warnings: list[str]


def build_team_features(
    session: Session,
    fixture_id: int,
    prediction_time: datetime,
    config: TeamFeatureConfig | None = None,
) -> TeamFeatureResult:
    """Build flat team features for one target fixture without reading future data."""
    resolved_config = config or TeamFeatureConfig()
    session.flush()
    target = session.get(models.Fixture, fixture_id)
    if target is None:
        raise DataQualityError(f"Unknown fixture_id={fixture_id}")

    prediction_cutoff = ensure_aware_utc(prediction_time)
    home_context = _build_side_context(
        session,
        target=target,
        team_id=target.home_team_id,
        prefix="home_team",
        prediction_time=prediction_cutoff,
        config=resolved_config,
    )
    away_context = _build_side_context(
        session,
        target=target,
        team_id=target.away_team_id,
        prefix="away_team",
        prediction_time=prediction_cutoff,
        config=resolved_config,
    )

    features: JsonDict = {
        "target_fixture_id": target.fixture_id,
        "league_id": target.league_id,
        "season": target.season,
        "home_team_id": target.home_team_id,
        "away_team_id": target.away_team_id,
        "prediction_time": prediction_cutoff.isoformat(),
        "fixture_round_number": extract_round_number(target.round),
        **home_context.features,
        **away_context.features,
    }
    features["rest_days_home"] = features.get("home_team_rest_days")
    features["rest_days_away"] = features.get("away_team_rest_days")
    features["matches_last_7_days_home"] = features.get("home_team_matches_last_7_days")
    features["matches_last_7_days_away"] = features.get("away_team_matches_last_7_days")
    features["matches_last_14_days_home"] = features.get("home_team_matches_last_14_days")
    features["matches_last_14_days_away"] = features.get("away_team_matches_last_14_days")
    _add_standing_diff_features(features)
    total_history = home_context.history_count + away_context.history_count
    stats_covered = home_context.stats_covered + away_context.stats_covered
    events_covered = home_context.events_covered + away_context.events_covered
    warnings = [*home_context.warnings, *away_context.warnings]
    data_quality: JsonDict = {
        "feature_version": resolved_config.feature_version,
        "home_team_history_count": home_context.history_count,
        "away_team_history_count": away_context.history_count,
        "fixture_statistics_coverage_ratio": _ratio(stats_covered, total_history),
        "missing_statistics_rate": 1 - _ratio(stats_covered, total_history),
        "events_coverage_ratio": _ratio(events_covered, total_history),
        "historical_matches_found": total_history,
        "standings_available": home_context.standing_available and away_context.standing_available,
        "standings_available_home": home_context.standing_available,
        "standings_available_away": away_context.standing_available,
        "pseudo_xg_available_home": home_context.pseudo_xg_available,
        "pseudo_xg_available_away": away_context.pseudo_xg_available,
        "warnings": warnings,
    }
    for window in resolved_config.windows:
        data_quality[f"home_team_matches_available_last{window}"] = min(
            home_context.history_count, window
        )
        data_quality[f"away_team_matches_available_last{window}"] = min(
            away_context.history_count, window
        )
    return TeamFeatureResult(features_json=features, data_quality_json=data_quality)


def save_team_feature_snapshot(
    session: Session,
    fixture_id: int,
    prediction_time: datetime,
    config: TeamFeatureConfig | None = None,
) -> models.FeatureSnapshot:
    """Build and upsert a `FeatureSnapshot` for team features."""
    resolved_config = config or TeamFeatureConfig()
    prediction_cutoff = ensure_aware_utc(prediction_time)
    result = build_team_features(session, fixture_id, prediction_cutoff, resolved_config)
    snapshot = upsert_by_fields(
        session,
        models.FeatureSnapshot,
        {
            "fixture_id": fixture_id,
            "prediction_time": prediction_cutoff,
            "feature_version": resolved_config.feature_version,
        },
        {
            "features_json": result.features_json,
            "data_quality_json": result.data_quality_json,
        },
    )
    session.flush()
    return snapshot


def _build_side_context(
    session: Session,
    *,
    target: models.Fixture,
    team_id: int,
    prefix: str,
    prediction_time: datetime,
    config: TeamFeatureConfig,
) -> SideFeatureContext:
    matches = _historical_matches_for_team(session, target, team_id, prediction_time)
    penalty_events_by_fixture = _latest_penalty_events_by_fixture(
        session, matches, team_id, prediction_time
    )
    stats_by_fixture = _latest_stats_by_fixture(
        session,
        matches,
        team_id,
        prediction_time,
        penalties_by_fixture=penalty_events_by_fixture,
    )
    opponent_stats_by_fixture = _latest_opponent_stats_by_fixture(
        session, matches, prediction_time
    )
    event_cards_by_fixture = _latest_card_events_by_fixture(
        session, matches, team_id, prediction_time
    )
    league_ppm = _league_points_per_match(session, target, prediction_time)
    standing = _latest_standing(session, target, team_id, prediction_time)
    features: JsonDict = {}
    warnings: list[str] = []

    if not matches:
        warnings.append(f"{prefix}: no historical matches before prediction_time")
    if not stats_by_fixture:
        warnings.append(f"{prefix}: no fixture statistics before prediction_time")
    if standing is None:
        warnings.append(f"{prefix}: no standings snapshot before prediction_time")

    for window in config.windows:
        for scope, scoped_matches in (
            ("global", matches),
            ("home", [match for match in matches if match.side == "home"]),
            ("away", [match for match in matches if match.side == "away"]),
        ):
            selected = list(scoped_matches[:window])
            _add_result_features(features, prefix, scope, window, selected)
            _add_performance_features(
                features,
                prefix,
                scope,
                window,
                selected,
                stats_by_fixture,
                opponent_stats_by_fixture,
                event_cards_by_fixture,
            )
            if scope == "global":
                _add_opponent_adjusted_features(
                    session,
                    features,
                    prefix,
                    target,
                    window,
                    selected,
                    prediction_time,
                    league_ppm,
                )

    _add_ewma_features(features, prefix, matches[: config.ewma_window], config.ewma_alpha)
    _add_standing_features(features, prefix, standing)
    _add_context_features(
        features,
        prefix,
        target,
        matches,
        prediction_time,
        travel_away_flag=1 if prefix == "away_team" else 0,
    )

    return SideFeatureContext(
        features=features,
        history_count=len(matches),
        stats_covered=len(stats_by_fixture),
        events_covered=len(event_cards_by_fixture),
        pseudo_xg_available=any(
            _stats_with_card_fallback(stats, event_cards_by_fixture.get(fixture_id)).get(
                "pseudo_xg"
            )
            is not None
            for fixture_id, stats in stats_by_fixture.items()
        ),
        standing_available=standing is not None,
        warnings=warnings,
    )


def _historical_matches_for_team(
    session: Session,
    target: models.Fixture,
    team_id: int,
    prediction_time: datetime,
    *,
    before_time: datetime | None = None,
    exclude_fixture_id: int | None = None,
) -> list[TeamMatch]:
    cutoff = before_time or prediction_time
    excluded_fixture_id = exclude_fixture_id or target.fixture_id
    stmt = (
        select(models.Fixture)
        .where(
            models.Fixture.fixture_id != excluded_fixture_id,
            models.Fixture.league_id == target.league_id,
            models.Fixture.season == target.season,
            models.Fixture.date.is_not(None),
            models.Fixture.date < cutoff,
            or_(models.Fixture.home_team_id == team_id, models.Fixture.away_team_id == team_id),
        )
        .order_by(models.Fixture.date.desc())
    )
    matches: list[TeamMatch] = []
    for fixture in session.execute(stmt).scalars():
        team_match = _team_match_from_fixture(fixture, team_id)
        if team_match is not None:
            matches.append(team_match)
    return matches


def _team_match_from_fixture(fixture: models.Fixture, team_id: int) -> TeamMatch | None:
    if not _is_finished_fixture(fixture):
        return None
    home_goals, away_goals = _fixture_score(fixture)
    if home_goals is None or away_goals is None:
        return None
    if fixture.home_team_id == team_id:
        goals_for = home_goals
        goals_against = away_goals
        opponent_id = fixture.away_team_id
        side = "home"
    elif fixture.away_team_id == team_id:
        goals_for = away_goals
        goals_against = home_goals
        opponent_id = fixture.home_team_id
        side = "away"
    else:
        return None
    if goals_for > goals_against:
        points = 3
    elif goals_for == goals_against:
        points = 1
    else:
        points = 0
    return TeamMatch(
        fixture=fixture,
        team_id=team_id,
        opponent_id=opponent_id,
        side=side,
        goals_for=goals_for,
        goals_against=goals_against,
        points=points,
    )


def _add_result_features(
    features: JsonDict,
    prefix: str,
    scope: str,
    window: int,
    matches: Sequence[TeamMatch],
) -> None:
    feature_prefix = f"{prefix}_{scope}"
    suffix = f"last{window}"
    features[f"{feature_prefix}_matches_available_{suffix}"] = len(matches)
    features[f"{feature_prefix}_win_rate_{suffix}"] = _rate(
        match.points == 3 for match in matches
    )
    features[f"{feature_prefix}_draw_rate_{suffix}"] = _rate(
        match.points == 1 for match in matches
    )
    features[f"{feature_prefix}_loss_rate_{suffix}"] = _rate(
        match.points == 0 for match in matches
    )
    features[f"{feature_prefix}_points_per_match_{suffix}"] = _mean(
        match.points for match in matches
    )
    features[f"{feature_prefix}_{suffix}_ppg"] = features[
        f"{feature_prefix}_points_per_match_{suffix}"
    ]
    features[f"{feature_prefix}_{suffix}_points_per_game"] = features[
        f"{feature_prefix}_points_per_match_{suffix}"
    ]
    features[f"{feature_prefix}_{suffix}_win_rate"] = features[
        f"{feature_prefix}_win_rate_{suffix}"
    ]
    features[f"{feature_prefix}_{suffix}_draw_rate"] = features[
        f"{feature_prefix}_draw_rate_{suffix}"
    ]
    features[f"{feature_prefix}_{suffix}_loss_rate"] = features[
        f"{feature_prefix}_loss_rate_{suffix}"
    ]
    features[f"{feature_prefix}_goals_for_avg_{suffix}"] = _mean(
        match.goals_for for match in matches
    )
    features[f"{feature_prefix}_goals_against_avg_{suffix}"] = _mean(
        match.goals_against for match in matches
    )
    features[f"{feature_prefix}_goal_diff_avg_{suffix}"] = _mean(
        match.goal_diff for match in matches
    )
    features[f"{feature_prefix}_clean_sheet_rate_{suffix}"] = _rate(
        match.goals_against == 0 for match in matches
    )
    features[f"{feature_prefix}_failed_to_score_rate_{suffix}"] = _rate(
        match.goals_for == 0 for match in matches
    )


def _add_performance_features(
    features: JsonDict,
    prefix: str,
    scope: str,
    window: int,
    matches: Sequence[TeamMatch],
    stats_by_fixture: dict[int, JsonDict],
    opponent_stats_by_fixture: dict[int, JsonDict],
    event_cards_by_fixture: dict[int, JsonDict],
) -> None:
    suffix = f"last{window}"
    feature_prefix = f"{prefix}_{scope}"
    rows: list[JsonDict] = []
    opponent_rows: list[JsonDict] = []
    for match in matches:
        fixture_id = match.fixture.fixture_id
        if fixture_id in stats_by_fixture:
            row = _stats_with_card_fallback(
                stats_by_fixture[fixture_id],
                event_cards_by_fixture.get(fixture_id),
            )
            row["goals_for"] = match.goals_for
            row["goals_against"] = match.goals_against
            rows.append(row)
        if fixture_id in opponent_stats_by_fixture:
            opponent_rows.append(opponent_stats_by_fixture[fixture_id])
    for metric in PERFORMANCE_METRICS:
        features[f"{feature_prefix}_{metric}_avg_{suffix}"] = _mean(
            row.get(metric) for row in rows
        )
    _add_for_against_feature_aliases(features, feature_prefix, suffix, rows, opponent_rows, matches)


def _add_for_against_feature_aliases(
    features: JsonDict,
    feature_prefix: str,
    suffix: str,
    rows: Sequence[JsonDict],
    opponent_rows: Sequence[JsonDict],
    matches: Sequence[TeamMatch],
) -> None:
    mapping = {
        "shots": "total_shots",
        "shots_on_goal": "shots_on_goal",
        "corners": "corners",
        "pseudo_xg": "pseudo_xg",
    }
    for public_name, metric in mapping.items():
        for_value = _mean(row.get(metric) for row in rows)
        against_value = _mean(row.get(metric) for row in opponent_rows)
        features[f"{feature_prefix}_{public_name}_for_avg_{suffix}"] = for_value
        features[f"{feature_prefix}_{public_name}_against_avg_{suffix}"] = against_value
        features[f"{feature_prefix}_{suffix}_{public_name}_for_avg"] = for_value
        features[f"{feature_prefix}_{suffix}_{public_name}_against_avg"] = against_value
    cards_avg = _mean(row.get("cards") for row in rows)
    pass_accuracy_avg = _mean(row.get("pass_accuracy") for row in rows)
    possession_avg = _mean(row.get("possession") for row in rows)
    features[f"{feature_prefix}_cards_avg_{suffix}"] = cards_avg
    features[f"{feature_prefix}_pass_accuracy_avg_{suffix}"] = pass_accuracy_avg
    features[f"{feature_prefix}_possession_avg_{suffix}"] = possession_avg
    features[f"{feature_prefix}_{suffix}_cards_avg"] = cards_avg
    features[f"{feature_prefix}_{suffix}_pass_accuracy_avg"] = pass_accuracy_avg
    features[f"{feature_prefix}_{suffix}_possession_avg"] = possession_avg

    total_shots_for = _sum(row.get("total_shots") for row in rows)
    shots_on_goal_for = _sum(row.get("shots_on_goal") for row in rows)
    shots_inside_for = _sum(row.get("shots_insidebox") for row in rows)
    shots_on_goal_against = _sum(row.get("shots_on_goal") for row in opponent_rows)
    goalkeeper_saves = _sum(row.get("goalkeeper_saves") for row in rows)
    goals_for = _sum(row.get("goals_for") for row in rows)
    features[f"{feature_prefix}_shot_accuracy_{suffix}"] = _safe_div(
        shots_on_goal_for, total_shots_for
    )
    features[f"{feature_prefix}_goal_conversion_{suffix}"] = _safe_div(
        goals_for, shots_on_goal_for
    )
    features[f"{feature_prefix}_box_shot_share_{suffix}"] = _safe_div(
        shots_inside_for, total_shots_for
    )
    features[f"{feature_prefix}_save_rate_{suffix}"] = _safe_div(
        goalkeeper_saves, shots_on_goal_against
    )
    for metric in ("shot_accuracy", "goal_conversion", "box_shot_share", "save_rate"):
        features[f"{feature_prefix}_{suffix}_{metric}"] = features[
            f"{feature_prefix}_{metric}_{suffix}"
        ]


def _add_opponent_adjusted_features(
    session: Session,
    features: JsonDict,
    prefix: str,
    target: models.Fixture,
    window: int,
    matches: Sequence[TeamMatch],
    prediction_time: datetime,
    league_ppm: float | None,
) -> None:
    suffix = f"last{window}"
    opponent_ppm_by_match = _opponent_ppm_by_fixture(session, target, matches, prediction_time)
    selected_opponent_ppm = [
        opponent_ppm_by_match.get(match.fixture.fixture_id)
        for match in matches
        if opponent_ppm_by_match.get(match.fixture.fixture_id) is not None
    ]
    opponent_ppm_avg = _mean(selected_opponent_ppm)
    goal_diff_avg = _mean(match.goal_diff for match in matches)
    adjustment = None
    if goal_diff_avg is not None and opponent_ppm_avg is not None and league_ppm is not None:
        adjustment = goal_diff_avg - (opponent_ppm_avg - league_ppm)
    features[f"{prefix}_global_opponent_ppm_avg_{suffix}"] = opponent_ppm_avg
    features[f"{prefix}_global_goal_diff_adj_avg_{suffix}"] = adjustment
    adjusted = _opponent_adjusted_averages(session, target, matches, prediction_time)
    for feature_name, value in adjusted.items():
        features[f"{prefix}_global_{feature_name}_{suffix}"] = value
        features[f"{prefix}_global_{suffix}_{feature_name}"] = value


def _add_ewma_features(
    features: JsonDict,
    prefix: str,
    matches: Sequence[TeamMatch],
    alpha: float,
) -> None:
    ordered = list(reversed(matches))
    features[f"{prefix}_global_points_ewma"] = _ewma([match.points for match in ordered], alpha)
    features[f"{prefix}_global_goals_for_ewma"] = _ewma(
        [match.goals_for for match in ordered], alpha
    )
    features[f"{prefix}_global_goals_against_ewma"] = _ewma(
        [match.goals_against for match in ordered], alpha
    )
    features[f"{prefix}_global_goal_diff_ewma"] = _ewma(
        [match.goal_diff for match in ordered], alpha
    )


def _add_standing_features(
    features: JsonDict,
    prefix: str,
    standing: models.StandingSnapshot | None,
) -> None:
    played = standing.all_played or standing.played if standing is not None else None
    points = standing.points if standing is not None else None
    features[f"{prefix}_standing_rank"] = standing.rank if standing is not None else None
    features[f"{prefix}_standing_points"] = points
    features[f"{prefix}_standing_goals_diff"] = (
        standing.goals_diff if standing is not None else None
    )
    features[f"{prefix}_standing_played"] = played
    features[f"{prefix}_standing_points_per_match"] = (
        points / played if points is not None and played else None
    )


def _add_context_features(
    features: JsonDict,
    prefix: str,
    target: models.Fixture,
    matches: Sequence[TeamMatch],
    prediction_time: datetime,
    *,
    travel_away_flag: int,
) -> None:
    features[f"{prefix}_rest_days"] = rest_days(matches, prediction_time)
    features[f"{prefix}_matches_last_7_days"] = matches_in_last_days(
        matches, prediction_time, 7
    )
    features[f"{prefix}_matches_last_14_days"] = matches_in_last_days(
        matches, prediction_time, 14
    )
    features[f"{prefix}_travel_away_flag"] = travel_away_flag
    features[f"{prefix}_fixture_round_number"] = extract_round_number(target.round)


def _add_standing_diff_features(features: JsonDict) -> None:
    rank_home = features.get("home_team_standing_rank")
    rank_away = features.get("away_team_standing_rank")
    points_home = features.get("home_team_standing_points")
    points_away = features.get("away_team_standing_points")
    gd_home = features.get("home_team_standing_goals_diff")
    gd_away = features.get("away_team_standing_goals_diff")
    features["rank_diff"] = _diff(rank_home, rank_away)
    features["points_diff"] = _diff(points_home, points_away)
    features["goals_diff_diff"] = _diff(gd_home, gd_away)


def _latest_stats_by_fixture(
    session: Session,
    matches: Sequence[TeamMatch],
    team_id: int,
    prediction_time: datetime,
    *,
    penalties_by_fixture: dict[int, int] | None = None,
) -> dict[int, JsonDict]:
    fixture_ids = [match.fixture.fixture_id for match in matches]
    if not fixture_ids:
        return {}
    stmt = (
        select(models.FixtureStatistics)
        .where(
            models.FixtureStatistics.fixture_id.in_(fixture_ids),
            models.FixtureStatistics.team_id == team_id,
            models.FixtureStatistics.fetched_at <= prediction_time,
        )
        .order_by(
            models.FixtureStatistics.fixture_id.asc(),
            models.FixtureStatistics.fetched_at.desc(),
        )
    )
    latest: dict[int, JsonDict] = {}
    for row in session.execute(stmt).scalars():
        latest.setdefault(
            row.fixture_id,
            parse_fixture_statistics(
                row.statistics_json,
                penalties=(penalties_by_fixture or {}).get(row.fixture_id, 0),
            ),
        )
    return latest


def _latest_opponent_stats_by_fixture(
    session: Session,
    matches: Sequence[TeamMatch],
    prediction_time: datetime,
) -> dict[int, JsonDict]:
    fixture_ids = [match.fixture.fixture_id for match in matches]
    if not fixture_ids:
        return {}
    opponent_by_fixture = {match.fixture.fixture_id: match.opponent_id for match in matches}
    stmt = (
        select(models.FixtureStatistics)
        .where(
            models.FixtureStatistics.fixture_id.in_(fixture_ids),
            models.FixtureStatistics.fetched_at <= prediction_time,
        )
        .order_by(
            models.FixtureStatistics.fixture_id.asc(),
            models.FixtureStatistics.team_id.asc(),
            models.FixtureStatistics.fetched_at.desc(),
        )
    )
    latest: dict[int, JsonDict] = {}
    seen: set[tuple[int, int]] = set()
    for row in session.execute(stmt).scalars():
        key = (row.fixture_id, row.team_id)
        if key in seen:
            continue
        seen.add(key)
        if opponent_by_fixture.get(row.fixture_id) == row.team_id:
            latest[row.fixture_id] = parse_fixture_statistics(row.statistics_json)
    return latest


def _latest_card_events_by_fixture(
    session: Session,
    matches: Sequence[TeamMatch],
    team_id: int,
    prediction_time: datetime,
) -> dict[int, JsonDict]:
    fixture_ids = [match.fixture.fixture_id for match in matches]
    if not fixture_ids:
        return {}
    stmt = (
        select(models.FixtureEvent)
        .where(
            models.FixtureEvent.fixture_id.in_(fixture_ids),
            models.FixtureEvent.team_id == team_id,
            models.FixtureEvent.fetched_at <= prediction_time,
        )
        .order_by(
            models.FixtureEvent.fixture_id.asc(),
            models.FixtureEvent.fetched_at.desc(),
        )
    )
    latest_time_by_fixture: dict[int, datetime] = {}
    rows = list(session.execute(stmt).scalars())
    for row in rows:
        latest_time_by_fixture.setdefault(row.fixture_id, ensure_aware_utc(row.fetched_at))

    counts: dict[int, JsonDict] = {}
    for row in rows:
        latest_time = latest_time_by_fixture[row.fixture_id]
        if ensure_aware_utc(row.fetched_at) != latest_time or not _is_card_event(row):
            continue
        fixture_counts = counts.setdefault(row.fixture_id, {"yellow_cards": 0, "red_cards": 0})
        detail = _normalize_label(row.detail or row.event_type or row.type or "")
        if "red" in detail:
            fixture_counts["red_cards"] += 1
        elif "yellow" in detail:
            fixture_counts["yellow_cards"] += 1
    return counts


def _latest_penalty_events_by_fixture(
    session: Session,
    matches: Sequence[TeamMatch],
    team_id: int,
    prediction_time: datetime,
) -> dict[int, int]:
    fixture_ids = [match.fixture.fixture_id for match in matches]
    if not fixture_ids:
        return {}
    stmt = (
        select(models.FixtureEvent)
        .where(
            models.FixtureEvent.fixture_id.in_(fixture_ids),
            models.FixtureEvent.team_id == team_id,
            models.FixtureEvent.fetched_at <= prediction_time,
        )
        .order_by(
            models.FixtureEvent.fixture_id.asc(),
            models.FixtureEvent.fetched_at.desc(),
        )
    )
    latest_time_by_fixture: dict[int, datetime] = {}
    rows = list(session.execute(stmt).scalars())
    for row in rows:
        latest_time_by_fixture.setdefault(row.fixture_id, ensure_aware_utc(row.fetched_at))

    counts: dict[int, int] = {}
    for row in rows:
        latest_time = latest_time_by_fixture[row.fixture_id]
        detail = _normalize_label(row.detail or row.event_type or row.type or "")
        if ensure_aware_utc(row.fetched_at) == latest_time and "penalty" in detail:
            counts[row.fixture_id] = counts.get(row.fixture_id, 0) + 1
    return counts


def _opponent_ppm_by_fixture(
    session: Session,
    target: models.Fixture,
    matches: Sequence[TeamMatch],
    prediction_time: datetime,
) -> dict[int, float | None]:
    opponent_ids = {match.opponent_id for match in matches}
    return {
        match.fixture.fixture_id: _team_points_per_match(
            session,
            target,
            match.opponent_id,
            min(prediction_time, ensure_aware_utc(match.fixture.date or prediction_time)),
            limit=10,
            exclude_fixture_id=match.fixture.fixture_id,
        )
        if match.opponent_id in opponent_ids
        else None
        for match in matches
    }


def _team_points_per_match(
    session: Session,
    target: models.Fixture,
    team_id: int,
    prediction_time: datetime,
    *,
    limit: int,
    exclude_fixture_id: int | None = None,
) -> float | None:
    matches = _historical_matches_for_team(
        session,
        target,
        team_id,
        prediction_time,
        exclude_fixture_id=exclude_fixture_id,
    )
    return _mean(match.points for match in matches[:limit])


def _league_points_per_match(
    session: Session,
    target: models.Fixture,
    prediction_time: datetime,
) -> float | None:
    stmt = (
        select(models.Fixture)
        .where(
            models.Fixture.fixture_id != target.fixture_id,
            models.Fixture.league_id == target.league_id,
            models.Fixture.season == target.season,
            models.Fixture.date.is_not(None),
            models.Fixture.date < prediction_time,
        )
        .order_by(models.Fixture.date.desc())
    )
    points: list[int] = []
    for fixture in session.execute(stmt).scalars():
        if not _is_finished_fixture(fixture):
            continue
        home_goals, away_goals = _fixture_score(fixture)
        if home_goals is None or away_goals is None:
            continue
        if home_goals > away_goals:
            points.extend([3, 0])
        elif home_goals == away_goals:
            points.extend([1, 1])
        else:
            points.extend([0, 3])
    return _mean(points)


def _opponent_adjusted_averages(
    session: Session,
    target: models.Fixture,
    matches: Sequence[TeamMatch],
    prediction_time: datetime,
) -> JsonDict:
    if not matches:
        return {
            "adj_goals_for": None,
            "adj_goals_against": None,
            "adj_shots_for": None,
            "adj_shots_against": None,
            "adj_shots_on_goal_for": None,
            "adj_shots_on_goal_against": None,
        }
    team_stats = _latest_stats_by_fixture(session, matches, matches[0].team_id, prediction_time)
    opponent_stats = _latest_opponent_stats_by_fixture(session, matches, prediction_time)
    adjusted_rows: dict[str, list[float]] = {
        "adj_goals_for": [],
        "adj_goals_against": [],
        "adj_shots_for": [],
        "adj_shots_against": [],
        "adj_shots_on_goal_for": [],
        "adj_shots_on_goal_against": [],
    }
    for match in matches:
        match_date = match.fixture.date
        if match_date is None:
            continue
        baseline = _opponent_baseline_before_match(
            session,
            target,
            match.opponent_id,
            ensure_aware_utc(match_date),
            prediction_time,
            exclude_fixture_id=match.fixture.fixture_id,
        )
        current_team_stats = team_stats.get(match.fixture.fixture_id, {})
        current_opponent_stats = opponent_stats.get(match.fixture.fixture_id, {})
        _append_adjusted(
            adjusted_rows["adj_goals_for"],
            float(match.goals_for),
            baseline.get("goals_against"),
        )
        _append_adjusted(
            adjusted_rows["adj_goals_against"],
            float(match.goals_against),
            baseline.get("goals_for"),
        )
        _append_adjusted(
            adjusted_rows["adj_shots_for"],
            current_team_stats.get("total_shots"),
            baseline.get("shots_against"),
        )
        _append_adjusted(
            adjusted_rows["adj_shots_against"],
            current_opponent_stats.get("total_shots"),
            baseline.get("shots_for"),
        )
        _append_adjusted(
            adjusted_rows["adj_shots_on_goal_for"],
            current_team_stats.get("shots_on_goal"),
            baseline.get("shots_on_goal_against"),
        )
        _append_adjusted(
            adjusted_rows["adj_shots_on_goal_against"],
            current_opponent_stats.get("shots_on_goal"),
            baseline.get("shots_on_goal_for"),
        )
    return {key: _mean(values) for key, values in adjusted_rows.items()}


def _opponent_baseline_before_match(
    session: Session,
    target: models.Fixture,
    opponent_id: int,
    match_date: datetime,
    prediction_time: datetime,
    *,
    exclude_fixture_id: int,
) -> JsonDict:
    prior_matches = _historical_matches_for_team(
        session,
        target,
        opponent_id,
        prediction_time,
        before_time=match_date,
        exclude_fixture_id=exclude_fixture_id,
    )
    opponent_stats = _latest_stats_by_fixture(session, prior_matches, opponent_id, prediction_time)
    conceded_stats = _latest_opponent_stats_by_fixture(session, prior_matches, prediction_time)
    return {
        "goals_for": _mean(match.goals_for for match in prior_matches),
        "goals_against": _mean(match.goals_against for match in prior_matches),
        "shots_for": _mean(stats.get("total_shots") for stats in opponent_stats.values()),
        "shots_against": _mean(stats.get("total_shots") for stats in conceded_stats.values()),
        "shots_on_goal_for": _mean(
            stats.get("shots_on_goal") for stats in opponent_stats.values()
        ),
        "shots_on_goal_against": _mean(
            stats.get("shots_on_goal") for stats in conceded_stats.values()
        ),
    }


def _append_adjusted(values: list[float], actual: Any, baseline: Any) -> None:
    if actual is None or baseline is None:
        return
    values.append(float(actual) - float(baseline))


def _latest_standing(
    session: Session,
    target: models.Fixture,
    team_id: int,
    prediction_time: datetime,
) -> models.StandingSnapshot | None:
    stmt = (
        select(models.StandingSnapshot)
        .where(
            models.StandingSnapshot.league_id == target.league_id,
            models.StandingSnapshot.season == target.season,
            models.StandingSnapshot.team_id == team_id,
            or_(
                models.StandingSnapshot.snapshot_date <= prediction_time,
                models.StandingSnapshot.fetched_at <= prediction_time,
            ),
        )
        .order_by(
            models.StandingSnapshot.snapshot_date.desc(),
            models.StandingSnapshot.fetched_at.desc(),
        )
        .limit(1)
    )
    return session.execute(stmt).scalar_one_or_none()


def _stats_with_card_fallback(stats: JsonDict, card_counts: JsonDict | None) -> JsonDict:
    resolved = dict(stats)
    if card_counts is not None:
        if resolved.get("yellow_cards") is None:
            resolved["yellow_cards"] = card_counts.get("yellow_cards")
        if resolved.get("red_cards") is None:
            resolved["red_cards"] = card_counts.get("red_cards")
    return resolved


def _fixture_score(fixture: models.Fixture) -> tuple[int | None, int | None]:
    home_goals = fixture.home_goals if fixture.home_goals is not None else fixture.goals_home
    away_goals = fixture.away_goals if fixture.away_goals is not None else fixture.goals_away
    return home_goals, away_goals


def _is_finished_fixture(fixture: models.Fixture) -> bool:
    status = (fixture.status_short or fixture.status or "").upper()
    return status in FINISHED_STATUSES


def _is_card_event(event: models.FixtureEvent) -> bool:
    return _normalize_label(event.type or event.event_type or "") == "card"


def _normalize_label(value: Any) -> str:
    return " ".join(str(value).strip().casefold().replace("-", " ").split())


def _mean(values: Iterable[float | int | None]) -> float | None:
    numeric = [float(value) for value in values if value is not None]
    if not numeric:
        return None
    return sum(numeric) / len(numeric)


def _sum(values: Iterable[float | int | None]) -> float | None:
    numeric = [float(value) for value in values if value is not None]
    if not numeric:
        return None
    return sum(numeric)


def _safe_div(numerator: float | int | None, denominator: float | int | None) -> float | None:
    if numerator is None or denominator is None or denominator == 0:
        return None
    return float(numerator) / float(denominator)


def _diff(left: Any, right: Any) -> float | None:
    if left is None or right is None:
        return None
    return float(left) - float(right)


def _rate(values: Iterable[bool]) -> float | None:
    items = list(values)
    if not items:
        return None
    return sum(1 for item in items if item) / len(items)


def _ratio(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return numerator / denominator


def _ewma(values: Sequence[float | int], alpha: float) -> float | None:
    if not values:
        return None
    current = float(values[0])
    for value in values[1:]:
        current = alpha * float(value) + (1 - alpha) * current
    return current
