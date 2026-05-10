"""Add V3 multi-model tables (Draw Risk + No-Draw Winner + Stacker)."""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy import inspect

from alembic import op

revision = "0004_v3_model_tables"
down_revision = "0003_ou_model_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    existing_tables = set(inspector.get_table_names())

    if "v3_feature_snapshots" not in existing_tables:
        op.create_table(
            "v3_feature_snapshots",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column(
                "fixture_id",
                sa.Integer(),
                sa.ForeignKey("fixtures.fixture_id"),
                nullable=False,
            ),
            sa.Column("prediction_time", sa.DateTime(timezone=True), nullable=False),
            sa.Column("feature_version", sa.String(64), nullable=False),
            sa.Column(
                "official_lineup_available_flag",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            ),
            sa.Column("features_json", sa.JSON(), nullable=True),
            sa.Column("data_quality_json", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
            sa.UniqueConstraint(
                "fixture_id",
                "prediction_time",
                "feature_version",
                name="uq_v3_feature_snapshot",
            ),
        )
        op.create_index(
            "ix_v3_feature_snapshot_fixture_time",
            "v3_feature_snapshots",
            ["fixture_id", "prediction_time"],
        )
        op.create_index(
            "ix_v3_feature_snapshots_fixture_id",
            "v3_feature_snapshots",
            ["fixture_id"],
        )
        op.create_index(
            "ix_v3_feature_snapshots_prediction_time",
            "v3_feature_snapshots",
            ["prediction_time"],
        )

    if "v3_model_predictions" not in existing_tables:
        op.create_table(
            "v3_model_predictions",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column(
                "fixture_id",
                sa.Integer(),
                sa.ForeignKey("fixtures.fixture_id"),
                nullable=False,
            ),
            sa.Column(
                "v3_feature_snapshot_id",
                sa.Integer(),
                sa.ForeignKey("v3_feature_snapshots.id"),
                nullable=False,
            ),
            sa.Column("prediction_time", sa.DateTime(timezone=True), nullable=False),
            sa.Column("model_version", sa.String(64), nullable=False),
            sa.Column("fusion_strategy", sa.String(32), nullable=False),
            sa.Column("p_v3_final_home", sa.Float(), nullable=False),
            sa.Column("p_v3_final_draw", sa.Float(), nullable=False),
            sa.Column("p_v3_final_away", sa.Float(), nullable=False),
            sa.Column("p_v3_draw_risk", sa.Float(), nullable=True),
            sa.Column("p_v3_home_no_draw", sa.Float(), nullable=True),
            sa.Column("p_v3_away_no_draw", sa.Float(), nullable=True),
            sa.Column("p_v2_home", sa.Float(), nullable=True),
            sa.Column("p_v2_draw", sa.Float(), nullable=True),
            sa.Column("p_v2_away", sa.Float(), nullable=True),
            sa.Column("p_market_home", sa.Float(), nullable=True),
            sa.Column("p_market_draw", sa.Float(), nullable=True),
            sa.Column("p_market_away", sa.Float(), nullable=True),
            sa.Column("p_api_home", sa.Float(), nullable=True),
            sa.Column("p_api_draw", sa.Float(), nullable=True),
            sa.Column("p_api_away", sa.Float(), nullable=True),
            sa.Column("data_quality_score", sa.Float(), nullable=True),
            sa.Column(
                "official_lineup_available_flag",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            ),
            sa.Column("confidence_score", sa.Float(), nullable=True),
            sa.Column("confidence_label", sa.String(32), nullable=True),
            sa.Column("predicted_result", sa.String(16), nullable=False),
            sa.Column("expert_probabilities_json", sa.JSON(), nullable=True),
            sa.Column("explanations_json", sa.JSON(), nullable=True),
            sa.Column("data_quality_json", sa.JSON(), nullable=True),
            sa.Column("payload_json", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        )
        op.create_index(
            "ix_v3_prediction_fixture_time",
            "v3_model_predictions",
            ["fixture_id", "prediction_time"],
        )
        op.create_index(
            "ix_v3_prediction_model_version",
            "v3_model_predictions",
            ["model_version"],
        )
        op.create_index(
            "ix_v3_model_predictions_fixture_id",
            "v3_model_predictions",
            ["fixture_id"],
        )
        op.create_index(
            "ix_v3_model_predictions_prediction_time",
            "v3_model_predictions",
            ["prediction_time"],
        )
        op.create_index(
            "ix_v3_model_predictions_v3_feature_snapshot_id",
            "v3_model_predictions",
            ["v3_feature_snapshot_id"],
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    existing_tables = set(inspector.get_table_names())

    if "v3_model_predictions" in existing_tables:
        for idx in (
            "ix_v3_model_predictions_v3_feature_snapshot_id",
            "ix_v3_model_predictions_prediction_time",
            "ix_v3_model_predictions_fixture_id",
            "ix_v3_prediction_model_version",
            "ix_v3_prediction_fixture_time",
        ):
            existing_indexes = {
                i["name"] for i in inspector.get_indexes("v3_model_predictions")
            }
            if idx in existing_indexes:
                op.drop_index(idx, table_name="v3_model_predictions")
        op.drop_table("v3_model_predictions")

    if "v3_feature_snapshots" in existing_tables:
        for idx in (
            "ix_v3_feature_snapshots_prediction_time",
            "ix_v3_feature_snapshots_fixture_id",
            "ix_v3_feature_snapshot_fixture_time",
        ):
            existing_indexes = {
                i["name"] for i in inspector.get_indexes("v3_feature_snapshots")
            }
            if idx in existing_indexes:
                op.drop_index(idx, table_name="v3_feature_snapshots")
        op.drop_table("v3_feature_snapshots")
