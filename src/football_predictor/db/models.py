"""SQLAlchemy models for local storage and snapshots."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON as SAJSON
from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    false,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from football_predictor.utils.time import utc_now

JsonValue = dict[str, Any] | list[Any] | str | int | float | bool | None


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
    )


class RawApiSnapshot(Base, TimestampMixin):
    __tablename__ = "raw_api_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    endpoint: Mapped[str] = mapped_column(String(128), index=True)
    params_json: Mapped[JsonValue] = mapped_column(SAJSON, default=dict)
    payload_json: Mapped[JsonValue] = mapped_column(SAJSON, default=dict)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    status_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source: Mapped[str] = mapped_column(String(64), default="api-football")


class League(Base, TimestampMixin):
    __tablename__ = "leagues"
    __table_args__ = (UniqueConstraint("league_id", "season", name="uq_league_season"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    league_id: Mapped[int] = mapped_column(Integer, index=True)
    season: Mapped[int] = mapped_column(Integer, index=True)
    name: Mapped[str] = mapped_column(String(160))
    country: Mapped[str | None] = mapped_column(String(120), nullable=True)
    type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    country_code: Mapped[str | None] = mapped_column(String(32), nullable=True)
    category: Mapped[str | None] = mapped_column(String(32), nullable=True)
    logo: Mapped[str | None] = mapped_column(Text, nullable=True)
    season_start: Mapped[str | None] = mapped_column(String(32), nullable=True)
    season_end: Mapped[str | None] = mapped_column(String(32), nullable=True)
    payload_json: Mapped[JsonValue] = mapped_column(SAJSON, default=dict)


class Venue(Base, TimestampMixin):
    __tablename__ = "venues"

    venue_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str | None] = mapped_column(String(180), nullable=True)
    address: Mapped[str | None] = mapped_column(String(240), nullable=True)
    city: Mapped[str | None] = mapped_column(String(120), nullable=True)
    capacity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    surface: Mapped[str | None] = mapped_column(String(64), nullable=True)
    image: Mapped[str | None] = mapped_column(Text, nullable=True)
    payload_json: Mapped[JsonValue] = mapped_column(SAJSON, default=dict)


class Team(Base, TimestampMixin):
    __tablename__ = "teams"

    team_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(180), index=True)
    code: Mapped[str | None] = mapped_column(String(16), nullable=True)
    country: Mapped[str | None] = mapped_column(String(120), nullable=True)
    founded: Mapped[int | None] = mapped_column(Integer, nullable=True)
    national: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    logo: Mapped[str | None] = mapped_column(Text, nullable=True)
    venue_id: Mapped[int | None] = mapped_column(ForeignKey("venues.venue_id"), nullable=True)
    payload_json: Mapped[JsonValue] = mapped_column(SAJSON, default=dict)


class TeamSeason(Base, TimestampMixin):
    __tablename__ = "team_seasons"
    __table_args__ = (
        UniqueConstraint("team_id", "league_id", "season", name="uq_team_league_season"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.team_id"), index=True)
    league_id: Mapped[int] = mapped_column(Integer, index=True)
    season: Mapped[int] = mapped_column(Integer, index=True)
    competition_key: Mapped[str | None] = mapped_column(String(80), nullable=True)
    payload_json: Mapped[JsonValue] = mapped_column(SAJSON, default=dict)


class Fixture(Base, TimestampMixin):
    __tablename__ = "fixtures"
    __table_args__ = (
        Index("ix_fixtures_league_season_date", "league_id", "season", "date"),
        Index("ix_fixtures_teams_date", "home_team_id", "away_team_id", "date"),
    )

    fixture_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    timestamp: Mapped[int | None] = mapped_column(Integer, nullable=True)
    timezone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    round: Mapped[str | None] = mapped_column(String(120), nullable=True)
    league_id: Mapped[int] = mapped_column(Integer, index=True)
    season: Mapped[int] = mapped_column(Integer, index=True)
    venue_id: Mapped[int | None] = mapped_column(ForeignKey("venues.venue_id"), nullable=True)
    venue_name: Mapped[str | None] = mapped_column(String(180), nullable=True)
    venue_city: Mapped[str | None] = mapped_column(String(120), nullable=True)
    referee: Mapped[str | None] = mapped_column(String(120), nullable=True)
    status: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    status_long: Mapped[str | None] = mapped_column(String(80), nullable=True)
    status_short: Mapped[str | None] = mapped_column(String(16), nullable=True)
    elapsed: Mapped[int | None] = mapped_column(Integer, nullable=True)
    home_team_id: Mapped[int] = mapped_column(ForeignKey("teams.team_id"), index=True)
    away_team_id: Mapped[int] = mapped_column(ForeignKey("teams.team_id"), index=True)
    home_team: Mapped[str] = mapped_column(String(180))
    away_team: Mapped[str] = mapped_column(String(180))
    home_goals: Mapped[int | None] = mapped_column(Integer, nullable=True)
    away_goals: Mapped[int | None] = mapped_column(Integer, nullable=True)
    goals_home: Mapped[int | None] = mapped_column(Integer, nullable=True)
    goals_away: Mapped[int | None] = mapped_column(Integer, nullable=True)
    payload_json: Mapped[JsonValue] = mapped_column(SAJSON, default=dict)


class StandingSnapshot(Base, TimestampMixin):
    __tablename__ = "standing_snapshots"
    __table_args__ = (
        UniqueConstraint(
            "league_id",
            "season",
            "team_id",
            "snapshot_date",
            name="uq_standing_snapshot",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    league_id: Mapped[int] = mapped_column(Integer, index=True)
    season: Mapped[int] = mapped_column(Integer, index=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.team_id"), index=True)
    snapshot_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, index=True
    )
    rank: Mapped[int | None] = mapped_column(Integer, nullable=True)
    points: Mapped[int | None] = mapped_column(Integer, nullable=True)
    goals_diff: Mapped[int | None] = mapped_column(Integer, nullable=True)
    form: Mapped[str | None] = mapped_column(String(64), nullable=True)
    description: Mapped[str | None] = mapped_column(String(180), nullable=True)
    played: Mapped[int | None] = mapped_column(Integer, nullable=True)
    all_played: Mapped[int | None] = mapped_column(Integer, nullable=True)
    all_win: Mapped[int | None] = mapped_column(Integer, nullable=True)
    all_draw: Mapped[int | None] = mapped_column(Integer, nullable=True)
    all_lose: Mapped[int | None] = mapped_column(Integer, nullable=True)
    all_goals_for: Mapped[int | None] = mapped_column(Integer, nullable=True)
    all_goals_against: Mapped[int | None] = mapped_column(Integer, nullable=True)
    home_played: Mapped[int | None] = mapped_column(Integer, nullable=True)
    home_win: Mapped[int | None] = mapped_column(Integer, nullable=True)
    home_draw: Mapped[int | None] = mapped_column(Integer, nullable=True)
    home_lose: Mapped[int | None] = mapped_column(Integer, nullable=True)
    away_played: Mapped[int | None] = mapped_column(Integer, nullable=True)
    away_win: Mapped[int | None] = mapped_column(Integer, nullable=True)
    away_draw: Mapped[int | None] = mapped_column(Integer, nullable=True)
    away_lose: Mapped[int | None] = mapped_column(Integer, nullable=True)
    goals_for: Mapped[int | None] = mapped_column(Integer, nullable=True)
    goals_against: Mapped[int | None] = mapped_column(Integer, nullable=True)
    payload_json: Mapped[JsonValue] = mapped_column(SAJSON, default=dict)


class Bookmaker(Base, TimestampMixin):
    __tablename__ = "bookmakers"

    bookmaker_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(180), index=True)
    payload_json: Mapped[JsonValue] = mapped_column(SAJSON, default=dict)


class Bet(Base, TimestampMixin):
    __tablename__ = "bets"
    __table_args__ = (UniqueConstraint("bet_id", "bet_type", name="uq_bet_id_type"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    bet_id: Mapped[int] = mapped_column(Integer, index=True)
    name: Mapped[str] = mapped_column(String(180), index=True)
    bet_type: Mapped[str] = mapped_column(String(32), default="prematch")
    payload_json: Mapped[JsonValue] = mapped_column(SAJSON, default=dict)


class Player(Base, TimestampMixin):
    __tablename__ = "players"

    player_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(180), index=True)
    firstname: Mapped[str | None] = mapped_column(String(120), nullable=True)
    lastname: Mapped[str | None] = mapped_column(String(120), nullable=True)
    age: Mapped[int | None] = mapped_column(Integer, nullable=True)
    birth_date: Mapped[str | None] = mapped_column(String(32), nullable=True)
    nationality: Mapped[str | None] = mapped_column(String(120), nullable=True)
    height: Mapped[str | None] = mapped_column(String(32), nullable=True)
    weight: Mapped[str | None] = mapped_column(String(32), nullable=True)
    injured: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    photo: Mapped[str | None] = mapped_column(Text, nullable=True)
    payload_json: Mapped[JsonValue] = mapped_column(SAJSON, default=dict)


class PlayerSquad(Base, TimestampMixin):
    __tablename__ = "player_squads"
    __table_args__ = (
        UniqueConstraint("player_id", "team_id", "league_id", "season", name="uq_player_squad"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    player_id: Mapped[int] = mapped_column(ForeignKey("players.player_id"), index=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.team_id"), index=True)
    league_id: Mapped[int] = mapped_column(Integer, index=True)
    season: Mapped[int] = mapped_column(Integer, index=True)
    position: Mapped[str | None] = mapped_column(String(64), nullable=True)
    number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    payload_json: Mapped[JsonValue] = mapped_column(SAJSON, default=dict)


class FixtureStatistics(Base, TimestampMixin):
    __tablename__ = "fixture_statistics"
    __table_args__ = (
        UniqueConstraint(
            "fixture_id", "team_id", "fetched_at", name="uq_fixture_statistics_snapshot"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    fixture_id: Mapped[int] = mapped_column(ForeignKey("fixtures.fixture_id"), index=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.team_id"), index=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    statistics_json: Mapped[JsonValue] = mapped_column(SAJSON, default=dict)
    payload_json: Mapped[JsonValue] = mapped_column(SAJSON, default=dict)


class FixtureEvent(Base, TimestampMixin):
    __tablename__ = "fixture_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    fixture_id: Mapped[int] = mapped_column(ForeignKey("fixtures.fixture_id"), index=True)
    team_id: Mapped[int | None] = mapped_column(
        ForeignKey("teams.team_id"), nullable=True, index=True
    )
    player_id: Mapped[int | None] = mapped_column(
        ForeignKey("players.player_id"), nullable=True, index=True
    )
    assist_player_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    event_time: Mapped[int | None] = mapped_column(Integer, nullable=True)
    event_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    detail: Mapped[str | None] = mapped_column(String(120), nullable=True)
    elapsed: Mapped[int | None] = mapped_column(Integer, nullable=True)
    extra: Mapped[int | None] = mapped_column(Integer, nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    payload_json: Mapped[JsonValue] = mapped_column(SAJSON, default=dict)


class FixtureLineup(Base, TimestampMixin):
    __tablename__ = "fixture_lineups"
    __table_args__ = (
        UniqueConstraint("fixture_id", "team_id", "fetched_at", name="uq_lineup_snapshot"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    fixture_id: Mapped[int] = mapped_column(ForeignKey("fixtures.fixture_id"), index=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.team_id"), index=True)
    coach_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    formation: Mapped[str | None] = mapped_column(String(32), nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    start_xi_json: Mapped[JsonValue] = mapped_column(SAJSON, default=list)
    substitutes_json: Mapped[JsonValue] = mapped_column(SAJSON, default=list)
    players_json: Mapped[JsonValue] = mapped_column(SAJSON, default=list)
    payload_json: Mapped[JsonValue] = mapped_column(SAJSON, default=dict)


class FixturePlayerStats(Base, TimestampMixin):
    __tablename__ = "fixture_player_stats"
    __table_args__ = (
        UniqueConstraint(
            "fixture_id", "team_id", "player_id", "fetched_at", name="uq_player_stats_snapshot"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    fixture_id: Mapped[int] = mapped_column(ForeignKey("fixtures.fixture_id"), index=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.team_id"), index=True)
    player_id: Mapped[int] = mapped_column(ForeignKey("players.player_id"), index=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    statistics_json: Mapped[JsonValue] = mapped_column(SAJSON, default=dict)
    stats_json: Mapped[JsonValue] = mapped_column(SAJSON, default=dict)
    rating: Mapped[float | None] = mapped_column(Float, nullable=True)
    minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    position: Mapped[str | None] = mapped_column(String(64), nullable=True)
    payload_json: Mapped[JsonValue] = mapped_column(SAJSON, default=dict)


class Injury(Base, TimestampMixin):
    __tablename__ = "injuries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    fixture_id: Mapped[int | None] = mapped_column(
        ForeignKey("fixtures.fixture_id"), nullable=True, index=True
    )
    team_id: Mapped[int | None] = mapped_column(
        ForeignKey("teams.team_id"), nullable=True, index=True
    )
    player_id: Mapped[int | None] = mapped_column(
        ForeignKey("players.player_id"), nullable=True, index=True
    )
    league_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    season: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    reason: Mapped[str | None] = mapped_column(String(180), nullable=True)
    type: Mapped[str | None] = mapped_column(String(80), nullable=True)
    date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    payload_json: Mapped[JsonValue] = mapped_column(SAJSON, default=dict)


class OddsSnapshot(Base, TimestampMixin):
    __tablename__ = "odds_snapshots"
    __table_args__ = (
        Index("ix_odds_fixture_market_time", "fixture_id", "bet_id", "fetched_at"),
        Index("ix_odds_fixture_market_live_time", "fixture_id", "bet_id", "is_live", "fetched_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    fixture_id: Mapped[int] = mapped_column(ForeignKey("fixtures.fixture_id"), index=True)
    league_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    season: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    bookmaker_id: Mapped[int | None] = mapped_column(
        ForeignKey("bookmakers.bookmaker_id"), nullable=True
    )
    bookmaker_name: Mapped[str | None] = mapped_column(String(180), nullable=True)
    bet_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    bet_name: Mapped[str | None] = mapped_column(String(180), nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    is_live: Mapped[bool] = mapped_column(Boolean, default=False)
    odd_home: Mapped[float | None] = mapped_column(Float, nullable=True)
    odd_draw: Mapped[float | None] = mapped_column(Float, nullable=True)
    odd_away: Mapped[float | None] = mapped_column(Float, nullable=True)
    values_json: Mapped[JsonValue] = mapped_column(SAJSON, default=list)
    odds_json: Mapped[JsonValue] = mapped_column(SAJSON, default=dict)
    payload_json: Mapped[JsonValue] = mapped_column(SAJSON, default=dict)


class ApiPredictionSnapshot(Base, TimestampMixin):
    __tablename__ = "api_prediction_snapshots"
    __table_args__ = (Index("ix_api_prediction_fixture_time", "fixture_id", "fetched_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    fixture_id: Mapped[int] = mapped_column(ForeignKey("fixtures.fixture_id"), index=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    source: Mapped[str] = mapped_column(String(64), default="api-football")
    winner_team_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    win_or_draw: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    advice: Mapped[str | None] = mapped_column(Text, nullable=True)
    percent_home: Mapped[float | None] = mapped_column(Float, nullable=True)
    percent_draw: Mapped[float | None] = mapped_column(Float, nullable=True)
    percent_away: Mapped[float | None] = mapped_column(Float, nullable=True)
    payload_json: Mapped[JsonValue] = mapped_column(SAJSON, default=dict)


class FeatureSnapshot(Base, TimestampMixin):
    __tablename__ = "feature_snapshots"
    __table_args__ = (
        UniqueConstraint(
            "fixture_id", "prediction_time", "feature_version", name="uq_feature_snapshot"
        ),
        Index("ix_feature_snapshot_fixture_time", "fixture_id", "prediction_time"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    fixture_id: Mapped[int] = mapped_column(ForeignKey("fixtures.fixture_id"), index=True)
    prediction_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    feature_version: Mapped[str] = mapped_column(String(64))
    features_json: Mapped[JsonValue] = mapped_column(SAJSON, default=dict)
    data_quality_json: Mapped[JsonValue] = mapped_column(SAJSON, default=dict)


class ModelPrediction(Base, TimestampMixin):
    __tablename__ = "model_predictions"
    __table_args__ = (
        Index("ix_model_prediction_fixture_time", "fixture_id", "prediction_time"),
        Index("ix_model_prediction_model_version", "model_version"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    fixture_id: Mapped[int] = mapped_column(ForeignKey("fixtures.fixture_id"), index=True)
    feature_snapshot_id: Mapped[int] = mapped_column(ForeignKey("feature_snapshots.id"), index=True)
    prediction_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    model_version: Mapped[str] = mapped_column(String(64))
    p_home: Mapped[float] = mapped_column(Float)
    p_draw: Mapped[float] = mapped_column(Float)
    p_away: Mapped[float] = mapped_column(Float)
    predicted_outcome: Mapped[str | None] = mapped_column(String(16), nullable=True)
    predicted_result: Mapped[str] = mapped_column(String(16))
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    confidence_label: Mapped[str] = mapped_column(String(32))
    confidence_score: Mapped[float] = mapped_column(Float)
    explanation_json: Mapped[JsonValue] = mapped_column(SAJSON, default=list)
    explanations_json: Mapped[JsonValue] = mapped_column(SAJSON, default=list)
    data_quality_json: Mapped[JsonValue] = mapped_column(SAJSON, default=dict)
    payload_json: Mapped[JsonValue] = mapped_column(SAJSON, default=dict)


class OUFeatureSnapshot(Base, TimestampMixin):
    __tablename__ = "ou_feature_snapshots"
    __table_args__ = (
        UniqueConstraint(
            "fixture_id",
            "prediction_time",
            "feature_version",
            "threshold",
            name="uq_ou_feature_snapshot",
        ),
        Index("ix_ou_feature_snapshot_fixture_time", "fixture_id", "prediction_time"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    fixture_id: Mapped[int] = mapped_column(ForeignKey("fixtures.fixture_id"), index=True)
    prediction_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    feature_version: Mapped[str] = mapped_column(String(64))
    threshold: Mapped[float] = mapped_column(Float, default=2.5)
    features_json: Mapped[JsonValue] = mapped_column(SAJSON, default=dict)
    data_quality_json: Mapped[JsonValue] = mapped_column(SAJSON, default=dict)


class OUModelPrediction(Base, TimestampMixin):
    __tablename__ = "ou_model_predictions"
    __table_args__ = (
        Index("ix_ou_prediction_fixture_time", "fixture_id", "prediction_time"),
        Index("ix_ou_prediction_model_version", "model_version"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    fixture_id: Mapped[int] = mapped_column(ForeignKey("fixtures.fixture_id"), index=True)
    ou_feature_snapshot_id: Mapped[int] = mapped_column(
        ForeignKey("ou_feature_snapshots.id"), index=True
    )
    prediction_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    model_version: Mapped[str] = mapped_column(String(64))
    threshold: Mapped[float] = mapped_column(Float, default=2.5)
    p_over: Mapped[float] = mapped_column(Float)
    p_under: Mapped[float] = mapped_column(Float)
    xg_home: Mapped[float | None] = mapped_column(Float, nullable=True)
    xg_away: Mapped[float | None] = mapped_column(Float, nullable=True)
    xg_total: Mapped[float | None] = mapped_column(Float, nullable=True)
    market_p_over: Mapped[float | None] = mapped_column(Float, nullable=True)
    market_p_under: Mapped[float | None] = mapped_column(Float, nullable=True)
    edge_over: Mapped[float | None] = mapped_column(Float, nullable=True)
    edge_under: Mapped[float | None] = mapped_column(Float, nullable=True)
    ev_over: Mapped[float | None] = mapped_column(Float, nullable=True)
    ev_under: Mapped[float | None] = mapped_column(Float, nullable=True)
    market_odd_over: Mapped[float | None] = mapped_column(Float, nullable=True)
    market_odd_under: Mapped[float | None] = mapped_column(Float, nullable=True)
    confidence_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    confidence_label: Mapped[str | None] = mapped_column(String(32), nullable=True)
    forecast_side: Mapped[str | None] = mapped_column(String(16), nullable=True)
    forecast_probability: Mapped[float | None] = mapped_column(Float, nullable=True)
    value_side: Mapped[str | None] = mapped_column(String(16), nullable=True)
    p_pick: Mapped[float | None] = mapped_column(Float, nullable=True)
    market_p_pick: Mapped[float | None] = mapped_column(Float, nullable=True)
    odd_pick: Mapped[float | None] = mapped_column(Float, nullable=True)
    edge_pick: Mapped[float | None] = mapped_column(Float, nullable=True)
    ev_pick: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_value_pick: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false())
    no_bet_reason: Mapped[str | None] = mapped_column(String(96), nullable=True)
    confidence_score_v2: Mapped[float | None] = mapped_column(Float, nullable=True)
    confidence_label_v2: Mapped[str | None] = mapped_column(String(32), nullable=True)
    publication_decision: Mapped[str | None] = mapped_column(String(16), nullable=True)
    expert_probabilities_json: Mapped[JsonValue] = mapped_column(SAJSON, default=dict)
    data_quality_json: Mapped[JsonValue] = mapped_column(SAJSON, default=dict)
    payload_json: Mapped[JsonValue] = mapped_column(SAJSON, default=dict)


class V3FeatureSnapshot(Base, TimestampMixin):
    __tablename__ = "v3_feature_snapshots"
    __table_args__ = (
        UniqueConstraint(
            "fixture_id", "prediction_time", "feature_version", name="uq_v3_feature_snapshot"
        ),
        Index("ix_v3_feature_snapshot_fixture_time", "fixture_id", "prediction_time"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    fixture_id: Mapped[int] = mapped_column(ForeignKey("fixtures.fixture_id"), index=True)
    prediction_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    feature_version: Mapped[str] = mapped_column(String(64))
    official_lineup_available_flag: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=false()
    )
    features_json: Mapped[JsonValue] = mapped_column(SAJSON, default=dict)
    data_quality_json: Mapped[JsonValue] = mapped_column(SAJSON, default=dict)


class V3ModelPrediction(Base, TimestampMixin):
    __tablename__ = "v3_model_predictions"
    __table_args__ = (
        Index("ix_v3_prediction_fixture_time", "fixture_id", "prediction_time"),
        Index("ix_v3_prediction_model_version", "model_version"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    fixture_id: Mapped[int] = mapped_column(ForeignKey("fixtures.fixture_id"), index=True)
    v3_feature_snapshot_id: Mapped[int] = mapped_column(
        ForeignKey("v3_feature_snapshots.id"), index=True
    )
    prediction_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    model_version: Mapped[str] = mapped_column(String(64))
    fusion_strategy: Mapped[str] = mapped_column(String(32))
    p_v3_final_home: Mapped[float] = mapped_column(Float)
    p_v3_final_draw: Mapped[float] = mapped_column(Float)
    p_v3_final_away: Mapped[float] = mapped_column(Float)
    p_v3_draw_risk: Mapped[float | None] = mapped_column(Float, nullable=True)
    p_v3_home_no_draw: Mapped[float | None] = mapped_column(Float, nullable=True)
    p_v3_away_no_draw: Mapped[float | None] = mapped_column(Float, nullable=True)
    p_v2_home: Mapped[float | None] = mapped_column(Float, nullable=True)
    p_v2_draw: Mapped[float | None] = mapped_column(Float, nullable=True)
    p_v2_away: Mapped[float | None] = mapped_column(Float, nullable=True)
    p_market_home: Mapped[float | None] = mapped_column(Float, nullable=True)
    p_market_draw: Mapped[float | None] = mapped_column(Float, nullable=True)
    p_market_away: Mapped[float | None] = mapped_column(Float, nullable=True)
    p_api_home: Mapped[float | None] = mapped_column(Float, nullable=True)
    p_api_draw: Mapped[float | None] = mapped_column(Float, nullable=True)
    p_api_away: Mapped[float | None] = mapped_column(Float, nullable=True)
    data_quality_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    official_lineup_available_flag: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=false()
    )
    confidence_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    confidence_label: Mapped[str | None] = mapped_column(String(32), nullable=True)
    predicted_result: Mapped[str] = mapped_column(String(16))
    expert_probabilities_json: Mapped[JsonValue] = mapped_column(SAJSON, default=dict)
    explanations_json: Mapped[JsonValue] = mapped_column(SAJSON, default=list)
    data_quality_json: Mapped[JsonValue] = mapped_column(SAJSON, default=dict)
    payload_json: Mapped[JsonValue] = mapped_column(SAJSON, default=dict)


class DiscordMessage(Base, TimestampMixin):
    __tablename__ = "discord_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    fixture_id: Mapped[int | None] = mapped_column(
        ForeignKey("fixtures.fixture_id"), nullable=True, index=True
    )
    model_prediction_id: Mapped[int | None] = mapped_column(
        ForeignKey("model_predictions.id"),
        nullable=True,
        index=True,
    )
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="pending")
    competition_key: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    league_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    season: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    channel_key: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    message_type: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    dry_run: Mapped[bool] = mapped_column(Boolean, default=False)
    print_only: Mapped[bool] = mapped_column(Boolean, default=False)
    webhook_url_hash: Mapped[str | None] = mapped_column(String(16), nullable=True)
    message_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    webhook_hash: Mapped[str | None] = mapped_column(String(16), nullable=True)
    message_markdown: Mapped[str] = mapped_column(Text)
    route_json: Mapped[JsonValue] = mapped_column(SAJSON, default=dict)
    payload_json: Mapped[JsonValue] = mapped_column(SAJSON, default=dict)
    response_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    response_json: Mapped[JsonValue] = mapped_column(SAJSON, default=dict)
