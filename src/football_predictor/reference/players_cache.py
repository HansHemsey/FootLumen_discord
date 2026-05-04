"""Optional helpers for the technical players collection cache.

The cache is only for resuming future `/players/squads` collection jobs. It is
not a business source for seeding players or squads.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from football_predictor.reference.loaders import load_players_cache


@dataclass(frozen=True)
class PlayersCacheSummary:
    teams: int
    keys: int
    generated_at: str | None


def summarize_players_cache(path: str | Path) -> PlayersCacheSummary:
    payload: dict[str, Any] = load_players_cache(path)
    teams = payload.get("teams") or {}
    timestamp = payload.get("generated_at") or payload.get("updated_at")
    return PlayersCacheSummary(
        teams=len(teams) if isinstance(teams, dict) else 0,
        keys=len(payload),
        generated_at=timestamp if isinstance(timestamp, str) else None,
    )
