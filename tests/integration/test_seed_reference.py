from __future__ import annotations

from sqlalchemy import func, select

from football_predictor.db import models
from football_predictor.db.session import (
    create_db_engine,
    create_session_factory,
    init_db,
    session_scope,
)
from football_predictor.ingestion.seed_reference import seed_reference_from_docs


def test_seed_reference_from_docs_is_idempotent(
    tmp_path, reference_path, players_reference_path
) -> None:
    database_url = f"sqlite:///{tmp_path / 'football_predictor.db'}"
    engine = create_db_engine(database_url)
    init_db(engine)
    session_factory = create_session_factory(engine)

    with session_scope(session_factory) as session:
        first = seed_reference_from_docs(session, reference_path, players_reference_path)
    with session_scope(session_factory) as session:
        second = seed_reference_from_docs(session, reference_path, players_reference_path)
        counts = {
            "leagues": session.scalar(select(func.count()).select_from(models.League)),
            "teams": session.scalar(select(func.count()).select_from(models.Team)),
            "venues": session.scalar(select(func.count()).select_from(models.Venue)),
            "fixtures": session.scalar(select(func.count()).select_from(models.Fixture)),
            "bookmakers": session.scalar(select(func.count()).select_from(models.Bookmaker)),
            "bets": session.scalar(select(func.count()).select_from(models.Bet)),
            "players": session.scalar(select(func.count()).select_from(models.Player)),
            "squads": session.scalar(select(func.count()).select_from(models.PlayerSquad)),
        }
        seeded_fixture = session.scalar(select(models.Fixture).limit(1))
        seeded_squad = session.scalar(select(models.PlayerSquad).limit(1))

    assert first.errors == []
    assert second.errors == []
    assert first.seasons == 6
    assert first.rounds > 0
    assert first.skipped == 0
    assert counts["leagues"] == 6
    assert counts["teams"] == 144
    assert counts["venues"] == 145
    assert counts["fixtures"] == 1824
    assert counts["bookmakers"] == 33
    assert counts["bets"] == 603
    assert counts["players"] == 4053
    assert counts["squads"] == 4645
    assert seeded_fixture is not None
    assert seeded_fixture.status == (seeded_fixture.status_short or seeded_fixture.status_long)
    assert seeded_squad is not None
    assert seeded_squad.fetched_at is not None
