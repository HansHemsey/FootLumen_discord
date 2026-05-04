"""Point-in-time player, XI and absence feature builder."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from football_predictor.db import models
from football_predictor.db.repositories import upsert_by_fields
from football_predictor.features.availability_features import (
    InjuryStatus,
    absence_impact,
    injury_severity,
)
from football_predictor.features.player_features import (
    PlayerProfile,
    PlayerUsage,
    _latest_lineups_for_fixtures,
    _latest_stats_for_fixtures,
    _team_history,
    formation_counts,
    nested_int,
    normalize_position_group,
    normalize_values_by_position,
    profile_from_reference,
    raw_player_value,
    stats_first_row,
    team_player_profiles,
)
from football_predictor.reference.lookups import PlayersReference
from football_predictor.utils.exceptions import DataQualityError, ReferenceLookupError
from football_predictor.utils.time import ensure_aware_utc

JsonDict = dict[str, Any]
FINISHED_STATUSES = {"FT", "AET", "PEN"}


@dataclass(frozen=True)
class PlayerXIConfig:
    lookback_matches: int = 10
    feature_version: str = "player_xi_features_v1"
    p_start_weights: tuple[float, float, float, float] = (0.50, 0.25, 0.15, 0.10)


@dataclass(frozen=True)
class PlayerXIResult:
    features_json: JsonDict
    data_quality_json: JsonDict


@dataclass
class Candidate:
    profile: PlayerProfile
    usage: PlayerUsage
    p_start: float = 0.0
    player_value: float = 0.0
    raw_value: float = 0.0

    @property
    def score(self) -> float:
        return self.p_start * self.player_value


@dataclass(frozen=True)
class SideXIContext:
    features: JsonDict
    data_quality: JsonDict


def build_player_xi_features(
    session: Session,
    fixture_id: int,
    prediction_time: datetime,
    players_reference: PlayersReference | None = None,
    config: PlayerXIConfig | None = None,
) -> PlayerXIResult:
    """Build player/XI features for a fixture without reading future data."""
    resolved_config = config or PlayerXIConfig()
    prediction_cutoff = ensure_aware_utc(prediction_time)
    session.flush()
    target = session.get(models.Fixture, fixture_id)
    if target is None:
        raise DataQualityError(f"Unknown fixture_id={fixture_id}")

    home_context = _build_side_context(
        session,
        target=target,
        team_id=target.home_team_id,
        prefix="home_team",
        prediction_time=prediction_cutoff,
        players_reference=players_reference,
        config=resolved_config,
    )
    away_context = _build_side_context(
        session,
        target=target,
        team_id=target.away_team_id,
        prefix="away_team",
        prediction_time=prediction_cutoff,
        players_reference=players_reference,
        config=resolved_config,
    )
    features: JsonDict = {
        "target_fixture_id": fixture_id,
        "home_team_id": target.home_team_id,
        "away_team_id": target.away_team_id,
        "prediction_time": prediction_cutoff.isoformat(),
        "feature_version": resolved_config.feature_version,
        **home_context.features,
        **away_context.features,
    }
    data_quality: JsonDict = {
        "feature_version": resolved_config.feature_version,
        **home_context.data_quality,
        **away_context.data_quality,
    }
    return PlayerXIResult(features_json=features, data_quality_json=data_quality)


def save_player_xi_feature_snapshot(
    session: Session,
    fixture_id: int,
    prediction_time: datetime,
    players_reference: PlayersReference | None = None,
    config: PlayerXIConfig | None = None,
) -> models.FeatureSnapshot:
    resolved_config = config or PlayerXIConfig()
    prediction_cutoff = ensure_aware_utc(prediction_time)
    result = build_player_xi_features(
        session,
        fixture_id,
        prediction_cutoff,
        players_reference=players_reference,
        config=resolved_config,
    )
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


def infer_probable_formation(
    session: Session,
    team_id: int,
    prediction_time: datetime,
    n_matches: int = 10,
) -> JsonDict:
    """Infer a team's probable formation from historical lineups only."""
    session.flush()
    cutoff = ensure_aware_utc(prediction_time)
    history = _team_history(session, team_id, cutoff, limit=n_matches)
    lineups = _latest_lineups_for_fixtures(session, history, team_id, cutoff)
    weighted: dict[str, float] = {}
    counts: dict[str, int] = {}
    for index, lineup in enumerate(lineups[:n_matches]):
        if not lineup.formation:
            continue
        weight = float(n_matches - index)
        weighted[lineup.formation] = weighted.get(lineup.formation, 0.0) + weight
        counts[lineup.formation] = counts.get(lineup.formation, 0) + 1
    if not weighted:
        return {
            "formation": None,
            "confidence": 0.0,
            "formation_stability": 0.0,
            "lineups_used": len(lineups),
        }
    formation = max(weighted, key=lambda key: weighted[key])
    total_weight = sum(weighted.values())
    return {
        "formation": formation,
        "confidence": weighted[formation] / total_weight if total_weight else 0.0,
        "formation_stability": counts[formation] / len(lineups) if lineups else 0.0,
        "lineups_used": len(lineups),
    }


def compute_start_probability(
    session: Session,
    player_id: int,
    team_id: int,
    prediction_time: datetime,
    players_reference: PlayersReference | None = None,
) -> float:
    """Return the V1 start probability for one player at prediction_time."""
    session.flush()
    xi = build_expected_xi(
        session,
        team_id,
        prediction_time,
        players_reference=players_reference,
        exclude_unavailable=False,
    )
    for row in xi["expected_xi"] + xi["bench_candidates"]:
        if row["player_id"] == player_id:
            return float(row["p_start"])
    return 0.0


def build_expected_xi(
    session: Session,
    team_id: int,
    prediction_time: datetime,
    fixture_id: int | None = None,
    players_reference: PlayersReference | None = None,
    *,
    n_matches: int = 10,
    exclude_unavailable: bool = True,
) -> JsonDict:
    """Build a team-level expected XI and bench candidates."""
    session.flush()
    cutoff = ensure_aware_utc(prediction_time)
    context_fixture = _context_fixture(session, team_id, cutoff, fixture_id)
    history = _team_history(
        session,
        team_id,
        cutoff,
        limit=n_matches,
        exclude_fixture_id=fixture_id,
    )
    lineups = _latest_lineups_for_fixtures(session, history, team_id, cutoff)
    stats = _latest_stats_for_fixtures(session, history, team_id, cutoff)
    injuries = (
        _active_injuries_for_team(session, team_id, cutoff, fixture_id)
        if exclude_unavailable
        else {}
    )
    profiles = team_player_profiles(
        session,
        team_id,
        players_reference=players_reference,
        league_id=context_fixture.league_id if context_fixture is not None else None,
        season=context_fixture.season if context_fixture is not None else None,
    )
    _merge_profiles_from_lineups(profiles, team_id, lineups)
    _merge_profiles_from_stats(session, profiles, team_id, stats)
    _merge_profiles_from_injuries(session, profiles, team_id, injuries)
    candidates = {
        player_id: Candidate(profile=profile, usage=PlayerUsage(player_id=player_id))
        for player_id, profile in profiles.items()
    }
    formation_info = infer_probable_formation(session, team_id, cutoff, n_matches=n_matches)
    formation = formation_info["formation"]
    config = PlayerXIConfig(lookback_matches=n_matches)
    _apply_lineup_usage(candidates, lineups, config)
    _apply_player_stats(candidates, stats, len(history))
    _score_candidates(
        candidates,
        formation if isinstance(formation, str) else None,
        injuries,
        config,
    )
    expected = _expected_xi(
        candidates,
        formation if isinstance(formation, str) else None,
        injuries,
    )
    expected_ids = {candidate.profile.player_id for candidate in expected}
    bench = sorted(
        [
            candidate
            for candidate in candidates.values()
            if candidate.profile.player_id not in expected_ids
            and _is_player_available(candidate.profile.player_id, injuries)
        ],
        key=lambda candidate: candidate.score,
        reverse=True,
    )
    return {
        "formation": formation,
        "confidence": formation_info["confidence"],
        "formation_stability": formation_info["formation_stability"],
        "expected_xi": [
            {**_candidate_json(candidate), "expected_role": "starter"}
            for candidate in expected
        ],
        "bench_candidates": [
            {**_candidate_json(candidate), "expected_role": "bench"}
            for candidate in bench[:7]
        ],
        "data_quality": {
            "history_count": len(history),
            "lineups_available": len(lineups),
            "player_stats_available": len({row.fixture_id for row in stats}),
            "reference_fallback_used": any(
                "reference" in candidate.profile.source for candidate in candidates.values()
            ),
            "warnings": [] if len(expected) >= 11 else ["expected_xi_incomplete"],
        },
    }


def xi_stability_features(
    session: Session,
    team_id: int,
    prediction_time: datetime,
    players_reference: PlayersReference | None = None,
) -> JsonDict:
    """Compute XI stability proxies from the latest historical lineups."""
    session.flush()
    cutoff = ensure_aware_utc(prediction_time)
    history = _team_history(session, team_id, cutoff, limit=10)
    lineups = _latest_lineups_for_fixtures(session, history, team_id, cutoff)
    expected = build_expected_xi(
        session,
        team_id,
        cutoff,
        players_reference=players_reference,
        n_matches=10,
    )
    expected_xi = expected["expected_xi"]
    expected_ids = {int(row["player_id"]) for row in expected_xi}
    last5 = lineups[:5]
    starts_by_player = _starts_by_player(last5)
    avg_starts = _mean(starts_by_player.get(player_id, 0) for player_id in expected_ids) or 0.0
    gk_ids = {
        int(row["player_id"])
        for row in expected_xi
        if row.get("position_group") == "GK"
    }
    defender_ids = {
        int(row["player_id"])
        for row in expected_xi
        if row.get("position_group") == "DEF"
    }
    return {
        "xi_stability_score": sum(float(row["p_start"]) for row in expected_xi) / 11
        if expected_xi
        else 0.0,
        "avg_starts_in_last5_for_expected_xi": avg_starts,
        "formation_stability": expected["formation_stability"],
        "gk_stability": _mean(starts_by_player.get(player_id, 0) for player_id in gk_ids) or 0.0,
        "defensive_line_stability": _mean(
            starts_by_player.get(player_id, 0) for player_id in defender_ids
        )
        or 0.0,
        "pair_stability_score": _pair_stability(last5, expected_ids),
    }


def _build_side_context(
    session: Session,
    *,
    target: models.Fixture,
    team_id: int,
    prefix: str,
    prediction_time: datetime,
    players_reference: PlayersReference | None,
    config: PlayerXIConfig,
) -> SideXIContext:
    history = _historical_fixtures(session, target, team_id, prediction_time, config)
    lineups = _latest_lineups(session, history, team_id, prediction_time)
    stats = _latest_player_stats(session, history, team_id, prediction_time)
    injuries = _active_injuries(session, target, team_id, prediction_time)
    profiles = _profiles_for_team(session, target, team_id, players_reference)
    _merge_profiles_from_lineups(profiles, team_id, lineups)
    _merge_profiles_from_stats(session, profiles, team_id, stats)
    _merge_profiles_from_injuries(session, profiles, team_id, injuries)

    candidates = {
        player_id: Candidate(profile=profile, usage=PlayerUsage(player_id=player_id))
        for player_id, profile in profiles.items()
    }
    probable_formation = _probable_formation(lineups, config)
    _apply_lineup_usage(candidates, lineups, config)
    _apply_player_stats(candidates, stats, len(history))
    _score_candidates(candidates, probable_formation, injuries, config)
    expected_xi = _expected_xi(candidates, probable_formation, injuries)
    key_absences = _key_absences(candidates, expected_xi, injuries)

    features = _side_features(prefix, probable_formation, candidates, expected_xi, key_absences)
    warnings: list[str] = []
    if not lineups:
        warnings.append(f"{prefix}: no historical lineups before prediction_time")
    if not stats:
        warnings.append(f"{prefix}: no player stats before prediction_time")
    if len(expected_xi) < 11:
        warnings.append(f"{prefix}: expected XI has fewer than 11 players")
    data_quality = {
        f"{prefix}_lineups_available": len(lineups),
        f"{prefix}_player_stats_available": len({row.fixture_id for row in stats}),
        f"{prefix}_players_with_reference_position": sum(
            1 for candidate in candidates.values() if "reference" in candidate.profile.source
        ),
        f"{prefix}_injuries_available": len(injuries),
        f"{prefix}_reference_fallback_used": any(
            "reference" in candidate.profile.source for candidate in candidates.values()
        ),
        f"{prefix}_warnings": warnings,
    }
    return SideXIContext(features=features, data_quality=data_quality)


def _historical_fixtures(
    session: Session,
    target: models.Fixture,
    team_id: int,
    prediction_time: datetime,
    config: PlayerXIConfig,
) -> list[models.Fixture]:
    stmt = (
        select(models.Fixture)
        .where(
            models.Fixture.fixture_id != target.fixture_id,
            models.Fixture.league_id == target.league_id,
            models.Fixture.season == target.season,
            models.Fixture.date.is_not(None),
            models.Fixture.date < prediction_time,
            or_(models.Fixture.home_team_id == team_id, models.Fixture.away_team_id == team_id),
        )
        .order_by(models.Fixture.date.desc())
        .limit(config.lookback_matches)
    )
    return [
        fixture
        for fixture in session.execute(stmt).scalars()
        if (fixture.status_short or fixture.status or "").upper() in FINISHED_STATUSES
    ]


def _latest_lineups(
    session: Session,
    fixtures: Sequence[models.Fixture],
    team_id: int,
    prediction_time: datetime,
) -> list[models.FixtureLineup]:
    fixture_ids = [fixture.fixture_id for fixture in fixtures]
    if not fixture_ids:
        return []
    stmt = (
        select(models.FixtureLineup)
        .where(
            models.FixtureLineup.fixture_id.in_(fixture_ids),
            models.FixtureLineup.team_id == team_id,
            models.FixtureLineup.fetched_at <= prediction_time,
        )
        .order_by(
            models.FixtureLineup.fixture_id.asc(),
            models.FixtureLineup.fetched_at.desc(),
        )
    )
    latest: dict[int, models.FixtureLineup] = {}
    for lineup in session.execute(stmt).scalars():
        latest.setdefault(lineup.fixture_id, lineup)
    fixture_order = {fixture.fixture_id: index for index, fixture in enumerate(fixtures)}
    return sorted(latest.values(), key=lambda lineup: fixture_order.get(lineup.fixture_id, 999))


def _latest_player_stats(
    session: Session,
    fixtures: Sequence[models.Fixture],
    team_id: int,
    prediction_time: datetime,
) -> list[models.FixturePlayerStats]:
    fixture_ids = [fixture.fixture_id for fixture in fixtures]
    if not fixture_ids:
        return []
    stmt = (
        select(models.FixturePlayerStats)
        .where(
            models.FixturePlayerStats.fixture_id.in_(fixture_ids),
            models.FixturePlayerStats.team_id == team_id,
            models.FixturePlayerStats.fetched_at <= prediction_time,
        )
        .order_by(
            models.FixturePlayerStats.fixture_id.asc(),
            models.FixturePlayerStats.player_id.asc(),
            models.FixturePlayerStats.fetched_at.desc(),
        )
    )
    latest: dict[tuple[int, int], models.FixturePlayerStats] = {}
    for stat in session.execute(stmt).scalars():
        latest.setdefault((stat.fixture_id, stat.player_id), stat)
    return list(latest.values())


def _active_injuries(
    session: Session,
    target: models.Fixture,
    team_id: int,
    prediction_time: datetime,
) -> dict[int, InjuryStatus]:
    stmt = (
        select(models.Injury)
        .where(
            models.Injury.team_id == team_id,
            models.Injury.fetched_at <= prediction_time,
            or_(models.Injury.fixture_id == target.fixture_id, models.Injury.fixture_id.is_(None)),
        )
        .order_by(models.Injury.fetched_at.desc())
    )
    injuries: dict[int, InjuryStatus] = {}
    for injury in session.execute(stmt).scalars():
        if injury.player_id is None:
            continue
        severity = injury_severity(injury.type, injury.reason)
        current = injuries.get(injury.player_id)
        if current is None or severity > current.severity:
            injuries[injury.player_id] = InjuryStatus(
                player_id=injury.player_id,
                severity=severity,
                reason=injury.reason,
                type=injury.type,
                payload_json=injury.payload_json if isinstance(injury.payload_json, dict) else {},
            )
    return injuries


def _profiles_for_team(
    session: Session,
    target: models.Fixture,
    team_id: int,
    players_reference: PlayersReference | None,
) -> dict[int, PlayerProfile]:
    profiles: dict[int, PlayerProfile] = {}
    if players_reference is not None:
        try:
            for player_ref in players_reference.find_players_by_team(team_id):
                profiles[player_ref.player_id] = profile_from_reference(player_ref)
        except ReferenceLookupError:
            pass

    squads = session.execute(
        select(models.PlayerSquad).where(
            models.PlayerSquad.team_id == team_id,
            models.PlayerSquad.league_id == target.league_id,
            models.PlayerSquad.season == target.season,
        )
    ).scalars()
    for squad in squads:
        player = session.get(models.Player, squad.player_id)
        profile = profiles.get(squad.player_id)
        if profile is None:
            profile = PlayerProfile(
                player_id=squad.player_id,
                name=player.name if player is not None else f"player:{squad.player_id}",
                team_id=team_id,
            )
            profiles[squad.player_id] = profile
        if profile.position is None:
            profile.position = squad.position
        if profile.number is None:
            profile.number = squad.number
        if player is not None and not profile.name:
            profile.name = player.name
        profile.position_group = normalize_position_group(profile.position)
        profile.source.add("db_squad")
    return profiles


def _merge_profiles_from_lineups(
    profiles: dict[int, PlayerProfile],
    team_id: int,
    lineups: Sequence[models.FixtureLineup],
) -> None:
    for lineup in lineups:
        for row in _lineup_players(lineup.start_xi_json) + _lineup_players(lineup.substitutes_json):
            player = _player_payload(row)
            player_id = _optional_int(player.get("id"))
            if player_id is None:
                continue
            profile = profiles.setdefault(
                player_id,
                PlayerProfile(
                    player_id=player_id,
                    name=str(player.get("name") or f"player:{player_id}"),
                    team_id=team_id,
                ),
            )
            if profile.position is None:
                profile.position = player.get("pos")
            if profile.number is None:
                profile.number = _optional_int(player.get("number"))
            profile.position_group = normalize_position_group(profile.position)
            profile.source.add("lineup")


def _merge_profiles_from_stats(
    session: Session,
    profiles: dict[int, PlayerProfile],
    team_id: int,
    stats: Sequence[models.FixturePlayerStats],
) -> None:
    for stat in stats:
        player = session.get(models.Player, stat.player_id)
        profile = profiles.setdefault(
            stat.player_id,
            PlayerProfile(
                player_id=stat.player_id,
                name=player.name if player is not None else f"player:{stat.player_id}",
                team_id=team_id,
            ),
        )
        if profile.position is None:
            profile.position = stat.position
        profile.position_group = normalize_position_group(profile.position)
        profile.source.add("player_stats")


def _merge_profiles_from_injuries(
    session: Session,
    profiles: dict[int, PlayerProfile],
    team_id: int,
    injuries: dict[int, InjuryStatus],
) -> None:
    for player_id in injuries:
        player = session.get(models.Player, player_id)
        profile = profiles.setdefault(
            player_id,
            PlayerProfile(
                player_id=player_id,
                name=player.name if player is not None else f"player:{player_id}",
                team_id=team_id,
            ),
        )
        profile.source.add("injury")


def _probable_formation(
    lineups: Sequence[models.FixtureLineup], config: PlayerXIConfig
) -> str | None:
    weighted: dict[str, float] = {}
    for index, lineup in enumerate(lineups[: config.lookback_matches]):
        if not lineup.formation:
            continue
        weighted[lineup.formation] = weighted.get(lineup.formation, 0.0) + (
            config.lookback_matches - index
        )
    if not weighted:
        return None
    return max(weighted, key=lambda formation: weighted[formation])


def _apply_lineup_usage(
    candidates: dict[int, Candidate],
    lineups: Sequence[models.FixtureLineup],
    config: PlayerXIConfig,
) -> None:
    weighted_total = sum(config.lookback_matches - index for index, _ in enumerate(lineups))
    for candidate in candidates.values():
        candidate.usage.weighted_available = float(weighted_total)
        candidate.usage.lineup_appearances = len(lineups)

    for index, lineup in enumerate(lineups):
        weight = float(config.lookback_matches - index)
        for row in _lineup_players(lineup.start_xi_json):
            player = _player_payload(row)
            player_id = _optional_int(player.get("id"))
            if player_id is None or player_id not in candidates:
                continue
            usage = candidates[player_id].usage
            usage.weighted_starts += weight
            usage.starts += 1
            usage.latest_grid = usage.latest_grid or player.get("grid")


def _apply_player_stats(
    candidates: dict[int, Candidate],
    stats: Sequence[models.FixturePlayerStats],
    history_count: int,
) -> None:
    for stat in stats:
        candidate = candidates.get(stat.player_id)
        if candidate is None:
            continue
        usage = candidate.usage
        usage.minutes += stat.minutes or 0
        if stat.rating is not None:
            usage.ratings.append(stat.rating)
        first_stats = stats_first_row(stat.statistics_json)
        usage.goals += nested_int(first_stats, "goals", "total")
        usage.assists += nested_int(first_stats, "goals", "assists")
        usage.shots_on += nested_int(first_stats, "shots", "on")
        usage.shots_total += nested_int(first_stats, "shots", "total")
        if candidate.profile.position is None:
            candidate.profile.position = stat.position
            candidate.profile.position_group = normalize_position_group(stat.position)
    for candidate in candidates.values():
        candidate.usage.lineup_appearances = max(candidate.usage.lineup_appearances, history_count)


def _score_candidates(
    candidates: dict[int, Candidate],
    formation: str | None,
    injuries: dict[int, InjuryStatus],
    config: PlayerXIConfig,
) -> None:
    counts = formation_counts(formation)
    raw_values: dict[int, float] = {}
    groups: dict[int, str] = {}
    for player_id, candidate in candidates.items():
        group = candidate.profile.position_group
        minutes_denominator = 90 * max(candidate.usage.lineup_appearances, 1)
        minutes_share = min(candidate.usage.minutes / minutes_denominator, 1.0)
        compatibility = 1.0 if counts.get(group, 0) > 0 else 0.4
        injury = injuries.get(player_id, InjuryStatus(player_id, 0, None, None, {}))
        availability = max(0.0, 1.0 - 0.7 * injury.severity)
        w_start, w_minutes, w_compat, w_availability = config.p_start_weights
        p_start = (
            w_start * candidate.usage.weighted_start_frequency
            + w_minutes * minutes_share
            + w_compat * compatibility
            + w_availability * availability
        )
        if candidate.usage.weighted_available <= 0 and "reference" in candidate.profile.source:
            p_start = max(p_start, 0.05)
        candidate.p_start = max(0.0, min(p_start, 1.0))
        candidate.raw_value = raw_player_value(candidate.usage, candidate.p_start)
        raw_values[player_id] = candidate.raw_value
        groups[player_id] = group
    normalized = normalize_values_by_position(raw_values, groups)
    for player_id, value in normalized.items():
        candidates[player_id].player_value = value


def _expected_xi(
    candidates: dict[int, Candidate],
    formation: str | None,
    injuries: dict[int, InjuryStatus],
) -> list[Candidate]:
    counts = formation_counts(formation)
    available = [
        candidate
        for candidate in candidates.values()
        if _is_player_available(candidate.profile.player_id, injuries)
    ]
    selected: list[Candidate] = []
    selected_ids: set[int] = set()
    for group in ("GK", "DEF", "MID", "ATT"):
        group_candidates = sorted(
            [candidate for candidate in available if candidate.profile.position_group == group],
            key=lambda candidate: candidate.score,
            reverse=True,
        )
        for candidate in group_candidates[: counts.get(group, 0)]:
            selected.append(candidate)
            selected_ids.add(candidate.profile.player_id)
    if len(selected) < 11:
        remaining = sorted(
            [
                candidate
                for candidate in available
                if candidate.profile.player_id not in selected_ids
            ],
            key=lambda candidate: candidate.score,
            reverse=True,
        )
        selected.extend(remaining[: 11 - len(selected)])
    return sorted(selected, key=lambda candidate: candidate.score, reverse=True)[:11]


def _key_absences(
    candidates: dict[int, Candidate],
    expected_xi: Sequence[Candidate],
    injuries: dict[int, InjuryStatus],
) -> list[JsonDict]:
    expected_ids = {candidate.profile.player_id for candidate in expected_xi}
    absences: list[JsonDict] = []
    for player_id, injury in injuries.items():
        candidate = candidates.get(player_id)
        if candidate is None:
            continue
        replacement = _best_replacement(candidate, candidates, injuries, expected_ids)
        replacement_value = replacement.player_value if replacement is not None else 0.0
        gap = max(candidate.player_value - replacement_value, 0.0)
        impact = absence_impact(
            p_start=candidate.p_start,
            player_value=candidate.player_value,
            severity=injury.severity,
            replacement_gap=gap,
            position_group=candidate.profile.position_group,
            is_central_defender=_is_central_defender(candidate),
        )
        absences.append(
            {
                "player_id": player_id,
                "name": candidate.profile.name,
                "position_group": candidate.profile.position_group,
                "p_start": candidate.p_start,
                "player_value": candidate.player_value,
                "severity": injury.severity,
                "replacement_player_id": replacement.profile.player_id if replacement else None,
                "replacement_value": replacement_value,
                "replacement_gap": gap,
                "absence_impact": impact,
                "reason": injury.reason,
                "type": injury.type,
            }
        )
    return sorted(absences, key=lambda row: row["absence_impact"], reverse=True)


def _side_features(
    prefix: str,
    formation: str | None,
    candidates: dict[int, Candidate],
    expected_xi: Sequence[Candidate],
    key_absences: Sequence[JsonDict],
) -> JsonDict:
    absence_impact_score = sum(float(row["absence_impact"]) for row in key_absences)
    starter_missing_count = sum(
        1 for row in key_absences if float(row["p_start"]) >= 0.35 and float(row["severity"]) >= 0.5
    )
    expected_total_value = sum(candidate.player_value for candidate in expected_xi)
    expected_avg_value = expected_total_value / len(expected_xi) if expected_xi else None
    available_candidates = [
        candidate
        for candidate in candidates.values()
        if all(absence["player_id"] != candidate.profile.player_id for absence in key_absences)
    ]
    expected_ids = {candidate.profile.player_id for candidate in expected_xi}
    bench = sorted(
        [
            candidate
            for candidate in available_candidates
            if candidate.profile.player_id not in expected_ids
        ],
        key=lambda candidate: candidate.score,
        reverse=True,
    )
    replacement_ratios = [
        min(float(row["replacement_value"]) / float(row["player_value"]), 1.0)
        for row in key_absences
        if float(row["player_value"]) > 0
    ]
    return {
        f"{prefix}_probable_formation": formation,
        f"{prefix}_expected_xi_json": [_candidate_json(candidate) for candidate in expected_xi],
        f"{prefix}_key_absences_json": list(key_absences),
        f"{prefix}_expected_xi_avg_value": expected_avg_value,
        f"{prefix}_expected_xi_total_value": expected_total_value,
        f"{prefix}_absence_impact_score": absence_impact_score,
        f"{prefix}_starter_missing_count": starter_missing_count,
        f"{prefix}_absent_expected_starters_count": starter_missing_count,
        f"{prefix}_xi_stability_score": sum(candidate.p_start for candidate in expected_xi) / 11,
        f"{prefix}_bench_depth_score": _mean(candidate.player_value for candidate in bench[:5]),
        f"{prefix}_replacement_quality_score": _mean(replacement_ratios) or 1.0,
        f"{prefix}_availability_score": max(0.0, 1.0 - min(absence_impact_score, 1.0)),
        f"{prefix}_player_stats_coverage_ratio": _ratio(
            sum(1 for candidate in candidates.values() if candidate.usage.minutes > 0),
            len(candidates),
        ),
        f"{prefix}_lineup_coverage_ratio": _ratio(
            sum(1 for candidate in candidates.values() if candidate.usage.weighted_available > 0),
            len(candidates),
        ),
    }


def _best_replacement(
    absent: Candidate,
    candidates: dict[int, Candidate],
    injuries: dict[int, InjuryStatus],
    expected_ids: set[int],
) -> Candidate | None:
    same_group = [
        candidate
        for candidate in candidates.values()
        if candidate.profile.player_id != absent.profile.player_id
        and candidate.profile.player_id not in expected_ids
        and candidate.profile.position_group == absent.profile.position_group
        and _is_player_available(candidate.profile.player_id, injuries)
    ]
    if not same_group:
        same_group = [
            candidate
            for candidate in candidates.values()
            if candidate.profile.player_id != absent.profile.player_id
            and candidate.profile.position_group == absent.profile.position_group
            and _is_player_available(candidate.profile.player_id, injuries)
        ]
    return max(same_group, key=lambda candidate: candidate.score, default=None)


def _is_player_available(player_id: int, injuries: dict[int, InjuryStatus]) -> bool:
    return injuries.get(player_id, InjuryStatus(player_id, 0, None, None, {})).severity < 1


def _context_fixture(
    session: Session,
    team_id: int,
    prediction_time: datetime,
    fixture_id: int | None,
) -> models.Fixture | None:
    if fixture_id is not None:
        return session.get(models.Fixture, fixture_id)
    stmt = (
        select(models.Fixture)
        .where(
            models.Fixture.date < prediction_time,
            or_(models.Fixture.home_team_id == team_id, models.Fixture.away_team_id == team_id),
        )
        .order_by(models.Fixture.date.desc())
        .limit(1)
    )
    return session.execute(stmt).scalar_one_or_none()


def _active_injuries_for_team(
    session: Session,
    team_id: int,
    prediction_time: datetime,
    fixture_id: int | None,
) -> dict[int, InjuryStatus]:
    conditions = [
        models.Injury.team_id == team_id,
        models.Injury.fetched_at <= prediction_time,
    ]
    if fixture_id is None:
        conditions.append(models.Injury.fixture_id.is_(None))
    else:
        conditions.append(
            or_(models.Injury.fixture_id == fixture_id, models.Injury.fixture_id.is_(None))
        )
    stmt = select(models.Injury).where(*conditions).order_by(models.Injury.fetched_at.desc())
    injuries: dict[int, InjuryStatus] = {}
    for injury in session.execute(stmt).scalars():
        if injury.player_id is None:
            continue
        severity = injury_severity(injury.type, injury.reason)
        current = injuries.get(injury.player_id)
        if current is None or severity > current.severity:
            injuries[injury.player_id] = InjuryStatus(
                player_id=injury.player_id,
                severity=severity,
                reason=injury.reason,
                type=injury.type,
                payload_json=injury.payload_json if isinstance(injury.payload_json, dict) else {},
            )
    return injuries


def _starts_by_player(lineups: Sequence[models.FixtureLineup]) -> dict[int, int]:
    starts: dict[int, int] = {}
    for lineup in lineups:
        for row in _lineup_players(lineup.start_xi_json):
            player_id = _optional_int(_player_payload(row).get("id"))
            if player_id is not None:
                starts[player_id] = starts.get(player_id, 0) + 1
    return starts


def _pair_stability(
    lineups: Sequence[models.FixtureLineup],
    expected_ids: set[int],
) -> float:
    if len(expected_ids) < 2 or not lineups:
        return 0.0
    pair_hits = 0
    pair_total = 0
    expected = sorted(expected_ids)
    expected_pairs = {
        (expected[left], expected[right])
        for left in range(len(expected))
        for right in range(left + 1, len(expected))
    }
    for lineup in lineups:
        starters = {
            player_id
            for row in _lineup_players(lineup.start_xi_json)
            if (player_id := _optional_int(_player_payload(row).get("id"))) is not None
        }
        pair_total += len(expected_pairs)
        pair_hits += sum(1 for first, second in expected_pairs if {first, second} <= starters)
    return pair_hits / pair_total if pair_total else 0.0


def _candidate_json(candidate: Candidate) -> JsonDict:
    return {
        "player_id": candidate.profile.player_id,
        "name": candidate.profile.name,
        "position": candidate.profile.position,
        "position_group": candidate.profile.position_group,
        "number": candidate.profile.number,
        "p_start": candidate.p_start,
        "player_value": candidate.player_value,
        "score": candidate.score,
    }


def _lineup_players(payload: Any) -> list[JsonDict]:
    if not isinstance(payload, list):
        return []
    return [row for row in payload if isinstance(row, dict)]


def _player_payload(row: JsonDict) -> JsonDict:
    player = row.get("player")
    return player if isinstance(player, dict) else row


def _optional_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _is_central_defender(candidate: Candidate) -> bool:
    if candidate.profile.position_group != "DEF" or not candidate.usage.latest_grid:
        return False
    return candidate.usage.latest_grid.endswith(":2") or candidate.usage.latest_grid.endswith(":3")


def _mean(values: Sequence[float] | Any) -> float | None:
    numeric = [float(value) for value in values if value is not None]
    if not numeric:
        return None
    return sum(numeric) / len(numeric)


def _ratio(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return numerator / denominator
