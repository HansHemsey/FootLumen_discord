"""Load local reference JSON files."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from football_predictor.reference.exceptions import ReferenceValidationError
from football_predictor.reference.lookups import ApiFootballReference, PlayersReference


def _read_json(path: str | Path) -> dict[str, Any]:
    resolved = Path(path)
    with resolved.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ReferenceValidationError(f"Expected JSON object in {resolved}")
    return payload


def load_api_football_reference(path: str | Path) -> ApiFootballReference:
    payload = _read_json(path)
    _require_sections(payload, ("competitions", "references"), path)
    return ApiFootballReference(payload)


def load_players_reference(path: str | Path) -> PlayersReference:
    payload = _read_json(path)
    _require_sections(payload, ("competitions",), path)
    return PlayersReference(payload)


def load_players_cache(path: str | Path) -> dict[str, Any]:
    """Load the technical players cache without treating it as business reference."""
    payload = _read_json(path)
    _require_sections(payload, ("teams",), path)
    return payload


def _require_sections(payload: dict[str, Any], sections: tuple[str, ...], path: str | Path) -> None:
    missing = [section for section in sections if section not in payload]
    if missing:
        raise ReferenceValidationError(f"Missing sections {missing} in {Path(path)}")
