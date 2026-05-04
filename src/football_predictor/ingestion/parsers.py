"""Small parsers for API-Football ingestion payloads."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from football_predictor.features.odds_features import extract_1x2_values
from football_predictor.utils.time import parse_datetime

JsonDict = dict[str, Any]


def response_items(payload: JsonDict) -> list[JsonDict]:
    """Return object rows from an API-Football `response` list."""
    response = payload.get("response") or []
    if not isinstance(response, list):
        return []
    return [item for item in response if isinstance(item, dict)]


def find_api_season(raw_seasons: Any, season: int) -> JsonDict:
    """Find the API-Football season row matching `season` when available."""
    if not isinstance(raw_seasons, list):
        return {}
    for row in raw_seasons:
        if isinstance(row, dict) and row.get("year") == season:
            return row
    for row in raw_seasons:
        if isinstance(row, dict):
            return row
    return {}


def league_row_parts(row: JsonDict) -> tuple[JsonDict, JsonDict]:
    return _dict_or_empty(row.get("league")), _dict_or_empty(row.get("country"))


def team_row_parts(row: JsonDict) -> tuple[JsonDict, JsonDict]:
    return _dict_or_empty(row.get("team")), _dict_or_empty(row.get("venue"))


def squad_row_parts(row: JsonDict) -> tuple[JsonDict, list[JsonDict]]:
    team = _dict_or_empty(row.get("team"))
    players = row.get("players") or []
    if not isinstance(players, list):
        return team, []
    return team, [player for player in players if isinstance(player, dict)]


def parse_fixture_row(row: JsonDict, *, ingestion_source: str = "api-football") -> JsonDict:
    """Normalize API-Football or local docs fixture rows for `models.Fixture`."""
    fixture = _dict_or_empty(row.get("fixture"))
    league = _dict_or_empty(row.get("league"))
    teams = _dict_or_empty(row.get("teams"))
    goals = _dict_or_empty(row.get("goals"))
    home_team = _dict_or_empty(teams.get("home"))
    away_team = _dict_or_empty(teams.get("away"))
    venue = _dict_or_empty(fixture.get("venue")) or {
        "id": row.get("venue_id"),
        "name": row.get("venue_name"),
        "city": row.get("venue_city"),
    }
    status = _dict_or_empty(fixture.get("status"))

    fixture_id = fixture.get("id") or row.get("fixture_id")
    league_id = league.get("id") or row.get("league_id")
    season = league.get("season") or row.get("season")
    home_team_id = home_team.get("id") or row.get("home_team_id")
    away_team_id = away_team.get("id") or row.get("away_team_id")

    return {
        "fixture_id": _required_int(fixture_id, "fixture_id"),
        "date": parse_datetime(fixture.get("date") or row.get("date")),
        "timestamp": fixture.get("timestamp") or row.get("timestamp"),
        "timezone": fixture.get("timezone") or row.get("timezone"),
        "round": league.get("round") or row.get("round"),
        "league_id": _required_int(league_id, "league_id"),
        "season": _required_int(season, "season"),
        "venue_id": int(venue["id"]) if venue.get("id") is not None else None,
        "venue_name": venue.get("name") or row.get("venue_name"),
        "venue_city": venue.get("city") or row.get("venue_city"),
        "referee": fixture.get("referee") or row.get("referee"),
        "status": status.get("short") or row.get("status_short") or status.get("long"),
        "status_long": status.get("long") or row.get("status_long"),
        "status_short": status.get("short") or row.get("status_short"),
        "elapsed": status.get("elapsed") or row.get("elapsed"),
        "home_team_id": _required_int(home_team_id, "home_team_id"),
        "away_team_id": _required_int(away_team_id, "away_team_id"),
        "home_team": home_team.get("name") or row.get("home_team") or "",
        "away_team": away_team.get("name") or row.get("away_team") or "",
        "home_goals": goals.get("home") if "home" in goals else row.get("goals_home"),
        "away_goals": goals.get("away") if "away" in goals else row.get("goals_away"),
        "goals_home": goals.get("home") if "home" in goals else row.get("goals_home"),
        "goals_away": goals.get("away") if "away" in goals else row.get("goals_away"),
        "payload_json": {**row, "ingestion_source": ingestion_source},
    }


def parse_fixture_venue(
    row: JsonDict,
    *,
    ingestion_source: str = "api-football",
) -> JsonDict | None:
    fixture = _dict_or_empty(row.get("fixture"))
    venue = _dict_or_empty(fixture.get("venue"))
    if not venue:
        venue = {
            "id": row.get("venue_id"),
            "name": row.get("venue_name"),
            "city": row.get("venue_city"),
        }
    if venue.get("id") is None:
        return None
    return {
        "venue_id": int(venue["id"]),
        "name": venue.get("name"),
        "address": venue.get("address"),
        "city": venue.get("city"),
        "capacity": venue.get("capacity"),
        "surface": venue.get("surface"),
        "image": venue.get("image"),
        "payload_json": {**venue, "ingestion_source": ingestion_source},
    }


def parse_standing_rows(
    payload: JsonDict,
    *,
    league_id: int,
    season: int,
    fetched_at: datetime,
    ingestion_source: str = "api-football",
) -> list[JsonDict]:
    """Normalize API-Football standings payload into `StandingSnapshot` values."""
    rows: list[JsonDict] = []
    for response_row in response_items(payload):
        league = _dict_or_empty(response_row.get("league"))
        raw_groups = league.get("standings") or response_row.get("standings") or []
        for group in raw_groups if isinstance(raw_groups, list) else []:
            if isinstance(group, dict):
                standings = [group]
            elif isinstance(group, list):
                standings = [item for item in group if isinstance(item, dict)]
            else:
                standings = []
            for standing in standings:
                parsed = parse_standing_row(
                    standing,
                    league_id=int(league.get("id") or league_id),
                    season=int(league.get("season") or season),
                    fetched_at=fetched_at,
                    ingestion_source=ingestion_source,
                )
                if parsed is not None:
                    rows.append(parsed)
    return rows


def parse_standing_row(
    row: JsonDict,
    *,
    league_id: int,
    season: int,
    fetched_at: datetime,
    ingestion_source: str = "api-football",
) -> JsonDict | None:
    team = _dict_or_empty(row.get("team"))
    team_id = team.get("id") or row.get("team_id")
    if team_id is None:
        return None
    all_stats = _dict_or_empty(row.get("all"))
    all_goals = _dict_or_empty(all_stats.get("goals"))
    home_stats = _dict_or_empty(row.get("home"))
    away_stats = _dict_or_empty(row.get("away"))
    update_time = parse_datetime(row.get("update")) or fetched_at
    return {
        "league_id": league_id,
        "season": season,
        "team_id": int(team_id),
        "snapshot_date": update_time,
        "fetched_at": fetched_at,
        "rank": row.get("rank"),
        "points": row.get("points"),
        "goals_diff": row.get("goalsDiff") or row.get("goals_diff"),
        "form": row.get("form"),
        "description": row.get("description"),
        "played": row.get("played"),
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
        "goals_for": row.get("goals_for"),
        "goals_against": row.get("goals_against"),
        "payload_json": {**row, "ingestion_source": ingestion_source},
    }


def parse_fixture_statistics_rows(
    payload: JsonDict,
    *,
    fixture_id: int,
    fetched_at: datetime,
    ingestion_source: str = "api-football",
) -> list[JsonDict]:
    """Normalize `/fixtures/statistics` rows for `FixtureStatistics`."""
    rows: list[JsonDict] = []
    for row in response_items(payload):
        team = _dict_or_empty(row.get("team"))
        team_id = team.get("id") or row.get("team_id")
        if team_id is None:
            continue
        statistics = row.get("statistics")
        rows.append(
            {
                "fixture_id": fixture_id,
                "team_id": int(team_id),
                "fetched_at": fetched_at,
                "statistics_json": statistics if isinstance(statistics, list) else [],
                "payload_json": {**row, "ingestion_source": ingestion_source},
            }
        )
    return rows


def parse_fixture_event_rows(
    payload: JsonDict,
    *,
    fixture_id: int,
    fetched_at: datetime,
    ingestion_source: str = "api-football",
) -> list[JsonDict]:
    """Normalize `/fixtures/events` rows for `FixtureEvent`."""
    rows: list[JsonDict] = []
    for row in response_items(payload):
        team = _dict_or_empty(row.get("team"))
        player = _dict_or_empty(row.get("player"))
        assist = _dict_or_empty(row.get("assist"))
        event_time = _dict_or_empty(row.get("time"))
        elapsed = _optional_int(event_time.get("elapsed") or row.get("elapsed"))
        rows.append(
            {
                "fixture_id": fixture_id,
                "team_id": _optional_int(team.get("id") or row.get("team_id")),
                "player_id": _optional_int(player.get("id") or row.get("player_id")),
                "assist_player_id": _optional_int(
                    assist.get("id") or row.get("assist_player_id")
                ),
                "type": row.get("type"),
                "event_time": elapsed,
                "event_type": row.get("type"),
                "detail": row.get("detail"),
                "elapsed": elapsed,
                "extra": _optional_int(event_time.get("extra") or row.get("extra")),
                "fetched_at": fetched_at,
                "payload_json": {**row, "ingestion_source": ingestion_source},
            }
        )
    return rows


def parse_fixture_lineup_rows(
    payload: JsonDict,
    *,
    fixture_id: int,
    fetched_at: datetime,
    ingestion_source: str = "api-football",
) -> list[JsonDict]:
    """Normalize `/fixtures/lineups` rows for `FixtureLineup`."""
    rows: list[JsonDict] = []
    for row in response_items(payload):
        team = _dict_or_empty(row.get("team"))
        team_id = team.get("id") or row.get("team_id")
        if team_id is None:
            continue
        coach = _dict_or_empty(row.get("coach"))
        start_xi = row.get("startXI")
        substitutes = row.get("substitutes")
        players = row.get("players")
        rows.append(
            {
                "fixture_id": fixture_id,
                "team_id": int(team_id),
                "coach_id": _optional_int(coach.get("id") or row.get("coach_id")),
                "formation": row.get("formation"),
                "start_xi_json": start_xi if isinstance(start_xi, list) else [],
                "substitutes_json": substitutes if isinstance(substitutes, list) else [],
                "players_json": players if isinstance(players, list) else [],
                "fetched_at": fetched_at,
                "payload_json": {**row, "ingestion_source": ingestion_source},
            }
        )
    return rows


def parse_fixture_player_stats_rows(
    payload: JsonDict,
    *,
    fixture_id: int,
    fetched_at: datetime,
    ingestion_source: str = "api-football",
) -> list[JsonDict]:
    """Normalize `/fixtures/players` rows for `FixturePlayerStats`."""
    rows: list[JsonDict] = []
    for team_row in response_items(payload):
        team = _dict_or_empty(team_row.get("team"))
        team_id = team.get("id") or team_row.get("team_id")
        players = team_row.get("players")
        if team_id is None or not isinstance(players, list):
            continue
        for player_row in players:
            if not isinstance(player_row, dict):
                continue
            player = _dict_or_empty(player_row.get("player"))
            player_id = player.get("id") or player_row.get("player_id")
            if player_id is None:
                continue
            statistics = player_row.get("statistics")
            statistics_list = statistics if isinstance(statistics, list) else []
            first_stats = _first_dict(statistics_list)
            games = _dict_or_empty(first_stats.get("games"))
            rows.append(
                {
                    "fixture_id": fixture_id,
                    "team_id": int(team_id),
                    "player_id": int(player_id),
                    "fetched_at": fetched_at,
                    "statistics_json": statistics_list,
                    "stats_json": first_stats,
                    "rating": _parse_float(games.get("rating")),
                    "minutes": _optional_int(games.get("minutes")),
                    "position": games.get("position"),
                    "payload_json": {
                        **player_row,
                        "team": team,
                        "ingestion_source": ingestion_source,
                    },
                }
            )
    return rows


def parse_injury_rows(
    payload: JsonDict,
    *,
    fixture_id: int | None = None,
    fetched_at: datetime,
    ingestion_source: str = "api-football",
) -> list[JsonDict]:
    """Normalize `/injuries` rows for `Injury`."""
    rows: list[JsonDict] = []
    for row in response_items(payload):
        player = _dict_or_empty(row.get("player"))
        team = _dict_or_empty(row.get("team"))
        fixture = _dict_or_empty(row.get("fixture"))
        league = _dict_or_empty(row.get("league"))
        parsed_fixture_id = _optional_int(fixture.get("id") or row.get("fixture_id"))
        rows.append(
            {
                "fixture_id": parsed_fixture_id or fixture_id,
                "league_id": _optional_int(league.get("id") or row.get("league_id")),
                "season": _optional_int(league.get("season") or row.get("season")),
                "team_id": _optional_int(team.get("id") or row.get("team_id")),
                "player_id": _optional_int(player.get("id") or row.get("player_id")),
                "reason": player.get("reason") or row.get("reason"),
                "type": player.get("type") or row.get("type"),
                "date": parse_datetime(fixture.get("date") or row.get("date")),
                "fetched_at": fetched_at,
                "payload_json": {**row, "ingestion_source": ingestion_source},
            }
        )
    return rows


def parse_api_prediction_row(
    payload: JsonDict,
    *,
    fixture_id: int,
    fetched_at: datetime,
    ingestion_source: str = "api-football",
) -> JsonDict | None:
    """Normalize the first `/predictions` row for `ApiPredictionSnapshot`."""
    rows = response_items(payload)
    if not rows:
        return None
    row = rows[0]
    predictions = _dict_or_empty(row.get("predictions"))
    winner = _dict_or_empty(predictions.get("winner"))
    percent = _dict_or_empty(predictions.get("percent"))
    return {
        "fixture_id": fixture_id,
        "fetched_at": fetched_at,
        "source": ingestion_source,
        "winner_team_id": _optional_int(winner.get("id")),
        "win_or_draw": predictions.get("win_or_draw"),
        "advice": predictions.get("advice"),
        "percent_home": _parse_percent(percent.get("home")),
        "percent_draw": _parse_percent(percent.get("draw")),
        "percent_away": _parse_percent(percent.get("away")),
        "payload_json": {**row, "ingestion_source": ingestion_source},
    }


def parse_odds_snapshot_rows(
    payload: JsonDict,
    *,
    target_bet_id: int,
    fetched_at: datetime,
    ingestion_source: str = "api-football",
) -> list[JsonDict]:
    """Normalize prematch `/odds` rows into `OddsSnapshot` values."""
    rows: list[JsonDict] = []
    for fixture_row in response_items(payload):
        fixture = _dict_or_empty(fixture_row.get("fixture"))
        league = _dict_or_empty(fixture_row.get("league"))
        teams = _dict_or_empty(fixture_row.get("teams"))
        home_team = _dict_or_empty(teams.get("home"))
        away_team = _dict_or_empty(teams.get("away"))
        fixture_id = fixture.get("id") or fixture_row.get("fixture_id")
        if fixture_id is None:
            continue
        bookmakers = fixture_row.get("bookmakers")
        if not isinstance(bookmakers, list):
            continue
        for bookmaker in bookmakers:
            bookmaker_row = _dict_or_empty(bookmaker)
            bookmaker_id = _optional_int(bookmaker_row.get("id"))
            bets = bookmaker_row.get("bets")
            if not isinstance(bets, list):
                continue
            for bet in bets:
                bet_row = _dict_or_empty(bet)
                bet_id = _optional_int(bet_row.get("id"))
                if bet_id != target_bet_id:
                    continue
                values = bet_row.get("values")
                if not isinstance(values, list):
                    continue
                parsed_odds = extract_1x2_values(
                    values,
                    home_team_name=home_team.get("name"),
                    away_team_name=away_team.get("name"),
                )
                if parsed_odds is None:
                    continue
                rows.append(
                    {
                        "fixture_id": int(fixture_id),
                        "league_id": _optional_int(
                            league.get("id") or fixture_row.get("league_id")
                        ),
                        "season": _optional_int(league.get("season") or fixture_row.get("season")),
                        "bookmaker_id": bookmaker_id,
                        "bookmaker_name": bookmaker_row.get("name"),
                        "bet_id": bet_id,
                        "bet_name": bet_row.get("name"),
                        "values_json": values,
                        "fetched_at": fetched_at,
                        "is_live": False,
                        "odd_home": parsed_odds.odd_home,
                        "odd_draw": parsed_odds.odd_draw,
                        "odd_away": parsed_odds.odd_away,
                        "odds_json": {
                            "home": parsed_odds.odd_home,
                            "draw": parsed_odds.odd_draw,
                            "away": parsed_odds.odd_away,
                        },
                        "payload_json": {
                            "fixture": fixture,
                            "league": league,
                            "bookmaker": bookmaker_row,
                            "bet": bet_row,
                            "ingestion_source": ingestion_source,
                        },
                    }
                )
    return rows


def _dict_or_empty(value: Any) -> JsonDict:
    return value if isinstance(value, dict) else {}


def _required_int(value: Any, field_name: str) -> int:
    if value is None:
        raise TypeError(f"Missing required integer field {field_name}")
    return int(value)


def _optional_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    return int(value)


def _parse_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _parse_percent(value: Any) -> float | None:
    if value is None or value == "":
        return None
    if isinstance(value, str):
        value = value.strip().removesuffix("%")
    return _parse_float(value)


def _first_dict(values: list[Any]) -> JsonDict:
    for value in values:
        if isinstance(value, dict):
            return value
    return {}


def _parse_1x2_values(values: list[Any]) -> dict[str, float] | None:
    parsed: dict[str, float] = {}
    for raw_value in values:
        value_row = _dict_or_empty(raw_value)
        label = _normalize_1x2_label(value_row.get("value"))
        odd = _parse_float(value_row.get("odd"))
        if label is None or odd is None:
            continue
        parsed[label] = odd
    if {"home", "draw", "away"}.issubset(parsed):
        return parsed
    return None


def _normalize_1x2_label(value: Any) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip().casefold()
    if normalized in {"home", "1"}:
        return "home"
    if normalized in {"draw", "x"}:
        return "draw"
    if normalized in {"away", "2"}:
        return "away"
    return None
