from __future__ import annotations

from datetime import UTC, datetime

import pytest
from typer.testing import CliRunner

from football_predictor.cli import app
from football_predictor.config.settings import get_settings
from football_predictor.db import models
from football_predictor.db.init_db import create_db_and_tables
from football_predictor.db.session import create_session_factory, session_scope
from football_predictor.features.odds_features import (
    compute_market_consensus,
    compute_odds_movement,
    decimal_odds_to_implied_probabilities,
    extract_1x2_values,
)


def test_decimal_odds_to_implied_probabilities_removes_margin() -> None:
    implied = decimal_odds_to_implied_probabilities(1.80, 3.80, 4.50)

    assert implied.probabilities.p_home > implied.probabilities.p_draw
    assert implied.probabilities.p_draw > implied.probabilities.p_away
    assert (
        implied.probabilities.p_home
        + implied.probabilities.p_draw
        + implied.probabilities.p_away
    ) == pytest.approx(1.0)
    assert implied.overround == pytest.approx((1 / 1.80) + (1 / 3.80) + (1 / 4.50) - 1)


def test_extract_1x2_values_supports_standard_numeric_and_team_labels() -> None:
    standard = extract_1x2_values(
        [
            {"value": "home", "odd": "1.80"},
            {"value": "DRAW", "odd": "3.80"},
            {"value": "Away", "odd": "4.50"},
        ]
    )
    numeric = extract_1x2_values(
        [
            {"value": "1", "odd": "1.82"},
            {"value": "X", "odd": "3.70"},
            {"value": "2", "odd": "4.40"},
        ]
    )
    team_names = extract_1x2_values(
        [
            {"value": "Liverpool", "odd": "1.80"},
            {"value": "Draw", "odd": "3.80"},
            {"value": "Bournemouth", "odd": "4.50"},
        ],
        home_team_name="Liverpool",
        away_team_name="Bournemouth",
    )

    assert standard is not None
    assert standard.odd_home == 1.80
    assert numeric is not None
    assert numeric.odd_draw == 3.70
    assert team_names is not None
    assert team_names.odd_away == 4.50
    assert extract_1x2_values([{"value": "Home", "odd": "1.80"}]) is None


def test_compute_market_consensus_uses_latest_snapshots_before_as_of_time(tmp_path) -> None:
    engine = create_db_and_tables(f"sqlite:///{tmp_path / 'consensus.db'}")
    session_factory = create_session_factory(engine)

    with session_scope(session_factory) as session:
        _seed_fixture(session)
        session.add_all(
            [
                _odds_snapshot(8, datetime(2026, 5, 2, 9, tzinfo=UTC), 1.90, 3.90, 4.70),
                _odds_snapshot(4, datetime(2026, 5, 2, 9, tzinfo=UTC), 1.92, 3.85, 4.60),
                _odds_snapshot(8, datetime(2026, 5, 2, 10, tzinfo=UTC), 1.80, 3.80, 4.50),
                _odds_snapshot(4, datetime(2026, 5, 2, 10, tzinfo=UTC), 1.85, 3.70, 4.40),
                _odds_snapshot(8, datetime(2026, 5, 2, 13, tzinfo=UTC), 1.60, 4.00, 5.20),
            ]
        )

        consensus = compute_market_consensus(
            session,
            1378969,
            as_of_time=datetime(2026, 5, 2, 11, tzinfo=UTC),
            bet_id=1,
        )

    assert consensus is not None
    assert consensus.bookmaker_count == 2
    assert consensus.fetched_at == datetime(2026, 5, 2, 10, tzinfo=UTC)
    assert consensus.p_market_home > consensus.p_market_away
    assert consensus.market_confidence > 0
    assert consensus.market_dispersion >= 0


def test_compute_odds_movement_excludes_future_snapshots(tmp_path) -> None:
    engine = create_db_and_tables(f"sqlite:///{tmp_path / 'movement.db'}")
    session_factory = create_session_factory(engine)

    with session_scope(session_factory) as session:
        _seed_fixture(session)
        session.add_all(
            [
                _odds_snapshot(8, datetime(2026, 5, 2, 9, tzinfo=UTC), 1.90, 3.90, 4.70),
                _odds_snapshot(4, datetime(2026, 5, 2, 9, tzinfo=UTC), 1.92, 3.85, 4.60),
                _odds_snapshot(8, datetime(2026, 5, 2, 10, tzinfo=UTC), 1.80, 3.80, 4.50),
                _odds_snapshot(4, datetime(2026, 5, 2, 10, tzinfo=UTC), 1.85, 3.70, 4.40),
                _odds_snapshot(8, datetime(2026, 5, 2, 13, tzinfo=UTC), 1.60, 4.00, 5.20),
            ]
        )

        movement = compute_odds_movement(
            session,
            1378969,
            datetime(2026, 5, 2, 11, tzinfo=UTC),
            bet_id=1,
        )

    assert movement.bookmaker_count == 2
    assert movement.first_fetched_at == datetime(2026, 5, 2, 9, tzinfo=UTC)
    assert movement.latest_fetched_at == datetime(2026, 5, 2, 10, tzinfo=UTC)
    assert movement.delta_home == pytest.approx(((1.80 + 1.85) / 2) - ((1.90 + 1.92) / 2))
    assert movement.delta_draw == pytest.approx(((3.80 + 3.70) / 2) - ((3.90 + 3.85) / 2))
    assert movement.delta_away == pytest.approx(((4.50 + 4.40) / 2) - ((4.70 + 4.60) / 2))


def test_cli_odds_features_reads_local_snapshots(tmp_path) -> None:
    get_settings.cache_clear()
    database_url = f"sqlite:///{tmp_path / 'cli_features.db'}"
    engine = create_db_and_tables(database_url)
    session_factory = create_session_factory(engine)
    with session_scope(session_factory) as session:
        _seed_fixture(session)
        session.add_all(
            [
                _odds_snapshot(8, datetime(2026, 5, 2, 9, tzinfo=UTC), 1.90, 3.90, 4.70),
                _odds_snapshot(8, datetime(2026, 5, 2, 10, tzinfo=UTC), 1.80, 3.80, 4.50),
            ]
        )

    result = CliRunner().invoke(
        app,
        [
            "odds-features",
            "--fixture",
            "1378969",
            "--as-of",
            "2026-05-02T11:00:00+00:00",
        ],
        env={"DATABASE_URL": database_url},
    )

    assert result.exit_code == 0
    assert "p_market_home" in result.stdout
    assert "delta_home" in result.stdout
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
