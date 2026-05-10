"""Leakage-aware feature selection for V3 Draw Risk models."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import pandas as pd  # type: ignore[import-untyped]

from football_predictor.modeling.preprocessing import (
    FORBIDDEN_FEATURE_PATTERNS,
    is_forbidden_feature,
    select_numeric_feature_names,
)
from football_predictor.modeling.v3.constants import DRAW_RISK_TARGET, NO_DRAW_WINNER_TARGET

DRAW_RISK_FORBIDDEN_PATTERNS: tuple[str, ...] = (
    *FORBIDDEN_FEATURE_PATTERNS,
    r"^is_draw$",
    r"^home_wins$",
    r"^outcome$",
    r"^split$",
    r"^total_goals$",
    r"^result$",
    r"^winner$",
    r"^p_v2_",
    r"^p_v3_",
    r"^predicted_",
    r"^model_",
    r"^confidence_label$",
)

PREFERRED_DRAW_RISK_PATTERNS: tuple[str, ...] = (
    "draw_risk_",
    "market_",
    "p_market_",
    "api_pred_",
    "p_api_",
    "lineup_",
    "official_lineup_",
    "data_quality_",
    "overall_data_quality_",
)

NO_DRAW_WINNER_FORBIDDEN_PATTERNS: tuple[str, ...] = (
    *FORBIDDEN_FEATURE_PATTERNS,
    r"^is_draw$",
    r"^home_wins$",
    r"^outcome$",
    r"^split$",
    r"^total_goals$",
    r"^result$",
    r"^winner$",
    r"^draw_risk_",
    r"^market_draw$",
    r"^p_market_draw$",
    r"^api_pred_draw$",
    r"^p_api_draw$",
    r"^p_v2_",
    r"^p_v3_",
    r"^predicted_",
    r"^model_",
    r"^confidence_label$",
)

PREFERRED_NO_DRAW_WINNER_PATTERNS: tuple[str, ...] = (
    "ndw_",
    "_edge",
    "market_home",
    "market_away",
    "p_market_home",
    "p_market_away",
    "api_pred_home",
    "api_pred_away",
    "p_api_home",
    "p_api_away",
    "lineup_",
    "official_lineup_",
    "absence_",
    "availability_",
    "data_quality_",
    "overall_data_quality_",
)


@dataclass(frozen=True)
class FeatureCoverage:
    """Coverage details for a selected numeric feature."""

    non_null: int
    coverage: float

    def as_dict(self) -> dict[str, int | float]:
        return {"non_null": self.non_null, "coverage": self.coverage}


def select_v3_draw_feature_names(
    frame: pd.DataFrame,
    *,
    min_coverage: float = 0.02,
    max_features: int = 260,
    forbidden_patterns: Sequence[str] = DRAW_RISK_FORBIDDEN_PATTERNS,
) -> list[str]:
    """Return numeric V3 Draw Risk feature columns without target leakage.

    The selector intentionally allows point-in-time market/API probability columns, but
    rejects final targets, match IDs, dates/times, goals and downstream model outputs.
    Sparse Draw Risk / market / lineup / quality signals are kept when they contain at
    least one usable value because those families are central to V3.
    """
    if max_features <= 0:
        return []

    numeric_names = select_numeric_feature_names(frame, forbidden_patterns=forbidden_patterns)
    if frame.empty:
        return numeric_names[:max_features]

    coverage = {
        name: float(pd.to_numeric(frame[name], errors="coerce").notna().mean())
        for name in numeric_names
    }
    selected = [
        name
        for name in numeric_names
        if coverage[name] >= min_coverage
        or (_is_preferred_draw_risk_feature(name) and coverage[name] > 0)
    ]

    if len(selected) <= max_features:
        return selected

    original_index = {name: index for index, name in enumerate(selected)}
    ranked = sorted(
        selected,
        key=lambda name: (
            _is_preferred_draw_risk_feature(name),
            coverage[name],
            -original_index[name],
        ),
        reverse=True,
    )
    return ranked[:max_features]


def feature_coverage(
    frame: pd.DataFrame,
    feature_names: Sequence[str],
) -> dict[str, dict[str, int | float]]:
    """Return non-null counts and coverage ratios for selected feature columns."""
    row_count = len(frame)
    coverage: dict[str, dict[str, int | float]] = {}
    for name in feature_names:
        if name not in frame.columns:
            coverage[name] = FeatureCoverage(non_null=0, coverage=0.0).as_dict()
            continue
        non_null = int(pd.to_numeric(frame[name], errors="coerce").notna().sum())
        ratio = float(non_null / row_count) if row_count else 0.0
        coverage[name] = FeatureCoverage(non_null=non_null, coverage=ratio).as_dict()
    return coverage


def is_v3_draw_forbidden_feature(column: str) -> bool:
    """Expose the V3 Draw Risk forbidden check for tests and audits."""
    return is_forbidden_feature(column, DRAW_RISK_FORBIDDEN_PATTERNS)


def select_v3_no_draw_winner_feature_names(
    frame: pd.DataFrame,
    *,
    min_coverage: float = 0.02,
    max_features: int = 260,
    forbidden_patterns: Sequence[str] = NO_DRAW_WINNER_FORBIDDEN_PATTERNS,
) -> list[str]:
    """Return numeric V3 No-Draw Winner features without target leakage."""
    if max_features <= 0:
        return []

    numeric_names = select_numeric_feature_names(frame, forbidden_patterns=forbidden_patterns)
    if frame.empty:
        return numeric_names[:max_features]

    coverage = {
        name: float(pd.to_numeric(frame[name], errors="coerce").notna().mean())
        for name in numeric_names
    }
    selected = [
        name
        for name in numeric_names
        if coverage[name] >= min_coverage
        or (_is_preferred_no_draw_winner_feature(name) and coverage[name] > 0)
    ]

    if len(selected) <= max_features:
        return selected

    original_index = {name: index for index, name in enumerate(selected)}
    ranked = sorted(
        selected,
        key=lambda name: (
            _is_preferred_no_draw_winner_feature(name),
            coverage[name],
            -original_index[name],
        ),
        reverse=True,
    )
    return ranked[:max_features]


def is_v3_no_draw_winner_forbidden_feature(column: str) -> bool:
    """Expose the V3 No-Draw Winner forbidden check for tests and audits."""
    return is_forbidden_feature(column, NO_DRAW_WINNER_FORBIDDEN_PATTERNS)


def _is_preferred_draw_risk_feature(name: str) -> bool:
    normalized = name.casefold()
    if normalized == DRAW_RISK_TARGET:
        return False
    return any(pattern in normalized for pattern in PREFERRED_DRAW_RISK_PATTERNS)


def _is_preferred_no_draw_winner_feature(name: str) -> bool:
    normalized = name.casefold()
    if normalized == NO_DRAW_WINNER_TARGET:
        return False
    return any(pattern in normalized for pattern in PREFERRED_NO_DRAW_WINNER_PATTERNS)
