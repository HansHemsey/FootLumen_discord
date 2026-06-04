"""Small repositories for idempotent writes and point-in-time reads."""

from __future__ import annotations

from datetime import datetime
from typing import Any, TypeVar

from sqlalchemy import Select, and_, or_, select
from sqlalchemy.orm import Session

from football_predictor.db import models
from football_predictor.security.sanitize import sanitize_mapping, sanitize_text, sanitize_value
from football_predictor.utils.secrets import hash_secret
from football_predictor.utils.time import ensure_aware_utc

ModelT = TypeVar("ModelT", bound=object)


def upsert_by_fields(
    session: Session,
    model: type[ModelT],
    match_fields: dict[str, Any],
    values: dict[str, Any],
) -> ModelT:
    for pending in session.new:
        if isinstance(pending, model) and all(
            getattr(pending, field) == value for field, value in match_fields.items()
        ):
            for key, value in values.items():
                setattr(pending, key, value)
            return pending

    conditions = [getattr(model, field) == value for field, value in match_fields.items()]
    instance = session.execute(select(model).where(and_(*conditions))).scalar_one_or_none()
    if instance is None:
        instance = model(**{**match_fields, **values})
        session.add(instance)
    else:
        for key, value in values.items():
            setattr(instance, key, value)
    return instance


def insert_raw_api_snapshot(
    session: Session,
    *,
    endpoint: str,
    params_json: dict[str, Any],
    payload_json: dict[str, Any] | list[Any],
    fetched_at: datetime,
    status_code: int | None,
    source: str = "api-football",
) -> models.RawApiSnapshot:
    """Insert an immutable raw API snapshot."""
    snapshot = models.RawApiSnapshot(
        endpoint=endpoint,
        params_json=sanitize_mapping(params_json),
        payload_json=sanitize_value(payload_json),
        fetched_at=ensure_aware_utc(fetched_at),
        status_code=status_code,
        source=source,
    )
    session.add(snapshot)
    return snapshot


def upsert_league(
    session: Session,
    *,
    league_id: int,
    season: int,
    values: dict[str, Any],
) -> models.League:
    return upsert_by_fields(
        session,
        models.League,
        {"league_id": league_id, "season": season},
        values,
    )


def upsert_team(session: Session, *, team_id: int, values: dict[str, Any]) -> models.Team:
    return upsert_by_fields(session, models.Team, {"team_id": team_id}, values)


def upsert_fixture(
    session: Session,
    *,
    fixture_id: int,
    values: dict[str, Any],
) -> models.Fixture:
    return upsert_by_fields(session, models.Fixture, {"fixture_id": fixture_id}, values)


def historical_fixtures_for_team(
    session: Session,
    team_id: int,
    prediction_time: datetime,
    exclude_fixture_id: int,
    limit: int | None = None,
) -> list[models.Fixture]:
    """Read only matches known before prediction_time and exclude the target fixture."""
    stmt: Select[tuple[models.Fixture]] = (
        select(models.Fixture)
        .where(
            models.Fixture.fixture_id != exclude_fixture_id,
            models.Fixture.date < ensure_aware_utc(prediction_time),
            or_(models.Fixture.home_team_id == team_id, models.Fixture.away_team_id == team_id),
        )
        .order_by(models.Fixture.date.desc())
    )
    if limit is not None:
        stmt = stmt.limit(limit)
    return list(session.execute(stmt).scalars())


def latest_odds_snapshots(
    session: Session,
    fixture_id: int,
    prediction_time: datetime,
    bet_id: int,
) -> list[models.OddsSnapshot]:
    """Return prematch odds snapshots available at prediction time."""
    stmt = (
        select(models.OddsSnapshot)
        .where(
            models.OddsSnapshot.fixture_id == fixture_id,
            models.OddsSnapshot.bet_id == bet_id,
            models.OddsSnapshot.is_live.is_(False),
            models.OddsSnapshot.fetched_at <= ensure_aware_utc(prediction_time),
        )
        .order_by(models.OddsSnapshot.fetched_at.desc())
    )
    return list(session.execute(stmt).scalars())


def create_discord_message_log(
    session: Session,
    *,
    message_markdown: str,
    message_hash: str,
    status: str,
    webhook_url: str | None = None,
    fixture_id: int | None = None,
    model_prediction_id: int | None = None,
    competition_key: str | None = None,
    league_id: int | None = None,
    season: int | None = None,
    channel_key: str | None = None,
    message_type: str | None = None,
    dry_run: bool = False,
    print_only: bool = False,
    sent_at: datetime | None = None,
    response_text: str | None = None,
    payload_json: dict[str, Any] | None = None,
    route_json: dict[str, Any] | None = None,
    response_json: dict[str, Any] | None = None,
) -> models.DiscordMessage:
    webhook_hash = hash_secret(webhook_url)
    row = models.DiscordMessage(
        fixture_id=fixture_id,
        model_prediction_id=model_prediction_id,
        competition_key=competition_key,
        league_id=league_id,
        season=season,
        channel_key=channel_key,
        message_type=message_type,
        dry_run=dry_run,
        print_only=print_only,
        webhook_url_hash=webhook_hash,
        webhook_hash=webhook_hash,
        message_hash=message_hash,
        message_markdown=sanitize_text(message_markdown),
        sent_at=sent_at,
        status=status,
        response_text=sanitize_text(response_text) if response_text else None,
        payload_json=sanitize_mapping(payload_json or {}),
        route_json=sanitize_mapping(route_json or {}),
        response_json=sanitize_mapping(response_json or {}),
    )
    session.add(row)
    session.flush()
    return row


def has_message_been_sent(session: Session, *, webhook_hash: str, message_hash: str) -> bool:
    return find_recent_message_by_hash(
        session,
        webhook_hash=webhook_hash,
        message_hash=message_hash,
    ) is not None


def find_recent_message_by_hash(
    session: Session,
    *,
    webhook_hash: str,
    message_hash: str,
) -> models.DiscordMessage | None:
    stmt = (
        select(models.DiscordMessage)
        .where(
            models.DiscordMessage.webhook_hash == webhook_hash,
            models.DiscordMessage.message_hash == message_hash,
            models.DiscordMessage.status == "sent",
        )
        .order_by(models.DiscordMessage.created_at.desc())
    )
    return session.execute(stmt).scalars().first()
