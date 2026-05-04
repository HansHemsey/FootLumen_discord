from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from datetime import date as date_type
from pathlib import Path
from typing import Any

from sqlalchemy import func, select
from typer.testing import CliRunner

from football_predictor.api.api_football_client import ApiFootballPayload
from football_predictor.api.endpoints import (
    FIXTURES_EVENTS,
    FIXTURES_LINEUPS,
    FIXTURES_PLAYERS,
    FIXTURES_STATISTICS,
    INJURIES,
    PREDICTIONS,
)
from football_predictor.api.exceptions import ApiFootballRateLimitError
from football_predictor.cli import app
from football_predictor.db import models
from football_predictor.db.init_db import create_db_and_tables
from football_predictor.db.session import create_session_factory, session_scope
from football_predictor.ingestion.ingest_match_details import FixtureDetailsIngestionService
from football_predictor.ingestion.parsers import (
    parse_api_prediction_row,
    parse_fixture_event_rows,
    parse_fixture_lineup_rows,
    parse_fixture_player_stats_rows,
    parse_fixture_statistics_rows,
    parse_injury_rows,
)
from football_predictor.reference.loaders import (
    load_api_football_reference,
    load_players_reference,
)

JsonDict = dict[str, Any]


@dataclass
class DetailPayloadClient:
    fixture_dir: Path
    status_overrides: dict[tuple[str, int], int] = field(default_factory=dict)
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
        fixture_id = int(safe_params["fixture"])
        self.calls.append((endpoint, safe_params))
        status_code = self.status_overrides.get((endpoint, fixture_id), 200)
        payload = (
            _empty_payload(endpoint, safe_params)
            if status_code == 204
            else _read_json(self.fixture_dir / _filename_for_endpoint(endpoint))
        )
        return ApiFootballPayload(
            endpoint=endpoint,
            params=safe_params,
            payload=payload,
            fetched_at=datetime(2026, 5, 2, 12, tzinfo=UTC).isoformat(),
            status_code=status_code,
        )


@dataclass
class RateLimitDetailPayloadClient:
    fixture_dir: Path
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
        raise ApiFootballRateLimitError(
            f"Rate limit endpoint={endpoint} status_code=429 params={safe_params}"
        )


def test_detail_parsers_handle_match_payloads(repo_root) -> None:
    fetched_at = datetime(2026, 5, 2, 12, tzinfo=UTC)

    statistics = parse_fixture_statistics_rows(
        _read_json(repo_root / "tests/fixtures/api/fixture_statistics.json"),
        fixture_id=1378969,
        fetched_at=fetched_at,
    )
    events = parse_fixture_event_rows(
        _read_json(repo_root / "tests/fixtures/api/fixture_events.json"),
        fixture_id=1378969,
        fetched_at=fetched_at,
    )
    lineups = parse_fixture_lineup_rows(
        _read_json(repo_root / "tests/fixtures/api/fixture_lineups.json"),
        fixture_id=1378969,
        fetched_at=fetched_at,
    )
    player_stats = parse_fixture_player_stats_rows(
        _read_json(repo_root / "tests/fixtures/api/fixture_players.json"),
        fixture_id=1378969,
        fetched_at=fetched_at,
    )
    injuries = parse_injury_rows(
        _read_json(repo_root / "tests/fixtures/api/injuries.json"),
        fixture_id=1378969,
        fetched_at=fetched_at,
    )
    prediction = parse_api_prediction_row(
        _read_json(repo_root / "tests/fixtures/api/predictions.json"),
        fixture_id=1378969,
        fetched_at=fetched_at,
    )

    assert len(statistics) == 2
    assert statistics[0]["team_id"] == 40
    assert len(events) == 2
    assert events[0]["player_id"] == 2864
    assert events[0]["assist_player_id"] == 30410
    assert len(lineups) == 2
    assert lineups[0]["formation"] == "4-2-3-1"
    assert len(player_stats) == 2
    assert player_stats[0]["rating"] == 8.1
    assert len(injuries) == 2
    assert injuries[0]["player_id"] == 792
    assert prediction is not None
    assert prediction["winner_team_id"] == 40
    assert prediction["percent_home"] == 45.0


def test_fixture_details_ingestion_snapshots_and_upserts_are_idempotent(
    tmp_path,
    repo_root,
    reference_path,
    players_reference_path,
) -> None:
    engine = create_db_and_tables(f"sqlite:///{tmp_path / 'details.db'}")
    session_factory = create_session_factory(engine)
    client = DetailPayloadClient(repo_root / "tests/fixtures/api")
    reference = load_api_football_reference(reference_path)
    players_reference = load_players_reference(players_reference_path)
    reference.validate_fixture_reference(1378969)
    players_reference.find_player_by_id(2864)

    with session_scope(session_factory) as session:
        _seed_fixture(session)
        service = FixtureDetailsIngestionService(
            session,
            client,
            reference=reference,
            players_reference=players_reference,
        )
        first = service.ingest_fixture_details(1378969)
        second = service.ingest_fixture_details(1378969)

        assert first.statistics == 2
        assert first.events == 2
        assert first.lineups == 2
        assert first.player_stats == 2
        assert first.injuries == 2
        assert first.predictions == 1
        assert second.statistics == 2
        assert session.scalar(select(func.count()).select_from(models.RawApiSnapshot)) == 12
        assert session.scalar(select(func.count()).select_from(models.FixtureStatistics)) == 2
        assert session.scalar(select(func.count()).select_from(models.FixtureEvent)) == 2
        assert session.scalar(select(func.count()).select_from(models.FixtureLineup)) == 2
        assert session.scalar(select(func.count()).select_from(models.FixturePlayerStats)) == 2
        assert session.scalar(select(func.count()).select_from(models.Injury)) == 2
        assert session.scalar(select(func.count()).select_from(models.ApiPredictionSnapshot)) == 1
        assert session.scalar(select(func.count()).select_from(models.Player)) == 4

        known_player = session.get(models.Player, 2864)
        synthetic_player = session.get(models.Player, -700001)

    assert known_player is not None
    assert known_player.payload_json["reference_status"] == "known_reference"
    assert synthetic_player is not None
    assert synthetic_player.payload_json["reference_status"] == "unknown_live"


def test_individual_fixture_detail_methods(tmp_path, repo_root, players_reference_path) -> None:
    engine = create_db_and_tables(f"sqlite:///{tmp_path / 'details_individual.db'}")
    session_factory = create_session_factory(engine)
    client = DetailPayloadClient(repo_root / "tests/fixtures/api")
    players_reference = load_players_reference(players_reference_path)

    with session_scope(session_factory) as session:
        _seed_fixture(session)
        service = FixtureDetailsIngestionService(
            session,
            client,
            players_reference=players_reference,
        )
        statistics = service.ingest_fixture_statistics(1378969)
        events = service.ingest_fixture_events(1378969)
        lineups = service.ingest_fixture_lineups(1378969)
        players = service.ingest_fixture_players(1378969)
        injuries = service.ingest_injuries_for_fixture(1378969)
        prediction = service.ingest_api_prediction(1378969)

        assert statistics.statistics == 2
        assert events.events == 2
        assert lineups.lineups == 2
        assert players.player_stats == 2
        assert injuries.injuries == 2
        assert prediction.predictions == 1
        assert session.scalar(select(func.count()).select_from(models.RawApiSnapshot)) == 6
        assert session.scalar(select(func.count()).select_from(models.FixtureStatistics)) == 2
        assert session.scalar(select(func.count()).select_from(models.FixtureEvent)) == 2
        assert session.scalar(select(func.count()).select_from(models.FixtureLineup)) == 2
        assert session.scalar(select(func.count()).select_from(models.FixturePlayerStats)) == 2
        assert session.scalar(select(func.count()).select_from(models.Injury)) == 2
        assert session.scalar(select(func.count()).select_from(models.ApiPredictionSnapshot)) == 1


def test_fixture_details_ingestion_handles_204_no_content(
    tmp_path,
    repo_root,
) -> None:
    engine = create_db_and_tables(f"sqlite:///{tmp_path / 'details_204.db'}")
    session_factory = create_session_factory(engine)
    client = DetailPayloadClient(
        repo_root / "tests/fixtures/api",
        status_overrides={(FIXTURES_LINEUPS, 1378969): 204},
    )

    with session_scope(session_factory) as session:
        _seed_fixture(session)
        summary = FixtureDetailsIngestionService(session, client).ingest_fixture_details(
            1378969,
            include=["lineups"],
        )
        assert summary.no_content == 1
        assert summary.lineups == 0
        assert session.scalar(select(func.count()).select_from(models.RawApiSnapshot)) == 1
        assert session.scalar(select(func.count()).select_from(models.FixtureLineup)) == 0


def test_fixture_details_batch_continues_after_missing_fixture(
    tmp_path,
    repo_root,
) -> None:
    engine = create_db_and_tables(f"sqlite:///{tmp_path / 'details_batch.db'}")
    session_factory = create_session_factory(engine)
    client = DetailPayloadClient(repo_root / "tests/fixtures/api")

    with session_scope(session_factory) as session:
        _seed_fixture(session)
        summary = FixtureDetailsIngestionService(session, client).ingest_fixture_details_batch(
            [1378969, 1378970],
            include=["predictions"],
            continue_on_error=True,
        )

        assert summary.predictions == 1
        assert summary.skipped == 1
        assert "fixture_id=1378970" in summary.errors[0]


def test_fixture_details_batch_stops_after_rate_limit(tmp_path, repo_root) -> None:
    engine = create_db_and_tables(f"sqlite:///{tmp_path / 'details_rate_limit.db'}")
    session_factory = create_session_factory(engine)
    client = RateLimitDetailPayloadClient(repo_root / "tests/fixtures/api")

    with session_scope(session_factory) as session:
        _seed_fixture(session)
        _seed_extra_fixture(session, fixture_id=1378970)
        summary = FixtureDetailsIngestionService(session, client).ingest_fixture_details_batch(
            [1378969, 1378970],
            include=["statistics"],
            continue_on_error=True,
            stop_on_rate_limit=True,
        )

        assert summary.skipped == 1
        assert "status_code=429" in summary.errors[0]
        assert client.calls == [(FIXTURES_STATISTICS, {"fixture": 1378969})]


def test_fixture_details_filter_batch_reads_stored_fixtures(
    tmp_path,
    repo_root,
) -> None:
    engine = create_db_and_tables(f"sqlite:///{tmp_path / 'details_filter.db'}")
    session_factory = create_session_factory(engine)
    client = DetailPayloadClient(repo_root / "tests/fixtures/api")

    with session_scope(session_factory) as session:
        _seed_fixture(session)
        service = FixtureDetailsIngestionService(session, client)
        fixture_ids = service.fixture_ids_for_filters(league_id=39, season=2025, status="FT")
        summary = service.ingest_fixture_details_for_filters(
            league_id=39,
            season=2025,
            status="FT",
            include=["predictions"],
        )

        assert fixture_ids == [1378969]
        assert summary.predictions == 1


def test_fixture_details_filter_batch_supports_date_range_and_statuses(
    tmp_path,
    repo_root,
) -> None:
    engine = create_db_and_tables(f"sqlite:///{tmp_path / 'details_range_filter.db'}")
    session_factory = create_session_factory(engine)
    client = DetailPayloadClient(repo_root / "tests/fixtures/api")

    with session_scope(session_factory) as session:
        _seed_fixture(session)
        _seed_extra_fixture(
            session,
            fixture_id=1378970,
            fixture_date=datetime(2025, 8, 16, 19, tzinfo=UTC),
            status_short="AET",
        )
        _seed_extra_fixture(
            session,
            fixture_id=1378971,
            fixture_date=datetime(2025, 8, 17, 19, tzinfo=UTC),
            status_short="PEN",
        )
        _seed_extra_fixture(
            session,
            fixture_id=1378972,
            fixture_date=datetime(2025, 8, 18, 19, tzinfo=UTC),
            status_short="NS",
        )
        service = FixtureDetailsIngestionService(session, client)

        fixture_ids = service.fixture_ids_for_filters(
            league_id=39,
            season=2025,
            date_from=date_type(2025, 8, 15),
            date_to=date_type(2025, 8, 17),
            statuses=["FT AET", "PEN"],
            limit=10,
        )

    assert fixture_ids == [1378969, 1378970, 1378971]


def test_cli_fixture_details_refuses_without_refresh_api() -> None:
    runner = CliRunner()

    result = runner.invoke(app, ["ingest-fixture-details", "--fixture", "1378969"])

    assert result.exit_code == 2
    assert "Live ingestion is disabled" in result.stdout


def test_cli_fixture_details_batch_refuses_without_refresh_api() -> None:
    runner = CliRunner()

    result = runner.invoke(
        app,
        ["ingest-fixture-details", "--league", "39", "--season", "2025", "--status", "FT"],
    )

    assert result.exit_code == 2
    assert "Live ingestion is disabled" in result.stdout


def _seed_fixture(session) -> None:
    session.add_all(
        [
            models.Team(team_id=40, name="Liverpool", country="England", payload_json={}),
            models.Team(team_id=35, name="Bournemouth", country="England", payload_json={}),
            models.Fixture(
                fixture_id=1378969,
                date=datetime(2025, 8, 15, 19, tzinfo=UTC),
                timezone="UTC",
                round="Regular Season - 1",
                league_id=39,
                season=2025,
                status="FT",
                status_long="Match Finished",
                status_short="FT",
                elapsed=90,
                home_team_id=40,
                away_team_id=35,
                home_team="Liverpool",
                away_team="Bournemouth",
                home_goals=4,
                away_goals=2,
                payload_json={"ingestion_source": "test"},
            ),
        ]
    )


def _seed_extra_fixture(
    session,
    *,
    fixture_id: int,
    fixture_date: datetime | None = None,
    status_short: str = "FT",
) -> None:
    session.add(
        models.Fixture(
            fixture_id=fixture_id,
            date=fixture_date or datetime(2025, 8, 16, 19, tzinfo=UTC),
            timezone="UTC",
            round="Regular Season - 1",
            league_id=39,
            season=2025,
            status=status_short,
            status_long="Match Finished",
            status_short=status_short,
            elapsed=90,
            home_team_id=40,
            away_team_id=35,
            home_team="Liverpool",
            away_team="Bournemouth",
            home_goals=1,
            away_goals=0,
            payload_json={"ingestion_source": "test"},
        )
    )


def _filename_for_endpoint(endpoint: str) -> str:
    return {
        FIXTURES_STATISTICS: "fixture_statistics.json",
        FIXTURES_EVENTS: "fixture_events.json",
        FIXTURES_LINEUPS: "fixture_lineups.json",
        FIXTURES_PLAYERS: "fixture_players.json",
        INJURIES: "injuries.json",
        PREDICTIONS: "predictions.json",
    }[endpoint]


def _empty_payload(endpoint: str, params: JsonDict) -> JsonDict:
    return {
        "get": endpoint.removeprefix("/"),
        "parameters": params,
        "errors": [],
        "results": 0,
        "paging": {"current": 1, "total": 1},
        "response": [],
    }


def _read_json(path: Path) -> JsonDict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload
