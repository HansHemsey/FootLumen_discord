"""World Cup group label helpers."""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

UNKNOWN_GROUP = "Group Unknown"
UNKNOWN_GROUP_FR = "Groupe non identifié"
VALID_WORLD_CUP_GROUPS = set("ABCDEFGHIJKL")


def normalize_worldcup_group_label(value: object) -> str | None:
    """Return a stable ``Group X`` label when the input contains a group name."""

    text = str(value or "").strip()
    if not text:
        return None
    match = re.search(r"\bgroup\s+([a-z])\b", text, flags=re.IGNORECASE)
    if match and match.group(1).upper() in VALID_WORLD_CUP_GROUPS:
        return f"Group {match.group(1).upper()}"
    match = re.search(r"\bgroupe\s+([a-z])\b", text, flags=re.IGNORECASE)
    if match and match.group(1).upper() in VALID_WORLD_CUP_GROUPS:
        return f"Group {match.group(1).upper()}"
    return None


def extract_group_from_payload(payload: Mapping[str, Any] | None) -> str | None:
    """Extract a World Cup group from a standing or fixture payload."""

    if not isinstance(payload, Mapping):
        return None
    candidates = [
        payload.get("group"),
        _mapping(payload.get("raw")).get("group"),
        _mapping(payload.get("league")).get("round"),
        _mapping(_mapping(payload.get("raw")).get("league")).get("round"),
    ]
    for candidate in candidates:
        group = normalize_worldcup_group_label(candidate)
        if group:
            return group
    return None


def worldcup_group_sort_key(group_name: str | None) -> tuple[int, str]:
    """Sort Group A-L before unknown or malformed groups."""

    normalized = normalize_worldcup_group_label(group_name) or group_name or UNKNOWN_GROUP
    match = re.search(r"\bgroup\s+([a-z])\b", normalized, flags=re.IGNORECASE)
    if match:
        return (ord(match.group(1).upper()) - ord("A"), normalized)
    return (999, normalized)


def localized_group_label(group_name: str | None) -> str:
    normalized = normalize_worldcup_group_label(group_name)
    if normalized is None:
        return UNKNOWN_GROUP_FR
    return normalized.replace("Group ", "Groupe ", 1)


def _mapping(value: object) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}
