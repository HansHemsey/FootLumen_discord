"""Scoring utilities for World Cup combo tickets."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

from football_predictor.world_cup_combos.enums import ComboMarketScope
from football_predictor.world_cup_combos.models import ComboLegCandidate

JsonDict = dict[str, Any]


@dataclass(frozen=True)
class ComboScoringResult:
    combined_decimal_odds: float
    combined_probability_raw: float
    combined_probability_adjusted: float
    combined_fair_odds: float
    combined_ev_raw: float
    combined_ev_adjusted: float
    combined_confidence_score: float
    combined_confidence_label: str
    post_lock_risk_score: float
    freshness_score: float
    lineup_risk_score: float
    correlation_penalty: float
    penalties_json: JsonDict = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)


class WorldCupComboScoring:
    """Calculate combined value, adjusted probability, confidence, and risks."""

    def score(
        self,
        legs: tuple[ComboLegCandidate, ...],
        *,
        is_matchday3: bool = False,
        is_knockout: bool = False,
        same_group_violation: bool = False,
        correlated: bool = False,
    ) -> ComboScoringResult:
        if not legs:
            raise ValueError("At least one combo leg is required")

        combined_decimal_odds = _product(leg.decimal_odd for leg in legs)
        combined_probability_raw = _product(leg.model_probability for leg in legs)
        combined_ev_raw = combined_probability_raw * combined_decimal_odds - 1.0

        post_lock_risk_score = _post_lock_risk_score(legs, is_matchday3, is_knockout)
        freshness_score = _freshness_score(legs)
        lineup_risk_score = _lineup_risk_score(legs)
        penalties = _penalties(
            legs=legs,
            post_lock_risk_score=post_lock_risk_score,
            freshness_score=freshness_score,
            lineup_risk_score=lineup_risk_score,
            is_matchday3=is_matchday3,
            is_knockout=is_knockout,
            same_group_violation=same_group_violation,
            correlated=correlated,
        )
        total_penalty = min(sum(float(value) for value in penalties.values()), 0.55)
        combined_probability_adjusted = combined_probability_raw * (1.0 - total_penalty)
        combined_fair_odds = (
            1.0 / combined_probability_adjusted
            if combined_probability_adjusted > 0
            else float("inf")
        )
        combined_ev_adjusted = combined_probability_adjusted * combined_decimal_odds - 1.0
        confidence_score = _combined_confidence(
            legs=legs,
            combined_ev_adjusted=combined_ev_adjusted,
            freshness_score=freshness_score,
            lineup_risk_score=lineup_risk_score,
            total_penalty=total_penalty,
        )

        warnings = _scoring_warnings(
            legs=legs,
            is_matchday3=is_matchday3,
            is_knockout=is_knockout,
            same_group_violation=same_group_violation,
            correlated=correlated,
        )
        return ComboScoringResult(
            combined_decimal_odds=round(combined_decimal_odds, 6),
            combined_probability_raw=round(combined_probability_raw, 6),
            combined_probability_adjusted=round(combined_probability_adjusted, 6),
            combined_fair_odds=round(combined_fair_odds, 6),
            combined_ev_raw=round(combined_ev_raw, 6),
            combined_ev_adjusted=round(combined_ev_adjusted, 6),
            combined_confidence_score=round(confidence_score, 2),
            combined_confidence_label=_confidence_label(confidence_score),
            post_lock_risk_score=round(post_lock_risk_score, 2),
            freshness_score=round(freshness_score, 2),
            lineup_risk_score=round(lineup_risk_score, 2),
            correlation_penalty=round(float(penalties.get("correlation_penalty", 0.0)), 6),
            penalties_json={**penalties, "total_penalty": round(total_penalty, 6)},
            warnings=warnings,
        )


def _penalties(
    *,
    legs: tuple[ComboLegCandidate, ...],
    post_lock_risk_score: float,
    freshness_score: float,
    lineup_risk_score: float,
    is_matchday3: bool,
    is_knockout: bool,
    same_group_violation: bool,
    correlated: bool,
) -> JsonDict:
    unknown_scope = any(leg.market_scope == ComboMarketScope.UNKNOWN for leg in legs)
    return {
        "legs_count_penalty": max(0.0, len(legs) - 2) * 0.04,
        "post_lock_risk_penalty": _clamp01(post_lock_risk_score / 100.0) * 0.15,
        "lineup_risk_penalty": _clamp01(lineup_risk_score / 100.0) * 0.15,
        "freshness_penalty": _clamp01((100.0 - freshness_score) / 100.0) * 0.12,
        "matchday3_penalty": 0.04 if is_matchday3 else 0.0,
        "knockout_market_scope_penalty": 0.10
        if unknown_scope
        else (0.03 if is_knockout else 0.0),
        "same_group_penalty": 0.08 if same_group_violation else 0.0,
        "correlation_penalty": 0.08 if correlated else 0.0,
    }


def _combined_confidence(
    *,
    legs: tuple[ComboLegCandidate, ...],
    combined_ev_adjusted: float,
    freshness_score: float,
    lineup_risk_score: float,
    total_penalty: float,
) -> float:
    confidences = [leg.confidence_score for leg in legs]
    min_leg_confidence = min(confidences)
    geometric_mean_confidence = _geometric_mean(confidences)
    ev_component = _clamp01(max(combined_ev_adjusted, 0.0) / 0.20) * 100.0
    data_quality_component = sum(leg.data_quality_score for leg in legs) / len(legs)
    lineup_readiness_component = max(0.0, 100.0 - lineup_risk_score)
    score = (
        0.35 * min_leg_confidence
        + 0.20 * geometric_mean_confidence
        + 0.15 * ev_component
        + 0.10 * data_quality_component
        + 0.10 * freshness_score
        + 0.10 * lineup_readiness_component
        - total_penalty * 35.0
    )
    return min(max(score, 0.0), 100.0)


def _post_lock_risk_score(
    legs: tuple[ComboLegCandidate, ...],
    is_matchday3: bool,
    is_knockout: bool,
) -> float:
    warning_points = {
        "lineup_missing_close_to_kickoff": 25.0,
        "lineup_missing": 18.0,
        "odds_stale": 15.0,
        "prediction_stale": 12.0,
        "odds_freshness_unknown": 10.0,
        "prediction_freshness_unknown": 10.0,
        "matchday3_public_risk": 15.0,
        "knockout_public_risk": 12.0,
        "critical_risk": 70.0,
    }
    score = 0.0
    for leg in legs:
        score += sum(warning_points.get(warning, 0.0) for warning in leg.warnings)
    if is_matchday3:
        score += 10.0
    if is_knockout:
        score += 8.0
    return min(score / max(len(legs), 1), 100.0)


def _freshness_score(legs: tuple[ComboLegCandidate, ...]) -> float:
    values = [leg.freshness_score for leg in legs if leg.freshness_score is not None]
    if not values:
        return 70.0
    return min(max(sum(values) / len(values), 0.0), 100.0)


def _lineup_risk_score(legs: tuple[ComboLegCandidate, ...]) -> float:
    status_points = {
        "available": 0.0,
        "partial": 25.0,
        "missing": 40.0,
        "unknown": 30.0,
    }
    scores = []
    for leg in legs:
        score = status_points.get((leg.lineup_status or "unknown").lower(), 30.0)
        if "lineup_missing_close_to_kickoff" in leg.warnings:
            score += 20.0
        scores.append(min(score, 100.0))
    return sum(scores) / len(scores)


def _scoring_warnings(
    *,
    legs: tuple[ComboLegCandidate, ...],
    is_matchday3: bool,
    is_knockout: bool,
    same_group_violation: bool,
    correlated: bool,
) -> list[str]:
    warnings: list[str] = []
    for leg in legs:
        warnings.extend(leg.warnings)
    if is_matchday3:
        warnings.append("matchday3_public_risk")
    if is_knockout:
        warnings.append("knockout_public_risk")
    if same_group_violation:
        warnings.append("same_group_matchday3_risk")
    if correlated:
        warnings.append("correlation_risk")
    return _dedupe(warnings)


def _product(values) -> float:
    result = 1.0
    for value in values:
        result *= float(value)
    return result


def _geometric_mean(values: list[float]) -> float:
    if not values:
        return 0.0
    positive = [max(value, 0.01) for value in values]
    return math.prod(positive) ** (1.0 / len(positive))


def _confidence_label(score: float) -> str:
    if score >= 80:
        return "Very High"
    if score >= 68:
        return "High"
    if score >= 55:
        return "Medium"
    if score >= 40:
        return "Low"
    return "Watchlist"


def _clamp01(value: float) -> float:
    return min(max(value, 0.0), 1.0)


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value not in seen:
            result.append(value)
            seen.add(value)
    return result
