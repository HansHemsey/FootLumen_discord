from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from unittest.mock import patch

from sqlalchemy import func, select
from typer.testing import CliRunner

from football_predictor.api.api_football_client import ApiFootballPayload
from football_predictor.api.endpoints import STANDINGS
from football_predictor.cli import app
from football_predictor.config.settings import get_settings
from football_predictor.db import models
from football_predictor.db.init_db import create_db_and_tables
from football_predictor.db.session import create_session_factory, session_scope
from football_predictor.ingestion.ingest_standings import StandingIngestor
from football_predictor.ingestion.parsers import parse_standing_rows
from football_predictor.reference.loaders import load_api_football_reference

JsonDict = dict[str, Any]


@dataclass
class StandingPayloadClient:
    fixture_dir: Path

    def get_payload(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
        *,
        save_raw: bool = False,
    ) -> ApiFootballPayload:
        del save_raw
        return ApiFootballPayload(
            endpoint=endpoint,
            params=dict(params or {}),
            payload=_read_json(self.fixture_dir / "standings.json"),
            fetched_at=datetime(2026, 5, 2, 12, tzinfo=UTC).isoformat(),
            status_code=200,
        )


def test_parse_standings_snapshot(repo_root) -> None:
    payload = _read_json(repo_root / "tests/fixtures/api/standings.json")
    fetched_at = datetime(2026, 5, 2, 12, tzinfo=UTC)

    standings = parse_standing_rows(payload, league_id=61, season=2025, fetched_at=fetched_at)

    assert len(standings) == 2
    assert standings[0]["league_id"] == 61
    assert standings[0]["season"] == 2025
    assert standings[0]["team_id"] == 85
    assert standings[0]["snapshot_date"] == datetime(2026, 5, 2, tzinfo=UTC)
    assert standings[1]["team_id"] == 77


def test_standing_ingestor_snapshots_are_idempotent_by_team_and_snapshot_date(
    tmp_path,
    repo_root,
    reference_path,
) -> None:
    engine = create_db_and_tables(f"sqlite:///{tmp_path / 'standing_ingestor.db'}")
    session_factory = create_session_factory(engine)
    client = StandingPayloadClient(repo_root / "tests/fixtures/api")
    reference = load_api_football_reference(reference_path)

    with session_scope(session_factory) as session:
        ingestor = StandingIngestor(session, client, reference=reference)
        first = ingestor.ingest_standings(61, 2025)
        second = ingestor.ingest_standings(61, 2025)
        standings = session.scalar(select(func.count()).select_from(models.StandingSnapshot))
        snapshots = session.scalar(select(func.count()).select_from(models.RawApiSnapshot))
        angers = session.scalar(
            select(models.StandingSnapshot).where(models.StandingSnapshot.team_id == 77)
        )

    assert first.standings == 2
    assert second.standings == 2
    assert standings == 2
    assert snapshots == 2
    assert angers is not None
    assert angers.fetched_at is not None
    assert angers.snapshot_date is not None
    assert angers.payload_json["ingestion_source"] == "api-football"


def test_live_standing_unknown_reference_id_warns_without_blocking(
    tmp_path,
    repo_root,
    reference_path,
) -> None:
    engine = create_db_and_tables(f"sqlite:///{tmp_path / 'standing_unknown.db'}")
    session_factory = create_session_factory(engine)
    client = StandingPayloadClient(repo_root / "tests/fixtures/api")
    reference = load_api_football_reference(reference_path)

    with (
        patch("football_predictor.ingestion.ingest_standings.logger.warning") as warning,
        session_scope(session_factory) as session,
    ):
        summary = StandingIngestor(session, client, reference=reference).ingest_standings(
            -999,
            2025,
        )

    assert summary.standings == 2
    warning.assert_called_once()


def test_standings_endpoint_constant_is_used() -> None:
    assert STANDINGS == "/standings"


def test_cli_ingest_standings_league_defaults_to_docs(tmp_path) -> None:
    get_settings.cache_clear()
    runner = CliRunner()

    result = runner.invoke(
        app,
        ["ingest-standings", "--league", "61", "--season", "2025", "--dry-run"],
        env={"DATABASE_URL": f"sqlite:///{tmp_path / 'cli_standings_docs.db'}"},
    )

    assert result.exit_code == 0
    assert "'standings': 18" in result.stdout
    get_settings.cache_clear()


def _read_json(path: Path) -> JsonDict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload
