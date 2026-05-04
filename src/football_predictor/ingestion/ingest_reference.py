"""Reference ingestion entry points used by CLI and tests."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from football_predictor.config.competitions import CompetitionConfig
from football_predictor.ingestion.api_reference import (
    ApiFootballClientProtocol,
    ApiReferenceIngestionService,
)
from football_predictor.ingestion.seed_reference import (
    PlayersSeedService,
    ReferenceSeedService,
    SeedSummary,
)
from football_predictor.ingestion.seed_reference import (
    seed_reference_from_docs as _seed_reference_from_docs,
)


@dataclass(frozen=True)
class ReferenceIngestOptions:
    dry_run: bool = False
    save_raw: bool = False
    prefer_docs: bool = True
    refresh_live: bool = False


def seed_reference_from_docs(
    session: Session,
    reference_path: str | Path,
    players_path: str | Path,
    *,
    dry_run: bool = False,
) -> SeedSummary:
    """Seed DB from local docs and optionally roll back the transaction."""
    summary = _seed_reference_from_docs(session, reference_path, players_path)
    if dry_run:
        session.rollback()
    return summary


def ingest_reference_live(
    session: Session,
    client: ApiFootballClientProtocol,
    competitions: list[CompetitionConfig],
    *,
    save_raw: bool = False,
) -> SeedSummary:
    """Ingest live API reference endpoints with DB RawApiSnapshot storage."""
    service = ApiReferenceIngestionService(session, client, save_raw=save_raw)
    summary = SeedSummary()
    summary.merge(service.ingest_leagues(competitions))
    summary.merge(service.ingest_teams(competitions))
    summary.merge(service.ingest_player_squads(competitions))
    return summary


def summary_from_dict(payload: dict[str, Any]) -> SeedSummary:
    """Build a summary from a dict, mainly for thin adapters."""
    summary = SeedSummary()
    for key, value in payload.items():
        if key == "errors" and isinstance(value, list):
            summary.errors.extend(str(item) for item in value)
        elif hasattr(summary, key) and isinstance(value, int):
            setattr(summary, key, value)
    return summary


__all__ = [
    "ApiReferenceIngestionService",
    "PlayersSeedService",
    "ReferenceIngestOptions",
    "ReferenceSeedService",
    "SeedSummary",
    "ingest_reference_live",
    "seed_reference_from_docs",
    "summary_from_dict",
]
