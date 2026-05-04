"""Collect and resolve live players missing from local reference docs."""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session

from football_predictor.api.api_football_client import ApiFootballPayload
from football_predictor.api.endpoints import PLAYERS, PLAYERS_SQUADS
from football_predictor.api.exceptions import (
    ApiFootballClientError,
    ApiFootballError,
    ApiFootballRateLimitError,
)
from football_predictor.db import models
from football_predictor.db.repositories import insert_raw_api_snapshot, upsert_by_fields
from football_predictor.ingestion.parsers import response_items
from football_predictor.utils.time import parse_datetime, utc_now

JsonDict = dict[str, Any]
DEFAULT_UNKNOWN_PLAYERS_PATH = Path("data/processed/unknown_players.jsonl")
UNKNOWN_RESOLUTION_SOURCE = "api/live_unknown_resolution"


class ApiFootballPayloadClient(Protocol):
    def get_payload(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
        *,
        save_raw: bool = False,
    ) -> ApiFootballPayload:
        ...


@dataclass(frozen=True)
class UnknownPlayerRecord:
    player_id: int
    name: str | None = None
    team_id: int | None = None
    league_id: int | None = None
    season: int | None = None
    fixture_id: int | None = None
    source_endpoint: str | None = None
    first_seen_at: str = field(default_factory=lambda: utc_now().isoformat())

    @classmethod
    def from_mapping(cls, value: JsonDict) -> UnknownPlayerRecord | None:
        player_id = _as_int(value.get("player_id"))
        if player_id is None:
            return None
        return cls(
            player_id=player_id,
            name=_as_optional_str(value.get("name")),
            team_id=_as_int(value.get("team_id")),
            league_id=_as_int(value.get("league_id")),
            season=_as_int(value.get("season")),
            fixture_id=_as_int(value.get("fixture_id")),
            source_endpoint=_as_optional_str(value.get("source_endpoint")),
            first_seen_at=_as_optional_str(value.get("first_seen_at")) or utc_now().isoformat(),
        )

    def merged_with_filters(
        self,
        *,
        league_id: int | None = None,
        season: int | None = None,
        team_id: int | None = None,
    ) -> UnknownPlayerRecord | None:
        if league_id is not None and self.league_id is not None and self.league_id != league_id:
            return None
        if season is not None and self.season is not None and self.season != season:
            return None
        if team_id is not None and self.team_id is not None and self.team_id != team_id:
            return None
        return UnknownPlayerRecord(
            player_id=self.player_id,
            name=self.name,
            team_id=self.team_id if self.team_id is not None else team_id,
            league_id=self.league_id if self.league_id is not None else league_id,
            season=self.season if self.season is not None else season,
            fixture_id=self.fixture_id,
            source_endpoint=self.source_endpoint,
            first_seen_at=self.first_seen_at,
        )


class UnknownPlayerQueue:
    """Append-only JSONL queue with in-process player_id deduplication."""

    def __init__(self, path: Path | str = DEFAULT_UNKNOWN_PLAYERS_PATH) -> None:
        self.path = Path(path)
        self._seen_player_ids: set[int] = set()

    def append(self, record: UnknownPlayerRecord) -> bool:
        if record.player_id in self._seen_player_ids:
            return False
        self._seen_player_ids.add(record.player_id)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as file:
            file.write(json.dumps(asdict(record), sort_keys=True, ensure_ascii=True) + "\n")
        return True


@dataclass
class UnknownPlayerResolutionSummary:
    queued: int = 0
    deduplicated: int = 0
    already_resolved: int = 0
    resolved_players: int = 0
    resolved_squads: int = 0
    still_unknown: int = 0
    queue_pruned: int = 0
    queue_remaining: int = 0
    api_calls: int = 0
    raw_snapshots: int = 0
    errors: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, int | list[str]]:
        return {
            "queued": self.queued,
            "deduplicated": self.deduplicated,
            "already_resolved": self.already_resolved,
            "resolved_players": self.resolved_players,
            "resolved_squads": self.resolved_squads,
            "still_unknown": self.still_unknown,
            "queue_pruned": self.queue_pruned,
            "queue_remaining": self.queue_remaining,
            "api_calls": self.api_calls,
            "raw_snapshots": self.raw_snapshots,
            "errors": self.errors,
        }


class UnknownPlayerResolutionService:
    """Resolve unknown live players with explicit API-Football calls."""

    def __init__(
        self,
        session: Session,
        client: ApiFootballPayloadClient,
        *,
        save_raw: bool = False,
    ) -> None:
        self.session = session
        self.client = client
        self.save_raw = save_raw

    def resolve_unknown_players(
        self,
        *,
        input_path: Path | str = DEFAULT_UNKNOWN_PLAYERS_PATH,
        league_id: int | None = None,
        season: int | None = None,
        team_id: int | None = None,
        limit: int | None = None,
        delay_seconds: float = 0.0,
        squads_fallback: bool = True,
        prune_resolved: bool = True,
    ) -> UnknownPlayerResolutionSummary:
        summary = UnknownPlayerResolutionSummary()
        input_path_obj = Path(input_path)
        self.session.flush()
        records, raw_candidate_count, already_resolved = self._candidate_records(
            input_path=input_path_obj,
            league_id=league_id,
            season=season,
            team_id=team_id,
            limit=limit,
        )
        summary.queued = raw_candidate_count
        summary.already_resolved = already_resolved
        summary.deduplicated = len(records)

        for index, record in enumerate(records):
            if delay_seconds > 0 and index > 0:
                time.sleep(delay_seconds)
            resolved = False
            try:
                if record.season is not None:
                    resolved = self._resolve_from_players_endpoint(record, summary)
                if not resolved and squads_fallback and record.team_id is not None:
                    resolved = self._resolve_from_squad_endpoint(record, summary)
            except ApiFootballRateLimitError as exc:
                summary.errors.append(str(exc))
                summary.still_unknown += 1
                break
            except (ApiFootballClientError, ApiFootballError) as exc:
                summary.errors.append(f"player_id={record.player_id}: {exc}")
            if not resolved:
                summary.still_unknown += 1

        self.session.flush()
        if prune_resolved:
            summary.queue_pruned, summary.queue_remaining = self._prune_resolved_queue(
                input_path_obj
            )
        return summary

    def _candidate_records(
        self,
        *,
        input_path: Path,
        league_id: int | None,
        season: int | None,
        team_id: int | None,
        limit: int | None,
    ) -> tuple[list[UnknownPlayerRecord], int, int]:
        candidates: dict[int, UnknownPlayerRecord] = {}
        raw_candidate_count = 0
        already_resolved = 0
        for record in _read_unknown_player_records(input_path):
            merged = record.merged_with_filters(league_id=league_id, season=season, team_id=team_id)
            if merged is not None:
                raw_candidate_count += 1
                if self._player_is_resolved(merged.player_id):
                    already_resolved += 1
                    continue
                candidates.setdefault(merged.player_id, merged)

        for player in self._unknown_players_from_db():
            record = UnknownPlayerRecord(
                player_id=player.player_id,
                name=player.name,
                league_id=league_id,
                season=season,
                team_id=team_id,
                source_endpoint="db/players",
            )
            merged = record.merged_with_filters(league_id=league_id, season=season, team_id=team_id)
            if merged is not None:
                raw_candidate_count += 1
                candidates.setdefault(merged.player_id, merged)

        records = list(candidates.values())
        if limit is not None:
            records = records[:limit]
        return records, raw_candidate_count, already_resolved

    def _unknown_players_from_db(self) -> list[models.Player]:
        stmt = select(models.Player).order_by(models.Player.player_id.asc())
        players = self.session.execute(stmt).scalars()
        return [
            player
            for player in players
            if isinstance(player.payload_json, dict)
            and player.payload_json.get("reference_status") == "unknown_live"
        ]

    def _player_is_resolved(self, player_id: int) -> bool:
        player = self.session.get(models.Player, player_id)
        if player is None:
            return False
        payload = player.payload_json if isinstance(player.payload_json, dict) else {}
        return payload.get("reference_status") != "unknown_live"

    def _prune_resolved_queue(self, input_path: Path) -> tuple[int, int]:
        records = _read_unknown_player_records(input_path)
        if not records:
            return 0, 0

        remaining_by_player_id: dict[int, UnknownPlayerRecord] = {}
        for record in records:
            if self._player_is_resolved(record.player_id):
                continue
            remaining_by_player_id.setdefault(record.player_id, record)

        remaining = list(remaining_by_player_id.values())
        input_path.parent.mkdir(parents=True, exist_ok=True)
        if remaining:
            content = "\n".join(
                json.dumps(asdict(record), sort_keys=True, ensure_ascii=True)
                for record in remaining
            )
            input_path.write_text(f"{content}\n", encoding="utf-8")
        else:
            input_path.write_text("", encoding="utf-8")
        return len(records) - len(remaining), len(remaining)

    def _resolve_from_players_endpoint(
        self,
        record: UnknownPlayerRecord,
        summary: UnknownPlayerResolutionSummary,
    ) -> bool:
        payload = self._fetch(PLAYERS, {"id": record.player_id, "season": record.season}, summary)
        resolved = False
        for row in response_items(payload.payload):
            player_count, squad_count = self._upsert_player_search_row(row, record)
            summary.resolved_players += player_count
            summary.resolved_squads += squad_count
            resolved = resolved or player_count > 0
        return resolved

    def _resolve_from_squad_endpoint(
        self,
        record: UnknownPlayerRecord,
        summary: UnknownPlayerResolutionSummary,
    ) -> bool:
        payload = self._fetch(PLAYERS_SQUADS, {"team": record.team_id}, summary)
        resolved = False
        for row in response_items(payload.payload):
            player_count, squad_count, matched = self._upsert_squad_row(row, record)
            summary.resolved_players += player_count
            summary.resolved_squads += squad_count
            resolved = resolved or matched
        return resolved

    def _fetch(
        self,
        endpoint: str,
        params: JsonDict,
        summary: UnknownPlayerResolutionSummary,
    ) -> ApiFootballPayload:
        summary.api_calls += 1
        payload = self.client.get_payload(endpoint, params, save_raw=self.save_raw)
        insert_raw_api_snapshot(
            self.session,
            endpoint=payload.endpoint,
            params_json=payload.params,
            payload_json=payload.payload,
            fetched_at=parse_datetime(payload.fetched_at) or utc_now(),
            status_code=payload.status_code,
            source=payload.source,
        )
        summary.raw_snapshots += 1
        return payload

    def _upsert_player_search_row(
        self,
        row: JsonDict,
        record: UnknownPlayerRecord,
    ) -> tuple[int, int]:
        player = _as_dict(row.get("player"))
        player_id = _as_int(player.get("id") or player.get("player_id"))
        if player_id is None or player_id != record.player_id:
            return 0, 0
        self._upsert_player(player, source_payload=row)
        squads = 0
        statistics = row.get("statistics")
        if isinstance(statistics, list):
            for stat in statistics:
                squads += self._upsert_player_squad_from_stat(player_id, _as_dict(stat), record)
        return 1, squads

    def _upsert_squad_row(
        self,
        row: JsonDict,
        record: UnknownPlayerRecord,
    ) -> tuple[int, int, bool]:
        team = _as_dict(row.get("team"))
        players = row.get("players")
        if not isinstance(players, list):
            return 0, 0, False
        team_id = _as_int(team.get("id")) or record.team_id
        resolved_players = 0
        resolved_squads = 0
        matched_target = False
        for player in players:
            player_row = _as_dict(player)
            player_id = _as_int(player_row.get("id") or player_row.get("player_id"))
            if player_id is None:
                continue
            self._upsert_player(player_row, source_payload={"player": player_row, "team": team})
            resolved_players += 1
            if player_id == record.player_id:
                matched_target = True
            if team_id is not None and record.league_id is not None and record.season is not None:
                upsert_by_fields(
                    self.session,
                    models.PlayerSquad,
                    {
                        "player_id": player_id,
                        "team_id": team_id,
                        "league_id": record.league_id,
                        "season": record.season,
                    },
                    {
                        "position": player_row.get("position"),
                        "number": player_row.get("number"),
                        "fetched_at": utc_now(),
                        "payload_json": {
                            "player": player_row,
                            "team": team,
                            "ingestion_source": UNKNOWN_RESOLUTION_SOURCE,
                        },
                    },
                )
                resolved_squads += 1
        return resolved_players, resolved_squads, matched_target

    def _upsert_player_squad_from_stat(
        self,
        player_id: int,
        stat: JsonDict,
        record: UnknownPlayerRecord,
    ) -> int:
        team = _as_dict(stat.get("team"))
        league = _as_dict(stat.get("league"))
        games = _as_dict(stat.get("games"))
        team_id = _as_int(team.get("id")) or record.team_id
        league_id = _as_int(league.get("id")) or record.league_id
        season = _as_int(league.get("season")) or record.season
        if team_id is None or league_id is None or season is None:
            return 0
        upsert_by_fields(
            self.session,
            models.PlayerSquad,
            {
                "player_id": player_id,
                "team_id": team_id,
                "league_id": league_id,
                "season": season,
            },
            {
                "position": games.get("position"),
                "number": games.get("number"),
                "fetched_at": utc_now(),
                "payload_json": {
                    "stat": stat,
                    "ingestion_source": UNKNOWN_RESOLUTION_SOURCE,
                },
            },
        )
        return 1

    def _upsert_player(self, player: JsonDict, *, source_payload: JsonDict) -> None:
        player_id = _as_int(player.get("id") or player.get("player_id"))
        if player_id is None:
            return
        existing = self.session.get(models.Player, player_id)
        existing_name = _existing_value(existing, "name")
        name = player.get("name") or existing_name or "Unknown API-Football player"
        upsert_by_fields(
            self.session,
            models.Player,
            {"player_id": player_id},
            {
                "name": str(name),
                "firstname": player.get("firstname") or _existing_value(existing, "firstname"),
                "lastname": player.get("lastname") or _existing_value(existing, "lastname"),
                "age": _as_int(player.get("age")) or _existing_value(existing, "age"),
                "birth_date": _birth_date(player) or _existing_value(existing, "birth_date"),
                "nationality": player.get("nationality")
                or _existing_value(existing, "nationality"),
                "height": player.get("height") or _existing_value(existing, "height"),
                "weight": player.get("weight") or _existing_value(existing, "weight"),
                "injured": player.get("injured")
                if player.get("injured") is not None
                else _existing_value(existing, "injured"),
                "photo": player.get("photo") or _existing_value(existing, "photo"),
                "payload_json": {
                    **source_payload,
                    "ingestion_source": UNKNOWN_RESOLUTION_SOURCE,
                    "reference_status": "resolved_live",
                    "identity_incomplete": not bool(player.get("name") or existing_name),
                },
            },
        )


def _read_unknown_player_records(path: Path) -> list[UnknownPlayerRecord]:
    if not path.exists():
        return []
    records: list[UnknownPlayerRecord] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            raw = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(raw, dict):
            continue
        record = UnknownPlayerRecord.from_mapping(raw)
        if record is not None:
            records.append(record)
    return records


def _as_dict(value: Any) -> JsonDict:
    return value if isinstance(value, dict) else {}


def _as_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _as_optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value)
    return text or None


def _existing_value(existing: models.Player | None, field_name: str) -> Any:
    return getattr(existing, field_name) if existing is not None else None


def _birth_date(player: JsonDict) -> str | None:
    birth = _as_dict(player.get("birth"))
    value = birth.get("date") or player.get("birth_date")
    return str(value) if value is not None else None
