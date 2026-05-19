"""Value-based decision layer for O/U 2.5 predictions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from football_predictor.ou_model.prediction.ou_publication_policy import (
    evaluate_ou_publication,
)

OUSide = Literal["OVER", "UNDER"]
OUPublicationDecision = Literal["public", "staff", "no_bet"]
OUNoBetReason = Literal[
    "market_unavailable",
    "edge_below_threshold",
    "ev_below_threshold",
    "invalid_odds",
]

DECISION_VERSION = "ou_decision_v2"
MIN_VALUE_EDGE = 0.03
MIN_VALUE_EV = 0.03

JsonDict = dict[str, Any]


@dataclass(frozen=True)
class OUValueCandidate:
    side: OUSide
    probability: float
    market_probability: float | None
    market_odd: float | None
    edge: float | None
    ev: float | None


@dataclass(frozen=True)
class OUDecision:
    decision_version: str
    forecast_side: OUSide
    forecast_probability: float
    value_side: OUSide | None
    value_probability: float | None
    value_market_probability: float | None
    value_market_odd: float | None
    value_edge: float | None
    value_ev: float | None
    p_pick: float | None
    market_p_pick: float | None
    odd_pick: float | None
    edge_pick: float | None
    ev_pick: float | None
    is_value_pick: bool
    no_bet_reason: OUNoBetReason | None
    non_publication_reason: str | None
    confidence_score_v2: float
    confidence_label_v2: str
    publication_decision: OUPublicationDecision
    data_quality_score: float | None
    bookmaker_count: float | None
    edge_over: float | None
    edge_under: float | None
    ev_over: float | None
    ev_under: float | None

    def as_payload(self) -> JsonDict:
        return {
            "decision_version": self.decision_version,
            "forecast_side": self.forecast_side,
            "forecast_probability": self.forecast_probability,
            "value_side": self.value_side,
            "value_probability": self.value_probability,
            "value_market_probability": self.value_market_probability,
            "value_market_odd": self.value_market_odd,
            "value_edge": self.value_edge,
            "value_ev": self.value_ev,
            "p_pick": self.p_pick,
            "market_p_pick": self.market_p_pick,
            "odd_pick": self.odd_pick,
            "edge_pick": self.edge_pick,
            "ev_pick": self.ev_pick,
            "is_value_pick": self.is_value_pick,
            "no_bet_reason": self.no_bet_reason,
            "non_publication_reason": self.non_publication_reason,
            "confidence_score_v2": self.confidence_score_v2,
            "confidence_label_v2": self.confidence_label_v2,
            "publication_decision": self.publication_decision,
            "data_quality_score": self.data_quality_score,
            "bookmaker_count": self.bookmaker_count,
        }


def decide_ou_prediction(
    *,
    p_over: float,
    p_under: float,
    market_p_over: float | None,
    market_p_under: float | None,
    odd_over: float | None,
    odd_under: float | None,
    data_quality_json: JsonDict | None = None,
    calibration_score: float | None = None,
    min_value_edge: float = MIN_VALUE_EDGE,
    min_value_ev: float = MIN_VALUE_EV,
) -> OUDecision:
    """Return forecast, value side, no-bet reason, and value-based confidence.

    The model forecast and betting decision are intentionally separate:
    the most probable side is not automatically a value pick.
    """
    p_over = _clamp_probability(p_over)
    p_under = _clamp_probability(p_under)
    forecast_side: OUSide = "OVER" if p_over >= p_under else "UNDER"
    forecast_probability = max(p_over, p_under)

    invalid_odds = _is_invalid_present_odd(odd_over) or _is_invalid_present_odd(odd_under)
    if invalid_odds:
        return _no_bet_decision(
            forecast_side=forecast_side,
            forecast_probability=forecast_probability,
            reason="invalid_odds",
        )

    if market_p_over is None or market_p_under is None or odd_over is None or odd_under is None:
        return _no_bet_decision(
            forecast_side=forecast_side,
            forecast_probability=forecast_probability,
            reason="market_unavailable",
        )

    edge_over = p_over - market_p_over
    edge_under = p_under - market_p_under
    ev_over = p_over * odd_over - 1.0
    ev_under = p_under * odd_under - 1.0

    candidates = [
        OUValueCandidate("OVER", p_over, market_p_over, odd_over, edge_over, ev_over),
        OUValueCandidate("UNDER", p_under, market_p_under, odd_under, edge_under, ev_under),
    ]
    ev_candidates = [
        candidate
        for candidate in candidates
        if candidate.ev is not None and candidate.ev >= min_value_ev
    ]
    if not ev_candidates:
        return _no_bet_decision(
            forecast_side=forecast_side,
            forecast_probability=forecast_probability,
            reason="ev_below_threshold",
            edge_over=edge_over,
            edge_under=edge_under,
            ev_over=ev_over,
            ev_under=ev_under,
        )

    value_candidates = [
        candidate
        for candidate in ev_candidates
        if candidate.edge is not None and candidate.edge >= min_value_edge
    ]
    if not value_candidates:
        return _no_bet_decision(
            forecast_side=forecast_side,
            forecast_probability=forecast_probability,
            reason="edge_below_threshold",
            edge_over=edge_over,
            edge_under=edge_under,
            ev_over=ev_over,
            ev_under=ev_under,
        )

    value = max(value_candidates, key=lambda c: (c.ev or 0.0, c.edge or 0.0))
    data_quality_score = _data_quality_score(data_quality_json)
    bookmaker_count = _bookmaker_count(data_quality_json)
    confidence = _confidence_score_v2(
        p_pick=value.probability,
        edge_pick=value.edge or 0.0,
        ev_pick=value.ev or 0.0,
        data_quality_json=data_quality_json,
        calibration_score=calibration_score,
    )
    label = confidence_label_v2(confidence)
    publication = evaluate_ou_publication(
        value_side=value.side,
        edge_pick=value.edge,
        ev_pick=value.ev,
        confidence_score_v2=confidence,
        data_quality_score=data_quality_score,
        bookmaker_count=bookmaker_count,
    )
    return OUDecision(
        decision_version=DECISION_VERSION,
        forecast_side=forecast_side,
        forecast_probability=forecast_probability,
        value_side=value.side,
        value_probability=value.probability,
        value_market_probability=value.market_probability,
        value_market_odd=value.market_odd,
        value_edge=value.edge,
        value_ev=value.ev,
        p_pick=value.probability,
        market_p_pick=value.market_probability,
        odd_pick=value.market_odd,
        edge_pick=value.edge,
        ev_pick=value.ev,
        is_value_pick=True,
        no_bet_reason=None,
        non_publication_reason=publication.reason,
        confidence_score_v2=confidence,
        confidence_label_v2=label,
        publication_decision=publication.decision,
        data_quality_score=data_quality_score,
        bookmaker_count=bookmaker_count,
        edge_over=edge_over,
        edge_under=edge_under,
        ev_over=ev_over,
        ev_under=ev_under,
    )


def confidence_label_v2(score: float) -> str:
    if score >= 80:
        return "Very High"
    if score >= 65:
        return "High"
    if score >= 50:
        return "Medium"
    if score >= 35:
        return "Low"
    return "Uncertain"


def _confidence_score_v2(
    *,
    p_pick: float,
    edge_pick: float,
    ev_pick: float,
    data_quality_json: JsonDict | None,
    calibration_score: float | None,
) -> float:
    data_quality_score = _data_quality_score(data_quality_json)
    bookmaker_count = _bookmaker_count(data_quality_json)
    calibration = _clamp01(
        calibration_score
        if calibration_score is not None
        else _number_from_payload(data_quality_json, ("calibration_score",), default=0.7)
    )
    separation_component = _clamp01(max(p_pick - 0.50, 0.0) / 0.12)
    edge_component = _clamp01(max(edge_pick, 0.0) / 0.06)
    ev_component = _clamp01(max(ev_pick, 0.0) / 0.08)
    quality_component = _clamp01(data_quality_score / 100.0)
    market_component = _clamp01((bookmaker_count or 0.0) / 6.0)
    score = 100.0 * (
        0.25 * separation_component
        + 0.30 * edge_component
        + 0.20 * ev_component
        + 0.10 * quality_component
        + 0.10 * calibration
        + 0.05 * market_component
    )
    return round(_clamp(score, 0.0, 100.0), 1)


def _no_bet_decision(
    *,
    forecast_side: OUSide,
    forecast_probability: float,
    reason: OUNoBetReason,
    edge_over: float | None = None,
    edge_under: float | None = None,
    ev_over: float | None = None,
    ev_under: float | None = None,
) -> OUDecision:
    return OUDecision(
        decision_version=DECISION_VERSION,
        forecast_side=forecast_side,
        forecast_probability=forecast_probability,
        value_side=None,
        value_probability=None,
        value_market_probability=None,
        value_market_odd=None,
        value_edge=None,
        value_ev=None,
        p_pick=None,
        market_p_pick=None,
        odd_pick=None,
        edge_pick=None,
        ev_pick=None,
        is_value_pick=False,
        no_bet_reason=reason,
        non_publication_reason=reason,
        confidence_score_v2=0.0,
        confidence_label_v2="Uncertain",
        publication_decision="no_bet",
        data_quality_score=None,
        bookmaker_count=None,
        edge_over=edge_over,
        edge_under=edge_under,
        ev_over=ev_over,
        ev_under=ev_under,
    )


def _data_quality_score(payload: JsonDict | None) -> float:
    return _number_from_payload(
        payload,
        (
            "ou_data_quality_score",
            "overall_data_quality_score",
            "publication_data_quality_score",
            "data_quality_score",
        ),
        default=50.0,
    )


def _bookmaker_count(payload: JsonDict | None) -> float | None:
    return _number_from_payload(
        payload,
        (
            "ou_market_bookmaker_count",
            "market_ou_bookmaker_count",
            "market_bookmaker_count",
            "bookmaker_count",
        ),
        default=None,
    )


def _number_from_payload(
    payload: JsonDict | None,
    keys: tuple[str, ...],
    *,
    default: float | None,
) -> float | None:
    if not isinstance(payload, dict):
        return default
    for key in keys:
        value = payload.get(key)
        if value is None:
            continue
        try:
            return float(value)
        except (TypeError, ValueError):
            continue
    return default


def _is_invalid_present_odd(value: float | None) -> bool:
    return value is not None and value <= 1.0


def _clamp_probability(value: float) -> float:
    return _clamp(float(value), 0.0, 1.0)


def _clamp01(value: float) -> float:
    return _clamp(value, 0.0, 1.0)


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))
