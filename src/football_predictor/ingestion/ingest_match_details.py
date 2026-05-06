"""Detailed fixture ingestion for API-Football dynamic endpoints."""

from __future__ import annotations

import time
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from datetime import date as date_type
from pathlib import Path
from typing import Any, Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session

from football_predictor.api.api_football_client import ApiFootballPayload
from football_predictor.api.endpoints import (
    FIXTURES_EVENTS,
    FIXTURES_LINEUPS,
    FIXTURES_PLAYERS,
    FIXTURES_STATISTICS,
    INJURIES,
    PREDICTIONS,
)
from football_predictor.api.exceptions import (
    ApiFootballClientError,
    ApiFootballError,
    ApiFootballRateLimitError,
)
from football_predictor.db import models
from football_predictor.db.repositories import insert_raw_api_snapshot, upsert_by_fields
from football_predictor.ingestion.parsers import (
    parse_api_prediction_row,
    parse_fixture_event_rows,
    parse_fixture_lineup_rows,
    parse_fixture_player_stats_rows,
    parse_fixture_statistics_rows,
    parse_injury_rows,
    response_items,
)
from football_predictor.ingestion.unknown_players import (
    UnknownPlayerQueue,
    UnknownPlayerRecord,
)
from football_predictor.reference.lookups import ApiFootballReference, PlayersReference
from football_predictor.utils.exceptions import FootballPredictorError, ReferenceLookupError
from football_predictor.utils.logging import get_logger
from football_predictor.utils.time import parse_datetime, utc_now

JsonDict = dict[str, Any]

DETAIL_STATISTICS = "statistics"
DETAIL_EVENTS = "events"
DETAIL_LINEUPS = "lineups"
DETAIL_PLAYERS = "players"
DETAIL_INJURIES = "injuries"
DETAIL_PREDICTIONS = "predictions"

ALL_DETAIL_KEYS = (
    DETAIL_STATISTICS,
    DETAIL_EVENTS,
    DETAIL_LINEUPS,
    DETAIL_PLAYERS,
    DETAIL_INJURIES,
    DETAIL_PREDICTIONS,
)

DETAIL_ENDPOINTS = {
    DETAIL_STATISTICS: FIXTURES_STATISTICS,
    DETAIL_EVENTS: FIXTURES_EVENTS,
    DETAIL_LINEUPS: FIXTURES_LINEUPS,
    DETAIL_PLAYERS: FIXTURES_PLAYERS,
    DETAIL_INJURIES: INJURIES,
    DETAIL_PREDICTIONS: PREDICTIONS,
}

logger = get_logger(__name__)


class ApiFootballPayloadClient(Protocol):
    def get_payload(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
        *,
        save_raw: bool = False,
    ) -> ApiFootballPayload:
        ...


@dataclass
class FixtureDetailsIngestionSummary:
    fixture_details: int = 0
    statistics: int = 0
    events: int = 0
    lineups: int = 0
    player_stats: int = 0
    injuries: int = 0
    predictions: int = 0
    players: int = 0
    unknown_players_queued: int = 0
    raw_snapshots: int = 0
    no_content: int = 0
    skipped: int = 0
    skipped_complete: int = 0
    errors: list[str] = field(default_factory=list)

    def merge(
        self,
        other: FixtureDetailsIngestionSummary,
    ) -> FixtureDetailsIngestionSummary:
        self.fixture_details += other.fixture_details
        self.statistics += other.statistics
        self.events += other.events
        self.lineups += other.lineups
        self.player_stats += other.player_stats
        self.injuries += other.injuries
        self.predictions += other.predictions
        self.players += other.players
        self.unknown_players_queued += other.unknown_players_queued
        self.raw_snapshots += other.raw_snapshots
        self.no_content += other.no_content
        self.skipped += other.skipped
        self.skipped_complete += other.skipped_complete
        self.errors.extend(other.errors)
        return self

    def as_dict(self) -> dict[str, int | list[str]]:
        return {
            "fixture_details": self.fixture_details,
            "statistics": self.statistics,
            "events": self.events,
            "lineups": self.lineups,
            "player_stats": self.player_stats,
            "injuries": self.injuries,
            "predictions": self.predictions,
            "players": self.players,
            "unknown_players_queued": self.unknown_players_queued,
            "raw_snapshots": self.raw_snapshots,
            "no_content": self.no_content,
            "skipped": self.skipped,
            "skipped_complete": self.skipped_complete,
            "errors": self.errors,
        }


class FixtureDetailsIngestionService:
    """Ingest detailed dynamic data for stored fixtures."""

    def __init__(
        self,
        session: Session,
        client: ApiFootballPayloadClient,
        *,
        reference: ApiFootballReference | None = None,
        players_reference: PlayersReference | None = None,
        save_raw: bool = False,
        unknown_players_path: Path | str | None = None,
    ) -> None:
        self.session = session
        self.client = client
        self.reference = reference
        self.players_reference = players_reference
        self.save_raw = save_raw
        self.unknown_player_queue = (
            UnknownPlayerQueue(unknown_players_path)
            if unknown_players_path is not None
            else None
        )

    def ingest_fixture_details(
        self,
        fixture_id: int,
        *,
        include: Iterable[str] | None = None,
        save_raw: bool | None = None,
        skip_if_complete: bool = False,
    ) -> FixtureDetailsIngestionSummary:
        """Ingest all or selected detail endpoints for one stored fixture."""
        self._require_fixture_exists(fixture_id)
        self._warn_if_unknown_fixture(fixture_id)
        summary = FixtureDetailsIngestionSummary(fixture_details=1)
        for key in _normalize_include(include):
            if skip_if_complete and self._detail_endpoint_is_complete(fixture_id, key):
                summary.skipped_complete += 1
                logger.info(
                    "Skipping complete fixture detail endpoint fixture_id=%s endpoint=%s",
                    fixture_id,
                    DETAIL_ENDPOINTS[key],
                )
                continue
            try:
                endpoint_summary = self._ingest_endpoint(
                    fixture_id,
                    key,
                    save_raw=self.save_raw if save_raw is None else save_raw,
                )
            except (ApiFootballRateLimitError, ApiFootballClientError):
                raise
            except ApiFootballError as exc:
                summary.errors.append(f"{key}: {exc}")
                continue
            summary.merge(endpoint_summary)
        self.session.flush()
        return summary

    def ingest_fixture_statistics(self, fixture_id: int) -> FixtureDetailsIngestionSummary:
        """Ingest `/fixtures/statistics` for one stored fixture."""
        return self._ingest_single_detail(fixture_id, DETAIL_STATISTICS)

    def ingest_fixture_events(self, fixture_id: int) -> FixtureDetailsIngestionSummary:
        """Ingest `/fixtures/events` for one stored fixture."""
        return self._ingest_single_detail(fixture_id, DETAIL_EVENTS)

    def ingest_fixture_lineups(self, fixture_id: int) -> FixtureDetailsIngestionSummary:
        """Ingest `/fixtures/lineups` for one stored fixture."""
        return self._ingest_single_detail(fixture_id, DETAIL_LINEUPS)

    def ingest_fixture_players(self, fixture_id: int) -> FixtureDetailsIngestionSummary:
        """Ingest `/fixtures/players` for one stored fixture."""
        return self._ingest_single_detail(fixture_id, DETAIL_PLAYERS)

    def ingest_injuries_for_fixture(self, fixture_id: int) -> FixtureDetailsIngestionSummary:
        """Ingest `/injuries?fixture=...` for one stored fixture."""
        return self._ingest_single_detail(fixture_id, DETAIL_INJURIES)

    def ingest_api_prediction(self, fixture_id: int) -> FixtureDetailsIngestionSummary:
        """Ingest `/predictions` for one stored fixture."""
        return self._ingest_single_detail(fixture_id, DETAIL_PREDICTIONS)

    def ingest_full_fixture_details(self, fixture_id: int) -> FixtureDetailsIngestionSummary:
        """Ingest all detailed endpoints for one stored fixture."""
        return self.ingest_fixture_details(fixture_id)

    def ingest_fixture_details_batch(
        self,
        fixture_ids: Iterable[int],
        *,
        include: Iterable[str] | None = None,
        save_raw: bool | None = None,
        continue_on_error: bool = True,
        stop_on_rate_limit: bool = True,
        delay_seconds: float = 0.0,
        skip_if_complete: bool = False,
    ) -> FixtureDetailsIngestionSummary:
        """Ingest detail endpoints for several fixtures."""
        summary = FixtureDetailsIngestionSummary()
        for index, fixture_id in enumerate(fixture_ids):
            if delay_seconds > 0 and index > 0:
                time.sleep(delay_seconds)
            try:
                fixture_summary = self.ingest_fixture_details(
                    fixture_id,
                    include=include,
                    save_raw=save_raw,
                    skip_if_complete=skip_if_complete,
                )
            except ApiFootballRateLimitError as exc:
                summary.skipped += 1
                summary.errors.append(f"fixture_id={fixture_id}: {exc}")
                if stop_on_rate_limit:
                    break
                if not continue_on_error:
                    raise
                continue
            except Exception as exc:
                if not continue_on_error:
                    raise
                summary.skipped += 1
                summary.errors.append(f"fixture_id={fixture_id}: {exc}")
                continue
            summary.merge(fixture_summary)
        return summary

    def fixture_ids_for_filters(
        self,
        *,
        league_id: int | None = None,
        season: int | None = None,
        fixture_date: date_type | None = None,
        date_from: date_type | None = None,
        date_to: date_type | None = None,
        status: str | None = None,
        statuses: Iterable[str] | None = None,
        limit: int | None = None,
    ) -> list[int]:
        """Return stored fixture IDs matching batch filters."""
        self.session.flush()
        stmt = select(models.Fixture).order_by(models.Fixture.date.asc())
        if league_id is not None:
            stmt = stmt.where(models.Fixture.league_id == league_id)
        if season is not None:
            stmt = stmt.where(models.Fixture.season == season)
        status_values = _normalized_statuses(status=status, statuses=statuses)
        if status_values:
            stmt = stmt.where(models.Fixture.status_short.in_(status_values))
        if fixture_date is not None:
            start = datetime.combine(fixture_date, datetime.min.time(), tzinfo=UTC)
            end = start + timedelta(days=1)
            stmt = stmt.where(models.Fixture.date >= start, models.Fixture.date < end)
        else:
            if date_from is not None:
                start = datetime.combine(date_from, datetime.min.time(), tzinfo=UTC)
                stmt = stmt.where(models.Fixture.date >= start)
            if date_to is not None:
                end = datetime.combine(date_to, datetime.min.time(), tzinfo=UTC) + timedelta(
                    days=1
                )
                stmt = stmt.where(models.Fixture.date < end)
        if limit is not None:
            stmt = stmt.limit(limit)
        return [fixture.fixture_id for fixture in self.session.execute(stmt).scalars()]

    def ingest_fixture_details_for_filters(
        self,
        *,
        league_id: int | None = None,
        season: int | None = None,
        fixture_date: date_type | None = None,
        date_from: date_type | None = None,
        date_to: date_type | None = None,
        status: str | None = None,
        statuses: Iterable[str] | None = None,
        limit: int | None = None,
        include: Iterable[str] | None = None,
        save_raw: bool | None = None,
        continue_on_error: bool = True,
        stop_on_rate_limit: bool = True,
        delay_seconds: float = 0.0,
        skip_if_complete: bool = False,
    ) -> FixtureDetailsIngestionSummary:
        fixture_ids = self.fixture_ids_for_filters(
            league_id=league_id,
            season=season,
            fixture_date=fixture_date,
            date_from=date_from,
            date_to=date_to,
            status=status,
            statuses=statuses,
            limit=limit,
        )
        return self.ingest_fixture_details_batch(
            fixture_ids,
            include=include,
            save_raw=save_raw,
            continue_on_error=continue_on_error,
            stop_on_rate_limit=stop_on_rate_limit,
            delay_seconds=delay_seconds,
            skip_if_complete=skip_if_complete,
        )

    def _ingest_single_detail(
        self,
        fixture_id: int,
        key: str,
    ) -> FixtureDetailsIngestionSummary:
        self._require_fixture_exists(fixture_id)
        self._warn_if_unknown_fixture(fixture_id)
        summary = FixtureDetailsIngestionSummary(fixture_details=1)
        summary.merge(self._ingest_endpoint(fixture_id, key, save_raw=self.save_raw))
        self.session.flush()
        return summary

    def _detail_endpoint_is_complete(self, fixture_id: int, key: str) -> bool:
        return self._has_detail_rows(fixture_id, key) or self._has_no_content_snapshot(
            fixture_id,
            DETAIL_ENDPOINTS[key],
        )

    def _has_detail_rows(self, fixture_id: int, key: str) -> bool:
        if key == DETAIL_STATISTICS:
            stmt = select(models.FixtureStatistics.id).where(
                models.FixtureStatistics.fixture_id == fixture_id
            )
        elif key == DETAIL_EVENTS:
            stmt = select(models.FixtureEvent.id).where(
                models.FixtureEvent.fixture_id == fixture_id
            )
        elif key == DETAIL_LINEUPS:
            stmt = select(models.FixtureLineup.id).where(
                models.FixtureLineup.fixture_id == fixture_id
            )
        elif key == DETAIL_PLAYERS:
            stmt = select(models.FixturePlayerStats.id).where(
                models.FixturePlayerStats.fixture_id == fixture_id
            )
        elif key == DETAIL_INJURIES:
            stmt = select(models.Injury.id).where(models.Injury.fixture_id == fixture_id)
        elif key == DETAIL_PREDICTIONS:
            stmt = select(models.ApiPredictionSnapshot.id).where(
                models.ApiPredictionSnapshot.fixture_id == fixture_id
            )
        else:
            return False
        return self.session.execute(stmt.limit(1)).first() is not None

    def _has_no_content_snapshot(self, fixture_id: int, endpoint: str) -> bool:
        stmt = (
            select(models.RawApiSnapshot)
            .where(
                models.RawApiSnapshot.endpoint == endpoint,
                models.RawApiSnapshot.status_code.in_((200, 204)),
            )
            .order_by(models.RawApiSnapshot.fetched_at.desc())
        )
        for snapshot in self.session.execute(stmt).scalars():
            params = snapshot.params_json if isinstance(snapshot.params_json, dict) else {}
            if int(params.get("fixture") or 0) != fixture_id:
                continue
            payload = snapshot.payload_json
            has_response = isinstance(payload, dict) and bool(response_items(payload))
            if snapshot.status_code == 204 or not has_response:
                return True
        return False

    def _ingest_endpoint(
        self,
        fixture_id: int,
        key: str,
        *,
        save_raw: bool,
    ) -> FixtureDetailsIngestionSummary:
        endpoint = DETAIL_ENDPOINTS[key]
        payload = self._fetch(endpoint, {"fixture": fixture_id}, save_raw=save_raw)
        summary = FixtureDetailsIngestionSummary(raw_snapshots=1)
        fetched_at = parse_datetime(payload.fetched_at) or utc_now()
        if payload.status_code == 204 or not response_items(payload.payload):
            logger.info(
                "API-Football detail endpoint returned no content endpoint=%s fixture_id=%s "
                "status_code=%s",
                endpoint,
                fixture_id,
                payload.status_code,
            )
            summary.no_content += 1
            return summary

        if key == DETAIL_STATISTICS:
            rows = parse_fixture_statistics_rows(
                payload.payload,
                fixture_id=fixture_id,
                fetched_at=fetched_at,
                ingestion_source=payload.source,
            )
            summary.statistics += self._upsert_fixture_statistics(rows)
        elif key == DETAIL_EVENTS:
            self._upsert_players_from_events(
                payload.payload,
                payload.source,
                summary,
                fixture_id=fixture_id,
                source_endpoint=endpoint,
            )
            rows = parse_fixture_event_rows(
                payload.payload,
                fixture_id=fixture_id,
                fetched_at=fetched_at,
                ingestion_source=payload.source,
            )
            summary.events += self._upsert_fixture_events(rows)
        elif key == DETAIL_LINEUPS:
            self._upsert_players_from_lineups(
                payload.payload,
                payload.source,
                summary,
                fixture_id=fixture_id,
                source_endpoint=endpoint,
            )
            rows = parse_fixture_lineup_rows(
                payload.payload,
                fixture_id=fixture_id,
                fetched_at=fetched_at,
                ingestion_source=payload.source,
            )
            summary.lineups += self._upsert_fixture_lineups(rows)
        elif key == DETAIL_PLAYERS:
            self._upsert_players_from_player_stats(
                payload.payload,
                payload.source,
                summary,
                fixture_id=fixture_id,
                source_endpoint=endpoint,
            )
            rows = parse_fixture_player_stats_rows(
                payload.payload,
                fixture_id=fixture_id,
                fetched_at=fetched_at,
                ingestion_source=payload.source,
            )
            summary.player_stats += self._upsert_fixture_player_stats(rows)
        elif key == DETAIL_INJURIES:
            self._upsert_players_from_injuries(
                payload.payload,
                payload.source,
                summary,
                fixture_id=fixture_id,
                source_endpoint=endpoint,
            )
            rows = parse_injury_rows(
                payload.payload,
                fixture_id=fixture_id,
                fetched_at=fetched_at,
                ingestion_source=payload.source,
            )
            summary.injuries += self._upsert_injuries(rows)
        elif key == DETAIL_PREDICTIONS:
            row = parse_api_prediction_row(
                payload.payload,
                fixture_id=fixture_id,
                fetched_at=fetched_at,
                ingestion_source=payload.source,
            )
            if row is None:
                summary.no_content += 1
            else:
                self._upsert_prediction(row)
                summary.predictions += 1
        if summary.unknown_players_queued:
            queue_path = (
                str(self.unknown_player_queue.path)
                if self.unknown_player_queue is not None
                else "disabled"
            )
            logger.warning(
                "Unknown live players queued for later resolution fixture_id=%s endpoint=%s "
                "count=%s queue_path=%s",
                fixture_id,
                endpoint,
                summary.unknown_players_queued,
                queue_path,
            )
        return summary

    def _fetch(
        self,
        endpoint: str,
        params: JsonDict,
        *,
        save_raw: bool,
    ) -> ApiFootballPayload:
        payload = self.client.get_payload(endpoint, params, save_raw=save_raw)
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

    def _upsert_fixture_statistics(self, rows: list[JsonDict]) -> int:
        for row in rows:
            match_fields = {
                "fixture_id": row.pop("fixture_id"),
                "team_id": row.pop("team_id"),
                "fetched_at": row.pop("fetched_at"),
            }
            upsert_by_fields(self.session, models.FixtureStatistics, match_fields, row)
        return len(rows)

    def _upsert_fixture_events(self, rows: list[JsonDict]) -> int:
        for row in rows:
            match_fields = {
                "fixture_id": row.pop("fixture_id"),
                "elapsed": row.pop("elapsed"),
                "extra": row.pop("extra"),
                "type": row.pop("type"),
                "detail": row.pop("detail"),
                "player_id": row.pop("player_id"),
                "assist_player_id": row.pop("assist_player_id"),
                "fetched_at": row.pop("fetched_at"),
            }
            upsert_by_fields(self.session, models.FixtureEvent, match_fields, row)
        return len(rows)

    def _upsert_fixture_lineups(self, rows: list[JsonDict]) -> int:
        for row in rows:
            match_fields = {
                "fixture_id": row.pop("fixture_id"),
                "team_id": row.pop("team_id"),
                "fetched_at": row.pop("fetched_at"),
            }
            upsert_by_fields(self.session, models.FixtureLineup, match_fields, row)
        return len(rows)

    def _upsert_fixture_player_stats(self, rows: list[JsonDict]) -> int:
        for row in rows:
            match_fields = {
                "fixture_id": row.pop("fixture_id"),
                "team_id": row.pop("team_id"),
                "player_id": row.pop("player_id"),
                "fetched_at": row.pop("fetched_at"),
            }
            upsert_by_fields(self.session, models.FixturePlayerStats, match_fields, row)
        return len(rows)

    def _upsert_injuries(self, rows: list[JsonDict]) -> int:
        for row in rows:
            match_fields = {
                "fixture_id": row.pop("fixture_id"),
                "team_id": row.pop("team_id"),
                "player_id": row.pop("player_id"),
                "reason": row.pop("reason"),
                "date": row.pop("date"),
                "fetched_at": row.pop("fetched_at"),
            }
            upsert_by_fields(self.session, models.Injury, match_fields, row)
        return len(rows)

    def _upsert_prediction(self, row: JsonDict) -> None:
        match_fields = {
            "fixture_id": row.pop("fixture_id"),
            "fetched_at": row.pop("fetched_at"),
            "source": row.pop("source"),
        }
        upsert_by_fields(self.session, models.ApiPredictionSnapshot, match_fields, row)

    def _upsert_players_from_events(
        self,
        payload: JsonDict,
        source: str,
        summary: FixtureDetailsIngestionSummary,
        *,
        fixture_id: int,
        source_endpoint: str,
    ) -> None:
        for row in response_items(payload):
            team_id = _optional_int(_as_dict(row.get("team")).get("id"))
            for key in ("player", "assist"):
                if self._upsert_player_from_payload(
                    _as_dict(row.get(key)),
                    source=source,
                    fixture_id=fixture_id,
                    team_id=team_id,
                    source_endpoint=source_endpoint,
                    summary=summary,
                ):
                    summary.players += 1
                elif _as_dict(row.get(key)):
                    summary.skipped += 1

    def _upsert_players_from_lineups(
        self,
        payload: JsonDict,
        source: str,
        summary: FixtureDetailsIngestionSummary,
        *,
        fixture_id: int,
        source_endpoint: str,
    ) -> None:
        for row in response_items(payload):
            team_id = _optional_int(_as_dict(row.get("team")).get("id"))
            for section in ("startXI", "substitutes"):
                raw_players = row.get(section)
                if not isinstance(raw_players, list):
                    continue
                for player_row in raw_players:
                    player = _as_dict(_as_dict(player_row).get("player"))
                    if self._upsert_player_from_payload(
                        player,
                        source=source,
                        fixture_id=fixture_id,
                        team_id=team_id,
                        source_endpoint=source_endpoint,
                        summary=summary,
                    ):
                        summary.players += 1
                    elif player:
                        summary.skipped += 1

    def _upsert_players_from_player_stats(
        self,
        payload: JsonDict,
        source: str,
        summary: FixtureDetailsIngestionSummary,
        *,
        fixture_id: int,
        source_endpoint: str,
    ) -> None:
        for team_row in response_items(payload):
            team_id = _optional_int(_as_dict(team_row.get("team")).get("id"))
            players = team_row.get("players")
            if not isinstance(players, list):
                continue
            for player_row in players:
                player = _as_dict(_as_dict(player_row).get("player"))
                if self._upsert_player_from_payload(
                    player,
                    source=source,
                    fixture_id=fixture_id,
                    team_id=team_id,
                    source_endpoint=source_endpoint,
                    summary=summary,
                ):
                    summary.players += 1
                elif player:
                    summary.skipped += 1

    def _upsert_players_from_injuries(
        self,
        payload: JsonDict,
        source: str,
        summary: FixtureDetailsIngestionSummary,
        *,
        fixture_id: int,
        source_endpoint: str,
    ) -> None:
        for row in response_items(payload):
            team_id = _optional_int(_as_dict(row.get("team")).get("id"))
            player = _as_dict(row.get("player"))
            if self._upsert_player_from_payload(
                player,
                source=source,
                fixture_id=fixture_id,
                team_id=team_id,
                source_endpoint=source_endpoint,
                summary=summary,
            ):
                summary.players += 1
            elif player:
                summary.skipped += 1

    def _upsert_player_from_payload(
        self,
        player: JsonDict,
        *,
        source: str,
        fixture_id: int | None = None,
        team_id: int | None = None,
        source_endpoint: str | None = None,
        summary: FixtureDetailsIngestionSummary | None = None,
    ) -> bool:
        player_id = player.get("id") or player.get("player_id")
        if player_id is None:
            return False
        typed_player_id = int(player_id)
        existing = self.session.get(models.Player, typed_player_id)
        reference_name = None
        reference_age = None
        reference_status = "not_checked"
        if self.players_reference is not None:
            try:
                reference_player = self.players_reference.find_player_by_id(typed_player_id)
                reference_name = reference_player.name
                reference_age = reference_player.age
                reference_status = "known_reference"
            except ReferenceLookupError:
                reference_status = "unknown_live"
                if summary is not None and self._queue_unknown_player(
                    player_id=typed_player_id,
                    name=player.get("name"),
                    fixture_id=fixture_id,
                    team_id=team_id,
                    source_endpoint=source_endpoint,
                ):
                    summary.unknown_players_queued += 1

        name = player.get("name") or _existing_value(existing, "name") or reference_name
        identity_incomplete = not bool(name)
        if not name:
            name = "Unknown API-Football player"

        values = {
            "name": name,
            "firstname": player.get("firstname") or _existing_value(existing, "firstname"),
            "lastname": player.get("lastname") or _existing_value(existing, "lastname"),
            "age": player.get("age") or _existing_value(existing, "age") or reference_age,
            "birth_date": _birth_date(player) or _existing_value(existing, "birth_date"),
            "nationality": player.get("nationality") or _existing_value(existing, "nationality"),
            "height": player.get("height") or _existing_value(existing, "height"),
            "weight": player.get("weight") or _existing_value(existing, "weight"),
            "injured": player.get("injured")
            if player.get("injured") is not None
            else _existing_value(existing, "injured"),
            "photo": player.get("photo") or _existing_value(existing, "photo"),
            "payload_json": {
                **player,
                "ingestion_source": source,
                "reference_status": reference_status,
                "identity_incomplete": identity_incomplete,
            },
        }
        upsert_by_fields(self.session, models.Player, {"player_id": typed_player_id}, values)
        return True

    def _queue_unknown_player(
        self,
        *,
        player_id: int,
        name: Any,
        fixture_id: int | None,
        team_id: int | None,
        source_endpoint: str | None,
    ) -> bool:
        if self.unknown_player_queue is None:
            return False
        fixture = self.session.get(models.Fixture, fixture_id) if fixture_id is not None else None
        record = UnknownPlayerRecord(
            player_id=player_id,
            name=str(name) if name else None,
            team_id=team_id,
            league_id=fixture.league_id if fixture is not None else None,
            season=fixture.season if fixture is not None else None,
            fixture_id=fixture_id,
            source_endpoint=source_endpoint,
        )
        return self.unknown_player_queue.append(record)

    def _require_fixture_exists(self, fixture_id: int) -> None:
        self.session.flush()
        if self.session.get(models.Fixture, fixture_id) is not None:
            return
        raise FootballPredictorError(
            f"fixture_id={fixture_id} is not in the local DB; run ingest-fixtures first"
        )

    def _warn_if_unknown_fixture(self, fixture_id: int) -> None:
        if self.reference is None:
            return
        try:
            self.reference.validate_fixture_reference(fixture_id)
        except ReferenceLookupError:
            logger.warning(
                "Fixture id not found in local reference; continuing live detail ingestion "
                "fixture_id=%s",
                fixture_id,
            )


def _normalize_include(include: Iterable[str] | None) -> tuple[str, ...]:
    if include is None:
        return ALL_DETAIL_KEYS
    normalized = tuple(item.strip().casefold() for item in include if item.strip())
    unknown = sorted(set(normalized) - set(ALL_DETAIL_KEYS))
    if unknown:
        raise FootballPredictorError(
            f"Unknown detail endpoint keys {unknown}; expected one of {list(ALL_DETAIL_KEYS)}"
        )
    return normalized or ALL_DETAIL_KEYS


def _normalized_statuses(
    *,
    status: str | None = None,
    statuses: Iterable[str] | None = None,
) -> list[str]:
    values: list[str] = []
    if status is not None:
        values.extend(_split_status_tokens(status))
    if statuses is not None:
        for item in statuses:
            values.extend(_split_status_tokens(item))
    return list(dict.fromkeys(values))


def _split_status_tokens(value: str) -> list[str]:
    return [item.strip().upper() for item in value.replace(",", " ").split() if item.strip()]


def _as_dict(value: Any) -> JsonDict:
    return value if isinstance(value, dict) else {}


def _existing_value(existing: models.Player | None, field_name: str) -> Any:
    return getattr(existing, field_name) if existing is not None else None


def _optional_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _birth_date(player: JsonDict) -> str | None:
    birth = _as_dict(player.get("birth"))
    value = birth.get("date") or player.get("birth_date")
    return str(value) if value is not None else None
