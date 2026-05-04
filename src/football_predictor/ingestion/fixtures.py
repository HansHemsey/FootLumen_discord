"""Fixture and standing ingestion services."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any, Protocol

from sqlalchemy.orm import Session

from football_predictor.api.api_football_client import ApiFootballPayload
from football_predictor.api.endpoints import FIXTURES, STANDINGS
from football_predictor.db import models
from football_predictor.db.repositories import insert_raw_api_snapshot, upsert_by_fields
from football_predictor.ingestion.parsers import (
    parse_fixture_row,
    parse_fixture_venue,
    parse_standing_row,
    parse_standing_rows,
    response_items,
)
from football_predictor.reference.loaders import load_api_football_reference
from football_predictor.utils.time import parse_datetime, utc_now

JsonDict = dict[str, Any]


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
class MatchIngestionSummary:
    fixtures: int = 0
    standings: int = 0
    venues: int = 0
    raw_snapshots: int = 0
    skipped: int = 0
    errors: list[str] = field(default_factory=list)

    def merge(self, other: MatchIngestionSummary) -> MatchIngestionSummary:
        self.fixtures += other.fixtures
        self.standings += other.standings
        self.venues += other.venues
        self.raw_snapshots += other.raw_snapshots
        self.skipped += other.skipped
        self.errors.extend(other.errors)
        return self

    def as_dict(self) -> dict[str, int | list[str]]:
        return {
            "fixtures": self.fixtures,
            "standings": self.standings,
            "venues": self.venues,
            "raw_snapshots": self.raw_snapshots,
            "skipped": self.skipped,
            "errors": self.errors,
        }


class FixtureIngestionService:
    """Ingest `/fixtures` data through the central API-Football client."""

    def __init__(
        self,
        session: Session,
        client: ApiFootballPayloadClient,
        *,
        save_raw: bool = False,
    ) -> None:
        self.session = session
        self.client = client
        self.save_raw = save_raw

    def ingest_league_season(self, league_id: int, season: int) -> MatchIngestionSummary:
        return self._ingest({"league": league_id, "season": season})

    def ingest_fixture_by_id(self, fixture_id: int) -> MatchIngestionSummary:
        return self._ingest({"id": fixture_id})

    def ingest_date(
        self,
        fixture_date: date,
        league_id: int | None = None,
        season: int | None = None,
    ) -> MatchIngestionSummary:
        params: JsonDict = {"date": fixture_date.isoformat()}
        if league_id is not None:
            params["league"] = league_id
        if season is not None:
            params["season"] = season
        return self._ingest(params)

    def ingest_team_last(self, team_id: int, last: int) -> MatchIngestionSummary:
        return self._ingest({"team": team_id, "last": last})

    def ingest_team_next(self, team_id: int, next_count: int) -> MatchIngestionSummary:
        return self._ingest({"team": team_id, "next": next_count})

    def _ingest(self, params: JsonDict) -> MatchIngestionSummary:
        payload = self._fetch(FIXTURES, params)
        summary = MatchIngestionSummary(raw_snapshots=1)
        for row in response_items(payload.payload):
            self._upsert_fixture(row, summary, ingestion_source=payload.source)
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

    def _upsert_fixture(
        self,
        row: JsonDict,
        summary: MatchIngestionSummary,
        *,
        ingestion_source: str,
    ) -> None:
        try:
            venue = parse_fixture_venue(row, ingestion_source=ingestion_source)
            if venue is not None:
                venue_id = venue.pop("venue_id")
                upsert_by_fields(self.session, models.Venue, {"venue_id": venue_id}, venue)
                summary.venues += 1
            values = parse_fixture_row(row, ingestion_source=ingestion_source)
            fixture_id = values.pop("fixture_id")
            upsert_by_fields(self.session, models.Fixture, {"fixture_id": fixture_id}, values)
            summary.fixtures += 1
        except (KeyError, TypeError, ValueError) as exc:
            summary.skipped += 1
            summary.errors.append(f"Skipped fixture row: {exc}")


class StandingIngestionService:
    """Ingest `/standings` snapshots through the central API-Football client."""

    def __init__(
        self,
        session: Session,
        client: ApiFootballPayloadClient,
        *,
        save_raw: bool = False,
    ) -> None:
        self.session = session
        self.client = client
        self.save_raw = save_raw

    def ingest_league_season(self, league_id: int, season: int) -> MatchIngestionSummary:
        payload = self.client.get_payload(
            STANDINGS,
            {"league": league_id, "season": season},
            save_raw=self.save_raw,
        )
        fetched_at = parse_datetime(payload.fetched_at) or utc_now()
        insert_raw_api_snapshot(
            self.session,
            endpoint=payload.endpoint,
            params_json=payload.params,
            payload_json=payload.payload,
            fetched_at=fetched_at,
            status_code=payload.status_code,
            source=payload.source,
        )
        summary = MatchIngestionSummary(raw_snapshots=1)
        for row in parse_standing_rows(
            payload.payload,
            league_id=league_id,
            season=season,
            fetched_at=fetched_at,
            ingestion_source=payload.source,
        ):
            self._upsert_standing(row, summary)
        self.session.flush()
        return summary

    def _upsert_standing(self, values: JsonDict, summary: MatchIngestionSummary) -> None:
        _upsert_standing_values(self.session, values, summary)


def seed_fixtures_and_standings_from_reference(
    session: Session,
    reference_path: str | Path,
    *,
    league_id: int | None = None,
    season: int | None = None,
    fixture_date: date | None = None,
    include_fixtures: bool = True,
    include_standings: bool = True,
) -> MatchIngestionSummary:
    """Seed fixtures and standings from docs reference without live snapshots."""
    reference = load_api_football_reference(reference_path)
    summary = MatchIngestionSummary()
    fetched_at = utc_now()
    for competition in reference.competitions:
        league = competition.get("league") or {}
        current_league_id = league.get("id")
        current_season = league.get("season") or (competition.get("target") or {}).get("season")
        if current_league_id is None or current_season is None:
            summary.skipped += 1
            continue
        if league_id is not None and int(current_league_id) != league_id:
            continue
        if season is not None and int(current_season) != season:
            continue
        if include_fixtures:
            for fixture in competition.get("fixtures") or []:
                if isinstance(fixture, dict) and _fixture_matches_date(fixture, fixture_date):
                    _upsert_docs_fixture(session, fixture, summary)
        if include_standings:
            for standing in competition.get("standings") or []:
                if not isinstance(standing, dict):
                    continue
                raw_payload = standing.get("raw")
                raw_standing: JsonDict = raw_payload if isinstance(raw_payload, dict) else standing
                parsed = parse_standing_row(
                    raw_standing,
                    league_id=int(current_league_id),
                    season=int(current_season),
                    fetched_at=fetched_at,
                    ingestion_source="docs/reference",
                )
                if parsed is None:
                    summary.skipped += 1
                    continue
                _upsert_standing_values(session, parsed, summary)
    session.flush()
    return summary


def _fixture_matches_date(fixture: JsonDict, fixture_date: date | None) -> bool:
    if fixture_date is None:
        return True
    parsed = parse_datetime(fixture.get("date"))
    return parsed is not None and parsed.date() == fixture_date


def _upsert_docs_fixture(
    session: Session,
    fixture: JsonDict,
    summary: MatchIngestionSummary,
) -> None:
    venue = parse_fixture_venue(fixture, ingestion_source="docs/reference")
    if venue is not None:
        venue_id = venue.pop("venue_id")
        upsert_by_fields(session, models.Venue, {"venue_id": venue_id}, venue)
        summary.venues += 1
    values = parse_fixture_row(fixture, ingestion_source="docs/reference")
    fixture_id = values.pop("fixture_id")
    upsert_by_fields(session, models.Fixture, {"fixture_id": fixture_id}, values)
    summary.fixtures += 1


def _upsert_standing_values(
    session: Session,
    values: JsonDict,
    summary: MatchIngestionSummary,
) -> None:
    match_fields = {
        "league_id": values.pop("league_id"),
        "season": values.pop("season"),
        "team_id": values.pop("team_id"),
        "snapshot_date": values.pop("snapshot_date"),
    }
    upsert_by_fields(session, models.StandingSnapshot, match_fields, values)
    summary.standings += 1
