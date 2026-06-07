"""Read-only 1X2 prediction queries for the API."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from football_predictor.db import models
from football_predictor.web_api.schemas.predictions import (
    Prediction1X2DTO,
    prediction_1x2_from_model,
)


class PredictionReadService:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_latest_for_fixture(self, fixture_id: int) -> Prediction1X2DTO | None:
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
        return prediction_1x2_from_model(prediction, fixture)

    def list_latest(self, *, limit: int = 25) -> list[Prediction1X2DTO]:
        stmt = (
            select(models.ModelPrediction, models.Fixture)
            .join(models.Fixture, models.Fixture.fixture_id == models.ModelPrediction.fixture_id)
            .order_by(
                models.ModelPrediction.prediction_time.desc(),
                models.ModelPrediction.id.desc(),
            )
            .limit(min(limit, 100))
        )
        rows = self._session.execute(stmt).all()
        return [prediction_1x2_from_model(prediction, fixture) for prediction, fixture in rows]
