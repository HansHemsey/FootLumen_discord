"""Seed the local database from bundled API-Football reference JSON files."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from football_predictor.db import models
from football_predictor.db.repositories import upsert_by_fields
from football_predictor.reference.loaders import load_api_football_reference, load_players_reference
from football_predictor.utils.time import parse_datetime, utc_now

JsonDict = dict[str, Any]


@dataclass
class SeedSummary:
    leagues: int = 0
    seasons: int = 0
    teams: int = 0
    team_seasons: int = 0
    venues: int = 0
    fixtures: int = 0
    standings: int = 0
    rounds: int = 0
    coverage: int = 0
    bookmakers: int = 0
    bets: int = 0
    players: int = 0
    squads: int = 0
    skipped: int = 0
    errors: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, int | list[str]]:
        return {
            "leagues": self.leagues,
            "seasons": self.seasons,
            "teams": self.teams,
            "team_seasons": self.team_seasons,
            "venues": self.venues,
            "fixtures": self.fixtures,
            "standings": self.standings,
            "rounds": self.rounds,
            "coverage": self.coverage,
            "bookmakers": self.bookmakers,
            "bets": self.bets,
            "players": self.players,
            "squads": self.squads,
            "skipped": self.skipped,
            "errors": self.errors,
        }

    def merge(self, other: SeedSummary) -> SeedSummary:
        self.leagues += other.leagues
        self.seasons += other.seasons
        self.teams += other.teams
        self.team_seasons += other.team_seasons
        self.venues += other.venues
        self.fixtures += other.fixtures
        self.standings += other.standings
        self.rounds += other.rounds
        self.coverage += other.coverage
        self.bookmakers += other.bookmakers
        self.bets += other.bets
        self.players += other.players
        self.squads += other.squads
        self.skipped += other.skipped
        self.errors.extend(other.errors)
        return self


class ReferenceSeedService:
    """Seed non-player reference entities from the local competitions JSON."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def seed(self, payload: JsonDict, summary: SeedSummary | None = None) -> SeedSummary:
        result = summary or SeedSummary()
        _seed_api_reference(self.session, payload, result)
        return result


class PlayersSeedService:
    """Seed players and squads from the local players reference JSON."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def seed(self, payload: JsonDict, summary: SeedSummary | None = None) -> SeedSummary:
        result = summary or SeedSummary()
        _seed_players_reference(self.session, payload, result)
        return result


def seed_reference_from_docs(
    session: Session,
    reference_path: str | Path,
    players_path: str | Path,
) -> SeedSummary:
    """Load leagues, teams, venues, fixtures, bookmakers, bets, players and squads.

    This function never calls API-Football and never mutates the source docs files.
    """
    api_reference = load_api_football_reference(reference_path)
    players_reference = load_players_reference(players_path)
    summary = SeedSummary()

    ReferenceSeedService(session).seed(api_reference.payload, summary)
    PlayersSeedService(session).seed(players_reference.payload, summary)
    session.flush()
    return summary


def _seed_api_reference(session: Session, payload: JsonDict, summary: SeedSummary) -> None:
    for competition in payload.get("competitions", []):
        _seed_competition(session, competition, summary)
    _seed_global_references(session, payload.get("references", {}), summary)


def _seed_competition(session: Session, competition: JsonDict, summary: SeedSummary) -> None:
    target = competition.get("target") or {}
    league = competition.get("league") or {}
    league_id = league.get("id")
    season = league.get("season") or target.get("season")
    if league_id is None or season is None:
        summary.errors.append(f"Skipped competition without league_id/season: {target.get('key')}")
        summary.skipped += 1
        return

    upsert_by_fields(
        session,
        models.League,
        {"league_id": int(league_id), "season": int(season)},
        {
            "name": league.get("name") or target.get("display_name") or "",
            "country": league.get("country") or target.get("country"),
            "type": league.get("type") or target.get("category"),
            "country_code": league.get("country_code"),
            "category": target.get("category"),
            "logo": league.get("logo"),
            "season_start": league.get("season_start"),
            "season_end": league.get("season_end"),
            "payload_json": league,
        },
    )
    summary.leagues += 1
    summary.seasons += 1
    summary.rounds += len(competition.get("rounds") or [])
    if league.get("coverage") or competition.get("coverage"):
        summary.coverage += 1

    for team in competition.get("teams") or []:
        _seed_team(session, team, int(league_id), int(season), target.get("key"), summary)

    for standing in competition.get("standings") or []:
        _seed_standing(session, standing, int(league_id), int(season), summary)

    for fixture in competition.get("fixtures") or []:
        _seed_fixture(session, fixture, summary)


def _seed_team(
    session: Session,
    team: JsonDict,
    league_id: int,
    season: int,
    competition_key: str | None,
    summary: SeedSummary,
) -> None:
    team_id = team.get("team_id")
    if team_id is None:
        summary.errors.append(f"Skipped team without team_id in league_id={league_id}")
        summary.skipped += 1
        return
    venue_id = team.get("venue_id")
    if venue_id is not None:
        raw_venue = (team.get("raw") or {}).get("venue") or {}
        upsert_by_fields(
            session,
            models.Venue,
            {"venue_id": int(venue_id)},
            {
                "name": team.get("venue_name"),
                "address": raw_venue.get("address"),
                "city": team.get("venue_city"),
                "capacity": team.get("venue_capacity"),
                "surface": team.get("venue_surface"),
                "image": team.get("venue_image"),
                "payload_json": raw_venue,
            },
        )
        summary.venues += 1

    upsert_by_fields(
        session,
        models.Team,
        {"team_id": int(team_id)},
        {
            "name": team.get("name") or "",
            "code": team.get("code"),
            "country": team.get("country"),
            "founded": team.get("founded"),
            "national": team.get("national"),
            "logo": team.get("logo"),
            "venue_id": int(venue_id) if venue_id is not None else None,
            "payload_json": team,
        },
    )
    summary.teams += 1

    upsert_by_fields(
        session,
        models.TeamSeason,
        {"team_id": int(team_id), "league_id": league_id, "season": season},
        {"competition_key": competition_key, "payload_json": team},
    )
    summary.team_seasons += 1


def _seed_standing(
    session: Session, standing: JsonDict, league_id: int, season: int, summary: SeedSummary
) -> None:
    team_id = standing.get("team_id")
    if team_id is None:
        summary.errors.append(f"Skipped standing without team_id in league_id={league_id}")
        summary.skipped += 1
        return
    raw = standing.get("raw") or {}
    all_stats = raw.get("all") or {}
    all_goals = all_stats.get("goals") or {}
    home_stats = raw.get("home") or {}
    away_stats = raw.get("away") or {}
    snapshot_date = parse_datetime(raw.get("update")) or utc_now()
    upsert_by_fields(
        session,
        models.StandingSnapshot,
        {
            "league_id": league_id,
            "season": season,
            "team_id": int(team_id),
            "snapshot_date": snapshot_date,
        },
        {
            "fetched_at": snapshot_date,
            "rank": standing.get("rank"),
            "points": standing.get("points"),
            "goals_diff": standing.get("goals_diff") or raw.get("goalsDiff"),
            "form": standing.get("form") or raw.get("form"),
            "description": standing.get("description") or raw.get("description"),
            "played": standing.get("played"),
            "all_played": all_stats.get("played"),
            "all_win": all_stats.get("win"),
            "all_draw": all_stats.get("draw"),
            "all_lose": all_stats.get("lose"),
            "all_goals_for": all_goals.get("for"),
            "all_goals_against": all_goals.get("against"),
            "home_played": home_stats.get("played"),
            "home_win": home_stats.get("win"),
            "home_draw": home_stats.get("draw"),
            "home_lose": home_stats.get("lose"),
            "away_played": away_stats.get("played"),
            "away_win": away_stats.get("win"),
            "away_draw": away_stats.get("draw"),
            "away_lose": away_stats.get("lose"),
            "goals_for": standing.get("goals_for"),
            "goals_against": standing.get("goals_against"),
            "payload_json": {**standing, "ingestion_source": "docs/reference"},
        },
    )
    summary.standings += 1


def _seed_fixture(session: Session, fixture: JsonDict, summary: SeedSummary) -> None:
    fixture_id = fixture.get("fixture_id")
    if fixture_id is None:
        summary.errors.append("Skipped fixture without fixture_id")
        summary.skipped += 1
        return
    venue_id = fixture.get("venue_id")
    if venue_id is not None:
        upsert_by_fields(
            session,
            models.Venue,
            {"venue_id": int(venue_id)},
            {
                "name": fixture.get("venue_name"),
                "address": None,
                "city": fixture.get("venue_city"),
                "capacity": None,
                "surface": None,
                "image": None,
                "payload_json": {
                    "id": venue_id,
                    "name": fixture.get("venue_name"),
                    "city": fixture.get("venue_city"),
                },
            },
        )
    upsert_by_fields(
        session,
        models.Fixture,
        {"fixture_id": int(fixture_id)},
        {
            "date": parse_datetime(fixture.get("date")),
            "timestamp": fixture.get("timestamp"),
            "timezone": fixture.get("timezone"),
            "round": fixture.get("round"),
            "league_id": int(fixture["league_id"]),
            "season": int(fixture["season"]),
            "venue_id": int(venue_id) if venue_id is not None else None,
            "venue_name": fixture.get("venue_name"),
            "venue_city": fixture.get("venue_city"),
            "referee": fixture.get("referee"),
            "status": fixture.get("status_short") or fixture.get("status_long"),
            "status_long": fixture.get("status_long"),
            "status_short": fixture.get("status_short"),
            "elapsed": fixture.get("elapsed"),
            "home_team_id": int(fixture["home_team_id"]),
            "away_team_id": int(fixture["away_team_id"]),
            "home_team": fixture.get("home_team") or "",
            "away_team": fixture.get("away_team") or "",
            "home_goals": fixture.get("goals_home"),
            "away_goals": fixture.get("goals_away"),
            "goals_home": fixture.get("goals_home"),
            "goals_away": fixture.get("goals_away"),
            "payload_json": {**fixture, "ingestion_source": "docs/reference"},
        },
    )
    summary.fixtures += 1


def _seed_global_references(session: Session, references: JsonDict, summary: SeedSummary) -> None:
    for bookmaker in references.get("bookmakers") or []:
        bookmaker_id = bookmaker.get("id")
        if bookmaker_id is None:
            summary.skipped += 1
            continue
        upsert_by_fields(
            session,
            models.Bookmaker,
            {"bookmaker_id": int(bookmaker_id)},
            {"name": bookmaker.get("name") or "", "payload_json": bookmaker},
        )
        summary.bookmakers += 1

    for bet_type, key in (("prematch", "prematch_bets"), ("live", "live_bets")):
        for bet in references.get(key) or []:
            bet_id = bet.get("id")
            if bet_id is None:
                summary.skipped += 1
                continue
            upsert_by_fields(
                session,
                models.Bet,
                {"bet_id": int(bet_id), "bet_type": bet_type},
                {"name": bet.get("name") or "", "bet_type": bet_type, "payload_json": bet},
            )
            summary.bets += 1


def _seed_players_reference(session: Session, payload: JsonDict, summary: SeedSummary) -> None:
    seen_players: set[int] = set()
    seen_squads: set[tuple[int, int, int, int]] = set()
    for competition in payload.get("competitions", []):
        for team_entry in competition.get("teams") or []:
            team = team_entry.get("team") or {}
            fetched_at = parse_datetime(team_entry.get("fetched_at"))
            for player in team_entry.get("players") or []:
                _seed_player(session, player, team, fetched_at, summary, seen_players, seen_squads)


def _seed_player(
    session: Session,
    player: JsonDict,
    team: JsonDict,
    fetched_at: Any,
    summary: SeedSummary,
    seen_players: set[int],
    seen_squads: set[tuple[int, int, int, int]],
) -> None:
    player_id = player.get("player_id")
    team_id = team.get("team_id")
    league_id = team.get("league_id")
    season = team.get("season")
    if player_id is None or team_id is None or league_id is None or season is None:
        summary.errors.append(f"Skipped incomplete player row: {player.get('name')}")
        summary.skipped += 1
        return

    typed_player_id = int(player_id)
    typed_team_id = int(team_id)
    typed_league_id = int(league_id)
    typed_season = int(season)

    if typed_player_id not in seen_players:
        upsert_by_fields(
            session,
            models.Player,
            {"player_id": typed_player_id},
            {
                "name": player.get("name") or "",
                "firstname": player.get("firstname"),
                "lastname": player.get("lastname"),
                "age": player.get("age"),
                "birth_date": (player.get("birth") or {}).get("date")
                if isinstance(player.get("birth"), dict)
                else None,
                "nationality": player.get("nationality"),
                "height": player.get("height"),
                "weight": player.get("weight"),
                "injured": player.get("injured"),
                "photo": player.get("photo"),
                "payload_json": player,
            },
        )
        seen_players.add(typed_player_id)
        summary.players += 1

    squad_key = (typed_player_id, typed_team_id, typed_league_id, typed_season)
    if squad_key in seen_squads:
        return

    upsert_by_fields(
        session,
        models.PlayerSquad,
        {
            "player_id": typed_player_id,
            "team_id": typed_team_id,
            "league_id": typed_league_id,
            "season": typed_season,
        },
        {
            "position": player.get("position"),
            "number": player.get("number"),
            "fetched_at": fetched_at or utc_now(),
            "payload_json": {"player": player, "team": team},
        },
    )
    seen_squads.add(squad_key)
    summary.squads += 1
