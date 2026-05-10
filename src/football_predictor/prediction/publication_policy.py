"""Shared rules for deciding whether a prediction may be published."""

from __future__ import annotations

from typing import Final

PUBLISHABLE_CONFIDENCE_LABELS: Final[frozenset[str]] = frozenset({"High", "Very High"})
CONFIDENCE_SKIP_REASON: Final[str] = "confidence_below_publish_threshold"


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
