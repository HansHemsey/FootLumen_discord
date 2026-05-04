"""Public fixture ingestion facade.

This module keeps the Sprint 5 method names stable while delegating to the
shared fixture ingestion service.
"""

from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session

from football_predictor.ingestion.fixtures import (
    ApiFootballPayloadClient,
    FixtureIngestionService,
    MatchIngestionSummary,
)
from football_predictor.reference.lookups import ApiFootballReference
from football_predictor.utils.logging import get_logger

logger = get_logger(__name__)


class FixtureIngestor:
    """Ingest fixtures with optional non-blocking local reference validation."""

    def __init__(
        self,
        session: Session,
        client: ApiFootballPayloadClient,
        *,
        reference: ApiFootballReference | None = None,
        save_raw: bool = False,
    ) -> None:
        self.reference = reference
        self.service = FixtureIngestionService(session, client, save_raw=save_raw)

    def ingest_fixtures_by_league_season(
        self,
        league_id: int,
        season: int,
    ) -> MatchIngestionSummary:
        self._warn_if_unknown_league(league_id, season)
        return self.service.ingest_league_season(league_id, season)

    def ingest_fixture_by_id(self, fixture_id: int) -> MatchIngestionSummary:
        self._warn_if_unknown_fixture(fixture_id)
        return self.service.ingest_fixture_by_id(fixture_id)

    def ingest_fixtures_by_date(
        self,
        target_date: date,
        league_id: int | None = None,
        season: int | None = None,
    ) -> MatchIngestionSummary:
        if league_id is not None:
            self._warn_if_unknown_league(league_id, season)
        return self.service.ingest_date(target_date, league_id=league_id, season=season)

    def ingest_team_last_fixtures(
        self,
        team_id: int,
        n: int,
        season: int | None = None,
    ) -> MatchIngestionSummary:
        del season
        self._warn_if_unknown_team(team_id)
        return self.service.ingest_team_last(team_id, n)

    def ingest_team_next_fixtures(
        self,
        team_id: int,
        n: int,
        season: int | None = None,
    ) -> MatchIngestionSummary:
        del season
        self._warn_if_unknown_team(team_id)
        return self.service.ingest_team_next(team_id, n)

    def _warn_if_unknown_league(self, league_id: int, season: int | None = None) -> None:
        if self.reference is None:
            return
        try:
            self.reference.find_league_by_id(league_id, season)
        except Exception:
            logger.warning(
                "League id not found in local reference; continuing live ingestion "
                "league_id=%s season=%s",
                league_id,
                season,
            )

    def _warn_if_unknown_team(self, team_id: int) -> None:
        if self.reference is None:
            return
        try:
            self.reference.find_team_by_id(team_id)
        except Exception:
            logger.warning(
                "Team id not found in local reference; continuing live ingestion team_id=%s",
                team_id,
            )

    def _warn_if_unknown_fixture(self, fixture_id: int) -> None:
        if self.reference is None:
            return
        try:
            self.reference.validate_fixture_reference(fixture_id)
        except Exception:
            logger.warning(
                "Fixture id not found in local reference; continuing live ingestion fixture_id=%s",
                fixture_id,
            )


__all__ = ["FixtureIngestor", "MatchIngestionSummary"]
