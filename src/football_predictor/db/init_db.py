"""Database initialization helpers."""

from __future__ import annotations

from sqlalchemy.engine import Engine

from football_predictor.db.session import create_db_engine, init_db


def create_db_and_tables(database_url: str, echo: bool = False) -> Engine:
    """Create an engine and initialize all SQLAlchemy tables.

    This helper is intentionally small for local bootstrap and tests. Durable databases
    should use Alembic migrations.
    """
    engine = create_db_engine(database_url, echo=echo)
    init_db(engine)
    return engine
