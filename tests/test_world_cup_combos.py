from __future__ import annotations

from collections import Counter
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

from sqlalchemy import inspect

from football_predictor.db import models as db_models
from football_predictor.db.session import (
    create_db_engine,
    create_session_factory,
    init_db,
    session_scope,
)
from football_predictor.world_cup_combos.config import (
    WorldCupComboConfig,
    load_world_cup_combo_config,
)
from football_predictor.world_cup_combos.enums import (
    ComboMarketScope,
    ComboMarketType,
    ComboTicketStatus,
)
from football_predictor.world_cup_combos.models import (
    ComboLegCandidate,
    ComboLegSelectionResult,
    ComboTicketCandidate,
    ComboTicketSnapshot,
)
from football_predictor.world_cup_combos.persistence import (
    ensure_combo_tables,
    persist_combo_ticket_candidate,
    persist_combo_ticket_snapshot,
)
from football_predictor.world_cup_combos.worldcup_combo_leg_selector import (
    WorldCupComboLegSelector,
)
from football_predictor.world_cup_combos.worldcup_combo_sessions import (
    WorldCupComboSessionService,
)


def test_worldcup_combo_config_defaults_disabled() -> None:
    config = WorldCupComboConfig()

    assert config.enabled is False
    assert config.competition_key == "fifa_world_cup_2026"
    assert config.league_id == 1
    assert config.season == 2026
    assert config.max_public_legs == 2
    assert config.max_staff_legs == 3
    assert config.lock_buffer_minutes == 20
    assert config.staff_only_shadow_mode is True


def test_worldcup_combo_config_loads_yaml(tmp_path: Path) -> None:
    path = tmp_path / "worldcup_combos.yaml"
    path.write_text(
        """
enabled: true
competition_key: fifa_world_cup_2026
league_id: 1
season: 2026
timezone_display: Europe/Paris
max_public_legs: 2
max_staff_legs: 3
lock_buffer_minutes: 20
max_session_span_hours_public: 4
min_leg_ev: 0.03
min_leg_edge: 0.03
min_leg_data_quality: 65
min_leg_confidence: 55
min_combined_ev_adjusted: 0.03
min_combined_confidence_public: 68
max_post_lock_risk_public: 30
require_positive_ev_each_leg: true
forbid_same_group_md3_multiple_legs: true
allow_public_matchday3: false
allow_public_knockout: false
staff_only_shadow_mode: true
""",
        encoding="utf-8",
    )

    config = load_world_cup_combo_config(path)

    assert config.enabled is True
    assert config.min_leg_ev == 0.03
    assert config.allow_public_matchday3 is False


def test_worldcup_combo_leg_candidate_serializes_warning_snapshot() -> None:
    leg = _leg_candidate()

    payload = leg.to_json_dict()

    assert payload["fixture_id"] == -101
    assert payload["market_type"] == "HOME"
    assert payload["market_scope"] == "NINETY_MIN"
    assert payload["warnings"] == ["synthetic-warning"]
    assert payload["kickoff_at_utc"].startswith("2026-06-11T18:00:00")


def test_worldcup_combo_ticket_candidate_serializes_nested_legs() -> None:
    leg = _leg_candidate()
    ticket = _ticket_candidate(legs=(leg,))

    payload = ticket.to_json_dict()

    assert payload["competition_key"] == "fifa_world_cup_2026"
    assert payload["publication_decision"] == "DRAFT"
    assert payload["legs"][0]["selection"] == "Synthetic Home"
    assert payload["warnings"] == ["ticket-warning"]


def test_worldcup_combo_tables_are_created_idempotently(tmp_path: Path) -> None:
    engine = create_db_engine(f"sqlite:///{tmp_path / 'combos.db'}")

    ensure_combo_tables(engine)
    ensure_combo_tables(engine)

    tables = set(inspect(engine).get_table_names())
    assert {"combo_tickets", "combo_ticket_legs", "combo_ticket_snapshots"}.issubset(tables)


def test_worldcup_combo_persistence_stores_ticket_legs_and_snapshot(tmp_path: Path) -> None:
    engine = create_db_engine(f"sqlite:///{tmp_path / 'combos.db'}")
    ensure_combo_tables(engine)
    session_factory = create_session_factory(engine)
    ticket = _ticket_candidate(legs=(_leg_candidate(),))

    with session_scope(session_factory) as session:
        record = persist_combo_ticket_candidate(
            session,
            ticket,
            model_versions_json={"worldcup_1x2": "synthetic"},
        )
        snapshot = ComboTicketSnapshot(
            ticket_key=ticket.ticket_key,
            status=ComboTicketStatus.DRAFT,
            candidate=ticket,
            captured_at=datetime(2026, 6, 11, 17, 35, tzinfo=UTC),
            model_versions_json={"worldcup_1x2": "synthetic"},
            warnings_json=["snapshot-warning"],
        )
        persist_combo_ticket_snapshot(session, snapshot, ticket_id=record.id)

    inspector = inspect(engine)
    assert _count_rows(engine, "combo_tickets") == 1
    assert _count_rows(engine, "combo_ticket_legs") == 1
    assert _count_rows(engine, "combo_ticket_snapshots") == 1
    assert "warnings_json" in {column["name"] for column in inspector.get_columns("combo_tickets")}


def test_worldcup_combo_sessions_group_by_public_time_span(tmp_path: Path) -> None:
    engine = _init_full_db(tmp_path)
    config = _enabled_config(max_session_span_hours_public=4)
    kickoff = datetime(2026, 6, 11, 14, tzinfo=UTC)
    with session_scope(create_session_factory(engine)) as session:
        _seed_fixture(session, fixture_id=-1001, kickoff=kickoff, round_name="Group Stage - 1")
        _seed_fixture(
            session,
            fixture_id=-1002,
            kickoff=kickoff + timedelta(hours=2),
            round_name="Group Stage - 1",
        )
        _seed_fixture(
            session,
            fixture_id=-1003,
            kickoff=kickoff + timedelta(hours=5),
            round_name="Group Stage - 1",
        )

    with session_scope(create_session_factory(engine)) as session:
        sessions = WorldCupComboSessionService(session, config).build_sessions(
            target_date=date(2026, 6, 11)
        )

    assert len(sessions) == 2
    assert len(sessions[0].fixtures) == 2
    assert len(sessions[1].fixtures) == 1


def test_worldcup_combo_selector_excludes_started_fixture(tmp_path: Path) -> None:
    engine = _init_full_db(tmp_path)
    config = _enabled_config()
    kickoff = datetime(2026, 6, 11, 18, tzinfo=UTC)
    with session_scope(create_session_factory(engine)) as session:
        _seed_fixture(session, fixture_id=-1101, kickoff=kickoff, status_short="1H")

    result = _select_for_date(engine, config, date(2026, 6, 11))

    assert result.candidates == ()
    assert _reason_counts(result)["fixture_started"] == 1


def test_worldcup_combo_selector_excludes_ev_negative_leg(tmp_path: Path) -> None:
    engine = _init_full_db(tmp_path)
    config = _enabled_config()
    kickoff = datetime(2026, 6, 11, 18, tzinfo=UTC)
    prediction_time = kickoff - timedelta(minutes=40)
    with session_scope(create_session_factory(engine)) as session:
        _seed_fixture(session, fixture_id=-1201, kickoff=kickoff)
        _seed_1x2_prediction(session, fixture_id=-1201, prediction_time=prediction_time)
        _seed_1x2_odds(
            session,
            fixture_id=-1201,
            fetched_at=kickoff - timedelta(minutes=30),
            odd_home=1.40,
            odd_draw=5.0,
            odd_away=8.0,
        )

    result = _select_for_date(engine, config, date(2026, 6, 11))

    assert result.candidates == ()
    assert _reason_counts(result)["ev_below_threshold"] == 1


def test_worldcup_combo_selector_excludes_edge_negative_leg(tmp_path: Path) -> None:
    engine = _init_full_db(tmp_path)
    config = _enabled_config()
    kickoff = datetime(2026, 6, 11, 18, tzinfo=UTC)
    prediction_time = kickoff - timedelta(minutes=40)
    with session_scope(create_session_factory(engine)) as session:
        _seed_fixture(session, fixture_id=-1301, kickoff=kickoff)
        _seed_ou_prediction(
            session,
            fixture_id=-1301,
            prediction_time=prediction_time,
            edge_pick=-0.04,
            ev_pick=0.08,
        )

    result = _select_for_date(engine, config, date(2026, 6, 11))

    assert result.candidates == ()
    assert _reason_counts(result)["edge_below_threshold"] == 1


def test_worldcup_combo_selector_excludes_invalid_odd(tmp_path: Path) -> None:
    engine = _init_full_db(tmp_path)
    config = _enabled_config()
    kickoff = datetime(2026, 6, 11, 18, tzinfo=UTC)
    prediction_time = kickoff - timedelta(minutes=40)
    with session_scope(create_session_factory(engine)) as session:
        _seed_fixture(session, fixture_id=-1401, kickoff=kickoff)
        _seed_ou_prediction(
            session,
            fixture_id=-1401,
            prediction_time=prediction_time,
            odd_pick=1.0,
            edge_pick=0.06,
            ev_pick=0.08,
        )

    result = _select_for_date(engine, config, date(2026, 6, 11))

    assert result.candidates == ()
    assert _reason_counts(result)["invalid_odds"] == 1


def test_worldcup_combo_selector_includes_clean_1x2_leg(tmp_path: Path) -> None:
    engine = _init_full_db(tmp_path)
    config = _enabled_config()
    kickoff = datetime(2026, 6, 11, 18, tzinfo=UTC)
    prediction_time = kickoff - timedelta(minutes=40)
    with session_scope(create_session_factory(engine)) as session:
        _seed_fixture(session, fixture_id=-1501, kickoff=kickoff)
        _seed_1x2_prediction(session, fixture_id=-1501, prediction_time=prediction_time)
        _seed_1x2_odds(session, fixture_id=-1501, fetched_at=kickoff - timedelta(minutes=30))

    result = _select_for_date(engine, config, date(2026, 6, 11))

    assert len(result.candidates) == 1
    candidate = result.candidates[0]
    assert candidate.fixture_id == -1501
    assert candidate.market_type == ComboMarketType.HOME
    assert candidate.ev >= config.min_leg_ev
    assert candidate.edge >= config.min_leg_edge


def test_worldcup_combo_selector_includes_clean_ou_v2_value_leg(tmp_path: Path) -> None:
    engine = _init_full_db(tmp_path)
    config = _enabled_config()
    kickoff = datetime(2026, 6, 11, 18, tzinfo=UTC)
    prediction_time = kickoff - timedelta(minutes=40)
    with session_scope(create_session_factory(engine)) as session:
        _seed_fixture(session, fixture_id=-1601, kickoff=kickoff)
        _seed_ou_prediction(
            session,
            fixture_id=-1601,
            prediction_time=prediction_time,
            value_side="UNDER",
            p_pick=0.58,
            market_p_pick=0.51,
            odd_pick=2.0,
            edge_pick=0.07,
            ev_pick=0.16,
        )

    result = _select_for_date(engine, config, date(2026, 6, 11))

    assert len(result.candidates) == 1
    assert result.candidates[0].market_type == ComboMarketType.UNDER_25
    assert result.candidates[0].selection == "Under 2.5"


def test_worldcup_combo_disabled_returns_no_sessions_or_legs(tmp_path: Path) -> None:
    engine = _init_full_db(tmp_path)
    config = WorldCupComboConfig(enabled=False)
    kickoff = datetime(2026, 6, 11, 18, tzinfo=UTC)
    with session_scope(create_session_factory(engine)) as session:
        _seed_fixture(session, fixture_id=-1701, kickoff=kickoff)
        sessions = WorldCupComboSessionService(session, config).build_sessions(
            target_date=date(2026, 6, 11)
        )
        result = WorldCupComboLegSelector(session, config).select_candidates(sessions)

    assert sessions == []
    assert result == ComboLegSelectionResult()


def test_worldcup_combo_selector_marks_matchday3_as_risk(tmp_path: Path) -> None:
    engine = _init_full_db(tmp_path)
    config = _enabled_config()
    kickoff = datetime(2026, 6, 11, 18, tzinfo=UTC)
    prediction_time = kickoff - timedelta(minutes=40)
    with session_scope(create_session_factory(engine)) as session:
        _seed_fixture(
            session,
            fixture_id=-1801,
            kickoff=kickoff,
            round_name="Group Stage - 3",
        )
        _seed_1x2_prediction(session, fixture_id=-1801, prediction_time=prediction_time)
        _seed_1x2_odds(session, fixture_id=-1801, fetched_at=kickoff - timedelta(minutes=30))

    result = _select_for_date(engine, config, date(2026, 6, 11))

    assert len(result.candidates) == 1
    assert "matchday3_public_risk" in result.candidates[0].warnings
    assert result.sessions[0].is_matchday3 is True


def test_worldcup_combo_selector_excludes_knockout_unknown_scope(tmp_path: Path) -> None:
    engine = _init_full_db(tmp_path)
    config = _enabled_config()
    kickoff = datetime(2026, 6, 11, 18, tzinfo=UTC)
    prediction_time = kickoff - timedelta(minutes=40)
    with session_scope(create_session_factory(engine)) as session:
        _seed_fixture(session, fixture_id=-1901, kickoff=kickoff, round_name="Quarter-finals")
        _seed_1x2_prediction(
            session,
            fixture_id=-1901,
            prediction_time=prediction_time,
            payload_json={"market_scope": "UNKNOWN"},
        )
        _seed_1x2_odds(session, fixture_id=-1901, fetched_at=kickoff - timedelta(minutes=30))

    result = _select_for_date(engine, config, date(2026, 6, 11))

    assert result.candidates == ()
    assert _reason_counts(result)["ambiguous_market_scope"] == 1


def _leg_candidate() -> ComboLegCandidate:
    kickoff = datetime(2026, 6, 11, 18, tzinfo=UTC)
    return ComboLegCandidate(
        fixture_id=-101,
        kickoff_at_utc=kickoff,
        kickoff_at_paris=kickoff + timedelta(hours=2),
        market_type=ComboMarketType.HOME,
        market_scope=ComboMarketScope.NINETY_MIN,
        selection="Synthetic Home",
        decimal_odd=2.1,
        model_probability=0.52,
        market_probability=0.47,
        edge=0.05,
        ev=0.092,
        confidence_score=62.0,
        confidence_label="Medium",
        data_quality_score=78.0,
        odds_snapshot_id=-201,
        prediction_snapshot_id=-301,
        lineup_status="unknown",
        odds_last_update=kickoff - timedelta(minutes=45),
        prediction_generated_at=kickoff - timedelta(minutes=40),
        warnings=["synthetic-warning"],
    )


def _ticket_candidate(legs: tuple[ComboLegCandidate, ...]) -> ComboTicketCandidate:
    first_kickoff = datetime(2026, 6, 11, 18, tzinfo=UTC)
    return ComboTicketCandidate(
        competition_key="fifa_world_cup_2026",
        league_id=1,
        season=2026,
        combo_date=date(2026, 6, 11),
        session_key="synthetic-session",
        ticket_key="synthetic-ticket",
        first_kickoff_at=first_kickoff,
        last_kickoff_at=first_kickoff + timedelta(hours=2),
        lock_time=first_kickoff - timedelta(minutes=20),
        legs_count=len(legs),
        combined_decimal_odds=2.1,
        combined_probability_raw=0.52,
        combined_probability_adjusted=0.50,
        combined_fair_odds=2.0,
        combined_ev_raw=0.092,
        combined_ev_adjusted=0.05,
        combined_confidence_score=61.0,
        combined_confidence_label="Medium",
        post_lock_risk_score=20.0,
        freshness_score=82.0,
        lineup_risk_score=15.0,
        publication_decision=ComboTicketStatus.DRAFT,
        no_publish_reason=None,
        legs=legs,
        warnings=["ticket-warning"],
    )


def _count_rows(engine, table_name: str) -> int:
    with engine.connect() as connection:
        return int(connection.exec_driver_sql(f"select count(*) from {table_name}").scalar_one())


def _init_full_db(tmp_path: Path):
    engine = create_db_engine(f"sqlite:///{tmp_path / 'combos_full.db'}")
    init_db(engine)
    return engine


def _enabled_config(**overrides) -> WorldCupComboConfig:
    payload = {
        "enabled": True,
        "competition_key": "fifa_world_cup_2026",
        "league_id": 1,
        "season": 2026,
        "timezone_display": "Europe/Paris",
        "max_public_legs": 2,
        "max_staff_legs": 3,
        "lock_buffer_minutes": 20,
        "max_session_span_hours_public": 4,
        "min_leg_ev": 0.03,
        "min_leg_edge": 0.03,
        "min_leg_data_quality": 65.0,
        "min_leg_confidence": 55.0,
        "min_combined_ev_adjusted": 0.03,
        "min_combined_confidence_public": 68.0,
        "max_post_lock_risk_public": 30.0,
        "require_positive_ev_each_leg": True,
        "forbid_same_group_md3_multiple_legs": True,
        "allow_public_matchday3": False,
        "allow_public_knockout": False,
        "staff_only_shadow_mode": True,
    }
    payload.update(overrides)
    return WorldCupComboConfig(**payload)


def _select_for_date(
    engine,
    config: WorldCupComboConfig,
    target_date: date,
) -> ComboLegSelectionResult:
    with session_scope(create_session_factory(engine)) as session:
        sessions = WorldCupComboSessionService(session, config).build_sessions(
            target_date=target_date
        )
        now = datetime(2026, 6, 11, 14, tzinfo=UTC)
        return WorldCupComboLegSelector(session, config).select_candidates(sessions, now=now)


def _seed_fixture(
    session,
    *,
    fixture_id: int,
    kickoff: datetime,
    round_name: str = "Group Stage - 1",
    status_short: str = "NS",
) -> None:
    _ensure_synthetic_teams(session)
    session.add(
        db_models.Fixture(
            fixture_id=fixture_id,
            date=kickoff,
            timestamp=int(kickoff.timestamp()),
            timezone="UTC",
            round=round_name,
            league_id=1,
            season=2026,
            status="Not Started" if status_short == "NS" else "In Play",
            status_long="Not Started" if status_short == "NS" else "In Play",
            status_short=status_short,
            home_team_id=-1,
            away_team_id=-2,
            home_team="Synthetic Home",
            away_team="Synthetic Away",
            payload_json={"synthetic": True, "competition_key": "fifa_world_cup_2026"},
        )
    )


def _ensure_synthetic_teams(session) -> None:
    if session.info.get("combo_synthetic_teams_seeded"):
        return
    if session.get(db_models.Team, -1) is None:
        session.add(
            db_models.Team(
                team_id=-1,
                name="Synthetic Home",
                country="Synthetic",
                national=True,
                payload_json={"synthetic": True},
            )
        )
    session.info["combo_synthetic_teams_seeded"] = True
    if session.get(db_models.Team, -2) is None:
        session.add(
            db_models.Team(
                team_id=-2,
                name="Synthetic Away",
                country="Synthetic",
                national=True,
                payload_json={"synthetic": True},
            )
        )


def _seed_1x2_prediction(
    session,
    *,
    fixture_id: int,
    prediction_time: datetime,
    p_home: float = 0.62,
    p_draw: float = 0.20,
    p_away: float = 0.18,
    predicted_result: str = "HOME",
    confidence_score: float = 70.0,
    data_quality_score: float = 80.0,
    payload_json: dict | None = None,
) -> None:
    feature = db_models.FeatureSnapshot(
        fixture_id=fixture_id,
        prediction_time=prediction_time,
        feature_version="synthetic-combo-test",
        features_json={"synthetic": True},
        data_quality_json={"overall_data_quality_score": data_quality_score},
    )
    session.add(feature)
    session.flush()
    session.add(
        db_models.ModelPrediction(
            fixture_id=fixture_id,
            feature_snapshot_id=feature.id,
            prediction_time=prediction_time,
            model_version="synthetic-worldcup-1x2",
            p_home=p_home,
            p_draw=p_draw,
            p_away=p_away,
            predicted_outcome=predicted_result,
            predicted_result=predicted_result,
            confidence=confidence_score / 100,
            confidence_label="High",
            confidence_score=confidence_score,
            explanation_json=[],
            explanations_json=[],
            data_quality_json={"overall_data_quality_score": data_quality_score},
            payload_json=payload_json or {"model_family": "worldcup_1x2", "synthetic": True},
        )
    )


def _seed_1x2_odds(
    session,
    *,
    fixture_id: int,
    fetched_at: datetime,
    odd_home: float = 2.0,
    odd_draw: float = 3.5,
    odd_away: float = 4.0,
) -> None:
    session.add(
        db_models.OddsSnapshot(
            fixture_id=fixture_id,
            league_id=1,
            season=2026,
            bookmaker_id=-10,
            bookmaker_name="Synthetic Book",
            bet_id=1,
            bet_name="Match Winner",
            fetched_at=fetched_at,
            is_live=False,
            odd_home=odd_home,
            odd_draw=odd_draw,
            odd_away=odd_away,
            values_json=[],
            odds_json={"synthetic": True},
            payload_json={"synthetic": True},
        )
    )


def _seed_ou_prediction(
    session,
    *,
    fixture_id: int,
    prediction_time: datetime,
    value_side: str = "OVER",
    p_pick: float = 0.58,
    market_p_pick: float = 0.51,
    odd_pick: float = 2.0,
    edge_pick: float = 0.07,
    ev_pick: float = 0.16,
    confidence_score: float = 70.0,
    data_quality_score: float = 80.0,
    payload_json: dict | None = None,
) -> None:
    feature = db_models.OUFeatureSnapshot(
        fixture_id=fixture_id,
        prediction_time=prediction_time,
        feature_version="synthetic-ou-combo-test",
        threshold=2.5,
        features_json={"synthetic": True},
        data_quality_json={"ou_data_quality_score": data_quality_score},
    )
    session.add(feature)
    session.flush()
    session.add(
        db_models.OUModelPrediction(
            fixture_id=fixture_id,
            ou_feature_snapshot_id=feature.id,
            prediction_time=prediction_time,
            model_version="synthetic-ou-v2",
            threshold=2.5,
            p_over=p_pick if value_side.upper() == "OVER" else 1 - p_pick,
            p_under=p_pick if value_side.upper() == "UNDER" else 1 - p_pick,
            market_p_over=market_p_pick if value_side.upper() == "OVER" else 1 - market_p_pick,
            market_p_under=market_p_pick if value_side.upper() == "UNDER" else 1 - market_p_pick,
            edge_over=edge_pick if value_side.upper() == "OVER" else None,
            edge_under=edge_pick if value_side.upper() == "UNDER" else None,
            ev_over=ev_pick if value_side.upper() == "OVER" else None,
            ev_under=ev_pick if value_side.upper() == "UNDER" else None,
            market_odd_over=odd_pick if value_side.upper() == "OVER" else None,
            market_odd_under=odd_pick if value_side.upper() == "UNDER" else None,
            confidence_score=confidence_score,
            confidence_label="High",
            forecast_side=value_side.upper(),
            forecast_probability=p_pick,
            value_side=value_side.upper(),
            p_pick=p_pick,
            market_p_pick=market_p_pick,
            odd_pick=odd_pick,
            edge_pick=edge_pick,
            ev_pick=ev_pick,
            is_value_pick=True,
            no_bet_reason=None,
            confidence_score_v2=confidence_score,
            confidence_label_v2="High",
            publication_decision="public",
            expert_probabilities_json={},
            data_quality_json={"ou_data_quality_score": data_quality_score},
            payload_json=payload_json or {"decision_version": "ou_decision_v2", "synthetic": True},
        )
    )


def _reason_counts(result: ComboLegSelectionResult) -> Counter:
    return Counter(item.reason for item in result.no_candidates)
