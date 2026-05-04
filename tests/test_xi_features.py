from __future__ import annotations

from datetime import UTC, datetime

from test_player_features import PREDICTION_TIME, _seed_team_history

from football_predictor.db import models
from football_predictor.db.init_db import create_db_and_tables
from football_predictor.db.session import create_session_factory, session_scope
from football_predictor.features.xi_features import (
    build_expected_xi,
    compute_start_probability,
    infer_probable_formation,
    xi_stability_features,
)
from football_predictor.reference.loaders import load_players_reference


def test_infer_probable_formation_ignores_lineup_after_prediction_time(tmp_path) -> None:
    engine = create_db_and_tables(f"sqlite:///{tmp_path / 'formation.db'}")
    session_factory = create_session_factory(engine)

    with session_scope(session_factory) as session:
        _seed_team_history(session)
        formation = infer_probable_formation(session, -10, PREDICTION_TIME, n_matches=10)

    assert formation["formation"] == "4-3-3"
    assert formation["confidence"] == 1.0
    assert formation["formation_stability"] == 1.0


def test_compute_start_probability_is_weighted_by_recent_starts(tmp_path) -> None:
    engine = create_db_and_tables(f"sqlite:///{tmp_path / 'p_start.db'}")
    session_factory = create_session_factory(engine)

    with session_scope(session_factory) as session:
        _seed_team_history(session)
        starter = compute_start_probability(session, -101, -10, PREDICTION_TIME)
        bench = compute_start_probability(session, -114, -10, PREDICTION_TIME)

    assert starter > 0.75
    assert bench < starter


def test_build_expected_xi_returns_starters_and_bench_without_future_data(tmp_path) -> None:
    engine = create_db_and_tables(f"sqlite:///{tmp_path / 'expected_xi.db'}")
    session_factory = create_session_factory(engine)

    with session_scope(session_factory) as session:
        _seed_team_history(session)
        session.add(
            models.Injury(
                fixture_id=-1000,
                team_id=-10,
                player_id=-109,
                league_id=-100,
                season=2026,
                type="Missing Fixture",
                reason="Synthetic starter injury",
                fetched_at=datetime(2026, 5, 2, 8, tzinfo=UTC),
                payload_json={"synthetic": True},
            )
        )
        xi = build_expected_xi(session, -10, PREDICTION_TIME, fixture_id=-1000)

    expected_ids = {row["player_id"] for row in xi["expected_xi"]}
    assert len(xi["expected_xi"]) == 11
    assert xi["formation"] == "4-3-3"
    assert -109 not in expected_ids
    assert xi["bench_candidates"]
    assert all("expected_role" in row for row in xi["expected_xi"])


def test_xi_stability_features_include_pair_and_defensive_proxies(tmp_path) -> None:
    engine = create_db_and_tables(f"sqlite:///{tmp_path / 'xi_stability.db'}")
    session_factory = create_session_factory(engine)

    with session_scope(session_factory) as session:
        _seed_team_history(session)
        stability = xi_stability_features(session, -10, PREDICTION_TIME)

    assert stability["xi_stability_score"] > 0
    assert stability["avg_starts_in_last5_for_expected_xi"] > 0
    assert stability["formation_stability"] == 1.0
    assert stability["gk_stability"] > 0
    assert stability["defensive_line_stability"] > 0
    assert stability["pair_stability_score"] > 0


def test_build_expected_xi_uses_players_reference_when_lineups_are_missing(
    tmp_path,
    players_reference_sample_path,
) -> None:
    engine = create_db_and_tables(f"sqlite:///{tmp_path / 'xi_reference.db'}")
    session_factory = create_session_factory(engine)
    players_reference = load_players_reference(players_reference_sample_path)

    with session_scope(session_factory) as session:
        session.add(models.Team(team_id=77, name="Angers", payload_json={}))
        session.add(
            models.Fixture(
                fixture_id=-1000,
                date=datetime(2026, 5, 3, 19, tzinfo=UTC),
                timezone="UTC",
                round="Synthetic Round",
                league_id=61,
                season=2025,
                status="NS",
                status_short="NS",
                home_team_id=77,
                away_team_id=-20,
                home_team="Angers",
                away_team="Synthetic Away",
                payload_json={"synthetic": True},
            )
        )
        xi = build_expected_xi(
            session,
            77,
            PREDICTION_TIME,
            fixture_id=-1000,
            players_reference=players_reference,
        )

    assert {455243, 191289} <= {row["player_id"] for row in xi["expected_xi"]}
    assert xi["data_quality"]["reference_fallback_used"] is True
    assert "expected_xi_incomplete" in xi["data_quality"]["warnings"]
