"""Player profile, position and value helpers for XI features."""

from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from football_predictor.db import models
from football_predictor.reference.lookups import PlayersReference
from football_predictor.reference.schemas import PlayerRef
from football_predictor.utils.exceptions import ReferenceLookupError
from football_predictor.utils.time import ensure_aware_utc

JsonDict = dict[str, Any]
FINISHED_STATUSES = {"FT", "AET", "PEN"}


@dataclass
class PlayerProfile:
    player_id: int
    name: str
    team_id: int
    position: str | None = None
    position_group: str = "UNK"
    number: int | None = None
    source: set[str] = field(default_factory=set)


@dataclass
class PlayerUsage:
    player_id: int
    weighted_starts: float = 0.0
    weighted_available: float = 0.0
    starts: int = 0
    lineup_appearances: int = 0
    minutes: int = 0
    ratings: list[float] = field(default_factory=list)
    goals: int = 0
    assists: int = 0
    shots_on: int = 0
    shots_total: int = 0
    latest_grid: str | None = None

    @property
    def weighted_start_frequency(self) -> float:
        if self.weighted_available <= 0:
            return 0.0
        return min(self.weighted_starts / self.weighted_available, 1.0)

    @property
    def average_rating(self) -> float | None:
        if not self.ratings:
            return None
        return sum(self.ratings) / len(self.ratings)


@dataclass
class PlayerFormAccumulator:
    player_id: int
    name: str
    position: str | None = None
    position_group: str = "UNK"
    minutes_by_fixture: dict[int, int] = field(default_factory=dict)
    starts_by_fixture: dict[int, int] = field(default_factory=dict)
    ratings_by_fixture: dict[int, float] = field(default_factory=dict)
    goals_by_fixture: dict[int, int] = field(default_factory=lambda: defaultdict(int))
    assists_by_fixture: dict[int, int] = field(default_factory=lambda: defaultdict(int))
    cards_by_fixture: dict[int, int] = field(default_factory=lambda: defaultdict(int))
    positions: Counter[str] = field(default_factory=Counter)


def normalize_position_group(position: str | None) -> str:
    """Normalize API-Football/squad positions to GK/DEF/MID/ATT."""
    if not position:
        return "UNK"
    normalized = position.strip().casefold()
    if normalized in {"g", "gk", "goalkeeper", "keeper"}:
        return "GK"
    if normalized in {"d", "def", "defender", "back", "centre-back", "center-back"}:
        return "DEF"
    if normalized in {"m", "mid", "midfielder", "dm", "cm", "am"}:
        return "MID"
    if normalized in {"f", "fw", "att", "attacker", "forward", "striker"}:
        return "ATT"
    return "UNK"


def build_player_recent_form(
    session: Session,
    team_id: int,
    prediction_time: datetime,
    windows: Sequence[int] = (3, 5, 10),
    players_reference: PlayersReference | None = None,
    *,
    exclude_fixture_id: int | None = None,
) -> dict[int, JsonDict]:
    """Build point-in-time recent player form for one team."""
    session.flush()
    cutoff = ensure_aware_utc(prediction_time)
    max_window = max(windows, default=10)
    fixtures = _team_history(
        session,
        team_id,
        cutoff,
        limit=max_window,
        exclude_fixture_id=exclude_fixture_id,
    )
    lineups = _latest_lineups_for_fixtures(session, fixtures, team_id, cutoff)
    stats = _latest_stats_for_fixtures(session, fixtures, team_id, cutoff)
    events = _events_for_fixtures(session, fixtures, team_id, cutoff)
    profiles = team_player_profiles(
        session,
        team_id,
        players_reference=players_reference,
    )
    accumulators = _form_accumulators_from_profiles(profiles, team_id)
    fixture_ids = [fixture.fixture_id for fixture in fixtures]

    _collect_lineup_form(accumulators, team_id, lineups)
    _collect_stat_form(session, accumulators, team_id, stats)
    _collect_event_form(accumulators, events)

    result: dict[int, JsonDict] = {}
    for player_id, accumulator in accumulators.items():
        position = accumulator.position or _most_common(accumulator.positions)
        position_group = normalize_position_group(position) or accumulator.position_group
        row: JsonDict = {
            "player_id": player_id,
            "name": accumulator.name,
            "team_id": team_id,
            "position": position,
            "position_group": position_group,
            "history_fixture_count": len(fixture_ids),
            "position_most_frequent": position,
            "last_match_minutes": _latest_value(accumulator.minutes_by_fixture, fixture_ids),
            "ewma_minutes": _ewma(
                [
                    float(accumulator.minutes_by_fixture.get(fixture_id, 0))
                    for fixture_id in reversed(fixture_ids)
                ]
            ),
            "ewma_rating": _ewma(
                [
                    accumulator.ratings_by_fixture[fixture_id]
                    for fixture_id in reversed(fixture_ids)
                    if fixture_id in accumulator.ratings_by_fixture
                ]
            ),
        }
        for window in windows:
            scoped_fixture_ids = fixture_ids[:window]
            ratings = [
                accumulator.ratings_by_fixture[fixture_id]
                for fixture_id in scoped_fixture_ids
                if fixture_id in accumulator.ratings_by_fixture
            ]
            row.update(
                {
                    f"minutes_recent_last{window}": sum(
                        accumulator.minutes_by_fixture.get(fixture_id, 0)
                        for fixture_id in scoped_fixture_ids
                    ),
                    f"starts_recent_last{window}": sum(
                        accumulator.starts_by_fixture.get(fixture_id, 0)
                        for fixture_id in scoped_fixture_ids
                    ),
                    f"average_rating_last{window}": _mean(ratings),
                    f"goals_last{window}": sum(
                        accumulator.goals_by_fixture.get(fixture_id, 0)
                        for fixture_id in scoped_fixture_ids
                    ),
                    f"assists_last{window}": sum(
                        accumulator.assists_by_fixture.get(fixture_id, 0)
                        for fixture_id in scoped_fixture_ids
                    ),
                    f"cards_last{window}": sum(
                        accumulator.cards_by_fixture.get(fixture_id, 0)
                        for fixture_id in scoped_fixture_ids
                    ),
                }
            )
        result[player_id] = row
    return result


def compute_player_value(
    session: Session,
    player_id: int,
    team_id: int,
    prediction_time: datetime,
    players_reference: PlayersReference | None = None,
) -> JsonDict:
    """Compute a point-in-time player value normalized within the player's position."""
    session.flush()
    form = build_player_recent_form(
        session,
        team_id,
        prediction_time,
        windows=(10,),
        players_reference=players_reference,
    )
    profiles = team_player_profiles(session, team_id, players_reference=players_reference)
    if player_id not in form and player_id in profiles:
        profile = profiles[player_id]
        form[player_id] = {
            "player_id": player_id,
            "name": profile.name,
            "team_id": team_id,
            "position": profile.position,
            "position_group": profile.position_group,
            "history_fixture_count": 0,
            "minutes_recent_last10": 0,
            "starts_recent_last10": 0,
            "average_rating_last10": None,
            "goals_last10": 0,
            "assists_last10": 0,
            "cards_last10": 0,
        }
    row = form.get(player_id)
    if row is None:
        return {
            "player_id": player_id,
            "team_id": team_id,
            "position_group": "UNK",
            "value_zscore": 0.0,
            "value_0_100": 50.0,
            "data_quality": "missing_player",
        }

    raw_scores = {
        candidate_id: _raw_value_from_form(candidate)
        for candidate_id, candidate in form.items()
    }
    groups = {
        candidate_id: str(candidate.get("position_group") or "UNK")
        for candidate_id, candidate in form.items()
    }
    group = str(row.get("position_group") or "UNK")
    peer_values = [
        raw_scores[candidate_id]
        for candidate_id, candidate_group in groups.items()
        if candidate_group == group
    ]
    raw_score = raw_scores[player_id]
    zscore = _zscore(raw_score, peer_values)
    normalized = normalize_values_by_position(raw_scores, groups).get(player_id, raw_score)
    return {
        "player_id": player_id,
        "team_id": team_id,
        "position": row.get("position"),
        "position_group": group,
        "value_zscore": zscore,
        "value_0_100": max(0.0, min(100.0, normalized * 100)),
        "raw_value": raw_score,
        "rating_available": row.get("average_rating_last10") is not None,
    }


def formation_counts(formation: str | None) -> dict[str, int]:
    """Return coarse position counts from a football formation string."""
    counts = {"GK": 1, "DEF": 4, "MID": 4, "ATT": 2}
    if not formation:
        return counts
    try:
        parts = [int(part) for part in formation.split("-") if part.strip().isdigit()]
    except ValueError:
        return counts
    if not parts or sum(parts) != 10:
        return counts
    counts["DEF"] = parts[0]
    counts["ATT"] = parts[-1]
    counts["MID"] = sum(parts[1:-1]) if len(parts) > 2 else 10 - parts[0] - parts[-1]
    return counts


def profile_from_reference(player: PlayerRef) -> PlayerProfile:
    return PlayerProfile(
        player_id=player.player_id,
        name=player.name,
        team_id=player.team_id,
        position=player.position,
        position_group=normalize_position_group(player.position),
        number=player.number,
        source={"reference"},
    )


def team_player_profiles(
    session: Session,
    team_id: int,
    players_reference: PlayersReference | None = None,
    *,
    league_id: int | None = None,
    season: int | None = None,
) -> dict[int, PlayerProfile]:
    """Load player identities from DB first and optional local reference as fallback."""
    profiles: dict[int, PlayerProfile] = {}
    if players_reference is not None:
        try:
            for player_ref in players_reference.find_players_by_team(team_id):
                profiles[player_ref.player_id] = profile_from_reference(player_ref)
        except ReferenceLookupError:
            pass

    stmt = select(models.PlayerSquad).where(models.PlayerSquad.team_id == team_id)
    if league_id is not None:
        stmt = stmt.where(models.PlayerSquad.league_id == league_id)
    if season is not None:
        stmt = stmt.where(models.PlayerSquad.season == season)
    for squad in session.execute(stmt).scalars():
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
        if player is not None:
            profile.name = player.name
        profile.position_group = normalize_position_group(profile.position)
        profile.source.add("db_squad")
    return profiles


def raw_player_value(usage: PlayerUsage, p_start: float) -> float:
    """Create a pre-normalized player value from point-in-time usage and stats."""
    rating_component = ((usage.average_rating or 6.0) - 5.0) / 5.0
    rating_component = max(0.0, min(rating_component, 1.0))
    minutes_component = min(usage.minutes / (90 * max(usage.lineup_appearances, 1)), 1.0)
    contribution_component = min((usage.goals + usage.assists + 0.2 * usage.shots_on) / 5, 1.0)
    return max(
        0.05,
        min(
            1.0,
            0.40 * rating_component
            + 0.25 * minutes_component
            + 0.20 * p_start
            + 0.15 * contribution_component,
        ),
    )


def normalize_values_by_position(
    raw_values: dict[int, float],
    groups: dict[int, str],
) -> dict[int, float]:
    """Normalize raw values within each position group, never across GK/DEF/MID/ATT."""
    normalized: dict[int, float] = {}
    for group in {"GK", "DEF", "MID", "ATT", "UNK"}:
        player_ids = [
            player_id
            for player_id, player_group in groups.items()
            if player_group == group
        ]
        values = [raw_values[player_id] for player_id in player_ids]
        if not player_ids:
            continue
        minimum = min(values)
        maximum = max(values)
        for player_id in player_ids:
            if maximum == minimum:
                normalized[player_id] = max(0.05, min(raw_values[player_id], 1.0))
            else:
                relative_value = (raw_values[player_id] - minimum) / (maximum - minimum)
                normalized[player_id] = 0.2 + 0.8 * relative_value
    return normalized


def stats_first_row(stats_json: Any) -> JsonDict:
    if isinstance(stats_json, list) and stats_json and isinstance(stats_json[0], dict):
        return stats_json[0]
    if isinstance(stats_json, dict):
        return stats_json
    return {}


def nested_int(payload: JsonDict, *path: str) -> int:
    value: Any = payload
    for key in path:
        if not isinstance(value, dict):
            return 0
        value = value.get(key)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        try:
            return int(float(value.strip().replace("%", "")))
        except ValueError:
            return 0
    return 0


def _team_history(
    session: Session,
    team_id: int,
    prediction_time: datetime,
    *,
    limit: int,
    exclude_fixture_id: int | None = None,
) -> list[models.Fixture]:
    stmt = (
        select(models.Fixture)
        .where(
            models.Fixture.date.is_not(None),
            models.Fixture.date < prediction_time,
            or_(models.Fixture.home_team_id == team_id, models.Fixture.away_team_id == team_id),
        )
        .order_by(models.Fixture.date.desc())
        .limit(limit)
    )
    if exclude_fixture_id is not None:
        stmt = stmt.where(models.Fixture.fixture_id != exclude_fixture_id)
    return [
        fixture
        for fixture in session.execute(stmt).scalars()
        if (fixture.status_short or fixture.status or "").upper() in FINISHED_STATUSES
    ]


def _latest_lineups_for_fixtures(
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


def _latest_stats_for_fixtures(
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


def _events_for_fixtures(
    session: Session,
    fixtures: Sequence[models.Fixture],
    team_id: int,
    prediction_time: datetime,
) -> list[models.FixtureEvent]:
    fixture_ids = [fixture.fixture_id for fixture in fixtures]
    if not fixture_ids:
        return []
    stmt = select(models.FixtureEvent).where(
        models.FixtureEvent.fixture_id.in_(fixture_ids),
        models.FixtureEvent.team_id == team_id,
        models.FixtureEvent.fetched_at <= prediction_time,
    )
    return list(session.execute(stmt).scalars())


def _form_accumulators_from_profiles(
    profiles: dict[int, PlayerProfile],
    team_id: int,
) -> dict[int, PlayerFormAccumulator]:
    return {
        player_id: PlayerFormAccumulator(
            player_id=player_id,
            name=profile.name,
            position=profile.position,
            position_group=profile.position_group,
        )
        for player_id, profile in profiles.items()
        if profile.team_id == team_id
    }


def _collect_lineup_form(
    accumulators: dict[int, PlayerFormAccumulator],
    team_id: int,
    lineups: Sequence[models.FixtureLineup],
) -> None:
    for lineup in lineups:
        for row in _lineup_rows(lineup.start_xi_json):
            player = _player_payload(row)
            player_id = _optional_int(player.get("id"))
            if player_id is None:
                continue
            accumulator = accumulators.setdefault(
                player_id,
                PlayerFormAccumulator(
                    player_id=player_id,
                    name=str(player.get("name") or f"player:{player_id}"),
                ),
            )
            accumulator.starts_by_fixture[lineup.fixture_id] = 1
            _set_position(accumulator, player.get("pos"))
        for row in _lineup_rows(lineup.substitutes_json):
            player = _player_payload(row)
            player_id = _optional_int(player.get("id"))
            if player_id is None:
                continue
            accumulator = accumulators.setdefault(
                player_id,
                PlayerFormAccumulator(
                    player_id=player_id,
                    name=str(player.get("name") or f"player:{player_id}"),
                ),
            )
            _set_position(accumulator, player.get("pos"))
            accumulator.starts_by_fixture.setdefault(lineup.fixture_id, 0)


def _collect_stat_form(
    session: Session,
    accumulators: dict[int, PlayerFormAccumulator],
    team_id: int,
    stats: Sequence[models.FixturePlayerStats],
) -> None:
    for stat in stats:
        player = session.get(models.Player, stat.player_id)
        accumulator = accumulators.setdefault(
            stat.player_id,
            PlayerFormAccumulator(
                player_id=stat.player_id,
                name=player.name if player is not None else f"player:{stat.player_id}",
            ),
        )
        accumulator.minutes_by_fixture[stat.fixture_id] = stat.minutes or 0
        rating = (
            stat.rating if stat.rating is not None else _rating_from_stats(stat.statistics_json)
        )
        if rating is not None:
            accumulator.ratings_by_fixture[stat.fixture_id] = rating
        _set_position(accumulator, stat.position)
        first_stats = stats_first_row(stat.statistics_json)
        accumulator.goals_by_fixture[stat.fixture_id] = max(
            accumulator.goals_by_fixture.get(stat.fixture_id, 0),
            nested_int(first_stats, "goals", "total"),
        )
        accumulator.assists_by_fixture[stat.fixture_id] = max(
            accumulator.assists_by_fixture.get(stat.fixture_id, 0),
            nested_int(first_stats, "goals", "assists"),
        )


def _collect_event_form(
    accumulators: dict[int, PlayerFormAccumulator],
    events: Sequence[models.FixtureEvent],
) -> None:
    for event in events:
        if event.player_id is None:
            continue
        accumulator = accumulators.setdefault(
            event.player_id,
            PlayerFormAccumulator(
                player_id=event.player_id,
                name=f"player:{event.player_id}",
            ),
        )
        event_type = (event.type or event.event_type or "").casefold()
        detail = (event.detail or "").casefold()
        if event_type == "goal":
            accumulator.goals_by_fixture[event.fixture_id] += 1
        if event.assist_player_id is not None:
            assist = accumulators.setdefault(
                event.assist_player_id,
                PlayerFormAccumulator(
                    player_id=event.assist_player_id,
                    name=f"player:{event.assist_player_id}",
                ),
            )
            assist.assists_by_fixture[event.fixture_id] += 1
        if event_type == "card" or "card" in detail:
            accumulator.cards_by_fixture[event.fixture_id] += 1


def _set_position(accumulator: PlayerFormAccumulator, position: Any) -> None:
    if position is None:
        return
    position_text = str(position)
    accumulator.positions[position_text] += 1
    if accumulator.position is None:
        accumulator.position = position_text
        accumulator.position_group = normalize_position_group(position_text)


def _lineup_rows(payload: Any) -> list[JsonDict]:
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


def _rating_from_stats(stats_json: Any) -> float | None:
    first_stats = stats_first_row(stats_json)
    games_payload = first_stats.get("games")
    games = games_payload if isinstance(games_payload, dict) else {}
    return _optional_float(games.get("rating"))


def _optional_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(str(value).replace("%", "").strip())
    except (TypeError, ValueError):
        return None


def _most_common(counter: Counter[str]) -> str | None:
    if not counter:
        return None
    return counter.most_common(1)[0][0]


def _latest_value(values_by_fixture: dict[int, int], fixture_ids: Sequence[int]) -> int | None:
    for fixture_id in fixture_ids:
        if fixture_id in values_by_fixture:
            return values_by_fixture[fixture_id]
    return None


def _mean(values: Sequence[float]) -> float | None:
    numeric = [value for value in values if value is not None]
    if not numeric:
        return None
    return sum(numeric) / len(numeric)


def _ewma(values: Sequence[float], *, alpha: float = 0.35) -> float | None:
    if not values:
        return None
    current = float(values[0])
    for value in values[1:]:
        current = alpha * float(value) + (1 - alpha) * current
    return current


def _raw_value_from_form(row: JsonDict) -> float:
    matches = max(int(row.get("history_fixture_count") or 1), 1)
    rating = row.get("average_rating_last10")
    rating_component = 0.5 if rating is None else max(0.0, min((float(rating) - 5.0) / 5.0, 1.0))
    minutes_share = min(float(row.get("minutes_recent_last10") or 0) / (90 * matches), 1.0)
    start_share = min(float(row.get("starts_recent_last10") or 0) / matches, 1.0)
    contributions = min(
        (float(row.get("goals_last10") or 0) + float(row.get("assists_last10") or 0)) / 5,
        1.0,
    )
    discipline_penalty = min(float(row.get("cards_last10") or 0) / 10, 0.25)
    return max(
        0.05,
        min(
            1.0,
            0.35 * rating_component
            + 0.25 * minutes_share
            + 0.20 * start_share
            + 0.15 * contributions
            - 0.05 * discipline_penalty,
        ),
    )


def _zscore(value: float, peers: Sequence[float]) -> float:
    if len(peers) < 2:
        return 0.0
    mean = sum(peers) / len(peers)
    variance = sum((peer - mean) ** 2 for peer in peers) / len(peers)
    if variance <= 0:
        return 0.0
    return float((value - mean) / (variance**0.5))
