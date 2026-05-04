from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any
from unittest.mock import patch

from sqlalchemy import func, select

from football_predictor.api.api_football_client import ApiFootballPayload
from football_predictor.api.endpoints import FIXTURES
from football_predictor.db import models
from football_predictor.db.init_db import create_db_and_tables
from football_predictor.db.session import create_session_factory, session_scope
from football_predictor.ingestion.ingest_fixtures import FixtureIngestor
from football_predictor.ingestion.parsers import parse_fixture_row
from football_predictor.reference.loaders import load_api_football_reference

JsonDict = dict[str, Any]


@dataclass
class FixturePayloadClient:
    fixture_dir: Path

    def get_payload(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
        *,
        save_raw: bool = False,
    ) -> ApiFootballPayload:
        del save_raw
        safe_params = dict(params or {})
        return ApiFootballPayload(
            endpoint=endpoint,
            params=safe_params,
            payload=self._payload_for(safe_params),
            fetched_at=datetime(2026, 5, 2, 12, tzinfo=UTC).isoformat(),
            status_code=200,
        )

    def _payload_for(self, params: dict[str, Any]) -> JsonDict:
        if params.get("next") is not None:
            return _read_json(self.fixture_dir / "fixtures_upcoming.json")
        if params.get("date") is not None:
            return _read_json(self.fixture_dir / "fixtures_finished.json")
        return _read_json(self.fixture_dir / "fixtures_finished.json")


def test_parse_finished_fixture(repo_root) -> None:
    payload = _read_json(repo_root / "tests/fixtures/api/fixtures_finished.json")

    fixture = parse_fixture_row(payload["response"][0])

    assert fixture["fixture_id"] == 1387797
    assert fixture["status_short"] == "FT"
    assert fixture["league_id"] == 61
    assert fixture["home_team_id"] == 77
    assert fixture["away_team_id"] == 108
    assert fixture["home_goals"] == 2


def test_parse_upcoming_fixture(repo_root) -> None:
    payload = _read_json(repo_root / "tests/fixtures/api/fixtures_upcoming.json")

    fixture = parse_fixture_row(payload["response"][0])

    assert fixture["fixture_id"] == 1387977
    assert fixture["status_short"] == "NS"
    assert fixture["home_goals"] is None
    assert fixture["away_goals"] is None


def test_fixture_ingestor_methods_are_idempotent(tmp_path, repo_root, reference_path) -> None:
    engine = create_db_and_tables(f"sqlite:///{tmp_path / 'fixture_ingestor.db'}")
    session_factory = create_session_factory(engine)
    client = FixturePayloadClient(repo_root / "tests/fixtures/api")
    reference = load_api_football_reference(reference_path)

    with session_scope(session_factory) as session:
        ingestor = FixtureIngestor(session, client, reference=reference)
        first = ingestor.ingest_fixtures_by_league_season(61, 2025)
        second = ingestor.ingest_fixtures_by_league_season(61, 2025)
        by_date = ingestor.ingest_fixtures_by_date(date(2026, 5, 2), league_id=61, season=2025)
        last = ingestor.ingest_team_last_fixtures(77, 1, season=2025)
        next_summary = ingestor.ingest_team_next_fixtures(77, 1, season=2025)
        fixtures = session.scalar(select(func.count()).select_from(models.Fixture))
        snapshots = session.scalar(select(func.count()).select_from(models.RawApiSnapshot))
        upcoming = session.get(models.Fixture, 1387977)

    assert first.fixtures == 1
    assert second.fixtures == 1
    assert by_date.fixtures == 1
    assert last.fixtures == 1
    assert next_summary.fixtures == 1
    assert fixtures == 2
    assert snapshots == 5
    assert upcoming is not None
    assert upcoming.status_short == "NS"


def test_live_fixture_unknown_reference_id_warns_without_blocking(
    tmp_path,
    repo_root,
    reference_path,
) -> None:
    engine = create_db_and_tables(f"sqlite:///{tmp_path / 'fixture_unknown.db'}")
    session_factory = create_session_factory(engine)
    client = FixturePayloadClient(repo_root / "tests/fixtures/api")
    reference = load_api_football_reference(reference_path)

    with (
        patch("football_predictor.ingestion.ingest_fixtures.logger.warning") as warning,
        session_scope(session_factory) as session,
    ):
        ingestor = FixtureIngestor(session, client, reference=reference)
        summary = ingestor.ingest_team_last_fixtures(-999, 1)

    assert summary.fixtures == 1
    warning.assert_called_once()


def test_fixture_client_endpoint_constant_is_used() -> None:
    assert FIXTURES == "/fixtures"


def _read_json(path: Path) -> JsonDict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload
