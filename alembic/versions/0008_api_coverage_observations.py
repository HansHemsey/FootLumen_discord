"""Add API coverage observation table."""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy import inspect

from alembic import op

revision = "0008_api_coverage_observations"
down_revision = "0007_combo_persistence_hardening"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    tables = set(inspector.get_table_names())

    if "api_coverage_observations" not in tables:
        op.create_table(
            "api_coverage_observations",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("competition_key", sa.String(length=80), nullable=False),
            sa.Column("league_id", sa.Integer(), nullable=False),
            sa.Column("season", sa.Integer(), nullable=False),
            sa.Column("endpoint", sa.String(length=128), nullable=False),
            sa.Column("fixture_id", sa.Integer(), nullable=True),
            sa.Column("team_id", sa.Integer(), nullable=True),
            sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("status", sa.String(length=32), nullable=False),
            sa.Column("result_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column(
                "useful_payload_flag",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            ),
            sa.Column("error_code", sa.String(length=80), nullable=True),
            sa.Column("warning", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        )

    _create_index("api_coverage_observations", "ix_api_coverage_observations_competition_key", ["competition_key"])
    _create_index("api_coverage_observations", "ix_api_coverage_observations_league_id", ["league_id"])
    _create_index("api_coverage_observations", "ix_api_coverage_observations_season", ["season"])
    _create_index("api_coverage_observations", "ix_api_coverage_observations_endpoint", ["endpoint"])
    _create_index("api_coverage_observations", "ix_api_coverage_observations_fixture_id", ["fixture_id"])
    _create_index("api_coverage_observations", "ix_api_coverage_observations_team_id", ["team_id"])
    _create_index("api_coverage_observations", "ix_api_coverage_observations_requested_at", ["requested_at"])
    _create_index("api_coverage_observations", "ix_api_coverage_observations_status", ["status"])
    _create_index(
        "api_coverage_observations",
        "ix_api_coverage_competition_endpoint",
        ["competition_key", "endpoint", "requested_at"],
    )
    _create_index(
        "api_coverage_observations",
        "ix_api_coverage_fixture_endpoint",
        ["fixture_id", "endpoint", "requested_at"],
    )
    _create_index(
        "api_coverage_observations",
        "ix_api_coverage_league_season_endpoint",
        ["league_id", "season", "endpoint"],
    )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    tables = set(inspector.get_table_names())
    if "api_coverage_observations" in tables:
        op.drop_table("api_coverage_observations")


def _create_index(table_name: str, index_name: str, columns: list[str]) -> None:
    inspector = inspect(op.get_bind())
    existing = {index["name"] for index in inspector.get_indexes(table_name)}
    if index_name not in existing:
        op.create_index(index_name, table_name, columns)
