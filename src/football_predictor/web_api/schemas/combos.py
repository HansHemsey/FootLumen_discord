"""Public World Cup combo DTOs."""

from __future__ import annotations

from typing import Any

from football_predictor.web_api.schemas.common import (
    PublicModel,
    public_warnings_from_json,
    safe_datetime,
    safe_float,
)


class ComboLegDTO(PublicModel):
    fixture_id: int
    match_label: str | None = None
    kickoff_at_utc: object
    market_type: str
    market_scope: str
    selection: str
    decimal_odd: float | None
    model_probability: float | None
    market_probability: float | None
    edge: float | None
    ev: float | None
    confidence_score: float | None
    confidence_label: str | None
    data_quality_score: float | None
    lineup_status: str | None
    bookmaker_name: str | None = None
    executable_decimal_odd: float | None = None
    warnings_public: list[object] = []


class ComboTicketDTO(PublicModel):
    ticket_key: str
    status: str
    combo_date: object
    session_key: str
    first_kickoff_at: object
    last_kickoff_at: object
    lock_time: object
    legs_count: int
    combined_decimal_odds: float | None
    combined_probability_adjusted: float | None
    combined_fair_odds: float | None
    combined_ev_adjusted: float | None
    combined_confidence_score: float | None
    combined_confidence_label: str | None
    post_lock_risk_score: float | None
    freshness_score: float | None
    lineup_risk_score: float | None
    publication_decision: str | None
    no_publish_reason: str | None
    warnings_public: list[object] = []
    legs: list[ComboLegDTO]


def combo_leg_from_model(leg: Any) -> ComboLegDTO:
    payload = getattr(leg, "payload_json", None)
    allowed_payload = payload if isinstance(payload, dict) else {}
    bookmaker_name = _safe_optional_string(allowed_payload.get("bookmaker_name"))
    return ComboLegDTO(
        fixture_id=int(leg.fixture_id),
        match_label=_safe_optional_string(allowed_payload.get("match_label")),
        kickoff_at_utc=safe_datetime(getattr(leg, "kickoff_at_utc", None)),
        market_type=str(leg.market_type),
        market_scope=str(leg.market_scope),
        selection=str(leg.selection),
        decimal_odd=safe_float(getattr(leg, "decimal_odd", None)),
        model_probability=safe_float(getattr(leg, "model_probability", None)),
        market_probability=safe_float(getattr(leg, "market_probability", None)),
        edge=safe_float(getattr(leg, "edge", None)),
        ev=safe_float(getattr(leg, "ev", None)),
        confidence_score=safe_float(getattr(leg, "confidence_score", None)),
        confidence_label=getattr(leg, "confidence_label", None),
        data_quality_score=safe_float(getattr(leg, "data_quality_score", None)),
        lineup_status=getattr(leg, "lineup_status", None),
        bookmaker_name=bookmaker_name,
        executable_decimal_odd=safe_float(allowed_payload.get("executable_decimal_odd")),
        warnings_public=public_warnings_from_json(getattr(leg, "warnings_json", None)),
    )


def combo_ticket_from_model(ticket: Any, legs: list[Any] | tuple[Any, ...]) -> ComboTicketDTO:
    return ComboTicketDTO(
        ticket_key=str(ticket.ticket_key),
        status=str(ticket.status),
        combo_date=getattr(ticket, "combo_date", None),
        session_key=str(ticket.session_key),
        first_kickoff_at=safe_datetime(getattr(ticket, "first_kickoff_at", None)),
        last_kickoff_at=safe_datetime(getattr(ticket, "last_kickoff_at", None)),
        lock_time=safe_datetime(getattr(ticket, "lock_time", None)),
        legs_count=int(ticket.legs_count),
        combined_decimal_odds=safe_float(getattr(ticket, "combined_decimal_odds", None)),
        combined_probability_adjusted=safe_float(
            getattr(ticket, "combined_probability_adjusted", None)
        ),
        combined_fair_odds=safe_float(getattr(ticket, "combined_fair_odds", None)),
        combined_ev_adjusted=safe_float(getattr(ticket, "combined_ev_adjusted", None)),
        combined_confidence_score=safe_float(getattr(ticket, "combined_confidence_score", None)),
        combined_confidence_label=getattr(ticket, "combined_confidence_label", None),
        post_lock_risk_score=safe_float(getattr(ticket, "post_lock_risk_score", None)),
        freshness_score=safe_float(getattr(ticket, "freshness_score", None)),
        lineup_risk_score=safe_float(getattr(ticket, "lineup_risk_score", None)),
        publication_decision=getattr(ticket, "publication_decision", None),
        no_publish_reason=getattr(ticket, "no_publish_reason", None),
        warnings_public=public_warnings_from_json(getattr(ticket, "warnings_json", None)),
        legs=[combo_leg_from_model(leg) for leg in legs],
    )


def _safe_optional_string(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
