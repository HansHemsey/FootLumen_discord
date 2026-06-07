"""Public performance DTOs for the FootLumen API."""

from __future__ import annotations

from datetime import date, datetime

from football_predictor.web_api.schemas.common import PublicModel


class PerformanceMetric(PublicModel):
    name: str
    value: float | int | str | None
    sample_size: int | None = None


class MarketPerformanceSummary(PublicModel):
    market: str
    total_predictions: int
    public_predictions: int | None = None
    no_bet: int | None = None
    settled_predictions: int | None = None
    successful_predictions: int | None = None
    note: str | None = None


class CompetitionPerformanceSummary(PublicModel):
    competition_key: str | None = None
    total_predictions: int = 0
    total_ou_predictions: int = 0
    total_combos: int = 0


class PerformanceSummaryDTO(PublicModel):
    generated_at: datetime
    scope: str = "global"
    period_start: date | None = None
    period_end: date | None = None
    total_predictions: int = 0
    total_public_predictions: int | None = None
    total_no_bet: int | None = None
    total_ou_predictions: int = 0
    total_combos: int = 0
    settled_predictions: int | None = None
    successful_predictions: int | None = None
    roi: float | None = None
    roi_note: str = "ROI non expose tant que la donnee n'est pas fiable."
    by_market: list[MarketPerformanceSummary] = []
    by_competition: list[CompetitionPerformanceSummary] = []
    notes: list[str] = []
    metrics: list[PerformanceMetric] = []
