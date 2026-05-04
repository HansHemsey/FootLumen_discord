from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
from sqlalchemy import func, select
from typer.testing import CliRunner

from football_predictor.api.api_football_client import ApiFootballPayload
from football_predictor.api.endpoints import ODDS
from football_predictor.cli import app
from football_predictor.config.settings import get_settings
from football_predictor.db import models
from football_predictor.db.init_db import create_db_and_tables
from football_predictor.db.session import create_session_factory, session_scope
from football_predictor.features.odds_features import (
    market_probabilities_for_fixture,
    resolve_1x2_bet_id,
)
from football_predictor.ingestion.ingest_odds import OddsIngestionService
from football_predictor.ingestion.parsers import parse_odds_snapshot_rows
from football_predictor.reference.loaders import load_api_football_reference

JsonDict = dict[str, Any]


@dataclass
class OddsPayloadClient:
    fixture_dir: Path
    fetched_at: datetime = datetime(2026, 5, 2, 10, tzinfo=UTC)
    incomplete: bool = False
    calls: list[tuple[str, dict[str, Any]]] = field(default_factory=list)

    def __enter__(self) -> OddsPayloadClient:
        return self

    def __exit__(self, *_exc: object) -> None:
        return None

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
        return ApiFootballPayload(
            endpoint=endpoint,
            params=safe_params,
            payload=self._payload_for(safe_params),
            fetched_at=self.fetched_at.isoformat(),
            status_code=200,
        )

    def _payload_for(self, params: dict[str, Any]) -> JsonDict:
        if self.incomplete:
            return _read_json(self.fixture_dir / "odds_incomplete.json")
        page = int(params.get("page", 1))
        filename = "odds_fixture_page_1.json" if page == 1 else "odds_fixture_page_2.json"
        return _read_json(self.fixture_dir / filename)


def test_resolve_match_winner_bet_from_reference(reference_path) -> None:
    reference = load_api_football_reference(reference_path)

    bet_id = resolve_1x2_bet_id(reference, configured_bet_name="Match Winner")

    assert bet_id == reference.find_bet_by_name("Match Winner").bet_id


def test_parse_odds_snapshot_rows_supports_home_draw_away_and_1x2_labels(
    repo_root,
) -> None:
    fetched_at = datetime(2026, 5, 2, 10, tzinfo=UTC)

    page_1_rows = parse_odds_snapshot_rows(
        _read_json(repo_root / "tests/fixtures/api/odds_fixture_page_1.json"),
        target_bet_id=1,
        fetched_at=fetched_at,
    )
    page_2_rows = parse_odds_snapshot_rows(
        _read_json(repo_root / "tests/fixtures/api/odds_fixture_page_2.json"),
        target_bet_id=1,
        fetched_at=fetched_at,
    )
    incomplete_rows = parse_odds_snapshot_rows(
        _read_json(repo_root / "tests/fixtures/api/odds_incomplete.json"),
        target_bet_id=1,
        fetched_at=fetched_at,
    )
    team_name_rows = parse_odds_snapshot_rows(
        _read_json(repo_root / "tests/fixtures/api/odds_fixture.json"),
        target_bet_id=1,
        fetched_at=fetched_at,
    )

    assert page_1_rows[0]["bookmaker_id"] == 8
    assert page_1_rows[0]["odd_home"] == 1.8
    assert page_1_rows[0]["odd_draw"] == 3.8
    assert page_1_rows[0]["odd_away"] == 4.5
    assert page_2_rows[0]["bookmaker_id"] == 4
    assert page_2_rows[0]["odd_draw"] == 3.7
    assert len(page_2_rows) == 2
    assert team_name_rows[0]["odd_home"] == 1.8
    assert team_name_rows[0]["odd_away"] == 4.5
    assert incomplete_rows == []


def test_odds_ingestion_paginates_snapshots_and_is_idempotent(
    tmp_path,
    repo_root,
    reference_path,
) -> None:
    engine = create_db_and_tables(f"sqlite:///{tmp_path / 'odds.db'}")
    session_factory = create_session_factory(engine)
    reference = load_api_football_reference(reference_path)
    client = OddsPayloadClient(repo_root / "tests/fixtures/api")

    with session_scope(session_factory) as session:
        _seed_fixture(session)
        service = OddsIngestionService(session, client, reference=reference)
        first = service.ingest_odds_for_fixture(1378969)
        second = service.ingest_odds_for_fixture(1378969)

        assert first.odds == 3
        assert second.odds == 3
        assert session.scalar(select(func.count()).select_from(models.RawApiSnapshot)) == 4
        assert session.scalar(select(func.count()).select_from(models.OddsSnapshot)) == 3
        assert session.get(models.Bookmaker, 8) is not None
        assert session.get(models.Bookmaker, -800001) is not None
        assert session.scalar(select(func.count()).select_from(models.Bet)) == 1

    assert client.calls[0] == (ODDS, {"fixture": 1378969, "bet": 1, "page": 1})
    assert client.calls[1] == (ODDS, {"fixture": 1378969, "bet": 1, "page": 2})


def test_odds_ingestion_supports_date_and_league_modes(
    tmp_path,
    repo_root,
    reference_path,
) -> None:
    engine = create_db_and_tables(f"sqlite:///{tmp_path / 'odds_modes.db'}")
    session_factory = create_session_factory(engine)
    reference = load_api_football_reference(reference_path)
    client = OddsPayloadClient(repo_root / "tests/fixtures/api")

    with session_scope(session_factory) as session:
        _seed_fixture(session)
        service = OddsIngestionService(session, client, reference=reference)
        by_date = service.ingest_odds_by_date(
            datetime(2026, 5, 2, tzinfo=UTC).date(),
            league_id=39,
            season=2025,
        )
        by_league = service.ingest_odds_by_league_season(39, 2025, bookmaker=8, bet=1)

        assert by_date.odds == 3
        assert by_league.odds == 3

    assert client.calls[0][1] == {
        "date": "2026-05-02",
        "league": 39,
        "season": 2025,
        "bet": 1,
        "page": 1,
    }
    assert client.calls[-2][1] == {
        "league": 39,
        "season": 2025,
        "bookmaker": 8,
        "bet": 1,
        "page": 1,
    }


def test_market_probabilities_are_point_in_time_and_include_movement(tmp_path) -> None:
    engine = create_db_and_tables(f"sqlite:///{tmp_path / 'market.db'}")
    session_factory = create_session_factory(engine)

    with session_scope(session_factory) as session:
        _seed_fixture(session)
        session.add_all(
            [
                _odds_snapshot(8, datetime(2026, 5, 2, 9, tzinfo=UTC), 1.90, 3.90, 4.70),
                _odds_snapshot(8, datetime(2026, 5, 2, 10, tzinfo=UTC), 1.80, 3.80, 4.50),
                _odds_snapshot(4, datetime(2026, 5, 2, 10, tzinfo=UTC), 1.85, 3.70, 4.40),
                _odds_snapshot(8, datetime(2026, 5, 2, 13, tzinfo=UTC), 1.60, 4.00, 5.20),
            ]
        )
        market = market_probabilities_for_fixture(
            session,
            fixture_id=1378969,
            prediction_time=datetime(2026, 5, 2, 11, tzinfo=UTC),
            bet_id=1,
        )

    assert market is not None
    assert market.bookmaker_count == 2
    assert market.fetched_at == datetime(2026, 5, 2, 10, tzinfo=UTC)
    assert market.probabilities.p_home > market.probabilities.p_away
    assert market.movement.bookmaker_count == 1
    assert market.movement.odd_home_delta == pytest.approx(-0.10)


def test_cli_ingest_odds_refuses_without_refresh_api() -> None:
    runner = CliRunner()

    result = runner.invoke(app, ["ingest-odds", "--fixture", "1378969"])

    assert result.exit_code == 2
    assert "Live ingestion is disabled" in result.stdout


def test_cli_ingest_odds_fixture_with_mock_client(tmp_path, repo_root) -> None:
    get_settings.cache_clear()
    database_url = f"sqlite:///{tmp_path / 'cli_odds.db'}"
    engine = create_db_and_tables(database_url)
    session_factory = create_session_factory(engine)
    with session_scope(session_factory) as session:
        _seed_fixture(session)

    client = OddsPayloadClient(repo_root / "tests/fixtures/api")
    runner = CliRunner()
    with patch("football_predictor.cli._api_client_from_settings", return_value=client):
        result = runner.invoke(
            app,
            ["ingest-odds", "--fixture", "1378969", "--refresh-api", "--dry-run"],
            env={"DATABASE_URL": database_url, "API_FOOTBALL_KEY": "synthetic-cli-key"},
        )

    assert result.exit_code == 0
    assert "'odds': 3" in result.stdout
    get_settings.cache_clear()


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


def _odds_snapshot(
    bookmaker_id: int,
    fetched_at: datetime,
    odd_home: float,
    odd_draw: float,
    odd_away: float,
) -> models.OddsSnapshot:
    return models.OddsSnapshot(
        fixture_id=1378969,
        league_id=39,
        season=2025,
        bookmaker_id=bookmaker_id,
        bookmaker_name=f"Bookmaker {bookmaker_id}",
        bet_id=1,
        bet_name="Match Winner",
        fetched_at=fetched_at,
        is_live=False,
        odd_home=odd_home,
        odd_draw=odd_draw,
        odd_away=odd_away,
        values_json=[],
        odds_json={},
        payload_json={},
    )


def _read_json(path: Path) -> JsonDict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload
