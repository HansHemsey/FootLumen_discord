from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import func, select
from typer.testing import CliRunner

from football_predictor.api.api_football_client import ApiFootballPayload
from football_predictor.api.endpoints import FIXTURES, STANDINGS
from football_predictor.cli import app
from football_predictor.config.settings import get_settings
from football_predictor.db import models
from football_predictor.db.init_db import create_db_and_tables
from football_predictor.db.session import create_session_factory, session_scope
from football_predictor.ingestion.fixtures import (
    FixtureIngestionService,
    StandingIngestionService,
    seed_fixtures_and_standings_from_reference,
)
from football_predictor.ingestion.parsers import parse_fixture_row, parse_standing_rows

JsonDict = dict[str, Any]


@dataclass
class FixtureApiClient:
    fixture_dir: Path
    calls: list[tuple[str, dict[str, Any], bool]] = field(default_factory=list)

    def get_payload(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
        *,
        save_raw: bool = False,
    ) -> ApiFootballPayload:
        safe_params = dict(params or {})
        self.calls.append((endpoint, safe_params, save_raw))
        return ApiFootballPayload(
            endpoint=endpoint,
            params=safe_params,
            payload=self._payload_for(endpoint, safe_params),
            fetched_at=datetime(2026, 5, 2, 10, tzinfo=UTC).isoformat(),
            status_code=200,
        )

    def _payload_for(self, endpoint: str, params: dict[str, Any]) -> JsonDict:
        if endpoint == STANDINGS:
            return _read_json(self.fixture_dir / "standings.json")
        if endpoint == FIXTURES and params.get("last") is not None:
            return _read_json(self.fixture_dir / "fixtures_team_last.json")
        if endpoint == FIXTURES and params.get("next") is not None:
            return _read_json(self.fixture_dir / "fixtures_team_next.json")
        return _read_json(self.fixture_dir / "fixtures_league_season.json")


def test_parse_fixture_finished_and_future(repo_root) -> None:
    payload = _read_json(repo_root / "tests/fixtures/api/fixtures_league_season.json")

    finished = parse_fixture_row(payload["response"][0])
    future = parse_fixture_row(payload["response"][1])

    assert finished["fixture_id"] == 1387797
    assert finished["status_short"] == "FT"
    assert finished["home_goals"] == 2
    assert future["fixture_id"] == 1387977
    assert future["status_short"] == "NS"
    assert future["home_goals"] is None


def test_parse_standings(repo_root) -> None:
    payload = _read_json(repo_root / "tests/fixtures/api/standings.json")

    standings = parse_standing_rows(
        payload,
        league_id=61,
        season=2025,
        fetched_at=datetime(2026, 5, 2, 10, tzinfo=UTC),
    )

    assert len(standings) == 2
    assert standings[0]["team_id"] == 85
    assert standings[0]["snapshot_date"] == datetime(2026, 5, 2, tzinfo=UTC)
    assert standings[1]["team_id"] == 77


def test_fixture_ingestion_writes_snapshot_and_is_idempotent(tmp_path, repo_root) -> None:
    engine = create_db_and_tables(f"sqlite:///{tmp_path / 'fixtures.db'}")
    session_factory = create_session_factory(engine)
    client = FixtureApiClient(repo_root / "tests/fixtures/api")

    with session_scope(session_factory) as session:
        service = FixtureIngestionService(session, client, save_raw=True)
        first = service.ingest_league_season(61, 2025)
        second = service.ingest_league_season(61, 2025)
        fixture_count = session.scalar(select(func.count()).select_from(models.Fixture))
        venue_count = session.scalar(select(func.count()).select_from(models.Venue))
        snapshot_count = session.scalar(select(func.count()).select_from(models.RawApiSnapshot))
        future_fixture = session.get(models.Fixture, 1387977)

    assert first.fixtures == 2
    assert second.fixtures == 2
    assert fixture_count == 2
    assert venue_count == 2
    assert snapshot_count == 2
    assert future_fixture is not None
    assert future_fixture.status_short == "NS"
    assert all(call[2] is True for call in client.calls)


def test_team_last_and_next_modes_use_expected_params(tmp_path, repo_root) -> None:
    engine = create_db_and_tables(f"sqlite:///{tmp_path / 'team_modes.db'}")
    session_factory = create_session_factory(engine)
    client = FixtureApiClient(repo_root / "tests/fixtures/api")

    with session_scope(session_factory) as session:
        service = FixtureIngestionService(session, client)
        last_summary = service.ingest_team_last(77, 1)
        next_summary = service.ingest_team_next(77, 1)

    assert last_summary.fixtures == 1
    assert next_summary.fixtures == 1
    assert client.calls[0][1] == {"team": 77, "last": 1}
    assert client.calls[1][1] == {"team": 77, "next": 1}


def test_standing_ingestion_creates_snapshots(tmp_path, repo_root) -> None:
    engine = create_db_and_tables(f"sqlite:///{tmp_path / 'standings.db'}")
    session_factory = create_session_factory(engine)
    client = FixtureApiClient(repo_root / "tests/fixtures/api")

    with session_scope(session_factory) as session:
        summary = StandingIngestionService(session, client).ingest_league_season(61, 2025)
        standing_count = session.scalar(select(func.count()).select_from(models.StandingSnapshot))
        raw_count = session.scalar(select(func.count()).select_from(models.RawApiSnapshot))
        angers = session.scalar(
            select(models.StandingSnapshot).where(models.StandingSnapshot.team_id == 77)
        )

    assert summary.standings == 2
    assert standing_count == 2
    assert raw_count == 1
    assert angers is not None
    assert angers.fetched_at is not None
    assert angers.snapshot_date is not None


def test_docs_fixture_seed_marks_reference_source(tmp_path, reference_sample_path) -> None:
    engine = create_db_and_tables(f"sqlite:///{tmp_path / 'docs_fixtures.db'}")
    session_factory = create_session_factory(engine)

    with session_scope(session_factory) as session:
        summary = seed_fixtures_and_standings_from_reference(
            session,
            reference_sample_path,
            league_id=61,
            season=2025,
        )
        fixture = session.get(models.Fixture, 1387797)
        raw_count = session.scalar(select(func.count()).select_from(models.RawApiSnapshot))

    assert summary.fixtures == 1
    assert fixture is not None
    assert fixture.payload_json["ingestion_source"] == "docs/reference"
    assert raw_count == 0


def test_cli_ingest_fixtures_league_defaults_to_docs(tmp_path) -> None:
    get_settings.cache_clear()
    runner = CliRunner()

    result = runner.invoke(
        app,
        ["ingest-fixtures", "--league", "61", "--season", "2025", "--dry-run"],
        env={"DATABASE_URL": f"sqlite:///{tmp_path / 'cli_docs_default.db'}"},
    )

    assert result.exit_code == 0
    assert "'fixtures': 306" in result.stdout
    get_settings.cache_clear()


def test_cli_rejects_synthetic_unknown_team_id() -> None:
    get_settings.cache_clear()
    runner = CliRunner()

    result = runner.invoke(
        app,
        ["ingest-fixtures", "--team-id=-999", "--last", "1", "--prefer-docs"],
    )

    assert result.exit_code != 0
    assert "Unknown team_id=-999" in result.output
    get_settings.cache_clear()


def test_cli_docs_dry_run_uses_reference_without_network(tmp_path) -> None:
    get_settings.cache_clear()
    runner = CliRunner()

    result = runner.invoke(
        app,
        [
            "ingest-fixtures",
            "--league-id",
            "61",
            "--season",
            "2025",
            "--prefer-docs",
            "--dry-run",
        ],
        env={"DATABASE_URL": f"sqlite:///{tmp_path / 'cli_docs.db'}"},
    )

    assert result.exit_code == 0
    assert "'fixtures': 306" in result.stdout
    assert "'dry_run': 1" in result.stdout
    get_settings.cache_clear()


def test_cli_ingest_fixtures_date_defaults_to_docs(tmp_path) -> None:
    get_settings.cache_clear()
    runner = CliRunner()

    result = runner.invoke(
        app,
        ["ingest-fixtures", "--date", "2025-11-09", "--dry-run"],
        env={"DATABASE_URL": f"sqlite:///{tmp_path / 'cli_docs_date.db'}"},
    )

    assert result.exit_code == 0
    assert "'fixtures': 23" in result.stdout
    get_settings.cache_clear()


def test_parse_fixture_rejects_incomplete_synthetic_row() -> None:
    with pytest.raises(TypeError):
        parse_fixture_row({"fixture": {"id": -1}})


def _read_json(path: Path) -> JsonDict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload
