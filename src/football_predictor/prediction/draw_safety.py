"""Post-prediction DRAW safeguards for public publication decisions."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, dataclass, field
from typing import Any

from football_predictor.prediction.publication_policy import normalize_confidence_label

JsonDict = dict[str, Any]

DRAW_PROBABILITY_UNDERESTIMATED = "draw_probability_underestimated"
DRAW_RISK_PROBABILITY_CONTRADICTION = "draw_risk_probability_contradiction"
DRAW_SAFETY_UNAVAILABLE = "draw_safety_unavailable"
WORLDCUP_BALANCED_MATCH_DRAW_CAP = "worldcup_balanced_match_draw_cap"
DRAW_SAFETY_SKIP_REASON = "draw_safety_confidence_cap"
DRAW_SAFETY_SEVERE_SKIP_REASON = "draw_safety_severe_conflict"

_LABEL_RANK = {
    "Uncertain": 0,
    "Low": 1,
    "Medium": 2,
    "High": 3,
    "Very High": 4,
}


@dataclass(frozen=True)
class DrawSafetyConfig:
    """Configuration for post-model DRAW confidence safeguards."""

    enabled: bool = True
    draw_risk_high_threshold: float = 0.32
    min_p_draw_when_draw_risk_high: float = 0.22
    severe_draw_risk_threshold: float = 0.38
    severe_min_p_draw: float = 0.18
    confidence_cap_on_draw_conflict: str = "Medium"
    severe_confidence_cap_label: str = "Low"
    confidence_score_cap_on_draw_conflict: float = 67.0
    severe_confidence_score_cap: float = 54.0
    worldcup_balanced_match_gap: float = 0.08
    worldcup_balanced_min_p_draw: float = 0.20

    @classmethod
    def from_settings(cls, settings: Any) -> DrawSafetyConfig:
        return cls(
            enabled=bool(getattr(settings, "draw_safety_enabled", cls.enabled)),
            draw_risk_high_threshold=float(
                getattr(settings, "draw_risk_high_threshold", cls.draw_risk_high_threshold)
            ),
            min_p_draw_when_draw_risk_high=float(
                getattr(
                    settings,
                    "min_p_draw_when_draw_risk_high",
                    cls.min_p_draw_when_draw_risk_high,
                )
            ),
            confidence_cap_on_draw_conflict=str(
                getattr(
                    settings,
                    "confidence_cap_on_draw_conflict",
                    cls.confidence_cap_on_draw_conflict,
                )
            ),
        )

    def as_dict(self) -> JsonDict:
        return asdict(self)


@dataclass(frozen=True)
class DrawSafetySignals:
    """Signals needed to decide whether DRAW risk contradicts final probabilities."""

    model_family: str
    p_home: float
    p_draw: float
    p_away: float
    confidence_label: str
    confidence_score: float | None
    draw_risk_probability: float | None = None
    source_draw_probability: float | None = None
    market_draw_probability: float | None = None
    is_worldcup: bool = False
    metadata: JsonDict = field(default_factory=dict)

    def as_dict(self) -> JsonDict:
        return asdict(self)


@dataclass(frozen=True)
class DrawSafetyDecision:
    """Effective confidence/publication decision after DRAW safeguards."""

    enabled: bool
    severity: str
    original_confidence_label: str
    original_confidence_score: float | None
    effective_confidence_label: str
    effective_confidence_score: float | None
    confidence_capped: bool
    public_blocked: bool
    skip_reason: str | None
    warnings: list[str]
    public_note: str | None
    technical_reason: str | None
    signals: JsonDict
    config: JsonDict

    def as_dict(self) -> JsonDict:
        return asdict(self)


def evaluate_draw_safety(
    signals: DrawSafetySignals,
    *,
    config: DrawSafetyConfig | None = None,
) -> DrawSafetyDecision:
    """Cap confidence and block public publication on severe DRAW contradictions."""
    resolved = config or DrawSafetyConfig()
    original_label = normalize_confidence_label(signals.confidence_label)
    if not resolved.enabled:
        return DrawSafetyDecision(
            enabled=False,
            severity="none",
            original_confidence_label=original_label,
            original_confidence_score=signals.confidence_score,
            effective_confidence_label=original_label,
            effective_confidence_score=signals.confidence_score,
            confidence_capped=False,
            public_blocked=False,
            skip_reason=None,
            warnings=[],
            public_note=None,
            technical_reason=None,
            signals=signals.as_dict(),
            config=resolved.as_dict(),
        )

    warnings: list[str] = []
    severity = "none"
    technical_reason: str | None = None
    draw_risk = _max_optional(
        signals.draw_risk_probability,
        signals.source_draw_probability,
        signals.market_draw_probability,
    )
    cap_label: str | None = None
    cap_score: float | None = None

    if (
        draw_risk is not None
        and draw_risk >= resolved.draw_risk_high_threshold
        and signals.p_draw < resolved.min_p_draw_when_draw_risk_high
    ):
        warnings.append(DRAW_PROBABILITY_UNDERESTIMATED)
        severity = "standard"
        cap_label = resolved.confidence_cap_on_draw_conflict
        cap_score = resolved.confidence_score_cap_on_draw_conflict
        technical_reason = (
            "draw_risk_probability is high while final p_draw is below the minimum "
            "conservative threshold"
        )
        if (
            draw_risk >= resolved.severe_draw_risk_threshold
            and signals.p_draw < resolved.severe_min_p_draw
        ):
            warnings.append(DRAW_RISK_PROBABILITY_CONTRADICTION)
            severity = "severe"
            cap_label = resolved.severe_confidence_cap_label
            cap_score = resolved.severe_confidence_score_cap
            technical_reason = (
                "severe draw_risk_probability/final p_draw contradiction; public "
                "publication is blocked"
            )
    elif (
        signals.is_worldcup
        and draw_risk is None
        and abs(signals.p_home - signals.p_away) <= resolved.worldcup_balanced_match_gap
        and signals.p_draw < resolved.worldcup_balanced_min_p_draw
    ):
        warnings.extend([DRAW_SAFETY_UNAVAILABLE, WORLDCUP_BALANCED_MATCH_DRAW_CAP])
        severity = "standard"
        cap_label = resolved.confidence_cap_on_draw_conflict
        cap_score = resolved.confidence_score_cap_on_draw_conflict
        technical_reason = (
            "World Cup match is balanced but no dedicated draw-risk signal is available "
            "and final p_draw is low"
        )

    effective_label = _cap_label(original_label, cap_label)
    effective_score = _cap_score(signals.confidence_score, cap_score)
    confidence_capped = (
        effective_label != original_label
        or effective_score != signals.confidence_score
    )
    skip_reason = None
    if severity == "severe":
        skip_reason = DRAW_SAFETY_SEVERE_SKIP_REASON
    elif confidence_capped:
        skip_reason = DRAW_SAFETY_SKIP_REASON

    return DrawSafetyDecision(
        enabled=True,
        severity=severity,
        original_confidence_label=original_label,
        original_confidence_score=signals.confidence_score,
        effective_confidence_label=effective_label,
        effective_confidence_score=effective_score,
        confidence_capped=confidence_capped,
        public_blocked=bool(skip_reason),
        skip_reason=skip_reason,
        warnings=warnings,
        public_note=(
            "Risque de nul élevé : confiance plafonnée."
            if confidence_capped
            else None
        ),
        technical_reason=technical_reason,
        signals=signals.as_dict(),
        config=resolved.as_dict(),
    )


def draw_safety_skip_reason(payload: Mapping[str, Any] | None) -> str | None:
    """Return the staff skip reason encoded in a draw safety payload."""
    if not isinstance(payload, Mapping):
        return None
    reason = payload.get("skip_reason")
    return str(reason) if reason else None


def _cap_label(label: str, cap_label: str | None) -> str:
    if not cap_label:
        return label
    normalized_cap = normalize_confidence_label(cap_label)
    if _LABEL_RANK.get(label, 0) > _LABEL_RANK.get(normalized_cap, 0):
        return normalized_cap
    return label


def _cap_score(score: float | None, cap_score: float | None) -> float | None:
    if score is None or cap_score is None:
        return score
    return min(float(score), float(cap_score))


def _max_optional(*values: float | None) -> float | None:
    available = [float(value) for value in values if value is not None]
    return max(available) if available else None
