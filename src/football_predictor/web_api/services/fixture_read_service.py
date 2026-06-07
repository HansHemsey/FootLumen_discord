"""Read-only fixture queries for the API."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from football_predictor.db import models
from football_predictor.web_api.schemas.fixtures import (
    FixtureSummaryDTO,
    fixture_summary_from_model,
)


class FixtureReadService:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_fixture(self, fixture_id: int) -> FixtureSummaryDTO | None:
        fixture = self._session.get(models.Fixture, fixture_id)
        if fixture is None:
            return None
        return fixture_summary_from_model(fixture)

    def list_upcoming(
        self,
        *,
        limit: int = 25,
        date_from: datetime | None = None,
        competition_key: str | None = None,
    ) -> list[FixtureSummaryDTO]:
        stmt = select(models.Fixture).order_by(models.Fixture.date.asc()).limit(min(limit, 100))
        if date_from is not None:
            stmt = stmt.where(models.Fixture.date >= date_from)
        if competition_key == "fifa_world_cup_2026":
            stmt = stmt.where(models.Fixture.league_id == 1, models.Fixture.season == 2026)
        fixtures = self._session.scalars(stmt).all()
        return [
            fixture_summary_from_model(fixture, competition_key=competition_key)
            for fixture in fixtures
        ]
