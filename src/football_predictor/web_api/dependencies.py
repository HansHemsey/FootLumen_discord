"""FastAPI dependencies for the read-only API."""

from __future__ import annotations

from collections.abc import Generator
from functools import lru_cache

from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from football_predictor.config.settings import Settings, get_settings
from football_predictor.db.session import create_db_engine, create_session_factory


def get_api_settings() -> Settings:
    return get_settings()


@lru_cache(maxsize=4)
def _engine_for_url(database_url: str) -> Engine:
    return create_db_engine(database_url)


def get_read_only_session() -> Generator[Session, None, None]:
    """Yield a DB session that is always rolled back and never committed."""

    settings = get_settings()
    engine = _engine_for_url(settings.database_url)
    session_factory = create_session_factory(engine)
    session = session_factory()
    try:
        yield session
    finally:
        session.rollback()
        session.close()
