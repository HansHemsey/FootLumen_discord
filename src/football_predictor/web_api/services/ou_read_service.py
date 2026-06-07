"""Read-only O/U prediction queries for the API."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from football_predictor.db import models
from football_predictor.web_api.schemas.ou import OUPredictionDTO, ou_prediction_from_model


class OUReadService:
    def __init__(self, session: Session) -> None:
        self._session = session

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

    def list_latest(self, *, limit: int = 25) -> list[OUPredictionDTO]:
        stmt = (
            select(models.OUModelPrediction, models.Fixture)
            .join(models.Fixture, models.Fixture.fixture_id == models.OUModelPrediction.fixture_id)
            .order_by(
                models.OUModelPrediction.prediction_time.desc(),
                models.OUModelPrediction.id.desc(),
            )
            .limit(min(limit, 100))
        )
        rows = self._session.execute(stmt).all()
        return [ou_prediction_from_model(prediction, fixture) for prediction, fixture in rows]
