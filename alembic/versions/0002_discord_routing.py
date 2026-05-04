"""Add Discord routing fields."""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy import inspect

from alembic import op

revision = "0002_discord_routing"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("discord_messages")}
    additions = {
        "competition_key": sa.Column("competition_key", sa.String(length=80), nullable=True),
        "league_id": sa.Column("league_id", sa.Integer(), nullable=True),
        "season": sa.Column("season", sa.Integer(), nullable=True),
        "channel_key": sa.Column("channel_key", sa.String(length=80), nullable=True),
        "message_type": sa.Column("message_type", sa.String(length=80), nullable=True),
        "dry_run": sa.Column("dry_run", sa.Boolean(), nullable=False, server_default=sa.false()),
        "print_only": sa.Column(
            "print_only", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        "route_json": sa.Column("route_json", sa.JSON(), nullable=True),
        "payload_json": sa.Column("payload_json", sa.JSON(), nullable=True),
    }
    for name, column in additions.items():
        if name not in columns:
            op.add_column("discord_messages", column)

    for name, column_names in {
        "ix_discord_messages_competition_key": ["competition_key"],
        "ix_discord_messages_league_id": ["league_id"],
        "ix_discord_messages_season": ["season"],
        "ix_discord_messages_channel_key": ["channel_key"],
        "ix_discord_messages_message_type": ["message_type"],
    }.items():
        if name not in {index["name"] for index in inspector.get_indexes("discord_messages")}:
            op.create_index(name, "discord_messages", column_names)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    indexes = {index["name"] for index in inspector.get_indexes("discord_messages")}
    for name in (
        "ix_discord_messages_message_type",
        "ix_discord_messages_channel_key",
        "ix_discord_messages_season",
        "ix_discord_messages_league_id",
        "ix_discord_messages_competition_key",
    ):
        if name in indexes:
            op.drop_index(name, table_name="discord_messages")

    columns = {column["name"] for column in inspector.get_columns("discord_messages")}
    for name in (
        "route_json",
        "payload_json",
        "print_only",
        "dry_run",
        "message_type",
        "channel_key",
        "season",
        "league_id",
        "competition_key",
    ):
        if name in columns:
            op.drop_column("discord_messages", name)
