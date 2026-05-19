"""Dedicated publication policy for O/U 2.5 value picks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

OUPublicationDecision = Literal["public", "staff", "no_bet"]

MIN_PUBLIC_EDGE = 0.03
MIN_PUBLIC_EV = 0.03
MIN_PUBLIC_CONFIDENCE_SCORE = 65.0
MIN_PUBLIC_DATA_QUALITY_SCORE = 70.0
MIN_PUBLIC_BOOKMAKER_COUNT = 2


@dataclass(frozen=True)
class OUPublicationPolicyResult:
    decision: OUPublicationDecision
    reason: str | None


def evaluate_ou_publication(
    *,
    value_side: str | None,
    edge_pick: float | None,
    ev_pick: float | None,
    confidence_score_v2: float | None,
    data_quality_score: float | None,
    bookmaker_count: float | None,
) -> OUPublicationPolicyResult:
    """Return public/staff/no-bet using O/U betting-specific thresholds."""
    if value_side is None:
        return OUPublicationPolicyResult("no_bet", "no_value_side")
    if edge_pick is None or edge_pick < MIN_PUBLIC_EDGE:
        return OUPublicationPolicyResult("staff", "edge_insufficient")
    if ev_pick is None or ev_pick < MIN_PUBLIC_EV:
        return OUPublicationPolicyResult("staff", "ev_insufficient")
    if confidence_score_v2 is None or confidence_score_v2 < MIN_PUBLIC_CONFIDENCE_SCORE:
        return OUPublicationPolicyResult("staff", "confidence_insufficient")
    if data_quality_score is None or data_quality_score < MIN_PUBLIC_DATA_QUALITY_SCORE:
        return OUPublicationPolicyResult("staff", "data_quality_insufficient")
    if bookmaker_count is not None and bookmaker_count < MIN_PUBLIC_BOOKMAKER_COUNT:
        return OUPublicationPolicyResult("staff", "bookmaker_count_insufficient")
    return OUPublicationPolicyResult("public", None)
