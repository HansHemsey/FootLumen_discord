"""Add O/U model tables."""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy import inspect

from alembic import op

revision = "0003_ou_model_tables"
down_revision = "0002_discord_routing"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    existing_tables = set(inspector.get_table_names())

    if "ou_feature_snapshots" not in existing_tables:
        op.create_table(
            "ou_feature_snapshots",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("fixture_id", sa.Integer(), sa.ForeignKey("fixtures.fixture_id"), nullable=False),
            sa.Column("prediction_time", sa.DateTime(timezone=True), nullable=False),
            sa.Column("feature_version", sa.String(64), nullable=False),
            sa.Column("threshold", sa.Float(), nullable=False, server_default="2.5"),
            sa.Column("features_json", sa.JSON(), nullable=True),
            sa.Column("data_quality_json", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
            sa.UniqueConstraint(
                "fixture_id", "prediction_time", "feature_version", "threshold",
                name="uq_ou_feature_snapshot",
            ),
        )
        op.create_index(
            "ix_ou_feature_snapshot_fixture_time",
            "ou_feature_snapshots",
            ["fixture_id", "prediction_time"],
        )
        op.create_index(
            "ix_ou_feature_snapshots_fixture_id",
            "ou_feature_snapshots",
            ["fixture_id"],
        )
        op.create_index(
            "ix_ou_feature_snapshots_prediction_time",
            "ou_feature_snapshots",
            ["prediction_time"],
        )

    if "ou_model_predictions" not in existing_tables:
        op.create_table(
            "ou_model_predictions",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("fixture_id", sa.Integer(), sa.ForeignKey("fixtures.fixture_id"), nullable=False),
            sa.Column(
                "ou_feature_snapshot_id",
                sa.Integer(),
                sa.ForeignKey("ou_feature_snapshots.id"),
                nullable=False,
            ),
            sa.Column("prediction_time", sa.DateTime(timezone=True), nullable=False),
            sa.Column("model_version", sa.String(64), nullable=False),
            sa.Column("threshold", sa.Float(), nullable=False, server_default="2.5"),
            sa.Column("p_over", sa.Float(), nullable=False),
            sa.Column("p_under", sa.Float(), nullable=False),
            sa.Column("xg_home", sa.Float(), nullable=True),
            sa.Column("xg_away", sa.Float(), nullable=True),
            sa.Column("xg_total", sa.Float(), nullable=True),
            sa.Column("market_p_over", sa.Float(), nullable=True),
            sa.Column("market_p_under", sa.Float(), nullable=True),
            sa.Column("edge_over", sa.Float(), nullable=True),
            sa.Column("edge_under", sa.Float(), nullable=True),
            sa.Column("ev_over", sa.Float(), nullable=True),
            sa.Column("ev_under", sa.Float(), nullable=True),
            sa.Column("market_odd_over", sa.Float(), nullable=True),
            sa.Column("market_odd_under", sa.Float(), nullable=True),
            sa.Column("confidence_score", sa.Float(), nullable=True),
            sa.Column("confidence_label", sa.String(32), nullable=True),
            sa.Column("expert_probabilities_json", sa.JSON(), nullable=True),
            sa.Column("data_quality_json", sa.JSON(), nullable=True),
            sa.Column("payload_json", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        )
        op.create_index(
            "ix_ou_prediction_fixture_time",
            "ou_model_predictions",
            ["fixture_id", "prediction_time"],
        )
        op.create_index(
            "ix_ou_prediction_model_version",
            "ou_model_predictions",
            ["model_version"],
        )
        op.create_index(
            "ix_ou_model_predictions_fixture_id",
            "ou_model_predictions",
            ["fixture_id"],
        )
        op.create_index(
            "ix_ou_model_predictions_prediction_time",
            "ou_model_predictions",
            ["prediction_time"],
        )
        op.create_index(
            "ix_ou_model_predictions_ou_feature_snapshot_id",
            "ou_model_predictions",
            ["ou_feature_snapshot_id"],
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    existing_tables = set(inspector.get_table_names())

    if "ou_model_predictions" in existing_tables:
        for idx in (
            "ix_ou_model_predictions_ou_feature_snapshot_id",
            "ix_ou_model_predictions_prediction_time",
            "ix_ou_model_predictions_fixture_id",
            "ix_ou_prediction_model_version",
            "ix_ou_prediction_fixture_time",
        ):
            existing_indexes = {i["name"] for i in inspector.get_indexes("ou_model_predictions")}
            if idx in existing_indexes:
                op.drop_index(idx, table_name="ou_model_predictions")
        op.drop_table("ou_model_predictions")

    if "ou_feature_snapshots" in existing_tables:
        for idx in (
            "ix_ou_feature_snapshots_prediction_time",
            "ix_ou_feature_snapshots_fixture_id",
            "ix_ou_feature_snapshot_fixture_time",
        ):
            existing_indexes = {i["name"] for i in inspector.get_indexes("ou_feature_snapshots")}
            if idx in existing_indexes:
                op.drop_index(idx, table_name="ou_feature_snapshots")
        op.drop_table("ou_feature_snapshots")
