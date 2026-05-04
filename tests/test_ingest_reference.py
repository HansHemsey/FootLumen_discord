from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import func, select

from football_predictor.api.api_football_client import ApiFootballPayload
from football_predictor.api.endpoints import LEAGUES, PLAYERS_SQUADS, TEAMS
from football_predictor.config.competitions import CompetitionConfig
from football_predictor.db import models
from football_predictor.db.init_db import create_db_and_tables
from football_predictor.db.session import create_session_factory, session_scope
from football_predictor.ingestion.ingest_reference import (
    ingest_reference_live,
    seed_reference_from_docs,
)

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
        payload = self._payload_for(endpoint, safe_params)
        return ApiFootballPayload(
            endpoint=endpoint,
            params=safe_params,
            payload=payload,
            fetched_at=datetime(2026, 5, 2, 10, tzinfo=UTC).isoformat(),
            status_code=200,
        )

    def _payload_for(self, endpoint: str, params: dict[str, Any]) -> JsonDict:
        if endpoint == LEAGUES:
            return _read_json(self.fixture_dir / "leagues.json")
        if endpoint == TEAMS:
            return _read_json(self.fixture_dir / "teams.json")
        if endpoint == PLAYERS_SQUADS and params.get("team") == 77:
            return _read_json(self.fixture_dir / "players_squads.json")
        return {"response": []}


def test_seed_reference_from_docs_sample_is_idempotent(
    tmp_path,
    reference_sample_path,
    players_reference_sample_path,
) -> None:
    engine = create_db_and_tables(f"sqlite:///{tmp_path / 'seed_sample.db'}")
    session_factory = create_session_factory(engine)

    with session_scope(session_factory) as session:
        first = seed_reference_from_docs(
            session,
            reference_sample_path,
            players_reference_sample_path,
        )
    with session_scope(session_factory) as session:
        second = seed_reference_from_docs(
            session,
            reference_sample_path,
            players_reference_sample_path,
        )
        counts = _reference_counts(session)

    assert first.errors == []
    assert second.errors == []
    assert counts == {
        "leagues": 1,
        "teams": 2,
        "venues": 2,
        "fixtures": 1,
        "bookmakers": 1,
        "bets": 2,
        "players": 2,
        "squads": 2,
    }


def test_seed_reference_from_docs_dry_run_rolls_back(
    tmp_path,
    reference_sample_path,
    players_reference_sample_path,
) -> None:
    engine = create_db_and_tables(f"sqlite:///{tmp_path / 'seed_dry_run.db'}")
    session_factory = create_session_factory(engine)

    with session_scope(session_factory) as session:
        summary = seed_reference_from_docs(
            session,
            reference_sample_path,
            players_reference_sample_path,
            dry_run=True,
        )
        counts = _reference_counts(session)

    assert summary.leagues == 1
    assert counts["leagues"] == 0
    assert counts["players"] == 0


def test_live_reference_ingestion_mocked_writes_snapshots_and_upserts(tmp_path, repo_root) -> None:
    engine = create_db_and_tables(f"sqlite:///{tmp_path / 'live_reference.db'}")
    session_factory = create_session_factory(engine)
    client = FixtureApiClient(repo_root / "tests" / "fixtures" / "api")
    competition = CompetitionConfig(
        key="ligue_1",
        league_id=61,
        season=2025,
        name="Ligue 1",
        country="France",
        source="tests/fixtures/reference/reference_sample.json",
    )

    with session_scope(session_factory) as session:
        summary = ingest_reference_live(session, client, [competition], save_raw=True)
        counts = _reference_counts(session)
        snapshots = session.scalar(select(func.count()).select_from(models.RawApiSnapshot))

    assert summary.leagues == 1
    assert summary.teams == 2
    assert summary.players == 2
    assert summary.squads == 2
    assert counts["leagues"] == 1
    assert counts["teams"] == 2
    assert counts["players"] == 2
    assert snapshots == 4
    assert all(call[2] is True for call in client.calls)


def _reference_counts(session) -> dict[str, int | None]:
    return {
        "leagues": session.scalar(select(func.count()).select_from(models.League)),
        "teams": session.scalar(select(func.count()).select_from(models.Team)),
        "venues": session.scalar(select(func.count()).select_from(models.Venue)),
        "fixtures": session.scalar(select(func.count()).select_from(models.Fixture)),
        "bookmakers": session.scalar(select(func.count()).select_from(models.Bookmaker)),
        "bets": session.scalar(select(func.count()).select_from(models.Bet)),
        "players": session.scalar(select(func.count()).select_from(models.Player)),
        "squads": session.scalar(select(func.count()).select_from(models.PlayerSquad)),
    }


def _read_json(path: Path) -> JsonDict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload
