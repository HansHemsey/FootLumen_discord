"""Public 1X2 prediction DTOs."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from football_predictor.web_api.schemas.common import (
    ConfidenceSummary,
    DataQualitySummary,
    PaginationMeta,
    PublicModel,
    data_quality_score_from_json,
    data_quality_summary_from_json,
    public_explanations_from_json,
    public_warnings_from_json,
    safe_datetime,
    safe_float,
)
from football_predictor.web_api.schemas.fixtures import (
    FixtureSummaryDTO,
    fixture_summary_from_model,
)


class Prediction1X2DTO(PublicModel):
    fixture: FixtureSummaryDTO
    prediction_id: int
    prediction_time: datetime | None
    model_version: str
    p_home: float | None
    p_draw: float | None
    p_away: float | None
    predicted_result: str | None
    confidence_score: float | None
    confidence_label: str | None
    data_quality_score: float | None
    publication_decision: str | None = None
    explanations_public: list[str] = []
    warnings_public: list[object] = []
    confidence: ConfidenceSummary | None = None
    data_quality: DataQualitySummary | None = None


class Prediction1X2ListResponse(PublicModel):
    items: list[Prediction1X2DTO]
    meta: PaginationMeta


def prediction_1x2_from_model(prediction: Any, fixture: Any) -> Prediction1X2DTO:
    data_quality_payload = getattr(prediction, "data_quality_json", None)
    warnings_payload = _warnings_payload(prediction)
    confidence_score = safe_float(getattr(prediction, "confidence_score", None))
    confidence_label = getattr(prediction, "confidence_label", None)
    data_quality_score = data_quality_score_from_json(data_quality_payload)
    return Prediction1X2DTO(
        fixture=fixture_summary_from_model(fixture, data_quality_score=data_quality_score),
        prediction_id=int(prediction.id),
        prediction_time=safe_datetime(getattr(prediction, "prediction_time", None)),
        model_version=str(prediction.model_version),
        p_home=safe_float(getattr(prediction, "p_home", None)),
        p_draw=safe_float(getattr(prediction, "p_draw", None)),
        p_away=safe_float(getattr(prediction, "p_away", None)),
        predicted_result=getattr(prediction, "predicted_result", None),
        confidence_score=confidence_score,
        confidence_label=confidence_label,
        data_quality_score=data_quality_score,
        publication_decision=_publication_decision(prediction),
        explanations_public=public_explanations_from_json(
            getattr(prediction, "explanations_json", None)
            or getattr(prediction, "explanation_json", None)
        ),
        warnings_public=public_warnings_from_json(warnings_payload),
        confidence=ConfidenceSummary(score=confidence_score, label=confidence_label),
        data_quality=data_quality_summary_from_json(data_quality_payload),
    )


def _publication_decision(prediction: Any) -> str | None:
    payload = getattr(prediction, "payload_json", None)
    if isinstance(payload, dict):
        value = payload.get("publication_decision") or payload.get("publication_policy")
        return str(value) if value is not None else None
    return None


def _warnings_payload(prediction: Any) -> Any:
    payload = getattr(prediction, "payload_json", None)
    data_quality = getattr(prediction, "data_quality_json", None)
    if isinstance(payload, dict) and "warnings" in payload:
        return payload["warnings"]
    if isinstance(data_quality, dict) and "warnings" in data_quality:
        return data_quality["warnings"]
    return []


def prediction_1x2_from_v3_model(prediction: Any, fixture: Any) -> Prediction1X2DTO:
    data_quality_payload = getattr(prediction, "data_quality_json", None)
    warnings_payload = _warnings_payload(prediction)
    confidence_score = safe_float(getattr(prediction, "confidence_score", None))
    confidence_label = getattr(prediction, "confidence_label", None)
    data_quality_score = safe_float(getattr(prediction, "data_quality_score", None))
    if data_quality_score is None:
        data_quality_score = data_quality_score_from_json(data_quality_payload)
    return Prediction1X2DTO(
        fixture=fixture_summary_from_model(fixture, data_quality_score=data_quality_score),
        prediction_id=int(prediction.id),
        prediction_time=safe_datetime(getattr(prediction, "prediction_time", None)),
        model_version=str(prediction.model_version),
        p_home=safe_float(getattr(prediction, "p_v3_final_home", None)),
        p_draw=safe_float(getattr(prediction, "p_v3_final_draw", None)),
        p_away=safe_float(getattr(prediction, "p_v3_final_away", None)),
        predicted_result=getattr(prediction, "predicted_result", None),
        confidence_score=confidence_score,
        confidence_label=confidence_label,
        data_quality_score=data_quality_score,
        publication_decision=_publication_decision(prediction),
        explanations_public=public_explanations_from_json(
            getattr(prediction, "explanations_json", None)
        ),
        warnings_public=public_warnings_from_json(warnings_payload),
        confidence=ConfidenceSummary(score=confidence_score, label=confidence_label),
        data_quality=data_quality_summary_from_json(data_quality_payload),
    )
