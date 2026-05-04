"""Public standings ingestion facade."""

from __future__ import annotations

from sqlalchemy.orm import Session

from football_predictor.ingestion.fixtures import (
    ApiFootballPayloadClient,
    MatchIngestionSummary,
    StandingIngestionService,
)
from football_predictor.reference.lookups import ApiFootballReference
from football_predictor.utils.logging import get_logger

logger = get_logger(__name__)


class StandingIngestor:
    """Ingest standings with optional non-blocking local reference validation."""

    def __init__(
        self,
        session: Session,
        client: ApiFootballPayloadClient,
        *,
        reference: ApiFootballReference | None = None,
        save_raw: bool = False,
    ) -> None:
        self.reference = reference
        self.service = StandingIngestionService(session, client, save_raw=save_raw)

    def ingest_standings(self, league_id: int, season: int) -> MatchIngestionSummary:
        self._warn_if_unknown_league(league_id, season)
        return self.service.ingest_league_season(league_id, season)

    def _warn_if_unknown_league(self, league_id: int, season: int) -> None:
        if self.reference is None:
            return
        try:
            self.reference.find_league_by_id(league_id, season)
        except Exception:
            logger.warning(
                "League id not found in local reference; continuing live standings ingestion "
                "league_id=%s season=%s",
                league_id,
                season,
            )


__all__ = ["StandingIngestor", "MatchIngestionSummary"]
