"""Read-only performance summaries for the API."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from football_predictor.db import models
from football_predictor.utils.time import utc_now
from football_predictor.web_api.schemas.performance import PerformanceMetric, PerformanceSummaryDTO


class PerformanceReadService:
    def __init__(self, session: Session) -> None:
        self._session = session

    def summary(self) -> PerformanceSummaryDTO:
        predictions_count = self._session.scalar(select(func.count(models.ModelPrediction.id))) or 0
        ou_predictions_count = (
            self._session.scalar(select(func.count(models.OUModelPrediction.id))) or 0
        )
        combo_count = self._session.scalar(select(func.count(models.ComboTicket.id))) or 0
        return PerformanceSummaryDTO(
            generated_at=utc_now(),
            metrics=[
                PerformanceMetric(name="1x2_predictions", value=int(predictions_count)),
                PerformanceMetric(name="ou_predictions", value=int(ou_predictions_count)),
                PerformanceMetric(name="combo_tickets", value=int(combo_count)),
            ],
        )
