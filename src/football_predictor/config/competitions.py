"""Competition configuration helpers."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from football_predictor.reference.exceptions import ReferenceValidationError
from football_predictor.reference.lookups import ApiFootballReference

JsonDict = dict[str, Any]


@dataclass(frozen=True)
class CompetitionConfig:
    key: str | None
    league_id: int
    season: int
    name: str
    country: str | None
    enabled: bool = True
    source: str | None = None


def competitions_from_reference(reference: ApiFootballReference) -> list[CompetitionConfig]:
    return [
        CompetitionConfig(
            key=league.key,
            league_id=league.league_id,
            season=league.season,
            name=league.name,
            country=league.country,
            source="docs/api_football_reference.json",
        )
        for league in reference.leagues()
    ]


def competition_config_payload_from_reference(reference: ApiFootballReference) -> JsonDict:
    """Build a serializable competitions config payload from local docs reference."""
    return {
        "competitions": [
            {
                "key": competition.key,
                "league_id": competition.league_id,
                "season": competition.season,
                "name": competition.name,
                "country": competition.country,
                "enabled": competition.enabled,
                "source": competition.source,
            }
            for competition in competitions_from_reference(reference)
        ]
    }


def validate_competition_config(
    path: str | Path,
    reference: ApiFootballReference,
) -> list[CompetitionConfig]:
    """Validate a competitions config against local reference IDs."""
    return load_competition_config(path, reference)


def load_competition_config(
    path: str | Path,
    reference: ApiFootballReference,
) -> list[CompetitionConfig]:
    payload = _read_config(path)
    competitions = payload.get("competitions")
    if not isinstance(competitions, list):
        raise ReferenceValidationError(f"Missing competitions list in {Path(path)}")

    resolved: list[CompetitionConfig] = []
    for item in competitions:
        if not isinstance(item, dict):
            raise ReferenceValidationError(f"Invalid competition row in {Path(path)}")
        enabled = bool(item.get("enabled", True))
        key = item.get("key")
        if key:
            league = reference.find_league_by_key(str(key))
        elif item.get("league_id") is not None:
            league = reference.find_league_by_id(
                int(item["league_id"]),
                int(item["season"]) if item.get("season") is not None else None,
            )
        else:
            raise ReferenceValidationError("Competition config row needs key or league_id")

        league_id = int(item.get("league_id") or league.league_id)
        season = int(item.get("season") or league.season)
        if key and (league_id != league.league_id or season != league.season):
            raise ReferenceValidationError(
                f"Competition key={key!r} does not match league_id={league_id} season={season}"
            )
        if not key and (league_id != league.league_id or season != league.season):
            reference.find_league_by_id(league_id, season)
        resolved.append(
            CompetitionConfig(
                key=str(key) if key is not None else league.key,
                league_id=league_id,
                season=season,
                name=str(item.get("name") or league.name),
                country=item.get("country") or league.country,
                enabled=enabled,
                source=item.get("source"),
            )
        )
    return [competition for competition in resolved if competition.enabled]


def _read_config(path: str | Path) -> JsonDict:
    resolved = Path(path)
    text = resolved.read_text(encoding="utf-8")
    payload = json.loads(text) if resolved.suffix.lower() == ".json" else _load_yaml(text)
    if not isinstance(payload, dict):
        raise ReferenceValidationError(f"Expected object config in {resolved}")
    return payload


def _load_yaml(text: str) -> JsonDict:
    try:
        import yaml  # type: ignore[import-untyped]
    except ModuleNotFoundError:
        return _load_simple_competitions_yaml(text)
    payload = yaml.safe_load(text)
    return payload if isinstance(payload, dict) else {}


def _load_simple_competitions_yaml(text: str) -> JsonDict:
    """Minimal parser for config/competitions.example.yaml when PyYAML is absent."""
    rows: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or line == "competitions:":
            continue
        if line.startswith("- "):
            if current is not None:
                rows.append(current)
            current = {}
            line = line[2:].strip()
            if line:
                key, value = _split_yaml_pair(line)
                current[key] = _parse_scalar(value)
            continue
        if current is None:
            continue
        key, value = _split_yaml_pair(line)
        current[key] = _parse_scalar(value)
    if current is not None:
        rows.append(current)
    return {"competitions": rows}


def _split_yaml_pair(line: str) -> tuple[str, str]:
    key, separator, value = line.partition(":")
    if not separator:
        raise ReferenceValidationError(f"Invalid YAML line: {line}")
    return key.strip(), value.strip()


def _parse_scalar(value: str) -> Any:
    if value.lower() in {"true", "false"}:
        return value.lower() == "true"
    if value.isdigit():
        return int(value)
    return value.strip("'\"")
