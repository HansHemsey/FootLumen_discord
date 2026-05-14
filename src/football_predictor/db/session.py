"""Database engine and session helpers."""

from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from football_predictor.db.models import Base


def create_db_engine(database_url: str, echo: bool = False) -> Engine:
    connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
    return create_engine(database_url, echo=echo, future=True, connect_args=connect_args)


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def init_db(engine: Engine) -> None:
    Base.metadata.create_all(bind=engine)
    if engine.dialect.name == "sqlite":
        _ensure_sqlite_discord_columns(engine)


def _ensure_sqlite_discord_columns(engine: Engine) -> None:
    """Keep local SQLite DBs usable when Sprint 15 columns are added.

    Durable databases should still use Alembic. This helper only covers idempotent
    SQLite bootstrap for developer machines and CLI smoke runs.
    """
    inspector = inspect(engine)
    if not inspector.has_table("discord_messages"):
        return
    columns = {column["name"] for column in inspector.get_columns("discord_messages")}
    additions = {
        "competition_key": "VARCHAR(80)",
        "league_id": "INTEGER",
        "season": "INTEGER",
        "channel_key": "VARCHAR(80)",
        "message_type": "VARCHAR(80)",
        "dry_run": "BOOLEAN DEFAULT 0",
        "print_only": "BOOLEAN DEFAULT 0",
        "v3_model_prediction_id": "INTEGER",
        "ou_model_prediction_id": "INTEGER",
        "webhook_url_hash": "VARCHAR(16)",
        "message_hash": "VARCHAR(64)",
        "webhook_hash": "VARCHAR(16)",
        "dedupe_key": "VARCHAR(160)",
        "message_markdown": "TEXT",
        "route_json": "JSON",
        "payload_json": "JSON",
        "response_text": "TEXT",
        "response_json": "JSON",
        "created_at": "DATETIME",
        "updated_at": "DATETIME",
    }
    with engine.begin() as connection:
        for name, definition in additions.items():
            if name not in columns:
                connection.execute(
                    text(f"ALTER TABLE discord_messages ADD COLUMN {name} {definition}")
                )
        for index_name, column_name in {
            "ix_discord_messages_competition_key": "competition_key",
            "ix_discord_messages_league_id": "league_id",
            "ix_discord_messages_season": "season",
            "ix_discord_messages_channel_key": "channel_key",
            "ix_discord_messages_message_type": "message_type",
            "ix_discord_messages_v3_model_prediction_id": "v3_model_prediction_id",
            "ix_discord_messages_ou_model_prediction_id": "ou_model_prediction_id",
            "ix_discord_messages_dedupe_key": "dedupe_key",
        }.items():
            connection.execute(
                text(
                    f"CREATE INDEX IF NOT EXISTS {index_name} "
                    f"ON discord_messages ({column_name})"
                )
            )


@contextmanager
def session_scope(session_factory: sessionmaker[Session]) -> Generator[Session, None, None]:
    session = session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
