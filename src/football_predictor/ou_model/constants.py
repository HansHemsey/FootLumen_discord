"""Constants for the Over/Under 2.5 prediction module."""

from __future__ import annotations

OU_THRESHOLD: float = 2.5

DEFAULT_HOME_LAMBDA: float = 1.38
DEFAULT_AWAY_LAMBDA: float = 1.12

OU_BET_NAME: str = "Goals Over/Under"
OU_OVER_LABEL: str = "Over 2.5"
OU_UNDER_LABEL: str = "Under 2.5"

FEATURE_VERSION: str = "ou_v1"

FALLBACK_WEIGHTS: dict[str, float] = {
    "market": 0.30,
    "lgbm": 0.25,
    "poisson": 0.20,
    "xgb": 0.15,
    "logistic": 0.10,
}

LEAKAGE_FIELDS: tuple[str, ...] = (
    "target",
    "target_ou25",
    "home_goals",
    "away_goals",
    "goals_home",
    "goals_away",
    "total_goals",
    "is_over25",
)

OVER_LABEL: str = "OVER"
UNDER_LABEL: str = "UNDER"

CONFIDENCE_HIGH_THRESHOLD: float = 0.62
CONFIDENCE_MEDIUM_THRESHOLD: float = 0.55
