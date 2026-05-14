"""Add direct Discord links to V3 and O/U predictions."""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy import inspect

from alembic import op

revision = "0005_discord_prediction_links"
down_revision = "0004_v3_model_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("discord_messages")}
    additions = {
        "v3_model_prediction_id": sa.Column(
            "v3_model_prediction_id",
            sa.Integer(),
            sa.ForeignKey("v3_model_predictions.id"),
            nullable=True,
        ),
        "ou_model_prediction_id": sa.Column(
            "ou_model_prediction_id",
            sa.Integer(),
            sa.ForeignKey("ou_model_predictions.id"),
            nullable=True,
        ),
        "dedupe_key": sa.Column("dedupe_key", sa.String(length=160), nullable=True),
    }
    for name, column in additions.items():
        if name not in columns:
            op.add_column("discord_messages", column)

    indexes = {index["name"] for index in inspector.get_indexes("discord_messages")}
    for name, column_names in {
        "ix_discord_messages_v3_model_prediction_id": ["v3_model_prediction_id"],
        "ix_discord_messages_ou_model_prediction_id": ["ou_model_prediction_id"],
        "ix_discord_messages_dedupe_key": ["dedupe_key"],
    }.items():
        if name not in indexes:
            op.create_index(name, "discord_messages", column_names)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    indexes = {index["name"] for index in inspector.get_indexes("discord_messages")}
    for name in (
        "ix_discord_messages_dedupe_key",
        "ix_discord_messages_ou_model_prediction_id",
        "ix_discord_messages_v3_model_prediction_id",
    ):
        if name in indexes:
            op.drop_index(name, table_name="discord_messages")

    columns = {column["name"] for column in inspector.get_columns("discord_messages")}
    names_to_drop = [
        name
        for name in ("dedupe_key", "ou_model_prediction_id", "v3_model_prediction_id")
        if name in columns
    ]
    if not names_to_drop:
        return
    if bind.dialect.name == "sqlite":
        with op.batch_alter_table("discord_messages") as batch_op:
            for name in names_to_drop:
                batch_op.drop_column(name)
        return
    for name in names_to_drop:
        op.drop_column("discord_messages", name)
