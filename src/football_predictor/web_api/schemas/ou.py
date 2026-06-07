"""Public O/U prediction DTOs."""

from __future__ import annotations

from typing import Any

from football_predictor.web_api.schemas.common import (
    PublicModel,
    data_quality_score_from_json,
    safe_datetime,
    safe_float,
)
from football_predictor.web_api.schemas.fixtures import (
    FixtureSummaryDTO,
    fixture_summary_from_model,
)


class OUPredictionDTO(PublicModel):
    fixture: FixtureSummaryDTO
    prediction_id: int
    prediction_time: object
    model_version: str
    threshold: float | None
    forecast_side: str | None
    forecast_probability: float | None
    value_side: str | None
    p_pick: float | None
    edge_pick: float | None
    ev_pick: float | None
    confidence_score_v2: float | None
    confidence_label_v2: str | None
    publication_decision: str | None
    no_bet_reason: str | None
    data_quality_score: float | None


def ou_prediction_from_model(prediction: Any, fixture: Any) -> OUPredictionDTO:
    data_quality_score = data_quality_score_from_json(
        getattr(prediction, "data_quality_json", None)
    )
    return OUPredictionDTO(
        fixture=fixture_summary_from_model(
            fixture,
            has_ou_prediction=True,
            data_quality_score=data_quality_score,
        ),
        prediction_id=int(prediction.id),
        prediction_time=safe_datetime(getattr(prediction, "prediction_time", None)),
        model_version=str(prediction.model_version),
        threshold=safe_float(getattr(prediction, "threshold", None)),
        forecast_side=getattr(prediction, "forecast_side", None),
        forecast_probability=safe_float(getattr(prediction, "forecast_probability", None)),
        value_side=getattr(prediction, "value_side", None),
        p_pick=safe_float(getattr(prediction, "p_pick", None)),
        edge_pick=safe_float(getattr(prediction, "edge_pick", None)),
        ev_pick=safe_float(getattr(prediction, "ev_pick", None)),
        confidence_score_v2=safe_float(
            getattr(prediction, "confidence_score_v2", None)
            or getattr(prediction, "confidence_score", None)
        ),
        confidence_label_v2=getattr(prediction, "confidence_label_v2", None)
        or getattr(prediction, "confidence_label", None),
        publication_decision=getattr(prediction, "publication_decision", None),
        no_bet_reason=getattr(prediction, "no_bet_reason", None),
        data_quality_score=data_quality_score,
    )
