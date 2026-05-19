"""Add O/U decision v2 fields."""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy import inspect

from alembic import op

revision = "0005_ou_decision_v2"
down_revision = "0004_v3_model_tables"
branch_labels = None
depends_on = None

TABLE = "ou_model_predictions"


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if TABLE not in set(inspector.get_table_names()):
        return

    existing_columns = {column["name"] for column in inspector.get_columns(TABLE)}
    columns = [
        ("forecast_side", sa.Column("forecast_side", sa.String(16), nullable=True)),
        ("forecast_probability", sa.Column("forecast_probability", sa.Float(), nullable=True)),
        ("value_side", sa.Column("value_side", sa.String(16), nullable=True)),
        ("p_pick", sa.Column("p_pick", sa.Float(), nullable=True)),
        ("market_p_pick", sa.Column("market_p_pick", sa.Float(), nullable=True)),
        ("odd_pick", sa.Column("odd_pick", sa.Float(), nullable=True)),
        ("edge_pick", sa.Column("edge_pick", sa.Float(), nullable=True)),
        ("ev_pick", sa.Column("ev_pick", sa.Float(), nullable=True)),
        (
            "is_value_pick",
            sa.Column(
                "is_value_pick",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            ),
        ),
        ("no_bet_reason", sa.Column("no_bet_reason", sa.String(96), nullable=True)),
        ("confidence_score_v2", sa.Column("confidence_score_v2", sa.Float(), nullable=True)),
        ("confidence_label_v2", sa.Column("confidence_label_v2", sa.String(32), nullable=True)),
        ("publication_decision", sa.Column("publication_decision", sa.String(16), nullable=True)),
    ]
    for name, column in columns:
        if name not in existing_columns:
            op.add_column(TABLE, column)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if TABLE not in set(inspector.get_table_names()):
        return

    existing_columns = {column["name"] for column in inspector.get_columns(TABLE)}
    for name in (
        "publication_decision",
        "confidence_label_v2",
        "confidence_score_v2",
        "no_bet_reason",
        "is_value_pick",
        "ev_pick",
        "edge_pick",
        "odd_pick",
        "market_p_pick",
        "p_pick",
        "value_side",
        "forecast_probability",
        "forecast_side",
    ):
        if name in existing_columns:
            op.drop_column(TABLE, name)
