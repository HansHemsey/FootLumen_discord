"""Read-only 1X2 prediction queries for the API."""

from __future__ import annotations

from datetime import date

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from football_predictor.db import models
from football_predictor.web_api.schemas.predictions import (
    Prediction1X2DTO,
    prediction_1x2_from_model,
    prediction_1x2_from_v3_model,
)
from football_predictor.web_api.services.fixture_read_service import (
    FixtureReadService,
    _local_day_bounds_utc,
    _zoneinfo,
)


class PredictionReadService:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._fixtures = FixtureReadService(session)

    def get_latest_for_fixture(self, fixture_id: int) -> Prediction1X2DTO | None:
        v3 = self._latest_v3_for_fixture(fixture_id)
        if v3 is not None:
            prediction, fixture = v3
            return prediction_1x2_from_v3_model(prediction, fixture)
        legacy = self._latest_legacy_for_fixture(fixture_id)
        if legacy is None:
            return None
        prediction, fixture = legacy
        return prediction_1x2_from_model(prediction, fixture)

    def list_latest(
        self,
        *,
        competition_key: str | None = None,
        target_date: date | None = None,
        timezone_name: str = "Europe/Paris",
        limit: int = 20,
        only_public: bool = False,
        include_no_bet: bool = True,
    ) -> list[Prediction1X2DTO]:
        bounded_limit = min(limit, 100)
        selected: dict[int, Prediction1X2DTO] = {}
        for prediction, fixture in self._query_v3(
            competition_key=competition_key,
            target_date=target_date,
            timezone_name=timezone_name,
            fetch_limit=max(bounded_limit * 5, 100),
        ):
            if fixture.fixture_id in selected:
                continue
            dto = prediction_1x2_from_v3_model(prediction, fixture)
            if _passes_prediction_filters(
                dto,
                only_public=only_public,
                include_no_bet=include_no_bet,
            ):
                selected[fixture.fixture_id] = dto

        for prediction, fixture in self._query_legacy(
            competition_key=competition_key,
            target_date=target_date,
            timezone_name=timezone_name,
            fetch_limit=max(bounded_limit * 5, 100),
        ):
            if fixture.fixture_id in selected:
                continue
            dto = prediction_1x2_from_model(prediction, fixture)
            if _passes_prediction_filters(
                dto,
                only_public=only_public,
                include_no_bet=include_no_bet,
            ):
                selected[fixture.fixture_id] = dto

        return sorted(
            selected.values(),
            key=lambda item: item.prediction_time or item.fixture.kickoff_at_utc,
            reverse=True,
        )[:bounded_limit]

    def _latest_v3_for_fixture(
        self,
        fixture_id: int,
    ) -> tuple[models.V3ModelPrediction, models.Fixture] | None:
        stmt = (
            select(models.V3ModelPrediction, models.Fixture)
            .join(models.Fixture, models.Fixture.fixture_id == models.V3ModelPrediction.fixture_id)
            .where(models.V3ModelPrediction.fixture_id == fixture_id)
            .order_by(
                models.V3ModelPrediction.prediction_time.desc(),
                models.V3ModelPrediction.id.desc(),
            )
            .limit(1)
        )
        row = self._session.execute(stmt).first()
        if row is None:
            return None
        prediction, fixture = row
        return prediction, fixture

    def _latest_legacy_for_fixture(
        self,
        fixture_id: int,
    ) -> tuple[models.ModelPrediction, models.Fixture] | None:
        stmt = (
            select(models.ModelPrediction, models.Fixture)
            .join(models.Fixture, models.Fixture.fixture_id == models.ModelPrediction.fixture_id)
            .where(models.ModelPrediction.fixture_id == fixture_id)
            .order_by(
                models.ModelPrediction.prediction_time.desc(),
                models.ModelPrediction.id.desc(),
            )
            .limit(1)
        )
        row = self._session.execute(stmt).first()
        if row is None:
            return None
        prediction, fixture = row
        return prediction, fixture

    def _query_v3(
        self,
        *,
        competition_key: str | None,
        target_date: date | None,
        timezone_name: str,
        fetch_limit: int,
    ) -> list[tuple[models.V3ModelPrediction, models.Fixture]]:
        stmt = (
            select(models.V3ModelPrediction, models.Fixture)
            .join(models.Fixture, models.Fixture.fixture_id == models.V3ModelPrediction.fixture_id)
            .order_by(
                models.V3ModelPrediction.prediction_time.desc(),
                models.V3ModelPrediction.id.desc(),
            )
            .limit(fetch_limit)
        )
        stmt = self._apply_fixture_filters(
            stmt,
            competition_key=competition_key,
            target_date=target_date,
            timezone_name=timezone_name,
        )
        rows = self._session.execute(stmt).all()
        return [(prediction, fixture) for prediction, fixture in rows]

    def _query_legacy(
        self,
        *,
        competition_key: str | None,
        target_date: date | None,
        timezone_name: str,
        fetch_limit: int,
    ) -> list[tuple[models.ModelPrediction, models.Fixture]]:
        stmt = (
            select(models.ModelPrediction, models.Fixture)
            .join(models.Fixture, models.Fixture.fixture_id == models.ModelPrediction.fixture_id)
            .order_by(
                models.ModelPrediction.prediction_time.desc(),
                models.ModelPrediction.id.desc(),
            )
            .limit(fetch_limit)
        )
        stmt = self._apply_fixture_filters(
            stmt,
            competition_key=competition_key,
            target_date=target_date,
            timezone_name=timezone_name,
        )
        rows = self._session.execute(stmt).all()
        return [(prediction, fixture) for prediction, fixture in rows]

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


def _passes_prediction_filters(
    dto: Prediction1X2DTO,
    *,
    only_public: bool,
    include_no_bet: bool,
) -> bool:
    decision = (dto.publication_decision or "").lower()
    if only_public and decision not in {"public", "public_published"}:
        return False
    return not (not include_no_bet and decision in {"no_bet", "no bet"})
