from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import select
from typer.testing import CliRunner

from football_predictor.api.api_football_client import ApiFootballPayload
from football_predictor.api.endpoints import PLAYERS, PLAYERS_SQUADS
from football_predictor.api.exceptions import ApiFootballRateLimitError
from football_predictor.cli import app
from football_predictor.db import models
from football_predictor.db.init_db import create_db_and_tables
from football_predictor.db.session import create_session_factory, session_scope
from football_predictor.ingestion.ingest_match_details import FixtureDetailsIngestionService
from football_predictor.ingestion.unknown_players import (
    UnknownPlayerQueue,
    UnknownPlayerRecord,
    UnknownPlayerResolutionService,
)
from football_predictor.reference.loaders import load_players_reference

JsonDict = dict[str, Any]


@dataclass
class UnknownPlayerClient:
    payloads: dict[str, JsonDict]
    rate_limit: bool = False
    calls: list[tuple[str, dict[str, Any]]] = field(default_factory=list)

    def get_payload(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
        *,
        save_raw: bool = False,
    ) -> ApiFootballPayload:
        del save_raw
        safe_params = dict(params or {})
        self.calls.append((endpoint, safe_params))
        if self.rate_limit:
            raise ApiFootballRateLimitError(
                f"Rate limit endpoint={endpoint} status_code=429 params={safe_params}"
            )
        payload = self.payloads[endpoint]
        return ApiFootballPayload(
            endpoint=endpoint,
            params=safe_params,
            payload=payload,
            fetched_at=datetime(2026, 5, 3, 8, tzinfo=UTC).isoformat(),
            status_code=200,
        )


def test_unknown_player_queue_writes_jsonl_and_deduplicates(tmp_path: Path) -> None:
    queue_path = tmp_path / "unknown_players.jsonl"
    queue = UnknownPlayerQueue(queue_path)
    record = UnknownPlayerRecord(
        player_id=-700001,
        name="Synthetic Unknown",
        team_id=-40,
        league_id=-39,
        season=2025,
        fixture_id=-100,
        source_endpoint="/fixtures/players",
    )

    assert queue.append(record) is True
    assert queue.append(record) is False

    lines = queue_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    payload = json.loads(lines[0])
    assert payload["player_id"] == -700001
    assert payload["source_endpoint"] == "/fixtures/players"


def test_fixture_detail_ingestion_queues_unknown_player(
    tmp_path: Path,
    repo_root: Path,
    players_reference_path: Path,
) -> None:
    from tests.test_ingest_match_details import DetailPayloadClient, _seed_fixture

    engine = create_db_and_tables(f"sqlite:///{tmp_path / 'unknown_queue.db'}")
    session_factory = create_session_factory(engine)
    queue_path = tmp_path / "unknown_players.jsonl"
    players_reference = load_players_reference(players_reference_path)

    with session_scope(session_factory) as session:
        _seed_fixture(session)
        summary = FixtureDetailsIngestionService(
            session,
            DetailPayloadClient(repo_root / "tests/fixtures/api"),
            players_reference=players_reference,
            unknown_players_path=queue_path,
        ).ingest_fixture_details(1378969, include=["injuries"])

    assert summary.unknown_players_queued == 1
    payload = json.loads(queue_path.read_text(encoding="utf-8").splitlines()[0])
    assert payload["player_id"] == -700001
    assert payload["fixture_id"] == 1378969
    assert payload["league_id"] == 39
    assert payload["season"] == 2025
    assert "API_FOOTBALL_KEY" not in queue_path.read_text(encoding="utf-8")


def test_unknown_player_resolution_uses_players_endpoint(tmp_path: Path) -> None:
    engine = create_db_and_tables(f"sqlite:///{tmp_path / 'resolve_players.db'}")
    session_factory = create_session_factory(engine)
    queue_path = _write_unknown_queue(tmp_path)
    client = UnknownPlayerClient({PLAYERS: _players_payload()})

    with session_scope(session_factory) as session:
        _seed_resolution_context(session)
        summary = UnknownPlayerResolutionService(session, client).resolve_unknown_players(
            input_path=queue_path,
            limit=10,
            squads_fallback=False,
        )
        player = session.get(models.Player, -700001)
        squad = session.execute(select(models.PlayerSquad)).scalar_one()

    assert summary.resolved_players == 1
    assert summary.resolved_squads == 1
    assert summary.queue_pruned == 1
    assert summary.queue_remaining == 0
    assert summary.api_calls == 1
    assert player is not None
    assert player.name == "Resolved Synthetic"
    assert player.payload_json["reference_status"] == "resolved_live"
    assert squad.team_id == -40
    assert queue_path.read_text(encoding="utf-8") == ""


def test_unknown_player_resolution_squads_fallback(tmp_path: Path) -> None:
    engine = create_db_and_tables(f"sqlite:///{tmp_path / 'resolve_squad.db'}")
    session_factory = create_session_factory(engine)
    queue_path = _write_unknown_queue(tmp_path)
    client = UnknownPlayerClient(
        {PLAYERS: _empty_players_payload(), PLAYERS_SQUADS: _squad_payload()}
    )

    with session_scope(session_factory) as session:
        _seed_resolution_context(session)
        summary = UnknownPlayerResolutionService(session, client).resolve_unknown_players(
            input_path=queue_path,
            squads_fallback=True,
        )
        player = session.get(models.Player, -700001)
        squads = session.execute(select(models.PlayerSquad)).scalars().all()

    assert [call[0] for call in client.calls] == [PLAYERS, PLAYERS_SQUADS]
    assert summary.resolved_players == 1
    assert summary.resolved_squads == 1
    assert summary.still_unknown == 0
    assert summary.queue_pruned == 1
    assert summary.queue_remaining == 0
    assert player is not None
    assert player.name == "Resolved From Squad"
    assert len(squads) == 1
    assert queue_path.read_text(encoding="utf-8") == ""


def test_unknown_player_resolution_stops_on_rate_limit(tmp_path: Path) -> None:
    engine = create_db_and_tables(f"sqlite:///{tmp_path / 'resolve_rate_limit.db'}")
    session_factory = create_session_factory(engine)
    queue_path = _write_unknown_queue(tmp_path)
    client = UnknownPlayerClient({PLAYERS: _players_payload()}, rate_limit=True)

    with session_scope(session_factory) as session:
        _seed_resolution_context(session)
        summary = UnknownPlayerResolutionService(session, client).resolve_unknown_players(
            input_path=queue_path,
            squads_fallback=False,
        )

    assert summary.still_unknown == 1
    assert summary.api_calls == 1
    assert summary.queue_pruned == 0
    assert summary.queue_remaining == 1
    assert "status_code=429" in summary.errors[0]
    assert _queue_player_ids(queue_path) == [-700001]


def test_unknown_player_resolution_skips_and_prunes_already_resolved(
    tmp_path: Path,
) -> None:
    engine = create_db_and_tables(f"sqlite:///{tmp_path / 'resolve_already_done.db'}")
    session_factory = create_session_factory(engine)
    queue_path = _write_unknown_queue(tmp_path)
    client = UnknownPlayerClient({PLAYERS: _players_payload()})

    with session_scope(session_factory) as session:
        session.add(models.Team(team_id=-40, name="Synthetic Team", payload_json={}))
        session.add(
            models.Player(
                player_id=-700001,
                name="Already Resolved Synthetic",
                payload_json={"reference_status": "resolved_live"},
            )
        )
        summary = UnknownPlayerResolutionService(session, client).resolve_unknown_players(
            input_path=queue_path,
            limit=10,
            squads_fallback=False,
        )

    assert summary.queued == 1
    assert summary.already_resolved == 1
    assert summary.deduplicated == 0
    assert summary.api_calls == 0
    assert summary.queue_pruned == 1
    assert summary.queue_remaining == 0
    assert client.calls == []
    assert queue_path.read_text(encoding="utf-8") == ""


def test_unknown_player_resolution_can_keep_queue_for_dry_run(
    tmp_path: Path,
) -> None:
    engine = create_db_and_tables(f"sqlite:///{tmp_path / 'resolve_no_prune.db'}")
    session_factory = create_session_factory(engine)
    queue_path = _write_unknown_queue(tmp_path)
    client = UnknownPlayerClient({PLAYERS: _players_payload()})

    with session_scope(session_factory) as session:
        _seed_resolution_context(session)
        summary = UnknownPlayerResolutionService(session, client).resolve_unknown_players(
            input_path=queue_path,
            limit=10,
            squads_fallback=False,
            prune_resolved=False,
        )

    assert summary.resolved_players == 1
    assert summary.queue_pruned == 0
    assert summary.queue_remaining == 0
    assert _queue_player_ids(queue_path) == [-700001]


def test_cli_resolve_unknown_players_refuses_without_refresh_api(tmp_path: Path) -> None:
    result = CliRunner().invoke(
        app,
        [
            "resolve-unknown-players",
            "--input",
            str(tmp_path / "unknown_players.jsonl"),
        ],
    )

    assert result.exit_code == 2
    assert "Live ingestion is disabled" in result.stdout


def _write_unknown_queue(tmp_path: Path) -> Path:
    path = tmp_path / "unknown_players.jsonl"
    path.write_text(
        json.dumps(
            {
                "player_id": -700001,
                "name": "Synthetic Unknown",
                "team_id": -40,
                "league_id": -39,
                "season": 2025,
                "fixture_id": -100,
                "source_endpoint": "/fixtures/players",
                "first_seen_at": "2026-05-03T08:00:00+00:00",
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return path


def _queue_player_ids(path: Path) -> list[int]:
    ids: list[int] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        ids.append(int(json.loads(line)["player_id"]))
    return ids


def _seed_resolution_context(session) -> None:
    session.add(models.Team(team_id=-40, name="Synthetic Team", payload_json={}))
    session.add(
        models.Player(
            player_id=-700001,
            name="Unknown API-Football player",
            payload_json={"reference_status": "unknown_live"},
        )
    )


def _players_payload() -> JsonDict:
    return {
        "get": "players",
        "parameters": {"id": "-700001", "season": "2025"},
        "errors": [],
        "results": 1,
        "paging": {"current": 1, "total": 1},
        "response": [
            {
                "player": {
                    "id": -700001,
                    "name": "Resolved Synthetic",
                    "firstname": "Resolved",
                    "lastname": "Synthetic",
                    "age": 24,
                },
                "statistics": [
                    {
                        "team": {"id": -40, "name": "Synthetic Team"},
                        "league": {"id": -39, "season": 2025},
                        "games": {"position": "Attacker", "number": 9},
                    }
                ],
            }
        ],
    }


def _empty_players_payload() -> JsonDict:
    payload = _players_payload()
    payload["response"] = []
    payload["results"] = 0
    return payload


def _squad_payload() -> JsonDict:
    return {
        "get": "players/squads",
        "parameters": {"team": "-40"},
        "errors": [],
        "results": 1,
        "paging": {"current": 1, "total": 1},
        "response": [
            {
                "team": {"id": -40, "name": "Synthetic Team"},
                "players": [
                    {
                        "id": -700001,
                        "name": "Resolved From Squad",
                        "position": "Midfielder",
                        "number": 8,
                    }
                ],
            }
        ],
    }
