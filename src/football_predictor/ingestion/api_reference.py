"""Live API-Football ingestion for reference entities.

These services only run when the CLI receives an explicit refresh flag. Every
live payload is saved as a database RawApiSnapshot before normalized upserts.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any, Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session

from football_predictor.api.api_football_client import ApiFootballPayload
from football_predictor.api.endpoints import (
    LEAGUES,
    ODDS_BETS,
    ODDS_BOOKMAKERS,
    PLAYERS_SQUADS,
    TEAMS,
)
from football_predictor.config.competitions import CompetitionConfig
from football_predictor.db import models
from football_predictor.db.repositories import insert_raw_api_snapshot, upsert_by_fields
from football_predictor.ingestion.parsers import (
    find_api_season,
    league_row_parts,
    response_items,
    squad_row_parts,
    team_row_parts,
)
from football_predictor.ingestion.seed_reference import SeedSummary
from football_predictor.utils.time import parse_datetime, utc_now

JsonDict = dict[str, Any]


class ApiFootballClientProtocol(Protocol):
    def get_payload(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
        *,
        save_raw: bool = False,
    ) -> ApiFootballPayload:
        ...


class ApiReferenceIngestionService:
    """Ingest API-Football reference endpoints through the central client."""

    def __init__(
        self,
        session: Session,
        client: ApiFootballClientProtocol,
        *,
        save_raw: bool = False,
    ) -> None:
        self.session = session
        self.client = client
        self.save_raw = save_raw

    def ingest_leagues(self, competitions: Iterable[CompetitionConfig]) -> SeedSummary:
        summary = SeedSummary()
        for competition in competitions:
            payload = self._fetch(
                LEAGUES,
                {"id": competition.league_id, "season": competition.season},
            )
            for row in response_items(payload.payload):
                self._upsert_league(row, competition, summary)
        self.session.flush()
        return summary

    def ingest_teams(self, competitions: Iterable[CompetitionConfig]) -> SeedSummary:
        summary = SeedSummary()
        for competition in competitions:
            payload = self._fetch(
                TEAMS,
                {"league": competition.league_id, "season": competition.season},
            )
            for row in response_items(payload.payload):
                self._upsert_team(row, competition, summary)
        self.session.flush()
        return summary

    def ingest_player_squads(self, competitions: Iterable[CompetitionConfig]) -> SeedSummary:
        summary = SeedSummary()
        for competition in competitions:
            team_ids = self._team_ids_for_competition(competition)
            if not team_ids:
                summary.skipped += 1
                summary.errors.append(
                    "No local teams found for "
                    f"league_id={competition.league_id} season={competition.season}; "
                    "run seed-reference-from-docs or ingest-teams first."
                )
                continue
            for team_id in team_ids:
                payload = self._fetch(PLAYERS_SQUADS, {"team": team_id})
                for row in response_items(payload.payload):
                    self._upsert_player_squad(row, competition, team_id, summary)
        self.session.flush()
        return summary

    def ingest_bookmakers(self) -> SeedSummary:
        summary = SeedSummary()
        payload = self._fetch(ODDS_BOOKMAKERS, {})
        for row in response_items(payload.payload):
            bookmaker_id = row.get("id")
            if bookmaker_id is None:
                summary.skipped += 1
                continue
            upsert_by_fields(
                self.session,
                models.Bookmaker,
                {"bookmaker_id": int(bookmaker_id)},
                {"name": row.get("name") or "", "payload_json": row},
            )
            summary.bookmakers += 1
        self.session.flush()
        return summary

    def ingest_bets(self, bet_type: str = "prematch") -> SeedSummary:
        summary = SeedSummary()
        payload = self._fetch(ODDS_BETS, {})
        for row in response_items(payload.payload):
            bet_id = row.get("id")
            if bet_id is None:
                summary.skipped += 1
                continue
            upsert_by_fields(
                self.session,
                models.Bet,
                {"bet_id": int(bet_id), "bet_type": bet_type},
                {"name": row.get("name") or "", "bet_type": bet_type, "payload_json": row},
            )
            summary.bets += 1
        self.session.flush()
        return summary

    def _fetch(self, endpoint: str, params: JsonDict) -> ApiFootballPayload:
        payload = self.client.get_payload(endpoint, params, save_raw=self.save_raw)
        insert_raw_api_snapshot(
            self.session,
            endpoint=payload.endpoint,
            params_json=payload.params,
            payload_json=payload.payload,
            fetched_at=parse_datetime(payload.fetched_at) or utc_now(),
            status_code=payload.status_code,
            source=payload.source,
        )
        return payload

    def _upsert_league(
        self,
        row: JsonDict,
        competition: CompetitionConfig,
        summary: SeedSummary,
    ) -> None:
        league, country = league_row_parts(row)
        season_row = find_api_season(row.get("seasons"), competition.season)
        league_id = league.get("id") or competition.league_id
        upsert_by_fields(
            self.session,
            models.League,
            {"league_id": int(league_id), "season": competition.season},
            {
                "name": league.get("name") or competition.name,
                "country": country.get("name") or competition.country,
                "type": league.get("type"),
                "country_code": country.get("code"),
                "logo": league.get("logo"),
                "season_start": season_row.get("start"),
                "season_end": season_row.get("end"),
                "payload_json": row,
            },
        )
        summary.leagues += 1
        summary.seasons += 1
        if season_row.get("coverage"):
            summary.coverage += 1

    def _upsert_team(
        self,
        row: JsonDict,
        competition: CompetitionConfig,
        summary: SeedSummary,
    ) -> None:
        team, venue = team_row_parts(row)
        team_id = team.get("id")
        if team_id is None:
            summary.skipped += 1
            return
        venue_id = venue.get("id")
        if venue_id is not None:
            upsert_by_fields(
                self.session,
                models.Venue,
                {"venue_id": int(venue_id)},
                {
                    "name": venue.get("name"),
                    "address": venue.get("address"),
                    "city": venue.get("city"),
                    "capacity": venue.get("capacity"),
                    "surface": venue.get("surface"),
                    "image": venue.get("image"),
                    "payload_json": venue,
                },
            )
            summary.venues += 1

        upsert_by_fields(
            self.session,
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
                "payload_json": row,
            },
        )
        summary.teams += 1

        upsert_by_fields(
            self.session,
            models.TeamSeason,
            {
                "team_id": int(team_id),
                "league_id": competition.league_id,
                "season": competition.season,
            },
            {"competition_key": competition.key, "payload_json": row},
        )
        summary.team_seasons += 1

    def _upsert_player_squad(
        self,
        row: JsonDict,
        competition: CompetitionConfig,
        fallback_team_id: int,
        summary: SeedSummary,
    ) -> None:
        team, players = squad_row_parts(row)
        team_id = int(team.get("id") or fallback_team_id)
        for player in players:
            player_id = player.get("id") or player.get("player_id")
            if player_id is None:
                summary.skipped += 1
                continue
            typed_player_id = int(player_id)
            upsert_by_fields(
                self.session,
                models.Player,
                {"player_id": typed_player_id},
                {
                    "name": player.get("name") or "",
                    "age": player.get("age"),
                    "photo": player.get("photo"),
                    "payload_json": player,
                },
            )
            summary.players += 1
            upsert_by_fields(
                self.session,
                models.PlayerSquad,
                {
                    "player_id": typed_player_id,
                    "team_id": team_id,
                    "league_id": competition.league_id,
                    "season": competition.season,
                },
                {
                    "position": player.get("position"),
                    "number": player.get("number"),
                    "fetched_at": utc_now(),
                    "payload_json": {"player": player, "team": team},
                },
            )
            summary.squads += 1

    def _team_ids_for_competition(self, competition: CompetitionConfig) -> list[int]:
        self.session.flush()
        stmt = (
            select(models.TeamSeason.team_id)
            .where(
                models.TeamSeason.league_id == competition.league_id,
                models.TeamSeason.season == competition.season,
            )
            .order_by(models.TeamSeason.team_id)
        )
        return list(self.session.execute(stmt).scalars())
