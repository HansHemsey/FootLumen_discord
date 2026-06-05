"""Enums for World Cup 2026 combo tickets."""

from __future__ import annotations

from enum import StrEnum


class ComboTicketStatus(StrEnum):
    DRAFT = "DRAFT"
    WATCHLIST_STAFF = "WATCHLIST_STAFF"
    PRE_LOCK_REVALIDATION = "PRE_LOCK_REVALIDATION"
    LOCKED = "LOCKED"
    PUBLIC_PUBLISHED = "PUBLIC_PUBLISHED"
    STAFF_ONLY = "STAFF_ONLY"
    NO_BET = "NO_BET"
    SETTLED = "SETTLED"


class ComboMarketType(StrEnum):
    HOME = "HOME"
    DRAW = "DRAW"
    AWAY = "AWAY"
    DOUBLE_CHANCE = "DOUBLE_CHANCE"
    DRAW_NO_BET = "DRAW_NO_BET"
    OVER_25 = "OVER_25"
    UNDER_25 = "UNDER_25"
    BTTS_YES = "BTTS_YES"
    BTTS_NO = "BTTS_NO"
    TO_QUALIFY = "TO_QUALIFY"


class ComboMarketScope(StrEnum):
    NINETY_MIN = "NINETY_MIN"
    TO_QUALIFY = "TO_QUALIFY"
    EXTRA_TIME_INCLUDED = "EXTRA_TIME_INCLUDED"
    UNKNOWN = "UNKNOWN"
