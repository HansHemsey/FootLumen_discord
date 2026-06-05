"""Harden World Cup combo persistence indexes and Discord idempotency."""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy import inspect

from alembic import op

revision = "0007_combo_persistence_hardening"
down_revision = "0006_world_cup_combo_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    tables = set(inspector.get_table_names())

    if "discord_messages" in tables:
        columns = {column["name"] for column in inspector.get_columns("discord_messages")}
        if "idempotency_key" not in columns:
            op.add_column(
                "discord_messages",
                sa.Column("idempotency_key", sa.String(length=512), nullable=True),
            )
        _create_index(
            "discord_messages",
            "ix_discord_messages_idempotency_key",
            ["idempotency_key"],
        )
        _create_index(
            "discord_messages",
            "ix_discord_messages_type_created",
            ["message_type", "created_at"],
        )

    if "combo_tickets" in tables:
        _create_index(
            "combo_tickets",
            "ix_combo_tickets_status_combo_date",
            ["status", "combo_date"],
        )
        _create_index("combo_tickets", "ix_combo_tickets_ticket_key", ["ticket_key"])

    if "combo_ticket_legs" in tables:
        _create_index(
            "combo_ticket_legs",
            "ix_combo_ticket_legs_combo_ticket_id",
            ["ticket_id"],
        )

    if "combo_ticket_snapshots" in tables:
        _create_index(
            "combo_ticket_snapshots",
            "ix_combo_ticket_snapshots_ticket_status_time",
            ["ticket_id", "status", "captured_at"],
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    tables = set(inspector.get_table_names())

    if "combo_ticket_snapshots" in tables:
        _drop_index(
            "combo_ticket_snapshots",
            "ix_combo_ticket_snapshots_ticket_status_time",
        )
    if "combo_ticket_legs" in tables:
        _drop_index("combo_ticket_legs", "ix_combo_ticket_legs_combo_ticket_id")
    if "combo_tickets" in tables:
        _drop_index("combo_tickets", "ix_combo_tickets_ticket_key")
        _drop_index("combo_tickets", "ix_combo_tickets_status_combo_date")
    if "discord_messages" in tables:
        _drop_index("discord_messages", "ix_discord_messages_type_created")
        _drop_index("discord_messages", "ix_discord_messages_idempotency_key")
        columns = {column["name"] for column in inspector.get_columns("discord_messages")}
        if "idempotency_key" in columns:
            op.drop_column("discord_messages", "idempotency_key")


def _create_index(table_name: str, index_name: str, columns: list[str]) -> None:
    inspector = inspect(op.get_bind())
    existing = {index["name"] for index in inspector.get_indexes(table_name)}
    if index_name not in existing:
        op.create_index(index_name, table_name, columns)


def _drop_index(table_name: str, index_name: str) -> None:
    inspector = inspect(op.get_bind())
    existing = {index["name"] for index in inspector.get_indexes(table_name)}
    if index_name in existing:
        op.drop_index(index_name, table_name=table_name)
