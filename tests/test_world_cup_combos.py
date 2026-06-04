from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from pathlib import Path

from sqlalchemy import inspect

from football_predictor.db.session import create_db_engine, create_session_factory, session_scope
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
    ComboTicketCandidate,
    ComboTicketSnapshot,
)
from football_predictor.world_cup_combos.persistence import (
    ensure_combo_tables,
    persist_combo_ticket_candidate,
    persist_combo_ticket_snapshot,
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
