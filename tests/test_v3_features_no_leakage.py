"""Anti-leakage tests for V3 M-30 feature modules.

Each test asserts that no feature computation reads data from after prediction_time,
and that the target fixture is excluded from its own historical stats.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from football_predictor.db import models
from football_predictor.db.init_db import create_db_and_tables
from football_predictor.db.session import create_session_factory, session_scope
from football_predictor.features.draw_risk_features import build_draw_risk_features
from football_predictor.features.lineup_m30_features import build_lineup_m30_features
from football_predictor.features.no_draw_winner_features import build_no_draw_winner_features

# --------------------------------------------------------------------------- #
# Constants
# --------------------------------------------------------------------------- #

KICKOFF = datetime(2026, 5, 8, 20, 0, tzinfo=UTC)
PREDICTION_TIME = KICKOFF - timedelta(minutes=30)  # M-30: 2026-05-08 19:30 UTC
BEFORE_PREDICTION = KICKOFF - timedelta(hours=2)   # 2026-05-08 18:00 UTC — valid
AFTER_PREDICTION = KICKOFF - timedelta(minutes=10) # 2026-05-08 19:50 UTC — future at M-30

# --------------------------------------------------------------------------- #
# Shared fixtures
# --------------------------------------------------------------------------- #


def _seed_base(session) -> None:
    """Minimal seed: two teams + one target fixture + two historical fixtures."""
    session.add_all([
        models.Team(team_id=-10, name="Synthetic Home", payload_json={}),
        models.Team(team_id=-20, name="Synthetic Away", payload_json={}),
        models.Team(team_id=-30, name="Synthetic Opp", payload_json={}),
    ])
    _fixture(session, -900, KICKOFF, -10, -20, None, None, "NS")
    _fixture(session, -901, KICKOFF - timedelta(days=7), -10, -30, 2, 0)
    _fixture(session, -902, KICKOFF - timedelta(days=14), -10, -30, 1, 1)
    _fixture(session, -911, KICKOFF - timedelta(days=7), -30, -20, 0, 1)
    _fixture(session, -912, KICKOFF - timedelta(days=14), -30, -20, 2, 2)


def _fixture(
    session,
    fixture_id: int,
    date: datetime,
    home_team_id: int,
    away_team_id: int,
    home_goals: int | None,
    away_goals: int | None,
    status_short: str = "FT",
) -> None:
    session.add(
        models.Fixture(
            fixture_id=fixture_id,
            date=date,
            league_id=-100,
            season=2026,
            status_short=status_short,
            status_long="Synthetic",
            home_team_id=home_team_id,
            away_team_id=away_team_id,
            home_team=f"Team {home_team_id}",
            away_team=f"Team {away_team_id}",
            home_goals=home_goals,
            away_goals=away_goals,
            payload_json={},
        )
    )


HOME_STARTERS = [-101, -102, -103, -104, -105, -106, -107, -108, -109, -110, -111]
AWAY_STARTERS = [-201, -202, -203, -204, -205, -206, -207, -208, -209, -210, -211]
NEW_STARTERS = [-151, -152, -153, -154, -155, -156, -157, -158, -159, -160, -161]


def _lineup(
    fixture_id: int,
    team_id: int,
    formation: str,
    player_ids: list[int],
    fetched_at: datetime,
) -> models.FixtureLineup:
    return models.FixtureLineup(
        fixture_id=fixture_id,
        team_id=team_id,
        formation=formation,
        start_xi_json=[
            {"player": {"id": pid, "name": f"Player {pid}", "pos": "M", "grid": None}}
            for pid in player_ids
        ],
        substitutes_json=[],
        fetched_at=fetched_at,
        payload_json={},
    )


# --------------------------------------------------------------------------- #
# lineup_m30_features — anti-leakage tests
# --------------------------------------------------------------------------- #


def test_lineup_m30_future_lineup_not_counted(tmp_path) -> None:
    """A lineup fetched AFTER prediction_time must not raise the official flag."""
    engine = create_db_and_tables(f"sqlite:///{tmp_path / 'l1.db'}")
    factory = create_session_factory(engine)

    with session_scope(factory) as session:
        _seed_base(session)
        # Both lineups fetched AFTER prediction_time
        session.add(_lineup(-900, -10, "4-3-3", HOME_STARTERS, AFTER_PREDICTION))
        session.add(_lineup(-900, -20, "4-2-3-1", AWAY_STARTERS, AFTER_PREDICTION))

    with session_scope(factory) as session:
        result = build_lineup_m30_features(session, -900, PREDICTION_TIME)

    assert result["official_lineup_available_flag"] == 0
    assert result["official_lineup_home_available_flag"] == 0
    assert result["official_lineup_away_available_flag"] == 0


def test_lineup_m30_lineup_before_prediction_time_is_counted(tmp_path) -> None:
    """A lineup fetched BEFORE prediction_time raises the flag."""
    engine = create_db_and_tables(f"sqlite:///{tmp_path / 'l2.db'}")
    factory = create_session_factory(engine)

    with session_scope(factory) as session:
        _seed_base(session)
        session.add(_lineup(-900, -10, "4-3-3", HOME_STARTERS, BEFORE_PREDICTION))
        session.add(_lineup(-900, -20, "4-2-3-1", AWAY_STARTERS, BEFORE_PREDICTION))

    with session_scope(factory) as session:
        result = build_lineup_m30_features(session, -900, PREDICTION_TIME)

    assert result["official_lineup_available_flag"] == 1
    assert result["official_lineup_home_available_flag"] == 1
    assert result["official_lineup_away_available_flag"] == 1


def test_lineup_m30_partial_availability(tmp_path) -> None:
    """Only home lineup available → both_available is False."""
    engine = create_db_and_tables(f"sqlite:///{tmp_path / 'l3.db'}")
    factory = create_session_factory(engine)

    with session_scope(factory) as session:
        _seed_base(session)
        session.add(_lineup(-900, -10, "4-3-3", HOME_STARTERS, BEFORE_PREDICTION))
        # No lineup for away team at all

    with session_scope(factory) as session:
        result = build_lineup_m30_features(session, -900, PREDICTION_TIME)

    assert result["official_lineup_home_available_flag"] == 1
    assert result["official_lineup_away_available_flag"] == 0
    assert result["official_lineup_available_flag"] == 0


def test_lineup_m30_formation_stability_only_uses_past_fixtures(tmp_path) -> None:
    """Formation stability must only use historical fixtures with date < prediction_time."""
    engine = create_db_and_tables(f"sqlite:///{tmp_path / 'l4.db'}")
    factory = create_session_factory(engine)

    with session_scope(factory) as session:
        _seed_base(session)
        # Historical lineups (valid)
        t7 = BEFORE_PREDICTION - timedelta(days=7)
        t14 = BEFORE_PREDICTION - timedelta(days=14)
        session.add(_lineup(-901, -10, "4-3-3", HOME_STARTERS, t7))
        session.add(_lineup(-902, -10, "4-3-3", HOME_STARTERS, t14))
        # Official lineup with DIFFERENT formation (valid, before prediction_time)
        session.add(_lineup(-900, -10, "3-5-2", HOME_STARTERS, BEFORE_PREDICTION))

    with session_scope(factory) as session:
        result = build_lineup_m30_features(session, -900, PREDICTION_TIME)

    # Probable formation (from history) = 4-3-3; official = 3-5-2 → change detected
    assert result["home_team_official_formation"] == "3-5-2"
    assert result["home_team_formation_change_flag"] == 1


def test_lineup_m30_future_historical_fixture_not_used_for_stability(tmp_path) -> None:
    """Fixtures with date >= prediction_time must not contribute to formation stability."""
    engine = create_db_and_tables(f"sqlite:///{tmp_path / 'l5.db'}")
    factory = create_session_factory(engine)

    with session_scope(factory) as session:
        _seed_base(session)
        # A fixture with date AFTER prediction_time — must not be used for stability
        future_date = KICKOFF + timedelta(days=1)
        session.add(
            models.Fixture(
                fixture_id=-950,
                date=future_date,
                league_id=-100,
                season=2026,
                status_short="FT",
                status_long="Synthetic",
                home_team_id=-10,
                away_team_id=-30,
                home_team="Team -10",
                away_team="Team -30",
                home_goals=1,
                away_goals=0,
                payload_json={},
            )
        )
        # Lineup for future fixture with "5-4-1" — should be ignored
        future_t = BEFORE_PREDICTION - timedelta(days=1)
        session.add(_lineup(-950, -10, "5-4-1", HOME_STARTERS, future_t))
        # Only valid historical lineups use "4-3-3"
        hist_t = BEFORE_PREDICTION - timedelta(days=7)
        session.add(_lineup(-901, -10, "4-3-3", HOME_STARTERS, hist_t))
        session.add(_lineup(-900, -10, "4-3-3", HOME_STARTERS, BEFORE_PREDICTION))

    with session_scope(factory) as session:
        result = build_lineup_m30_features(session, -900, PREDICTION_TIME)

    # Formation from future fixture (-950) must not alter stability
    assert result["home_team_official_formation"] == "4-3-3"
    assert result["home_team_formation_change_flag"] == 0


def test_lineup_m30_target_fixture_excluded_from_historical_lineup_for_surprise(tmp_path) -> None:
    """Target fixture lineup must not be used when computing surprise score (only past fixtures)."""
    engine = create_db_and_tables(f"sqlite:///{tmp_path / 'l6.db'}")
    factory = create_session_factory(engine)

    with session_scope(factory) as session:
        _seed_base(session)
        # Historical lineups use HOME_STARTERS
        hist_t = BEFORE_PREDICTION - timedelta(days=7)
        session.add(_lineup(-901, -10, "4-3-3", HOME_STARTERS, hist_t))
        # Official lineup uses entirely new player IDs never seen in history
        session.add(_lineup(-900, -10, "4-3-3", NEW_STARTERS, BEFORE_PREDICTION))

    with session_scope(factory) as session:
        result = build_lineup_m30_features(session, -900, PREDICTION_TIME)

    # All 11 starters are new → surprise score = 1.0
    surprise = result["home_team_lineup_surprise_score"]
    assert surprise is not None
    assert surprise == pytest.approx(1.0)


# --------------------------------------------------------------------------- #
# draw_risk_features — anti-leakage tests
# --------------------------------------------------------------------------- #


def test_draw_risk_league_rate_excludes_target_fixture(tmp_path) -> None:
    """Target fixture must not contribute to its own league draw rate."""
    engine = create_db_and_tables(f"sqlite:///{tmp_path / 'dr1.db'}")
    factory = create_session_factory(engine)

    with session_scope(factory) as session:
        _seed_base(session)
        # Target fixture is -900 (not finished). Historical: -901 (no draw), -902 (draw), etc.

    with session_scope(factory) as session:
        features: dict = {"league_id": -100, "season": 2026}
        result = build_draw_risk_features(
            features,
            session=session,
            fixture_id=-900,
            prediction_time=PREDICTION_TIME,
        )

    # History: -902 and -912 are draws; -901 and -911 are not draws
    # -900 is NS (not finished) and must be excluded
    draw_rate = result["draw_risk_league_draw_rate"]
    assert draw_rate is not None
    assert 0.0 <= draw_rate <= 1.0
    # 2 draws out of 4 finished fixtures → 0.5
    assert draw_rate == pytest.approx(0.5, abs=0.01)


def test_draw_risk_league_rate_excludes_fixtures_after_prediction_time(tmp_path) -> None:
    """Fixtures played AFTER prediction_time must not appear in league draw rate."""
    engine = create_db_and_tables(f"sqlite:///{tmp_path / 'dr2.db'}")
    factory = create_session_factory(engine)

    with session_scope(factory) as session:
        _seed_base(session)
        # A fixture that 'finished' AFTER prediction_time
        _fixture(
            session,
            -960,
            KICKOFF,  # same date as target → NOT before prediction_time
            -10,
            -30,
            0,
            0,
            "FT",
        )

    with session_scope(factory) as session:
        features: dict = {}
        result = build_draw_risk_features(
            features,
            session=session,
            fixture_id=-900,
            prediction_time=PREDICTION_TIME,
        )

    draw_rate = result["draw_risk_league_draw_rate"]
    # -960 has date == KICKOFF which is NOT < PREDICTION_TIME → excluded
    # Same 4 historical fixtures → draw_rate still 0.5
    assert draw_rate == pytest.approx(0.5, abs=0.01)


def test_draw_risk_pure_features_no_session_needed(tmp_path) -> None:
    """Draw risk features that don't need DB should work without session."""
    features = {
        "home_team_global_points_per_match_last10": 1.8,
        "away_team_global_points_per_match_last10": 1.6,
        "home_team_global_pseudo_xg_for_avg_last10": 1.4,
        "away_team_global_pseudo_xg_for_avg_last10": 1.2,
        "home_team_global_clean_sheet_rate_last10": 0.3,
        "away_team_global_clean_sheet_rate_last10": 0.4,
        "home_team_global_failed_to_score_rate_last10": 0.1,
        "away_team_global_failed_to_score_rate_last10": 0.2,
        "home_team_global_draw_rate_last10": 0.25,
        "home_team_home_draw_rate_last10": 0.20,
        "away_team_away_draw_rate_last10": 0.30,
        "market_draw": 0.26,
        "odds_movement_draw": 0.01,
    }
    result = build_draw_risk_features(features)

    assert result["draw_risk_parity_score"] == pytest.approx(
        1.0 / (1.0 + abs(1.8 - 1.6)), rel=1e-3
    )
    assert result["draw_risk_xg_total_low_score"] == pytest.approx(
        1.0 / (1.0 + 1.4 + 1.2), rel=1e-3
    )
    assert result["draw_risk_league_draw_rate"] is None  # no session provided
    assert result["draw_risk_market_prob"] == pytest.approx(0.26)
    assert result["draw_risk_market_movement"] == pytest.approx(0.01)
    assert result["draw_risk_poisson_prob"] is not None
    assert 0.0 <= result["draw_risk_poisson_prob"] <= 1.0
    assert result["draw_risk_score"] is not None
    assert 0.0 <= result["draw_risk_score"] <= 1.0


def test_draw_risk_missing_features_returns_none_gracefully() -> None:
    """When upstream features are absent, draw risk returns None without crashing."""
    result = build_draw_risk_features({})

    assert result["draw_risk_parity_score"] is None
    assert result["draw_risk_xg_total_low_score"] is None
    assert result["draw_risk_xg_gap_abs"] is None
    assert result["draw_risk_defensive_solidity"] is None
    assert result["draw_risk_attacking_weakness"] is None
    assert result["draw_risk_market_prob"] is None
    assert result["draw_risk_league_draw_rate"] is None
    # Poisson and score still computed from Poisson defaults
    assert result["draw_risk_poisson_prob"] is not None


# --------------------------------------------------------------------------- #
# no_draw_winner_features — anti-leakage tests
# --------------------------------------------------------------------------- #


def test_ndw_features_pure_computation_no_db() -> None:
    """No-draw winner features are pure calculations — no session needed."""
    features = {
        "home_team_home_points_per_match_last10": 1.9,
        "away_team_away_points_per_match_last10": 1.5,
        "home_team_away_points_per_match_last10": 1.2,
        "home_team_global_pseudo_xg_for_avg_last10": 1.5,
        "away_team_global_pseudo_xg_against_avg_last10": 1.1,
        "away_team_global_pseudo_xg_for_avg_last10": 1.0,
        "home_team_global_pseudo_xg_against_avg_last10": 1.3,
        "home_team_expected_xi_total_value": 200.0,
        "away_team_expected_xi_total_value": 170.0,
        "home_team_absence_impact_score": 0.1,
        "away_team_absence_impact_score": 0.3,
        "market_home": 0.50,
        "market_draw": 0.27,
        "market_away": 0.23,
    }
    result = build_no_draw_winner_features(features)

    assert result["ndw_home_away_strength_edge"] == pytest.approx(1.9 - 1.5)
    assert result["ndw_home_advantage_edge"] == pytest.approx(1.9 - 1.2)
    assert result["ndw_xi_value_edge"] == pytest.approx(200.0 - 170.0)
    assert result["ndw_absence_impact_edge"] == pytest.approx(0.3 - 0.1)
    expected_home_nd_prob = 0.50 / (0.50 + 0.23)
    assert result["ndw_odds_home_prob"] == pytest.approx(expected_home_nd_prob, rel=1e-3)
    assert result["ndw_odds_away_prob"] == pytest.approx(1.0 - expected_home_nd_prob, rel=1e-3)
    confidence = result["ndw_market_no_draw_confidence"]
    assert confidence is not None
    assert 0.0 <= confidence <= 1.0


def test_ndw_features_missing_inputs_return_none() -> None:
    """None inputs propagate as None without raising."""
    result = build_no_draw_winner_features({})

    assert result["ndw_home_away_strength_edge"] is None
    assert result["ndw_attack_defense_edge"] is None
    assert result["ndw_home_advantage_edge"] is None
    assert result["ndw_xi_value_edge"] is None
    assert result["ndw_absence_impact_edge"] is None
    assert result["ndw_odds_home_prob"] is None
    assert result["ndw_odds_away_prob"] is None
    assert result["ndw_market_no_draw_confidence"] is None


def test_ndw_odds_no_draw_symmetry() -> None:
    """home_prob + away_prob == 1 when both are computed."""
    features = {"market_home": 0.45, "market_draw": 0.28, "market_away": 0.27}
    result = build_no_draw_winner_features(features)

    assert result["ndw_odds_home_prob"] is not None
    assert result["ndw_odds_away_prob"] is not None
    total = result["ndw_odds_home_prob"] + result["ndw_odds_away_prob"]
    assert total == pytest.approx(1.0, abs=1e-9)


# --------------------------------------------------------------------------- #
# dataset_builder.py — prediction_offset_minutes tests
# --------------------------------------------------------------------------- #


def test_dataset_builder_offset_minutes_none_uses_hours(tmp_path) -> None:
    """Default (prediction_offset_minutes=None) should use prediction_offset_hours=24."""
    from football_predictor.backtesting.dataset_builder import build_training_dataset

    engine = create_db_and_tables(f"sqlite:///{tmp_path / 'ds_hours.db'}")
    factory = create_session_factory(engine)
    kickoff = datetime(2026, 4, 1, 20, 0, tzinfo=UTC)

    with session_scope(factory) as session:
        _seed_base_for_dataset(session, kickoff)

    with session_scope(factory) as session:
        frame = build_training_dataset(
            session,
            league_ids=[-100],
            seasons=[2026],
            prediction_offset_hours=24,
            prediction_offset_minutes=None,
        )

    # Only fixture -800 is in league -100 → exactly 1 row
    assert len(frame) == 1
    expected_time = (kickoff - timedelta(hours=24)).isoformat()
    assert frame.iloc[0]["prediction_time"] == expected_time


def test_dataset_builder_offset_minutes_30_overrides_hours(tmp_path) -> None:
    """prediction_offset_minutes=30 must override prediction_offset_hours."""
    from football_predictor.backtesting.dataset_builder import build_training_dataset

    engine = create_db_and_tables(f"sqlite:///{tmp_path / 'ds_minutes.db'}")
    factory = create_session_factory(engine)
    kickoff = datetime(2026, 4, 1, 20, 0, tzinfo=UTC)

    with session_scope(factory) as session:
        _seed_base_for_dataset(session, kickoff)

    with session_scope(factory) as session:
        frame = build_training_dataset(
            session,
            league_ids=[-100],
            seasons=[2026],
            prediction_offset_hours=24,
            prediction_offset_minutes=30,
        )

    # Only fixture -800 is in league -100 → exactly 1 row
    assert len(frame) == 1
    expected_time = (kickoff - timedelta(minutes=30)).isoformat()
    assert frame.iloc[0]["prediction_time"] == expected_time


def _seed_base_for_dataset(session, kickoff: datetime) -> None:
    """Seed dataset: -800 is the ONLY fixture in league -100; historical ones are in league -99."""
    session.add_all([
        models.Team(team_id=-10, name="Synthetic Home", payload_json={}),
        models.Team(team_id=-20, name="Synthetic Away", payload_json={}),
        models.Team(team_id=-30, name="Synthetic Opp", payload_json={}),
    ])
    # Target fixture (finished, will appear in dataset)
    session.add(models.Fixture(
        fixture_id=-800,
        date=kickoff,
        league_id=-100,
        season=2026,
        status_short="FT",
        status_long="Full Time",
        home_team_id=-10,
        away_team_id=-20,
        home_team="Team -10",
        away_team="Team -20",
        home_goals=2,
        away_goals=1,
        payload_json={},
    ))
    # Historical fixtures in a different league (-99) so they don't appear in the training
    # dataset for league -100, but team_features still picks them up via team_id queries.
    for fid, date, h, a, hg, ag in [
        (-801, kickoff - timedelta(days=7), -10, -30, 1, 0),
        (-802, kickoff - timedelta(days=14), -10, -30, 0, 0),
        (-811, kickoff - timedelta(days=7), -30, -20, 1, 1),
        (-812, kickoff - timedelta(days=14), -30, -20, 2, 0),
    ]:
        session.add(models.Fixture(
            fixture_id=fid, date=date, league_id=-99, season=2026,
            status_short="FT", status_long="Full Time",
            home_team_id=h, away_team_id=a,
            home_team=f"Team {h}", away_team=f"Team {a}",
            home_goals=hg, away_goals=ag, payload_json={},
        ))
