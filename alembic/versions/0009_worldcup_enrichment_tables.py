"""Add point-in-time World Cup enrichment tables."""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy import inspect

from alembic import op

revision = "0009_worldcup_enrichment_tables"
down_revision = "0008_api_coverage_observations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    tables = set(inspector.get_table_names())

    if "national_team_aliases" not in tables:
        op.create_table(
            "national_team_aliases",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("canonical_name", sa.String(length=180), nullable=False),
            sa.Column("normalized_alias", sa.String(length=180), nullable=False),
            sa.Column("source", sa.String(length=80), nullable=False, server_default="manual"),
            sa.Column("api_team_id", sa.Integer(), nullable=True),
            sa.Column("elo_code", sa.String(length=32), nullable=True),
            sa.Column("fifa_code", sa.String(length=32), nullable=True),
            sa.Column("valid_from", sa.Date(), nullable=True),
            sa.Column("valid_to", sa.Date(), nullable=True),
            sa.Column("confidence", sa.Float(), nullable=True),
            sa.Column("payload_json", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
            sa.UniqueConstraint(
                "normalized_alias",
                "source",
                name="uq_national_team_alias_source",
            ),
        )

    if "national_team_matches" not in tables:
        op.create_table(
            "national_team_matches",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("match_date", sa.Date(), nullable=False),
            sa.Column("home_team_canonical", sa.String(length=180), nullable=False),
            sa.Column("away_team_canonical", sa.String(length=180), nullable=False),
            sa.Column("home_team_id", sa.Integer(), nullable=True),
            sa.Column("away_team_id", sa.Integer(), nullable=True),
            sa.Column("home_score", sa.Integer(), nullable=False),
            sa.Column("away_score", sa.Integer(), nullable=False),
            sa.Column("tournament", sa.String(length=180), nullable=True),
            sa.Column("competition_type", sa.String(length=80), nullable=True),
            sa.Column("neutral", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("city", sa.String(length=160), nullable=True),
            sa.Column("country", sa.String(length=160), nullable=True),
            sa.Column("source", sa.String(length=80), nullable=False, server_default="csv"),
            sa.Column("source_match_id", sa.String(length=240), nullable=False),
            sa.Column("payload_json", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
            sa.UniqueConstraint("source", "source_match_id", name="uq_national_team_match_source"),
        )

    if "national_elo_snapshots" not in tables:
        op.create_table(
            "national_elo_snapshots",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("canonical_team", sa.String(length=180), nullable=False),
            sa.Column("elo_code", sa.String(length=32), nullable=True),
            sa.Column("snapshot_date", sa.Date(), nullable=False),
            sa.Column("rank", sa.Integer(), nullable=True),
            sa.Column("elo", sa.Float(), nullable=False),
            sa.Column("source", sa.String(length=80), nullable=False, server_default="computed"),
            sa.Column("payload_json", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
            sa.UniqueConstraint(
                "canonical_team",
                "snapshot_date",
                "source",
                name="uq_national_elo_snapshot",
            ),
        )

    if "fifa_ranking_snapshots" not in tables:
        op.create_table(
            "fifa_ranking_snapshots",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("canonical_team", sa.String(length=180), nullable=False),
            sa.Column("snapshot_date", sa.Date(), nullable=False),
            sa.Column("rank", sa.Integer(), nullable=True),
            sa.Column("points", sa.Float(), nullable=True),
            sa.Column("previous_points", sa.Float(), nullable=True),
            sa.Column("delta", sa.Float(), nullable=True),
            sa.Column("source", sa.String(length=80), nullable=False, server_default="fifa_csv"),
            sa.Column("payload_json", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
            sa.UniqueConstraint(
                "canonical_team",
                "snapshot_date",
                "source",
                name="uq_fifa_ranking_snapshot",
            ),
        )

    if "worldcup_group_state_snapshots" not in tables:
        op.create_table(
            "worldcup_group_state_snapshots",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("competition_key", sa.String(length=80), nullable=False),
            sa.Column("league_id", sa.Integer(), nullable=False),
            sa.Column("season", sa.Integer(), nullable=False),
            sa.Column("group_name", sa.String(length=80), nullable=False),
            sa.Column("team_id", sa.Integer(), nullable=False),
            sa.Column("canonical_team", sa.String(length=180), nullable=False),
            sa.Column("snapshot_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("matchday", sa.Integer(), nullable=True),
            sa.Column("played", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("points", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("goals_for", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("goals_against", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("goal_diff", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("remaining_fixtures_json", sa.JSON(), nullable=True),
            sa.Column("incentives_json", sa.JSON(), nullable=True),
            sa.Column("qualification_risk_json", sa.JSON(), nullable=True),
            sa.Column("payload_json", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
            sa.UniqueConstraint(
                "competition_key",
                "league_id",
                "season",
                "group_name",
                "team_id",
                "snapshot_at",
                name="uq_worldcup_group_state_snapshot",
            ),
        )

    if "squad_strength_features" not in tables:
        op.create_table(
            "squad_strength_features",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("competition_key", sa.String(length=80), nullable=False),
            sa.Column("league_id", sa.Integer(), nullable=False),
            sa.Column("season", sa.Integer(), nullable=False),
            sa.Column("team_id", sa.Integer(), nullable=False),
            sa.Column("canonical_team", sa.String(length=180), nullable=False),
            sa.Column("snapshot_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("squad_status", sa.String(length=40), nullable=False, server_default="unknown"),
            sa.Column("player_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("strength_score", sa.Float(), nullable=False, server_default="0"),
            sa.Column("club_level_score", sa.Float(), nullable=True),
            sa.Column("minutes_weighted_score", sa.Float(), nullable=True),
            sa.Column("availability_score", sa.Float(), nullable=True),
            sa.Column("key_players_json", sa.JSON(), nullable=True),
            sa.Column("warnings_json", sa.JSON(), nullable=True),
            sa.Column("payload_json", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
            sa.UniqueConstraint(
                "competition_key",
                "league_id",
                "season",
                "team_id",
                "snapshot_at",
                name="uq_squad_strength_snapshot",
            ),
        )

    _indexes()


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    tables = set(inspector.get_table_names())
    for table_name in (
        "squad_strength_features",
        "worldcup_group_state_snapshots",
        "fifa_ranking_snapshots",
        "national_elo_snapshots",
        "national_team_matches",
        "national_team_aliases",
    ):
        if table_name in tables:
            op.drop_table(table_name)


def _indexes() -> None:
    _create_index("national_team_aliases", "ix_national_team_aliases_canonical_name", ["canonical_name"])
    _create_index("national_team_aliases", "ix_national_team_aliases_normalized_alias", ["normalized_alias"])
    _create_index("national_team_aliases", "ix_national_team_aliases_source", ["source"])
    _create_index("national_team_aliases", "ix_national_team_alias_canonical", ["canonical_name"])
    _create_index("national_team_aliases", "ix_national_team_alias_api_team", ["api_team_id"])
    _create_index("national_team_aliases", "ix_national_team_alias_elo_code", ["elo_code"])
    _create_index("national_team_aliases", "ix_national_team_alias_fifa_code", ["fifa_code"])

    _create_index("national_team_matches", "ix_national_team_matches_match_date", ["match_date"])
    _create_index("national_team_matches", "ix_national_team_matches_home_team_canonical", ["home_team_canonical"])
    _create_index("national_team_matches", "ix_national_team_matches_away_team_canonical", ["away_team_canonical"])
    _create_index("national_team_matches", "ix_national_team_matches_home_team_id", ["home_team_id"])
    _create_index("national_team_matches", "ix_national_team_matches_away_team_id", ["away_team_id"])
    _create_index("national_team_matches", "ix_national_team_matches_tournament", ["tournament"])
    _create_index("national_team_matches", "ix_national_team_matches_competition_type", ["competition_type"])
    _create_index("national_team_matches", "ix_national_team_matches_source", ["source"])
    _create_index("national_team_matches", "ix_national_team_matches_source_match_id", ["source_match_id"])
    _create_index("national_team_matches", "ix_national_team_matches_date", ["match_date"])
    _create_index(
        "national_team_matches",
        "ix_national_team_matches_home_date",
        ["home_team_canonical", "match_date"],
    )
    _create_index(
        "national_team_matches",
        "ix_national_team_matches_away_date",
        ["away_team_canonical", "match_date"],
    )
    _create_index(
        "national_team_matches",
        "ix_national_team_matches_teams_date",
        ["home_team_id", "away_team_id", "match_date"],
    )

    _create_index("national_elo_snapshots", "ix_national_elo_snapshots_canonical_team", ["canonical_team"])
    _create_index("national_elo_snapshots", "ix_national_elo_snapshots_elo_code", ["elo_code"])
    _create_index("national_elo_snapshots", "ix_national_elo_snapshots_snapshot_date", ["snapshot_date"])
    _create_index("national_elo_snapshots", "ix_national_elo_snapshots_source", ["source"])
    _create_index("national_elo_snapshots", "ix_national_elo_team_date", ["canonical_team", "snapshot_date"])
    _create_index("national_elo_snapshots", "ix_national_elo_code_date", ["elo_code", "snapshot_date"])

    _create_index("fifa_ranking_snapshots", "ix_fifa_ranking_snapshots_canonical_team", ["canonical_team"])
    _create_index("fifa_ranking_snapshots", "ix_fifa_ranking_snapshots_snapshot_date", ["snapshot_date"])
    _create_index("fifa_ranking_snapshots", "ix_fifa_ranking_snapshots_source", ["source"])
    _create_index("fifa_ranking_snapshots", "ix_fifa_ranking_team_date", ["canonical_team", "snapshot_date"])

    _create_index("worldcup_group_state_snapshots", "ix_worldcup_group_state_snapshots_competition_key", ["competition_key"])
    _create_index("worldcup_group_state_snapshots", "ix_worldcup_group_state_snapshots_league_id", ["league_id"])
    _create_index("worldcup_group_state_snapshots", "ix_worldcup_group_state_snapshots_season", ["season"])
    _create_index("worldcup_group_state_snapshots", "ix_worldcup_group_state_snapshots_group_name", ["group_name"])
    _create_index("worldcup_group_state_snapshots", "ix_worldcup_group_state_snapshots_team_id", ["team_id"])
    _create_index("worldcup_group_state_snapshots", "ix_worldcup_group_state_snapshots_canonical_team", ["canonical_team"])
    _create_index("worldcup_group_state_snapshots", "ix_worldcup_group_state_snapshots_snapshot_at", ["snapshot_at"])
    _create_index("worldcup_group_state_snapshots", "ix_worldcup_group_state_snapshots_matchday", ["matchday"])
    _create_index("worldcup_group_state_snapshots", "ix_worldcup_group_state_team_time", ["team_id", "snapshot_at"])
    _create_index(
        "worldcup_group_state_snapshots",
        "ix_worldcup_group_state_competition_time",
        ["competition_key", "league_id", "season", "snapshot_at"],
    )

    _create_index("squad_strength_features", "ix_squad_strength_features_competition_key", ["competition_key"])
    _create_index("squad_strength_features", "ix_squad_strength_features_league_id", ["league_id"])
    _create_index("squad_strength_features", "ix_squad_strength_features_season", ["season"])
    _create_index("squad_strength_features", "ix_squad_strength_features_team_id", ["team_id"])
    _create_index("squad_strength_features", "ix_squad_strength_features_canonical_team", ["canonical_team"])
    _create_index("squad_strength_features", "ix_squad_strength_features_snapshot_at", ["snapshot_at"])
    _create_index("squad_strength_features", "ix_squad_strength_features_squad_status", ["squad_status"])
    _create_index("squad_strength_features", "ix_squad_strength_team_time", ["team_id", "snapshot_at"])
    _create_index(
        "squad_strength_features",
        "ix_squad_strength_competition_time",
        ["competition_key", "league_id", "season", "snapshot_at"],
    )


def _create_index(table_name: str, index_name: str, columns: list[str]) -> None:
    inspector = inspect(op.get_bind())
    existing = {index["name"] for index in inspector.get_indexes(table_name)}
    if index_name not in existing:
        op.create_index(index_name, table_name, columns)
