"""Shared rules for deciding whether a prediction may be published."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Final

PUBLISHABLE_CONFIDENCE_LABELS: Final[frozenset[str]] = frozenset({"High", "Very High"})
PUBLICATION_POLICY_VERSION: Final[str] = "publication_policy_v1"
DEFAULT_MIN_DATA_QUALITY_SCORE: Final[float] = 60.0
CONFIDENCE_SKIP_REASON: Final[str] = "confidence_below_publish_threshold"
DATA_QUALITY_MISSING_REASON: Final[str] = "data_quality_score_missing"
DATA_QUALITY_SKIP_REASON: Final[str] = "data_quality_below_publish_threshold"
DATA_QUALITY_BLOCKER_REASON: Final[str] = "data_quality_blocker_present"
DATA_QUALITY_SCORE_KEYS: Final[tuple[str, ...]] = (
    "publication_data_quality_score",
    "overall_data_quality_score",
    "data_quality_score",
    "ou_data_quality_score",
)


@dataclass(frozen=True)
class PublicationDecision:
    """Decision emitted by the public Discord publication policy."""

    allowed: bool
    reason: str | None
    confidence_label: str
    data_quality_score: float | None
    min_data_quality_score: float
    data_quality_blockers: tuple[str, ...] = ()
    policy_version: str = PUBLICATION_POLICY_VERSION

    def as_dict(self) -> dict[str, Any]:
        return {
            "allowed": self.allowed,
            "reason": self.reason,
            "confidence_label": self.confidence_label,
            "data_quality_score": self.data_quality_score,
            "min_data_quality_score": self.min_data_quality_score,
            "data_quality_blockers": list(self.data_quality_blockers),
            "policy_version": self.policy_version,
        }


def normalize_confidence_label(label: str | None) -> str:
    """Return the canonical business label for a raw confidence label."""
    if label is None:
        return "Uncertain"
    normalized = " ".join(str(label).strip().replace("_", " ").split()).title()
    if normalized in {"Veryhigh", "Very High"}:
        return "Very High"
    if normalized in {"High", "Medium", "Low", "Uncertain"}:
        return normalized
    return normalized or "Uncertain"


def is_publishable_confidence(label: str | None) -> bool:
    """Publish only High / Very High predictions to public Discord channels."""
    return normalize_confidence_label(label) in PUBLISHABLE_CONFIDENCE_LABELS


def extract_data_quality_score(payload: Mapping[str, Any] | None) -> float | None:
    """Return the first usable public quality score from a prediction payload."""
    if payload is None:
        return None
    for key in DATA_QUALITY_SCORE_KEYS:
        if key not in payload:
            continue
        value = payload.get(key)
        if value is None:
            continue
        try:
            return float(value)
        except (TypeError, ValueError):
            continue
    return None


def extract_publication_blockers(payload: Mapping[str, Any] | None) -> tuple[str, ...]:
    """Return normalized dq_v2 blockers carried by a prediction payload."""
    if payload is None:
        return ()
    blockers = payload.get("publication_blockers")
    if not isinstance(blockers, list | tuple | set):
        return ()
    return tuple(str(item) for item in blockers if str(item).strip())


def evaluate_publication(
    confidence_label: str | None,
    data_quality: Mapping[str, Any] | None,
    *,
    min_data_quality_score: float = DEFAULT_MIN_DATA_QUALITY_SCORE,
) -> PublicationDecision:
    """Evaluate the common public Discord publication gate."""
    normalized_label = normalize_confidence_label(confidence_label)
    score = extract_data_quality_score(data_quality)
    blockers = extract_publication_blockers(data_quality)
    if normalized_label not in PUBLISHABLE_CONFIDENCE_LABELS:
        return PublicationDecision(
            allowed=False,
            reason=CONFIDENCE_SKIP_REASON,
            confidence_label=normalized_label,
            data_quality_score=score,
            min_data_quality_score=float(min_data_quality_score),
            data_quality_blockers=blockers,
        )
    if blockers:
        return PublicationDecision(
            allowed=False,
            reason=DATA_QUALITY_BLOCKER_REASON,
            confidence_label=normalized_label,
            data_quality_score=score,
            min_data_quality_score=float(min_data_quality_score),
            data_quality_blockers=blockers,
        )
    if score is None:
        return PublicationDecision(
            allowed=False,
            reason=DATA_QUALITY_MISSING_REASON,
            confidence_label=normalized_label,
            data_quality_score=None,
            min_data_quality_score=float(min_data_quality_score),
            data_quality_blockers=blockers,
        )
    if score < min_data_quality_score:
        return PublicationDecision(
            allowed=False,
            reason=DATA_QUALITY_SKIP_REASON,
            confidence_label=normalized_label,
            data_quality_score=score,
            min_data_quality_score=float(min_data_quality_score),
            data_quality_blockers=blockers,
        )
    return PublicationDecision(
        allowed=True,
        reason=None,
        confidence_label=normalized_label,
        data_quality_score=score,
        min_data_quality_score=float(min_data_quality_score),
        data_quality_blockers=blockers,
    )


def publication_decision_payload(
    decision: PublicationDecision,
) -> dict[str, Any]:
    """Return a JSON-safe payload for prediction and Discord metadata."""
    return decision.as_dict()
