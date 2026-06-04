"""Add World Cup combo ticket persistence tables."""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy import inspect

from alembic import op

revision = "0006_world_cup_combo_tables"
down_revision = "0005_ou_decision_v2"
branch_labels = None
depends_on = None

TICKETS = "combo_tickets"
LEGS = "combo_ticket_legs"
SNAPSHOTS = "combo_ticket_snapshots"


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    tables = set(inspector.get_table_names())

    if TICKETS not in tables:
        op.create_table(
            TICKETS,
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("ticket_key", sa.String(300), nullable=False),
            sa.Column("status", sa.String(32), nullable=False),
            sa.Column("competition_key", sa.String(80), nullable=False),
            sa.Column("league_id", sa.Integer(), nullable=False),
            sa.Column("season", sa.Integer(), nullable=False),
            sa.Column("combo_date", sa.Date(), nullable=False),
            sa.Column("session_key", sa.String(240), nullable=False),
            sa.Column("first_kickoff_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("last_kickoff_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("lock_time", sa.DateTime(timezone=True), nullable=False),
            sa.Column("legs_count", sa.Integer(), nullable=False),
            sa.Column("combined_decimal_odds", sa.Float(), nullable=False),
            sa.Column("combined_probability_raw", sa.Float(), nullable=False),
            sa.Column("combined_probability_adjusted", sa.Float(), nullable=False),
            sa.Column("combined_fair_odds", sa.Float(), nullable=False),
            sa.Column("combined_ev_raw", sa.Float(), nullable=False),
            sa.Column("combined_ev_adjusted", sa.Float(), nullable=False),
            sa.Column("combined_confidence_score", sa.Float(), nullable=False),
            sa.Column("combined_confidence_label", sa.String(32), nullable=False),
            sa.Column("post_lock_risk_score", sa.Float(), nullable=False),
            sa.Column("freshness_score", sa.Float(), nullable=False),
            sa.Column("lineup_risk_score", sa.Float(), nullable=False),
            sa.Column("publication_decision", sa.String(32), nullable=False),
            sa.Column("no_publish_reason", sa.String(160), nullable=True),
            sa.Column("model_versions_json", sa.JSON(), nullable=True),
            sa.Column("warnings_json", sa.JSON(), nullable=True),
            sa.Column("payload_json", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
            sa.UniqueConstraint("ticket_key", name="uq_combo_ticket_key"),
        )
    else:
        _add_missing_columns(inspector, TICKETS, _ticket_columns())

    inspector = inspect(bind)
    tables = set(inspector.get_table_names())
    if LEGS not in tables:
        op.create_table(
            LEGS,
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("ticket_id", sa.Integer(), sa.ForeignKey(f"{TICKETS}.id"), nullable=False),
            sa.Column(
                "fixture_id",
                sa.Integer(),
                sa.ForeignKey("fixtures.fixture_id"),
                nullable=False,
            ),
            sa.Column("leg_order", sa.Integer(), nullable=False),
            sa.Column("kickoff_at_utc", sa.DateTime(timezone=True), nullable=False),
            sa.Column("market_type", sa.String(32), nullable=False),
            sa.Column("market_scope", sa.String(32), nullable=False),
            sa.Column("selection", sa.String(120), nullable=False),
            sa.Column("decimal_odd", sa.Float(), nullable=False),
            sa.Column("model_probability", sa.Float(), nullable=False),
            sa.Column("market_probability", sa.Float(), nullable=False),
            sa.Column("edge", sa.Float(), nullable=False),
            sa.Column("ev", sa.Float(), nullable=False),
            sa.Column("confidence_score", sa.Float(), nullable=False),
            sa.Column("confidence_label", sa.String(32), nullable=False),
            sa.Column("data_quality_score", sa.Float(), nullable=False),
            sa.Column("odds_snapshot_id", sa.Integer(), nullable=True),
            sa.Column("prediction_snapshot_id", sa.Integer(), nullable=True),
            sa.Column("lineup_status", sa.String(32), nullable=False),
            sa.Column("odds_last_update", sa.DateTime(timezone=True), nullable=True),
            sa.Column("prediction_generated_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("model_versions_json", sa.JSON(), nullable=True),
            sa.Column("warnings_json", sa.JSON(), nullable=True),
            sa.Column("payload_json", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
            sa.UniqueConstraint("ticket_id", "leg_order", name="uq_combo_ticket_leg_order"),
        )
    else:
        _add_missing_columns(inspector, LEGS, _leg_columns())

    inspector = inspect(bind)
    tables = set(inspector.get_table_names())
    if SNAPSHOTS not in tables:
        op.create_table(
            SNAPSHOTS,
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("ticket_id", sa.Integer(), sa.ForeignKey(f"{TICKETS}.id"), nullable=True),
            sa.Column("ticket_key", sa.String(300), nullable=False),
            sa.Column("status", sa.String(32), nullable=False),
            sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("snapshot_json", sa.JSON(), nullable=True),
            sa.Column("model_versions_json", sa.JSON(), nullable=True),
            sa.Column("warnings_json", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        )
    else:
        _add_missing_columns(inspector, SNAPSHOTS, _snapshot_columns())

    _create_index(TICKETS, "ix_combo_ticket_date_status", ["combo_date", "status"])
    _create_index(TICKETS, "ix_combo_ticket_session", ["session_key"])
    _create_index(LEGS, "ix_combo_ticket_leg_ticket", ["ticket_id"])
    _create_index(LEGS, "ix_combo_ticket_leg_fixture", ["fixture_id"])
    _create_index(SNAPSHOTS, "ix_combo_ticket_snapshot_ticket", ["ticket_id"])
    _create_index(SNAPSHOTS, "ix_combo_ticket_snapshot_key", ["ticket_key"])


def downgrade() -> None:
    bind = op.get_bind()
    tables = set(inspect(bind).get_table_names())
    for table in (SNAPSHOTS, LEGS, TICKETS):
        if table in tables:
            op.drop_table(table)


def _ticket_columns() -> dict[str, sa.Column]:
    return {
        "ticket_key": sa.Column("ticket_key", sa.String(300), nullable=False),
        "status": sa.Column("status", sa.String(32), nullable=False),
        "competition_key": sa.Column("competition_key", sa.String(80), nullable=False),
        "league_id": sa.Column("league_id", sa.Integer(), nullable=False),
        "season": sa.Column("season", sa.Integer(), nullable=False),
        "combo_date": sa.Column("combo_date", sa.Date(), nullable=False),
        "session_key": sa.Column("session_key", sa.String(240), nullable=False),
        "first_kickoff_at": sa.Column(
            "first_kickoff_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        "last_kickoff_at": sa.Column(
            "last_kickoff_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        "lock_time": sa.Column("lock_time", sa.DateTime(timezone=True), nullable=False),
        "legs_count": sa.Column("legs_count", sa.Integer(), nullable=False),
        "combined_decimal_odds": sa.Column("combined_decimal_odds", sa.Float(), nullable=False),
        "combined_probability_raw": sa.Column(
            "combined_probability_raw",
            sa.Float(),
            nullable=False,
        ),
        "combined_probability_adjusted": sa.Column(
            "combined_probability_adjusted",
            sa.Float(),
            nullable=False,
        ),
        "combined_fair_odds": sa.Column("combined_fair_odds", sa.Float(), nullable=False),
        "combined_ev_raw": sa.Column("combined_ev_raw", sa.Float(), nullable=False),
        "combined_ev_adjusted": sa.Column("combined_ev_adjusted", sa.Float(), nullable=False),
        "combined_confidence_score": sa.Column(
            "combined_confidence_score",
            sa.Float(),
            nullable=False,
        ),
        "combined_confidence_label": sa.Column(
            "combined_confidence_label",
            sa.String(32),
            nullable=False,
        ),
        "post_lock_risk_score": sa.Column("post_lock_risk_score", sa.Float(), nullable=False),
        "freshness_score": sa.Column("freshness_score", sa.Float(), nullable=False),
        "lineup_risk_score": sa.Column("lineup_risk_score", sa.Float(), nullable=False),
        "publication_decision": sa.Column("publication_decision", sa.String(32), nullable=False),
        "no_publish_reason": sa.Column("no_publish_reason", sa.String(160), nullable=True),
        "model_versions_json": sa.Column("model_versions_json", sa.JSON(), nullable=True),
        "warnings_json": sa.Column("warnings_json", sa.JSON(), nullable=True),
        "payload_json": sa.Column("payload_json", sa.JSON(), nullable=True),
    }


def _leg_columns() -> dict[str, sa.Column]:
    return {
        "ticket_id": sa.Column("ticket_id", sa.Integer(), nullable=False),
        "fixture_id": sa.Column("fixture_id", sa.Integer(), nullable=False),
        "leg_order": sa.Column("leg_order", sa.Integer(), nullable=False),
        "kickoff_at_utc": sa.Column("kickoff_at_utc", sa.DateTime(timezone=True), nullable=False),
        "market_type": sa.Column("market_type", sa.String(32), nullable=False),
        "market_scope": sa.Column("market_scope", sa.String(32), nullable=False),
        "selection": sa.Column("selection", sa.String(120), nullable=False),
        "decimal_odd": sa.Column("decimal_odd", sa.Float(), nullable=False),
        "model_probability": sa.Column("model_probability", sa.Float(), nullable=False),
        "market_probability": sa.Column("market_probability", sa.Float(), nullable=False),
        "edge": sa.Column("edge", sa.Float(), nullable=False),
        "ev": sa.Column("ev", sa.Float(), nullable=False),
        "confidence_score": sa.Column("confidence_score", sa.Float(), nullable=False),
        "confidence_label": sa.Column("confidence_label", sa.String(32), nullable=False),
        "data_quality_score": sa.Column("data_quality_score", sa.Float(), nullable=False),
        "odds_snapshot_id": sa.Column("odds_snapshot_id", sa.Integer(), nullable=True),
        "prediction_snapshot_id": sa.Column("prediction_snapshot_id", sa.Integer(), nullable=True),
        "lineup_status": sa.Column("lineup_status", sa.String(32), nullable=False),
        "odds_last_update": sa.Column(
            "odds_last_update",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        "prediction_generated_at": sa.Column(
            "prediction_generated_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        "model_versions_json": sa.Column("model_versions_json", sa.JSON(), nullable=True),
        "warnings_json": sa.Column("warnings_json", sa.JSON(), nullable=True),
        "payload_json": sa.Column("payload_json", sa.JSON(), nullable=True),
    }


def _snapshot_columns() -> dict[str, sa.Column]:
    return {
        "ticket_id": sa.Column("ticket_id", sa.Integer(), nullable=True),
        "ticket_key": sa.Column("ticket_key", sa.String(300), nullable=False),
        "status": sa.Column("status", sa.String(32), nullable=False),
        "captured_at": sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False),
        "snapshot_json": sa.Column("snapshot_json", sa.JSON(), nullable=True),
        "model_versions_json": sa.Column("model_versions_json", sa.JSON(), nullable=True),
        "warnings_json": sa.Column("warnings_json", sa.JSON(), nullable=True),
    }


def _add_missing_columns(
    inspector: sa.Inspector,
    table_name: str,
    columns: dict[str, sa.Column],
) -> None:
    existing = {column["name"] for column in inspector.get_columns(table_name)}
    for name, column in columns.items():
        if name not in existing:
            op.add_column(table_name, column)


def _create_index(table_name: str, index_name: str, columns: list[str]) -> None:
    inspector = inspect(op.get_bind())
    existing = {index["name"] for index in inspector.get_indexes(table_name)}
    if index_name not in existing:
        op.create_index(index_name, table_name, columns)
