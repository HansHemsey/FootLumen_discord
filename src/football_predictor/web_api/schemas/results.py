"""Public recent result DTOs for the FootLumen API."""

from __future__ import annotations

from football_predictor.web_api.schemas.common import PaginationMeta, PublicModel
from football_predictor.web_api.schemas.fixtures import FixtureSummaryDTO


class ResultPredictionSummary(PublicModel):
    prediction_id: int
    model_version: str | None = None
    predicted_result: str | None = None
    confidence_label: str | None = None
    confidence_score: float | None = None
    publication_decision: str | None = None
    correct: bool | None = None


class ResultOUPredictionSummary(PublicModel):
    prediction_id: int
    model_version: str | None = None
    threshold: float | None = None
    forecast_side: str | None = None
    value_side: str | None = None
    confidence_label: str | None = None
    confidence_score: float | None = None
    publication_decision: str | None = None
    pick_result: str | None = None


class RecentResultDTO(PublicModel):
    fixture: FixtureSummaryDTO
    home_goals: int | None = None
    away_goals: int | None = None
    result_1x2: str | None = None
    ou_result: str | None = None
    prediction_1x2: ResultPredictionSummary | None = None
    ou_prediction: ResultOUPredictionSummary | None = None
    combo_ticket_count: int = 0
    combo_statuses: list[str] = []


class RecentResultsResponse(PublicModel):
    items: list[RecentResultDTO]
    meta: PaginationMeta
