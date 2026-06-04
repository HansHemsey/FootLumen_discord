from __future__ import annotations

from collections import Counter
from dataclasses import replace
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
from football_predictor.discord.service import DiscordDeliveryService
from football_predictor.world_cup_combos.config import (
    WorldCupComboConfig,
    load_world_cup_combo_config,
)
from football_predictor.world_cup_combos.cutoff import compute_effective_cutoff
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
    WorldCupComboFixtureRef,
    WorldCupComboSession,
)
from football_predictor.world_cup_combos.persistence import (
    ensure_combo_tables,
    persist_combo_ticket_candidate,
    persist_combo_ticket_snapshot,
    persist_combo_ticket_with_snapshots,
)
from football_predictor.world_cup_combos.pre_lock_revalidator import (
    WorldCupComboPreLockRevalidator,
)
from football_predictor.world_cup_combos.worldcup_combo_builder import WorldCupComboBuilder
from football_predictor.world_cup_combos.worldcup_combo_formatter import WorldCupComboFormatter
from football_predictor.world_cup_combos.worldcup_combo_leg_selector import (
    WorldCupComboLegSelector,
)
from football_predictor.world_cup_combos.worldcup_combo_lock_service import (
    WorldCupComboLockService,
)
from football_predictor.world_cup_combos.worldcup_combo_publication_policy import (
    WorldCupComboPublicationPolicy,
)
from football_predictor.world_cup_combos.worldcup_combo_publication_service import (
    WorldCupComboPublicationService,
)
from football_predictor.world_cup_combos.worldcup_combo_refresh_policy import (
    WorldCupComboRefreshPolicy,
)
from football_predictor.world_cup_combos.worldcup_combo_run_service import (
    WorldCupComboRunService,
)
from football_predictor.world_cup_combos.worldcup_combo_scoring import WorldCupComboScoring
from football_predictor.world_cup_combos.worldcup_combo_sessions import (
    WorldCupComboSessionService,
)
from football_predictor.world_cup_combos.worldcup_combo_settlement import (
    WorldCupComboSettlementService,
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
    assert "ticket-warning" in payload["warnings"]


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


def test_worldcup_combo_effective_cutoff_uses_now_before_lock() -> None:
    now = datetime(2026, 6, 11, 9, tzinfo=UTC)
    lock_time = datetime(2026, 6, 11, 18, 40, tzinfo=UTC)

    assert compute_effective_cutoff(now, lock_time) == now


def test_worldcup_combo_effective_cutoff_uses_lock_after_lock() -> None:
    now = datetime(2026, 6, 11, 18, 50, tzinfo=UTC)
    lock_time = datetime(2026, 6, 11, 18, 40, tzinfo=UTC)

    assert compute_effective_cutoff(now, lock_time) == lock_time


def test_worldcup_combo_selector_excludes_future_1x2_prediction_before_lock(
    tmp_path: Path,
) -> None:
    engine = _init_full_db(tmp_path)
    config = _enabled_config()
    kickoff = datetime(2026, 6, 11, 18, tzinfo=UTC)
    now = datetime(2026, 6, 11, 14, tzinfo=UTC)
    with session_scope(create_session_factory(engine)) as session:
        _seed_fixture(session, fixture_id=-1111, kickoff=kickoff)
        _seed_1x2_prediction(
            session,
            fixture_id=-1111,
            prediction_time=kickoff - timedelta(minutes=30),
        )
        _seed_1x2_odds(session, fixture_id=-1111, fetched_at=now - timedelta(minutes=5))

    result = _select_for_date(engine, config, date(2026, 6, 11), now=now)

    assert result.candidates == ()
    assert _reason_counts(result)["missing_prediction"] == 1


def test_worldcup_combo_selector_excludes_future_1x2_prediction_after_lock(
    tmp_path: Path,
) -> None:
    engine = _init_full_db(tmp_path)
    config = _enabled_config()
    kickoff = datetime(2026, 6, 11, 18, tzinfo=UTC)
    lock_time = kickoff - timedelta(minutes=config.lock_buffer_minutes)
    now = lock_time + timedelta(minutes=10)
    with session_scope(create_session_factory(engine)) as session:
        _seed_fixture(session, fixture_id=-1112, kickoff=kickoff)
        _seed_1x2_prediction(
            session,
            fixture_id=-1112,
            prediction_time=lock_time + timedelta(minutes=5),
        )
        _seed_1x2_odds(session, fixture_id=-1112, fetched_at=lock_time - timedelta(minutes=5))

    result = _select_for_date(engine, config, date(2026, 6, 11), now=now)

    assert result.candidates == ()
    assert _reason_counts(result)["missing_prediction"] == 1


def test_worldcup_combo_selector_excludes_future_odds_before_lock(tmp_path: Path) -> None:
    engine = _init_full_db(tmp_path)
    config = _enabled_config()
    kickoff = datetime(2026, 6, 11, 18, tzinfo=UTC)
    now = datetime(2026, 6, 11, 14, tzinfo=UTC)
    with session_scope(create_session_factory(engine)) as session:
        _seed_fixture(session, fixture_id=-1113, kickoff=kickoff)
        _seed_1x2_prediction(
            session,
            fixture_id=-1113,
            prediction_time=now - timedelta(minutes=10),
        )
        _seed_1x2_odds(
            session,
            fixture_id=-1113,
            fetched_at=kickoff - timedelta(minutes=30),
        )

    result = _select_for_date(engine, config, date(2026, 6, 11), now=now)

    assert result.candidates == ()
    assert _reason_counts(result)["market_unavailable"] == 1


def test_worldcup_combo_selector_excludes_future_lineups_before_lock(tmp_path: Path) -> None:
    engine = _init_full_db(tmp_path)
    config = _enabled_config()
    kickoff = datetime(2026, 6, 11, 18, tzinfo=UTC)
    now = datetime(2026, 6, 11, 17, tzinfo=UTC)
    with session_scope(create_session_factory(engine)) as session:
        _seed_fixture(session, fixture_id=-1114, kickoff=kickoff)
        _seed_1x2_prediction(
            session,
            fixture_id=-1114,
            prediction_time=now - timedelta(minutes=10),
        )
        _seed_1x2_odds(session, fixture_id=-1114, fetched_at=now - timedelta(minutes=10))
        _seed_lineups(session, fixture_id=-1114, fetched_at=now + timedelta(minutes=20))

    result = _select_for_date(engine, config, date(2026, 6, 11), now=now)

    assert len(result.candidates) == 1
    assert result.candidates[0].lineup_status == "missing"
    assert "lineup_missing_close_to_kickoff" in result.candidates[0].warnings


def test_worldcup_combo_selector_excludes_future_ou_prediction_before_lock(
    tmp_path: Path,
) -> None:
    engine = _init_full_db(tmp_path)
    config = _enabled_config()
    kickoff = datetime(2026, 6, 11, 18, tzinfo=UTC)
    now = datetime(2026, 6, 11, 14, tzinfo=UTC)
    with session_scope(create_session_factory(engine)) as session:
        _seed_fixture(session, fixture_id=-1115, kickoff=kickoff)
        _seed_ou_prediction(
            session,
            fixture_id=-1115,
            prediction_time=kickoff - timedelta(minutes=30),
            edge_pick=0.07,
            ev_pick=0.16,
        )

    result = _select_for_date(engine, config, date(2026, 6, 11), now=now)

    assert result.candidates == ()
    assert _reason_counts(result)["no_ou_value_side"] == 1


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


def test_worldcup_combo_scoring_multiplies_odds_probability_and_raw_ev() -> None:
    legs = (
        _leg_candidate(fixture_id=-2001, decimal_odd=2.0, model_probability=0.60),
        _leg_candidate(fixture_id=-2002, decimal_odd=2.0, model_probability=0.55),
    )

    scoring = WorldCupComboScoring().score(legs)

    assert scoring.combined_decimal_odds == 4.0
    assert scoring.combined_probability_raw == 0.33
    assert scoring.combined_ev_raw == 0.32
    assert scoring.combined_probability_adjusted == 0.33
    assert scoring.combined_ev_adjusted == 0.32


def test_worldcup_combo_scoring_adjusts_ev_with_penalties() -> None:
    legs = (
        _leg_candidate(
            fixture_id=-2101,
            freshness_score=45.0,
            lineup_status="missing",
            warnings=["lineup_missing_close_to_kickoff", "odds_stale"],
        ),
        _leg_candidate(
            fixture_id=-2102,
            freshness_score=55.0,
            lineup_status="partial",
            warnings=["prediction_stale"],
        ),
    )

    scoring = WorldCupComboScoring().score(legs, is_matchday3=True)

    assert scoring.combined_ev_adjusted < scoring.combined_ev_raw
    assert scoring.post_lock_risk_score > 0
    assert scoring.lineup_risk_score > 0
    assert "matchday3_public_risk" in scoring.warnings


def test_worldcup_combo_confidence_is_penalized_by_weakest_leg() -> None:
    scoring = WorldCupComboScoring()
    strong = scoring.score(
        (
            _leg_candidate(fixture_id=-2201, confidence_score=82.0),
            _leg_candidate(fixture_id=-2202, confidence_score=80.0),
        )
    )
    weak = scoring.score(
        (
            _leg_candidate(fixture_id=-2201, confidence_score=82.0),
            _leg_candidate(fixture_id=-2202, confidence_score=35.0),
        )
    )

    assert weak.combined_confidence_score < strong.combined_confidence_score


def test_worldcup_combo_builder_returns_no_ticket_with_single_leg() -> None:
    config = _enabled_config()
    session = _combo_session((-2301, -2302))

    tickets = WorldCupComboBuilder(config).build_for_session(
        session,
        [_leg_candidate(fixture_id=-2301)],
    )

    assert tickets == []


def test_worldcup_combo_builder_builds_valid_two_leg_ticket() -> None:
    config = _enabled_config(staff_only_shadow_mode=False)
    session = _combo_session((-2401, -2402))

    tickets = WorldCupComboBuilder(config).build_for_session(
        session,
        (
            _leg_candidate(fixture_id=-2401, confidence_score=88.0, data_quality_score=90.0),
            _leg_candidate(fixture_id=-2402, confidence_score=86.0, data_quality_score=90.0),
        ),
    )

    assert len(tickets) == 1
    assert tickets[0].legs_count == 2
    assert tickets[0].publication_decision == ComboTicketStatus.PUBLIC_PUBLISHED


def test_worldcup_combo_builder_builds_three_leg_staff_ticket() -> None:
    config = _enabled_config(staff_only_shadow_mode=False)
    session = _combo_session((-2501, -2502, -2503))

    tickets = WorldCupComboBuilder(config).build_for_session(
        session,
        (
            _leg_candidate(fixture_id=-2501, confidence_score=88.0, data_quality_score=90.0),
            _leg_candidate(fixture_id=-2502, confidence_score=86.0, data_quality_score=90.0),
            _leg_candidate(fixture_id=-2503, confidence_score=84.0, data_quality_score=90.0),
        ),
    )

    assert {ticket.legs_count for ticket in tickets} == {2, 3}
    staff_ticket = next(ticket for ticket in tickets if ticket.legs_count == 3)
    assert staff_ticket.publication_decision == ComboTicketStatus.STAFF_ONLY
    assert staff_ticket.no_publish_reason == "too_many_public_legs"


def test_worldcup_combo_builder_excludes_same_fixture_combos() -> None:
    config = _enabled_config(staff_only_shadow_mode=False)
    session = _combo_session((-2601, -2602))

    tickets = WorldCupComboBuilder(config).build_for_session(
        session,
        (
            _leg_candidate(fixture_id=-2601, market_type=ComboMarketType.HOME),
            _leg_candidate(fixture_id=-2601, market_type=ComboMarketType.OVER_25),
            _leg_candidate(fixture_id=-2602, market_type=ComboMarketType.AWAY),
        ),
    )

    assert tickets
    assert all(
        len({leg.fixture_id for leg in ticket.legs}) == ticket.legs_count
        for ticket in tickets
    )


def test_worldcup_combo_policy_blocks_matchday3_public() -> None:
    config = _enabled_config(staff_only_shadow_mode=False)
    session = _combo_session((-2701, -2702), is_matchday3=True)

    tickets = WorldCupComboBuilder(config).build_for_session(
        session,
        (
            _leg_candidate(fixture_id=-2701, confidence_score=88.0, data_quality_score=90.0),
            _leg_candidate(fixture_id=-2702, confidence_score=86.0, data_quality_score=90.0),
        ),
    )

    assert tickets[0].publication_decision == ComboTicketStatus.STAFF_ONLY
    assert tickets[0].no_publish_reason == "matchday3_public_forbidden"


def test_worldcup_combo_policy_knockout_unknown_scope_is_no_bet() -> None:
    config = _enabled_config(staff_only_shadow_mode=False, allow_public_knockout=True)
    ticket = _ticket_candidate(
        legs=(
            _leg_candidate(fixture_id=-2801, market_scope=ComboMarketScope.UNKNOWN),
            _leg_candidate(fixture_id=-2802),
        )
    )

    decided = WorldCupComboPublicationPolicy(config).decide(ticket)

    assert decided.publication_decision == ComboTicketStatus.NO_BET
    assert decided.no_publish_reason == "market_scope_unknown"


def test_worldcup_combo_policy_shadow_mode_prevents_public() -> None:
    config = _enabled_config(staff_only_shadow_mode=True)
    ticket = _ticket_candidate(
        legs=(
            _leg_candidate(fixture_id=-2901, confidence_score=88.0, data_quality_score=90.0),
            _leg_candidate(fixture_id=-2902, confidence_score=86.0, data_quality_score=90.0),
        )
    )

    decided = WorldCupComboPublicationPolicy(config).decide(ticket)

    assert decided.publication_decision == ComboTicketStatus.STAFF_ONLY
    assert decided.no_publish_reason == "staff_only_shadow_mode"


def test_worldcup_combo_policy_no_bet_if_adjusted_ev_non_positive() -> None:
    config = _enabled_config(staff_only_shadow_mode=False)
    ticket = _ticket_candidate(
        legs=(
            _leg_candidate(
                fixture_id=-3001,
                decimal_odd=1.97,
                model_probability=0.51,
                edge=0.01,
                ev=0.004,
                freshness_score=30.0,
                lineup_status="missing",
                warnings=["lineup_missing_close_to_kickoff"],
            ),
            _leg_candidate(
                fixture_id=-3002,
                decimal_odd=1.97,
                model_probability=0.51,
                edge=0.01,
                ev=0.004,
                freshness_score=30.0,
                lineup_status="missing",
                warnings=["lineup_missing_close_to_kickoff"],
            ),
        )
    )

    decided = WorldCupComboPublicationPolicy(config).decide(ticket)

    assert decided.combined_ev_adjusted <= 0
    assert decided.publication_decision == ComboTicketStatus.NO_BET


def test_worldcup_combo_persistence_stores_lifecycle_snapshots(tmp_path: Path) -> None:
    engine = create_db_engine(f"sqlite:///{tmp_path / 'combos.db'}")
    ensure_combo_tables(engine)
    session_factory = create_session_factory(engine)
    ticket = _ticket_candidate(
        legs=(
            _leg_candidate(fixture_id=-3101),
            _leg_candidate(fixture_id=-3102),
        )
    )

    with session_scope(session_factory) as session:
        persist_combo_ticket_with_snapshots(
            session,
            ticket,
            captured_at=datetime(2026, 6, 11, 17, 40, tzinfo=UTC),
        )

    assert _count_rows(engine, "combo_tickets") == 1
    assert _count_rows(engine, "combo_ticket_legs") == 2
    assert _count_rows(engine, "combo_ticket_snapshots") == 3


def test_worldcup_combo_refresh_policy_lock_time_and_freshness() -> None:
    config = _enabled_config()
    session = _combo_session((-3201, -3202))
    ticket = WorldCupComboBuilder(config).build_for_session(
        session,
        (
            _leg_candidate(fixture_id=-3201),
            _leg_candidate(fixture_id=-3202),
        ),
    )[0]
    policy = WorldCupComboRefreshPolicy(config)
    now = ticket.first_kickoff_at - timedelta(minutes=25)

    assert ticket.lock_time == ticket.first_kickoff_at - timedelta(
        minutes=config.lock_buffer_minutes
    )
    assert policy.required_freshness_minutes("odds", now, ticket.first_kickoff_at) == 10


def test_worldcup_combo_lock_does_not_modify_locked_ticket() -> None:
    config = _enabled_config(staff_only_shadow_mode=False)
    ticket = replace(
        _ticket_candidate(
            legs=(
                _leg_candidate(fixture_id=-3301),
                _leg_candidate(fixture_id=-3302),
            )
        ),
        publication_decision=ComboTicketStatus.LOCKED,
        warnings=["locked-original"],
    )

    locked = WorldCupComboLockService(config).lock_ticket(
        ticket,
        now=datetime(2026, 6, 11, 17, 40, tzinfo=UTC),
    )

    assert locked is ticket
    assert locked.warnings == ["locked-original"]


def test_worldcup_combo_lock_revalidates_no_bet_if_ev_turns_negative() -> None:
    config = _enabled_config(staff_only_shadow_mode=False)
    ticket = _ticket_candidate(
        legs=(
            _leg_candidate(
                fixture_id=-3401,
                decimal_odd=1.8,
                model_probability=0.45,
                edge=0.01,
                ev=-0.19,
            ),
            _leg_candidate(
                fixture_id=-3402,
                decimal_odd=1.8,
                model_probability=0.45,
                edge=0.01,
                ev=-0.19,
            ),
        )
    )

    locked = WorldCupComboLockService(config).lock_ticket(
        ticket,
        now=datetime(2026, 6, 11, 17, 40, tzinfo=UTC),
    )

    assert locked.publication_decision == ComboTicketStatus.NO_BET
    assert locked.no_publish_reason == "combined_ev_adjusted_non_positive"


def test_worldcup_combo_lock_revalidates_staff_if_post_lock_risk_high() -> None:
    config = _enabled_config(staff_only_shadow_mode=False)
    ticket = _ticket_candidate(
        legs=(
            _leg_candidate(
                fixture_id=-3501,
                lineup_status="missing",
                warnings=["lineup_missing_close_to_kickoff"],
            ),
            _leg_candidate(
                fixture_id=-3502,
                lineup_status="missing",
                warnings=["lineup_missing_close_to_kickoff"],
            ),
        )
    )

    locked = WorldCupComboLockService(config).lock_ticket(
        ticket,
        now=datetime(2026, 6, 11, 17, 45, tzinfo=UTC),
    )

    assert locked.publication_decision == ComboTicketStatus.STAFF_ONLY
    assert locked.no_publish_reason == "post_lock_risk_above_public_threshold"


def test_worldcup_combo_pre_lock_reloads_newer_odds(tmp_path: Path) -> None:
    engine = _init_full_db(tmp_path)
    config = _enabled_config(staff_only_shadow_mode=False)
    now_build = datetime(2026, 6, 11, 12, tzinfo=UTC)
    now_lock = datetime(2026, 6, 11, 17, 35, tzinfo=UTC)
    newer_odds_time = datetime(2026, 6, 11, 17, 30, tzinfo=UTC)

    with session_scope(create_session_factory(engine)) as session:
        _seed_pre_lock_fixture_sources(session, fixture_ids=(-5001, -5002))
        ticket = _build_ticket_from_db(
            session,
            config,
            target_date=date(2026, 6, 11),
            now=now_build,
            fixture_ids=(-5001, -5002),
        )
        _seed_1x2_odds(session, fixture_id=-5001, fetched_at=newer_odds_time, odd_home=2.2)
        _seed_1x2_odds(session, fixture_id=-5002, fetched_at=newer_odds_time, odd_home=2.2)
        revalidated = WorldCupComboPreLockRevalidator(session, config).revalidate(
            ticket,
            now=now_lock,
        ).ticket

    assert {leg.odds_last_update for leg in revalidated.legs} == {newer_odds_time}
    assert revalidated.data_cutoff_time == now_lock
    assert "pre_lock_revalidated" in revalidated.warnings


def test_worldcup_combo_pre_lock_removes_negative_ev_leg(tmp_path: Path) -> None:
    engine = _init_full_db(tmp_path)
    config = _enabled_config(staff_only_shadow_mode=False)
    now_build = datetime(2026, 6, 11, 12, tzinfo=UTC)
    now_lock = datetime(2026, 6, 11, 17, 35, tzinfo=UTC)

    with session_scope(create_session_factory(engine)) as session:
        _seed_pre_lock_fixture_sources(session, fixture_ids=(-5011, -5012))
        ticket = _build_ticket_from_db(
            session,
            config,
            target_date=date(2026, 6, 11),
            now=now_build,
            fixture_ids=(-5011, -5012),
        )
        _seed_1x2_odds(
            session,
            fixture_id=-5011,
            fetched_at=now_lock - timedelta(minutes=5),
            odd_home=1.2,
        )
        _seed_1x2_odds(
            session,
            fixture_id=-5012,
            fetched_at=now_lock - timedelta(minutes=5),
            odd_home=2.2,
        )
        revalidated = WorldCupComboPreLockRevalidator(session, config).revalidate(
            ticket,
            now=now_lock,
        ).ticket

    assert revalidated.publication_decision == ComboTicketStatus.NO_BET
    assert revalidated.no_publish_reason == "not_enough_clean_legs"
    assert "leg_ev_dropped" in revalidated.warnings
    assert "no_clean_replacement" in revalidated.warnings


def test_worldcup_combo_pre_lock_replaces_degraded_leg(tmp_path: Path) -> None:
    engine = _init_full_db(tmp_path)
    config = _enabled_config(staff_only_shadow_mode=False)
    now_build = datetime(2026, 6, 11, 12, tzinfo=UTC)
    now_lock = datetime(2026, 6, 11, 17, 35, tzinfo=UTC)

    with session_scope(create_session_factory(engine)) as session:
        _seed_pre_lock_fixture_sources(session, fixture_ids=(-5021, -5022, -5023))
        ticket = _build_ticket_from_db(
            session,
            config,
            target_date=date(2026, 6, 11),
            now=now_build,
            fixture_ids=(-5021, -5022),
        )
        _seed_1x2_odds(
            session,
            fixture_id=-5021,
            fetched_at=now_lock - timedelta(minutes=5),
            odd_home=2.2,
        )
        _seed_1x2_odds(
            session,
            fixture_id=-5022,
            fetched_at=now_lock - timedelta(minutes=5),
            odd_home=1.2,
        )
        _seed_1x2_odds(
            session,
            fixture_id=-5023,
            fetched_at=now_lock - timedelta(minutes=5),
            odd_home=2.2,
        )
        revalidated = WorldCupComboPreLockRevalidator(session, config).revalidate(
            ticket,
            now=now_lock,
        ).ticket

    assert -5022 not in {leg.fixture_id for leg in revalidated.legs}
    assert -5023 in {leg.fixture_id for leg in revalidated.legs}
    assert "replacement_used" in revalidated.warnings
    assert "pre_lock_replaced_leg" in revalidated.warnings


def test_worldcup_combo_pre_lock_staff_only_if_lineup_risk_high(tmp_path: Path) -> None:
    engine = _init_full_db(tmp_path)
    config = _enabled_config(staff_only_shadow_mode=False)
    now_build = datetime(2026, 6, 11, 12, tzinfo=UTC)
    now_lock = datetime(2026, 6, 11, 17, 10, tzinfo=UTC)

    with session_scope(create_session_factory(engine)) as session:
        _seed_pre_lock_fixture_sources(session, fixture_ids=(-5031, -5032))
        ticket = _build_ticket_from_db(
            session,
            config,
            target_date=date(2026, 6, 11),
            now=now_build,
            fixture_ids=(-5031, -5032),
        )
        _seed_1x2_odds(
            session,
            fixture_id=-5031,
            fetched_at=now_lock - timedelta(minutes=5),
            odd_home=2.2,
        )
        _seed_1x2_odds(
            session,
            fixture_id=-5032,
            fetched_at=now_lock - timedelta(minutes=5),
            odd_home=2.2,
        )
        revalidated = WorldCupComboPreLockRevalidator(session, config).revalidate(
            ticket,
            now=now_lock,
        ).ticket

    assert revalidated.publication_decision == ComboTicketStatus.STAFF_ONLY
    assert revalidated.no_publish_reason == "lineup_risk_too_high"
    assert "lineup_risk_too_high" in revalidated.warnings


def test_worldcup_combo_pre_lock_does_not_use_future_data(tmp_path: Path) -> None:
    engine = _init_full_db(tmp_path)
    config = _enabled_config(staff_only_shadow_mode=False)
    now_build = datetime(2026, 6, 11, 12, tzinfo=UTC)
    now_lock = datetime(2026, 6, 11, 17, tzinfo=UTC)
    future_time = datetime(2026, 6, 11, 17, 30, tzinfo=UTC)

    with session_scope(create_session_factory(engine)) as session:
        _seed_pre_lock_fixture_sources(session, fixture_ids=(-5041, -5042))
        ticket = _build_ticket_from_db(
            session,
            config,
            target_date=date(2026, 6, 11),
            now=now_build,
            fixture_ids=(-5041, -5042),
        )
        _seed_1x2_prediction(
            session,
            fixture_id=-5041,
            prediction_time=future_time,
            predicted_result="AWAY",
            p_home=0.15,
            p_draw=0.20,
            p_away=0.65,
        )
        _seed_1x2_odds(session, fixture_id=-5041, fetched_at=future_time, odd_home=2.8)
        _seed_1x2_odds(
            session,
            fixture_id=-5041,
            fetched_at=now_lock - timedelta(minutes=5),
            odd_home=2.2,
        )
        _seed_1x2_odds(
            session,
            fixture_id=-5042,
            fetched_at=now_lock - timedelta(minutes=5),
            odd_home=2.2,
        )
        revalidated = WorldCupComboPreLockRevalidator(session, config).revalidate(
            ticket,
            now=now_lock,
        ).ticket

    leg = next(item for item in revalidated.legs if item.fixture_id == -5041)
    assert leg.market_type == ComboMarketType.HOME
    assert leg.odds_last_update == now_lock - timedelta(minutes=5)
    assert revalidated.data_cutoff_time == now_lock


def test_worldcup_combo_pre_lock_execute_creates_revalidation_snapshot(tmp_path: Path) -> None:
    engine = _init_full_db(tmp_path)
    config = _enabled_config(staff_only_shadow_mode=False)
    now_build = datetime(2026, 6, 11, 12, tzinfo=UTC)
    now_lock = datetime(2026, 6, 11, 17, 35, tzinfo=UTC)

    with session_scope(create_session_factory(engine)) as session:
        _seed_pre_lock_fixture_sources(session, fixture_ids=(-5051, -5052))
        ticket = _build_ticket_from_db(
            session,
            config,
            target_date=date(2026, 6, 11),
            now=now_build,
            fixture_ids=(-5051, -5052),
        )
        record = persist_combo_ticket_candidate(session, ticket)
        _seed_1x2_odds(
            session,
            fixture_id=-5051,
            fetched_at=now_lock - timedelta(minutes=5),
            odd_home=2.2,
        )
        _seed_1x2_odds(
            session,
            fixture_id=-5052,
            fetched_at=now_lock - timedelta(minutes=5),
            odd_home=2.2,
        )
        locked = WorldCupComboLockService(config).lock_persisted_ticket(
            session,
            record,
            now=now_lock,
            execute=True,
        )
        session.flush()
        statuses = {
            row[0]
            for row in session.query(db_models.ComboTicketSnapshot.status)
            .filter(db_models.ComboTicketSnapshot.ticket_id == record.id)
            .all()
        }

    assert locked.publication_decision in {
        ComboTicketStatus.LOCKED,
        ComboTicketStatus.STAFF_ONLY,
    }
    assert "pre_lock_revalidated" in statuses


def test_worldcup_combo_formatter_outputs_watchlist_public_and_no_bet() -> None:
    formatter = WorldCupComboFormatter()
    ticket = _ticket_candidate(
        legs=(
            _leg_candidate(fixture_id=-3601),
            _leg_candidate(fixture_id=-3602),
        )
    )

    watchlist = formatter.format_watchlist_staff(ticket)
    public = formatter.format_public_locked(
        replace(ticket, publication_decision=ComboTicketStatus.LOCKED),
        locked_at=datetime(2026, 6, 11, 17, 40, tzinfo=UTC),
    )
    no_bet = formatter.format_no_bet(reason="risk_too_high", ticket=ticket)

    assert "COMBINÉ CDM — WATCHLIST STAFF" in watchlist
    assert "COMBINÉ CDM — VERROUILLÉ" in public
    assert "Aucun combiné CDM publiable" in no_bet
    assert "pas une certitude" in public


def test_worldcup_combo_publication_is_idempotent(tmp_path: Path) -> None:
    engine = _init_full_db(tmp_path)
    config = _enabled_config()
    ticket = _ticket_candidate(
        legs=(
            _leg_candidate(fixture_id=-3701),
            _leg_candidate(fixture_id=-3702),
        )
    )

    with session_scope(create_session_factory(engine)) as session:
        delivery = DiscordDeliveryService(session)
        service = WorldCupComboPublicationService(
            session,
            config,
            delivery_service=delivery,
        )
        first = service.publish_watchlist_staff(ticket, dry_run=True, execute=False)
        second = service.publish_watchlist_staff(ticket, dry_run=True, execute=False)

    assert first.status == "dry_run"
    assert second.status == "duplicate_skipped"


def test_worldcup_combo_publication_dry_run_does_not_block_execute(
    tmp_path: Path,
) -> None:
    engine = _init_full_db(tmp_path)
    config = _enabled_config()
    ticket = _ticket_candidate(
        legs=(
            _leg_candidate(fixture_id=-3711),
            _leg_candidate(fixture_id=-3712),
        )
    )

    with session_scope(create_session_factory(engine)) as session:
        dry_run_service = WorldCupComboPublicationService(
            session,
            config,
            delivery_service=DiscordDeliveryService(session),
        )
        dry_run = dry_run_service.publish_watchlist_staff(
            ticket,
            dry_run=True,
            execute=False,
        )
        execute_service = WorldCupComboPublicationService(session, config)
        execute = execute_service.publish_watchlist_staff(
            ticket,
            dry_run=False,
            execute=True,
        )

    assert dry_run.status == "dry_run"
    assert execute.status == "skipped"
    assert execute.reason == "no_delivery_service"


def test_worldcup_combo_locked_public_capable_ticket_still_publishes_to_staff(
    tmp_path: Path,
) -> None:
    engine = _init_full_db(tmp_path)
    config = _enabled_config(staff_only_shadow_mode=False)
    ticket = replace(
        _ticket_candidate(
            legs=(
                _leg_candidate(fixture_id=-3721),
                _leg_candidate(fixture_id=-3722),
            )
        ),
        publication_decision=ComboTicketStatus.LOCKED,
    )

    with session_scope(create_session_factory(engine)) as session:
        service = WorldCupComboPublicationService(
            session,
            config,
            delivery_service=DiscordDeliveryService(session),
        )
        result = service.publish_locked(
            ticket,
            locked_at=datetime(2026, 6, 11, 17, 40, tzinfo=UTC),
            dry_run=True,
            execute=False,
        )

    assert result.status == "dry_run"
    assert result.channel_key == "predictions_staff"
    assert result.message_type == "worldcup_combo_staff"


def test_worldcup_combo_run_service_dry_run_does_not_persist(tmp_path: Path) -> None:
    engine = _init_full_db(tmp_path)
    config = _enabled_config()
    target_date = date(2026, 6, 11)
    with session_scope(create_session_factory(engine)) as session:
        _seed_combo_run_sources(session)
        summary = WorldCupComboRunService(session, config).run(
            target_date=target_date,
            execute=False,
            captured_at=datetime(2026, 6, 11, 12, tzinfo=UTC),
        )

    assert summary.enabled is True
    assert summary.sessions == 1
    assert summary.candidate_legs >= 2
    assert summary.tickets >= 1
    assert summary.persisted_tickets == 0
    assert summary.generated_at == datetime(2026, 6, 11, 12, tzinfo=UTC)
    assert summary.session_summaries[0].data_cutoff_time == datetime(
        2026,
        6,
        11,
        12,
        tzinfo=UTC,
    )
    assert _count_rows(engine, "combo_tickets") == 0
    assert _count_rows(engine, "combo_ticket_snapshots") == 0


def test_worldcup_combo_run_service_execute_persists_tickets_and_snapshots(
    tmp_path: Path,
) -> None:
    engine = _init_full_db(tmp_path)
    config = _enabled_config()
    target_date = date(2026, 6, 11)
    with session_scope(create_session_factory(engine)) as session:
        _seed_combo_run_sources(session)
        summary = WorldCupComboRunService(session, config).run(
            target_date=target_date,
            execute=True,
            captured_at=datetime(2026, 6, 11, 12, tzinfo=UTC),
        )

    assert summary.enabled is True
    assert summary.persisted_tickets == summary.tickets
    assert _count_rows(engine, "combo_tickets") == summary.tickets
    assert _count_rows(engine, "combo_ticket_snapshots") == summary.tickets * 3


def test_worldcup_combo_settlement_won_and_lost(tmp_path: Path) -> None:
    engine = _init_full_db(tmp_path)
    session_factory = create_session_factory(engine)
    won_ticket = _ticket_candidate(
        legs=(
            _leg_candidate(fixture_id=-3801, market_type=ComboMarketType.HOME),
            _leg_candidate(fixture_id=-3802, market_type=ComboMarketType.OVER_25),
        )
    )
    lost_ticket = replace(
        _ticket_candidate(
            legs=(
                _leg_candidate(fixture_id=-3803, market_type=ComboMarketType.HOME),
                _leg_candidate(fixture_id=-3804, market_type=ComboMarketType.UNDER_25),
            )
        ),
        ticket_key="synthetic-lost-ticket",
    )

    with session_scope(session_factory) as session:
        _seed_finished_fixture(session, fixture_id=-3801, home_goals=2, away_goals=0)
        _seed_finished_fixture(session, fixture_id=-3802, home_goals=2, away_goals=1)
        _seed_finished_fixture(session, fixture_id=-3803, home_goals=0, away_goals=1)
        _seed_finished_fixture(session, fixture_id=-3804, home_goals=2, away_goals=2)
        won_record = persist_combo_ticket_candidate(session, won_ticket)
        lost_record = persist_combo_ticket_candidate(session, lost_ticket)
        service = WorldCupComboSettlementService(session)
        won = service.settle_record(
            won_record,
            settled_at=datetime(2026, 6, 12, 0, tzinfo=UTC),
            execute=True,
        )
        lost = service.settle_record(
            lost_record,
            settled_at=datetime(2026, 6, 12, 0, tzinfo=UTC),
            execute=True,
        )

    assert won.status == "WON"
    assert won.profit_unit > 0
    assert lost.status == "LOST"
    assert lost.profit_unit == -1.0


def test_worldcup_combo_services_disabled_noop(tmp_path: Path) -> None:
    engine = _init_full_db(tmp_path)
    config = WorldCupComboConfig(enabled=False)
    ticket = _ticket_candidate(
        legs=(
            _leg_candidate(fixture_id=-3901),
            _leg_candidate(fixture_id=-3902),
        )
    )

    with session_scope(create_session_factory(engine)) as session:
        service = WorldCupComboPublicationService(session, config)
        result = service.publish_watchlist_staff(ticket, dry_run=True, execute=False)

    assert result.status == "skipped"
    assert result.reason == "feature_disabled"


def _leg_candidate(
    *,
    fixture_id: int = -101,
    market_type: ComboMarketType = ComboMarketType.HOME,
    market_scope: ComboMarketScope = ComboMarketScope.NINETY_MIN,
    selection: str = "Synthetic Home",
    decimal_odd: float = 2.1,
    model_probability: float = 0.52,
    market_probability: float = 0.47,
    edge: float = 0.05,
    ev: float = 0.092,
    confidence_score: float = 78.0,
    confidence_label: str = "High",
    data_quality_score: float = 84.0,
    lineup_status: str = "available",
    freshness_score: float | None = 100.0,
    warnings: list[str] | None = None,
) -> ComboLegCandidate:
    kickoff = datetime(2026, 6, 11, 18, tzinfo=UTC)
    return ComboLegCandidate(
        fixture_id=fixture_id,
        kickoff_at_utc=kickoff,
        kickoff_at_paris=kickoff + timedelta(hours=2),
        market_type=market_type,
        market_scope=market_scope,
        selection=selection,
        decimal_odd=decimal_odd,
        model_probability=model_probability,
        market_probability=market_probability,
        edge=edge,
        ev=ev,
        confidence_score=confidence_score,
        confidence_label=confidence_label,
        data_quality_score=data_quality_score,
        odds_snapshot_id=-201,
        prediction_snapshot_id=-301,
        lineup_status=lineup_status,
        odds_last_update=kickoff - timedelta(minutes=45),
        prediction_generated_at=kickoff - timedelta(minutes=40),
        freshness_score=freshness_score,
        warnings=warnings if warnings is not None else ["synthetic-warning"],
    )


def _ticket_candidate(legs: tuple[ComboLegCandidate, ...]) -> ComboTicketCandidate:
    first_kickoff = datetime(2026, 6, 11, 18, tzinfo=UTC)
    scoring = WorldCupComboScoring().score(legs)
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
        combined_decimal_odds=scoring.combined_decimal_odds,
        combined_probability_raw=scoring.combined_probability_raw,
        combined_probability_adjusted=scoring.combined_probability_adjusted,
        combined_fair_odds=scoring.combined_fair_odds,
        combined_ev_raw=scoring.combined_ev_raw,
        combined_ev_adjusted=scoring.combined_ev_adjusted,
        combined_confidence_score=scoring.combined_confidence_score,
        combined_confidence_label=scoring.combined_confidence_label,
        post_lock_risk_score=scoring.post_lock_risk_score,
        freshness_score=scoring.freshness_score,
        lineup_risk_score=scoring.lineup_risk_score,
        publication_decision=ComboTicketStatus.DRAFT,
        no_publish_reason=None,
        legs=legs,
        warnings=["ticket-warning", *scoring.warnings],
    )


def _count_rows(engine, table_name: str) -> int:
    with engine.connect() as connection:
        return int(connection.exec_driver_sql(f"select count(*) from {table_name}").scalar_one())


def _combo_session(
    fixture_ids: tuple[int, ...],
    *,
    is_matchday3: bool = False,
    is_knockout: bool = False,
) -> WorldCupComboSession:
    first_kickoff = datetime(2026, 6, 11, 18, tzinfo=UTC)
    fixtures = tuple(
        WorldCupComboFixtureRef(
            fixture_id=fixture_id,
            kickoff_at_utc=first_kickoff + timedelta(hours=index),
            kickoff_at_paris=first_kickoff + timedelta(hours=index + 2),
            home_team=f"Synthetic Home {index}",
            away_team=f"Synthetic Away {index}",
            status_short="NS",
            round_name=_synthetic_round_name(index, is_matchday3, is_knockout),
            league_id=1,
            season=2026,
            competition_key="fifa_world_cup_2026",
        )
        for index, fixture_id in enumerate(fixture_ids)
    )
    return WorldCupComboSession(
        session_key="synthetic-session-builder",
        combo_date_paris=date(2026, 6, 11),
        first_kickoff_at=fixtures[0].kickoff_at_utc,
        last_kickoff_at=fixtures[-1].kickoff_at_utc,
        fixtures=fixtures,
        stage="KNOCKOUT" if is_knockout else "GROUP",
        group_matchday=3 if is_matchday3 else 1,
        is_matchday3=is_matchday3,
        is_knockout=is_knockout,
        lock_time=first_kickoff - timedelta(minutes=20),
    )


def _synthetic_round_name(index: int, is_matchday3: bool, is_knockout: bool) -> str:
    if is_knockout:
        return "Quarter-finals"
    group = chr(ord("A") + index)
    return f"Group {group} - {3 if is_matchday3 else 1}"


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
    *,
    now: datetime | None = None,
) -> ComboLegSelectionResult:
    with session_scope(create_session_factory(engine)) as session:
        sessions = WorldCupComboSessionService(session, config).build_sessions(
            target_date=target_date
        )
        current_time = now or datetime(2026, 6, 11, 17, 35, tzinfo=UTC)
        return WorldCupComboLegSelector(session, config).select_candidates(
            sessions,
            now=current_time,
        )


def _build_ticket_from_db(
    session,
    config: WorldCupComboConfig,
    *,
    target_date: date,
    now: datetime,
    fixture_ids: tuple[int, ...],
) -> ComboTicketCandidate:
    sessions = WorldCupComboSessionService(session, config).build_sessions(
        target_date=target_date
    )
    combo_session = next(
        item
        for item in sessions
        if set(fixture_ids).issubset({fixture.fixture_id for fixture in item.fixtures})
    )
    selection = WorldCupComboLegSelector(session, config).select_candidates(
        (combo_session,),
        now=now,
    )
    selected_legs = tuple(
        candidate
        for candidate in selection.candidates
        if candidate.fixture_id in set(fixture_ids)
        and candidate.market_type == ComboMarketType.HOME
    )
    tickets = WorldCupComboBuilder(config).build_for_session(combo_session, selected_legs)
    if not tickets:
        reasons = _reason_counts(selection)
        raise AssertionError(f"synthetic pre-lock ticket could not be built: {reasons}")
    ticket = next(
        (item for item in tickets if item.legs_count == min(len(fixture_ids), 3)),
        tickets[0],
    )
    return replace(ticket, ticket_key=f"synthetic-pre-lock:{'-'.join(map(str, fixture_ids))}")


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


def _seed_pre_lock_fixture_sources(
    session,
    *,
    fixture_ids: tuple[int, ...],
) -> None:
    first_kickoff = datetime(2026, 6, 11, 18, tzinfo=UTC)
    prediction_time = datetime(2026, 6, 11, 11, 45, tzinfo=UTC)
    odds_time = datetime(2026, 6, 11, 11, 50, tzinfo=UTC)
    for index, fixture_id in enumerate(fixture_ids):
        _seed_fixture(
            session,
            fixture_id=fixture_id,
            kickoff=first_kickoff + timedelta(minutes=30 * index),
            round_name="Group A - 1",
        )
        _seed_1x2_prediction(
            session,
            fixture_id=fixture_id,
            prediction_time=prediction_time,
            p_home=0.62,
            p_draw=0.20,
            p_away=0.18,
            predicted_result="HOME",
            confidence_score=82.0,
            data_quality_score=88.0,
        )
        _seed_1x2_odds(
            session,
            fixture_id=fixture_id,
            fetched_at=odds_time,
            odd_home=2.0,
            odd_draw=3.5,
            odd_away=4.0,
        )


def _seed_finished_fixture(
    session,
    *,
    fixture_id: int,
    home_goals: int,
    away_goals: int,
) -> None:
    kickoff = datetime(2026, 6, 11, 18, tzinfo=UTC)
    _ensure_synthetic_teams(session)
    session.add(
        db_models.Fixture(
            fixture_id=fixture_id,
            date=kickoff,
            timestamp=int(kickoff.timestamp()),
            timezone="UTC",
            round="Group Stage - 1",
            league_id=1,
            season=2026,
            status="Match Finished",
            status_long="Match Finished",
            status_short="FT",
            home_team_id=-1,
            away_team_id=-2,
            home_team="Synthetic Home",
            away_team="Synthetic Away",
            home_goals=home_goals,
            away_goals=away_goals,
            goals_home=home_goals,
            goals_away=away_goals,
            payload_json={"synthetic": True},
        )
    )


def _seed_combo_run_sources(session) -> None:
    first_kickoff = datetime(2026, 6, 11, 18, tzinfo=UTC)
    prediction_time = first_kickoff - timedelta(hours=7)
    odds_time = first_kickoff - timedelta(hours=7, minutes=5)
    for index, fixture_id in enumerate((-4101, -4102), start=1):
        kickoff = first_kickoff + timedelta(hours=index - 1)
        _seed_fixture(
            session,
            fixture_id=fixture_id,
            kickoff=kickoff,
            round_name=f"Group A - {index}",
        )
        _seed_1x2_prediction(
            session,
            fixture_id=fixture_id,
            prediction_time=prediction_time,
            p_home=0.62,
            p_draw=0.2,
            p_away=0.18,
            predicted_result="HOME",
            confidence_score=76.0,
            data_quality_score=82.0,
        )
        _seed_1x2_odds(
            session,
            fixture_id=fixture_id,
            fetched_at=odds_time,
            odd_home=2.05,
            odd_draw=3.5,
            odd_away=4.0,
        )
        session.flush()


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
    session.flush()


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
    session.flush()


def _seed_lineups(session, *, fixture_id: int, fetched_at: datetime) -> None:
    _ensure_synthetic_teams(session)
    for team_id in (-1, -2):
        session.add(
            db_models.FixtureLineup(
                fixture_id=fixture_id,
                team_id=team_id,
                coach_id=None,
                formation="4-3-3",
                fetched_at=fetched_at,
                start_xi_json=[],
                substitutes_json=[],
                players_json=[],
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
    session.flush()


def _reason_counts(result: ComboLegSelectionResult) -> Counter:
    return Counter(item.reason for item in result.no_candidates)
