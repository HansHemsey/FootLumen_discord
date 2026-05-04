"""Ingestion workflows."""

from football_predictor.ingestion.api_reference import ApiReferenceIngestionService
from football_predictor.ingestion.fixtures import (
    FixtureIngestionService,
    MatchIngestionSummary,
    StandingIngestionService,
    seed_fixtures_and_standings_from_reference,
)
from football_predictor.ingestion.ingest_fixtures import FixtureIngestor
from football_predictor.ingestion.ingest_match_details import (
    FixtureDetailsIngestionService,
    FixtureDetailsIngestionSummary,
)
from football_predictor.ingestion.ingest_odds import OddsIngestionService, OddsIngestionSummary
from football_predictor.ingestion.ingest_reference import (
    ReferenceIngestOptions,
    ingest_reference_live,
)
from football_predictor.ingestion.ingest_standings import StandingIngestor
from football_predictor.ingestion.seed_reference import (
    PlayersSeedService,
    ReferenceSeedService,
    SeedSummary,
    seed_reference_from_docs,
)

__all__ = [
    "ApiReferenceIngestionService",
    "FixtureIngestionService",
    "FixtureDetailsIngestionService",
    "FixtureDetailsIngestionSummary",
    "FixtureIngestor",
    "MatchIngestionSummary",
    "PlayersSeedService",
    "ReferenceSeedService",
    "ReferenceIngestOptions",
    "OddsIngestionService",
    "OddsIngestionSummary",
    "SeedSummary",
    "StandingIngestionService",
    "StandingIngestor",
    "seed_fixtures_and_standings_from_reference",
    "ingest_reference_live",
    "seed_reference_from_docs",
]
