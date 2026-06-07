"""Read-only O/U prediction queries for the API."""

from __future__ import annotations

from datetime import date

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from football_predictor.db import models
from football_predictor.web_api.schemas.ou import OUPredictionDTO, ou_prediction_from_model
from football_predictor.web_api.services.fixture_read_service import (
    FixtureReadService,
    _local_day_bounds_utc,
    _zoneinfo,
)


class OUReadService:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._fixtures = FixtureReadService(session)

    def get_latest_for_fixture(self, fixture_id: int) -> OUPredictionDTO | None:
        stmt = (
            select(models.OUModelPrediction, models.Fixture)
            .join(models.Fixture, models.Fixture.fixture_id == models.OUModelPrediction.fixture_id)
            .where(models.OUModelPrediction.fixture_id == fixture_id)
            .order_by(
                models.OUModelPrediction.prediction_time.desc(),
                models.OUModelPrediction.id.desc(),
            )
            .limit(1)
        )
        row = self._session.execute(stmt).first()
        if row is None:
            return None
        prediction, fixture = row
        return ou_prediction_from_model(prediction, fixture)

    def list_latest(
        self,
        *,
        competition_key: str | None = None,
        target_date: date | None = None,
        timezone_name: str = "Europe/Paris",
        limit: int = 20,
        only_value_picks: bool = False,
        include_no_bet: bool = True,
    ) -> list[OUPredictionDTO]:
        bounded_limit = min(limit, 100)
        stmt = (
            select(models.OUModelPrediction, models.Fixture)
            .join(models.Fixture, models.Fixture.fixture_id == models.OUModelPrediction.fixture_id)
            .order_by(
                models.OUModelPrediction.prediction_time.desc(),
                models.OUModelPrediction.id.desc(),
            )
            .limit(max(bounded_limit * 5, 100))
        )
        stmt = self._apply_fixture_filters(
            stmt,
            competition_key=competition_key,
            target_date=target_date,
            timezone_name=timezone_name,
        )
        selected: dict[int, OUPredictionDTO] = {}
        for prediction, fixture in self._session.execute(stmt).all():
            if fixture.fixture_id in selected:
                continue
            dto = ou_prediction_from_model(prediction, fixture)
            if _passes_ou_filters(
                dto,
                only_value_picks=only_value_picks,
                include_no_bet=include_no_bet,
            ):
                selected[fixture.fixture_id] = dto
        return sorted(
            selected.values(),
            key=lambda item: item.prediction_time or item.fixture.kickoff_at_utc,
            reverse=True,
        )[:bounded_limit]

    def _apply_fixture_filters(
        self,
        stmt: Select,
        *,
        competition_key: str | None,
        target_date: date | None,
        timezone_name: str,
    ) -> Select:
        if competition_key:
            competition = self._fixtures.get_competition(competition_key)
            if competition is None:
                return stmt.where(models.Fixture.fixture_id == -1)
            stmt = stmt.where(
                models.Fixture.league_id == competition.league_id,
                models.Fixture.season == competition.season,
            )
        if target_date is not None:
            start_utc, end_utc = _local_day_bounds_utc(target_date, _zoneinfo(timezone_name))
            stmt = stmt.where(models.Fixture.date >= start_utc, models.Fixture.date < end_utc)
        return stmt


def _passes_ou_filters(
    dto: OUPredictionDTO,
    *,
    only_value_picks: bool,
    include_no_bet: bool,
) -> bool:
    if only_value_picks and not dto.value_side:
        return False
    decision = (dto.publication_decision or "").lower()
    return not (
        not include_no_bet and (dto.no_bet_reason or decision in {"no_bet", "no bet"})
    )
