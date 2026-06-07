"""Public performance DTOs for the FootLumen API."""

from __future__ import annotations

from datetime import datetime

from football_predictor.web_api.schemas.common import PublicModel


class PerformanceMetric(PublicModel):
    name: str
    value: float | int | str | None
    sample_size: int | None = None


class PerformanceSummaryDTO(PublicModel):
    generated_at: datetime
    scope: str = "global"
    metrics: list[PerformanceMetric] = []
