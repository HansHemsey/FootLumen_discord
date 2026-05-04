"""Typed views over local reference JSON records."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from football_predictor.utils.time import parse_datetime

JsonDict = dict[str, Any]


@dataclass(frozen=True)
class LeagueRef:
    league_id: int
    name: str
    season: int
    country: str | None
    category: str | None
    key: str | None
    raw: JsonDict


@dataclass(frozen=True)
class TeamRef:
    team_id: int
    name: str
    league_id: int | None
    season: int | None
    country: str | None
    venue_id: int | None
    raw: JsonDict


@dataclass(frozen=True)
class FixtureRef:
    fixture_id: int
    date: datetime | None
    league_id: int
    season: int
    home_team_id: int
    away_team_id: int
    home_team: str
    away_team: str
    status_short: str | None
    raw: JsonDict

    @classmethod
    def from_record(cls, record: JsonDict) -> FixtureRef:
        return cls(
            fixture_id=int(record["fixture_id"]),
            date=parse_datetime(record.get("date")),
            league_id=int(record["league_id"]),
            season=int(record["season"]),
            home_team_id=int(record["home_team_id"]),
            away_team_id=int(record["away_team_id"]),
            home_team=str(record.get("home_team") or ""),
            away_team=str(record.get("away_team") or ""),
            status_short=record.get("status_short"),
            raw=record,
        )


@dataclass(frozen=True)
class BookmakerRef:
    bookmaker_id: int
    name: str
    raw: JsonDict


@dataclass(frozen=True)
class BetRef:
    bet_id: int
    name: str
    raw: JsonDict


@dataclass(frozen=True)
class PlayerRef:
    player_id: int
    name: str
    team_id: int
    league_id: int
    season: int
    position: str | None
    number: int | None
    age: int | None
    raw: JsonDict
