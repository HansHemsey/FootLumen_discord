"""Lookup indexes over local API-Football reference files."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from football_predictor.reference.schemas import (
    BetRef,
    BookmakerRef,
    FixtureRef,
    LeagueRef,
    PlayerRef,
    TeamRef,
)
from football_predictor.utils.exceptions import ReferenceLookupError

JsonDict = dict[str, Any]


def _normalize(value: str) -> str:
    return " ".join(value.casefold().replace("-", " ").split())


class ApiFootballReference:
    """Machine-readable reference for competitions, teams, fixtures and bets."""

    def __init__(self, payload: JsonDict) -> None:
        self.payload = payload
        self.meta = payload.get("meta", {})
        self.competitions: list[JsonDict] = list(payload.get("competitions", []))
        self.references: JsonDict = dict(payload.get("references", {}))
        self._leagues_by_id: dict[tuple[int, int | None], LeagueRef] = {}
        self._leagues_by_key: dict[str, LeagueRef] = {}
        self._teams_by_id: dict[int, list[TeamRef]] = defaultdict(list)
        self._teams_by_name: dict[str, list[TeamRef]] = defaultdict(list)
        self._fixtures_by_id: dict[int, FixtureRef] = {}
        self._bookmakers_by_id: dict[int, BookmakerRef] = {}
        self._bookmakers_by_name: dict[str, BookmakerRef] = {}
        self._bets_by_id: dict[int, BetRef] = {}
        self._bets_by_name: dict[str, BetRef] = {}
        self._build_indexes()

    def _build_indexes(self) -> None:
        for competition in self.competitions:
            league = competition.get("league") or {}
            target = competition.get("target") or {}
            league_id = league.get("id")
            season = league.get("season") or target.get("season")
            if league_id is None:
                continue
            league_ref = LeagueRef(
                league_id=int(league_id),
                name=str(league.get("name") or target.get("display_name") or ""),
                season=int(season) if season is not None else 0,
                country=league.get("country") or target.get("country"),
                category=target.get("category"),
                key=target.get("key"),
                raw=competition,
            )
            self._leagues_by_id[(league_ref.league_id, league_ref.season)] = league_ref
            self._leagues_by_id[(league_ref.league_id, None)] = league_ref
            if league_ref.key:
                self._leagues_by_key[_normalize(league_ref.key)] = league_ref

            for team in competition.get("teams") or []:
                team_id = team.get("team_id")
                if team_id is None:
                    continue
                team_ref = TeamRef(
                    team_id=int(team_id),
                    name=str(team.get("name") or ""),
                    league_id=league_ref.league_id,
                    season=league_ref.season,
                    country=team.get("country"),
                    venue_id=team.get("venue_id"),
                    raw=team,
                )
                self._teams_by_id[team_ref.team_id].append(team_ref)
                self._teams_by_name[_normalize(team_ref.name)].append(team_ref)

            for fixture in competition.get("fixtures") or []:
                fixture_id = fixture.get("fixture_id")
                if fixture_id is None:
                    continue
                self._fixtures_by_id[int(fixture_id)] = FixtureRef.from_record(fixture)

        for bookmaker in self.references.get("bookmakers") or []:
            bookmaker_id = bookmaker.get("id")
            if bookmaker_id is not None:
                bookmaker_ref = BookmakerRef(
                    bookmaker_id=int(bookmaker_id),
                    name=str(bookmaker.get("name") or ""),
                    raw=bookmaker,
                )
                self._bookmakers_by_id[int(bookmaker_id)] = bookmaker_ref
                self._bookmakers_by_name[_normalize(bookmaker_ref.name)] = bookmaker_ref

        for key in ("prematch_bets", "live_bets"):
            for bet in self.references.get(key) or []:
                bet_id = bet.get("id")
                if bet_id is not None:
                    bet_ref = BetRef(
                        bet_id=int(bet_id),
                        name=str(bet.get("name") or ""),
                        raw=bet,
                    )
                    self._bets_by_id.setdefault(int(bet_id), bet_ref)
                    self._bets_by_name.setdefault(_normalize(bet_ref.name), bet_ref)

    def leagues(self) -> list[LeagueRef]:
        unique = {
            (league.league_id, league.season): league
            for key, league in self._leagues_by_id.items()
            if key[1] is not None
        }
        return list(unique.values())

    def all_teams(self) -> list[TeamRef]:
        return [team for teams in self._teams_by_id.values() for team in teams]

    def all_fixtures(self) -> list[FixtureRef]:
        return list(self._fixtures_by_id.values())

    def all_bookmakers(self) -> list[BookmakerRef]:
        return list(self._bookmakers_by_id.values())

    def all_bets(self) -> list[BetRef]:
        return list(self._bets_by_id.values())

    def counts(self) -> dict[str, int]:
        return {
            "competitions": len(self.competitions),
            "leagues": len(self.leagues()),
            "teams": len(self.all_teams()),
            "fixtures": len(self._fixtures_by_id),
            "bookmakers": len(self._bookmakers_by_id),
            "bets": len(self._bets_by_id),
        }

    def find_league_by_id(self, league_id: int, season: int | None = None) -> LeagueRef:
        league = self._leagues_by_id.get((league_id, season))
        if league is None and season is not None:
            league = self._leagues_by_id.get((league_id, None))
        if league is None:
            raise ReferenceLookupError(f"Unknown league_id={league_id} season={season}")
        return league

    def find_league_by_key(self, key: str) -> LeagueRef:
        league = self._leagues_by_key.get(_normalize(key))
        if league is None:
            raise ReferenceLookupError(f"Unknown competition key={key!r}")
        return league

    def find_team_by_id(self, team_id: int, league_id: int | None = None) -> TeamRef:
        teams = self._teams_by_id.get(team_id, [])
        if league_id is not None:
            teams = [team for team in teams if team.league_id == league_id]
        if not teams:
            raise ReferenceLookupError(f"Unknown team_id={team_id} league_id={league_id}")
        return teams[0]

    def find_team_by_name(self, name: str, league_id: int | None = None) -> TeamRef:
        teams = self._teams_by_name.get(_normalize(name), [])
        if league_id is not None:
            teams = [team for team in teams if team.league_id == league_id]
        if not teams:
            raise ReferenceLookupError(f"Unknown team name={name!r} league_id={league_id}")
        return teams[0]

    def find_fixture_by_id(self, fixture_id: int) -> FixtureRef:
        fixture = self._fixtures_by_id.get(fixture_id)
        if fixture is None:
            raise ReferenceLookupError(f"Unknown fixture_id={fixture_id}")
        return fixture

    def validate_fixture_reference(self, fixture_id: int) -> FixtureRef:
        return self.find_fixture_by_id(fixture_id)

    def find_bookmaker_by_id(self, bookmaker_id: int) -> BookmakerRef:
        bookmaker = self._bookmakers_by_id.get(bookmaker_id)
        if bookmaker is None:
            raise ReferenceLookupError(f"Unknown bookmaker_id={bookmaker_id}")
        return bookmaker

    def find_bookmaker_by_name(self, name: str) -> BookmakerRef:
        bookmaker = self._bookmakers_by_name.get(_normalize(name))
        if bookmaker is None:
            raise ReferenceLookupError(f"Unknown bookmaker name={name!r}")
        return bookmaker

    def find_bet_by_id(self, bet_id: int) -> BetRef:
        bet = self._bets_by_id.get(bet_id)
        if bet is None:
            raise ReferenceLookupError(f"Unknown bet_id={bet_id}")
        return bet

    def find_bet_by_name(self, name: str) -> BetRef:
        bet = self._bets_by_name.get(_normalize(name))
        if bet is not None:
            return bet
        raise ReferenceLookupError(f"Unknown bet name={name!r}")


class PlayersReference:
    """Machine-readable player and squad reference."""

    def __init__(self, payload: JsonDict) -> None:
        self.payload = payload
        self.meta = payload.get("meta", {})
        self.competitions: list[JsonDict] = list(payload.get("competitions", []))
        self._players_by_id: dict[int, list[PlayerRef]] = defaultdict(list)
        self._players_by_team: dict[int, list[PlayerRef]] = defaultdict(list)
        self._build_indexes()

    def _build_indexes(self) -> None:
        for competition in self.competitions:
            for team_entry in competition.get("teams") or []:
                team = team_entry.get("team") or {}
                team_id = team.get("team_id")
                league_id = team.get("league_id")
                season = team.get("season")
                if team_id is None or league_id is None or season is None:
                    continue
                for player in team_entry.get("players") or []:
                    player_id = player.get("player_id")
                    if player_id is None:
                        continue
                    player_ref = PlayerRef(
                        player_id=int(player_id),
                        name=str(player.get("name") or ""),
                        team_id=int(team_id),
                        league_id=int(league_id),
                        season=int(season),
                        position=player.get("position"),
                        number=player.get("number"),
                        age=player.get("age"),
                        raw={**player, "team": team},
                    )
                    self._players_by_id[player_ref.player_id].append(player_ref)
                    self._players_by_team[player_ref.team_id].append(player_ref)

    def find_player_by_id(self, player_id: int) -> PlayerRef:
        players = self._players_by_id.get(player_id, [])
        if not players:
            raise ReferenceLookupError(f"Unknown player_id={player_id}")
        return players[0]

    def find_players_by_team(self, team_id: int) -> list[PlayerRef]:
        players = self._players_by_team.get(team_id, [])
        if not players:
            raise ReferenceLookupError(f"Unknown or empty player squad for team_id={team_id}")
        return list(players)

    def all_players(self) -> list[PlayerRef]:
        return [player for players in self._players_by_team.values() for player in players]

    def counts(self) -> dict[str, int]:
        return {
            "competitions": len(self.competitions),
            "players": len(self._players_by_id),
            "squads": sum(len(players) for players in self._players_by_team.values()),
            "teams": len(self._players_by_team),
        }
