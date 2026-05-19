"""Configuration loaders for Discord channel and webhook routing."""

from __future__ import annotations

import json
import os
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from football_predictor.discord.exceptions import DiscordRoutingError
from football_predictor.reference.lookups import ApiFootballReference
from football_predictor.utils.secrets import hash_secret

CHANNEL_KEYS = (
    "classement",
    "calendrier",
    "matchs_du_jour",
    "analyses",
    "predictions",
    "predictions_staff",
    "resultats",
    "score_pronos_semaine",
    "discussions",
)

REFERENCE_KEY_ALIASES = {
    "cdm_2026": "fifa_world_cup_2026",
    "ligue1": "ligue_1",
    "liga": "la_liga",
}

PLACEHOLDER_VALUES = {
    "",
    "REPLACE_WITH_CHANNEL_ID",
    "REPLACE_WITH_WEBHOOK_URL",
    "USE_VALUE_FROM_docs_api_football_reference_json",
    "USE_VALUE_FROM_CONFIG",
}


@dataclass(frozen=True)
class DiscordChannelConfig:
    channel_key: str
    channel_name: str | None = None
    channel_id: str | None = None
    webhook_name: str | None = None
    enabled: bool = True

    @property
    def allow_automated_messages(self) -> bool:
        return self.enabled and self.channel_key != "discussions"


@dataclass(frozen=True)
class DiscordCompetitionConfig:
    competition_key: str
    display_name: str
    league_id: int | None
    season: int | None
    enabled: bool = True
    reference_key: str | None = None
    channels: dict[str, DiscordChannelConfig] = field(default_factory=dict)


@dataclass(frozen=True)
class DiscordChannelsConfig:
    competitions: dict[str, DiscordCompetitionConfig]
    global_channels: dict[str, DiscordChannelConfig] = field(default_factory=dict)

    def find_competition(
        self,
        *,
        competition_key: str | None = None,
        league_id: int | None = None,
        season: int | None = None,
    ) -> DiscordCompetitionConfig | None:
        if competition_key:
            keys = {competition_key, _reference_key(competition_key)}
            for key, competition in self.competitions.items():
                if (key in keys or competition.reference_key in keys) and (
                    season is None or competition.season in {None, season}
                ):
                    return competition
        for competition in self.competitions.values():
            if (
                league_id is not None
                and competition.league_id == league_id
                and (season is None or competition.season in {None, season})
            ):
                return competition
        return None

    def find_global_channel(self, channel_key: str) -> DiscordChannelConfig | None:
        return self.global_channels.get(channel_key)


@dataclass(frozen=True)
class DiscordWebhookRouteConfig:
    competition_key: str
    channel_key: str
    webhook_url: str | None = field(default=None, repr=False)
    webhook_url_env: str | None = None
    webhook_name: str | None = None
    enabled: bool = True
    league_id: int | None = None
    season: int | None = None

    @property
    def webhook_hash(self) -> str | None:
        return hash_secret(self.webhook_url)


@dataclass(frozen=True)
class DiscordWebhooksConfig:
    routes: list[DiscordWebhookRouteConfig]

    def find_route(
        self,
        *,
        competition_key: str | None,
        league_id: int | None,
        season: int | None,
        channel_key: str,
    ) -> DiscordWebhookRouteConfig | None:
        keys = {competition_key, _reference_key(competition_key)} if competition_key else set()
        for route in self.routes:
            if route.channel_key != channel_key:
                continue
            if (
                not keys
                and league_id is None
                and route.competition_key in {"global", "_global"}
            ):
                return route
            if route.competition_key in keys:
                return route
        for route in self.routes:
            if route.channel_key != channel_key:
                continue
            if (
                league_id is not None
                and route.league_id == league_id
                and (season is None or route.season in {None, season})
            ):
                return route
        return None


def load_discord_channels_config(
    path: str | Path,
    reference: ApiFootballReference,
) -> DiscordChannelsConfig:
    payload = _read_yaml_object(path)
    source = payload.get("competitions")
    if not isinstance(source, Mapping):
        raise DiscordRoutingError(f"Missing competitions mapping in {Path(path)}")
    competitions: dict[str, DiscordCompetitionConfig] = {}
    global_channels = _parse_global_channels(payload.get("global_channels"))
    for competition_key, raw_row in source.items():
        if not isinstance(raw_row, Mapping):
            raise DiscordRoutingError(f"Invalid competition row for {competition_key}")
        reference_key = str(raw_row.get("reference_key") or _reference_key(str(competition_key)))
        reference_league = reference.find_league_by_key(reference_key)
        league_id = _optional_int(raw_row.get("league_id")) or reference_league.league_id
        season = _optional_config_season(raw_row, reference_league.season)
        if (
            league_id != reference_league.league_id
            or (season is not None and season != reference_league.season)
        ):
            reference.find_league_by_id(league_id, season)
        channels_payload = raw_row.get("channels")
        if not isinstance(channels_payload, Mapping):
            raise DiscordRoutingError(f"Missing channels for competition={competition_key}")
        channels = {
            str(channel_key): _parse_channel_config(str(channel_key), channel_payload)
            for channel_key, channel_payload in channels_payload.items()
        }
        invalid = set(channels) - set(CHANNEL_KEYS)
        if invalid:
            raise DiscordRoutingError(f"Unknown Discord channel_key={sorted(invalid)}")
        competitions[str(competition_key)] = DiscordCompetitionConfig(
            competition_key=str(competition_key),
            display_name=str(raw_row.get("display_name") or reference_league.name),
            league_id=league_id,
            season=season,
            enabled=bool(raw_row.get("enabled", True)),
            reference_key=reference_key,
            channels=channels,
        )
    return DiscordChannelsConfig(competitions, global_channels=global_channels)


def load_discord_webhooks_config(
    path: str | Path,
    reference: ApiFootballReference,
    *,
    env: Mapping[str, str] | None = None,
    reject_placeholders: bool = False,
) -> DiscordWebhooksConfig:
    payload = _read_yaml_object(path)
    source = payload.get("webhooks")
    if not isinstance(source, Mapping):
        raise DiscordRoutingError(f"Missing webhooks mapping in {Path(path)}")
    routes: list[DiscordWebhookRouteConfig] = []
    for competition_key, channels_payload in source.items():
        if not isinstance(channels_payload, Mapping):
            raise DiscordRoutingError(f"Invalid webhook row for {competition_key}")
        is_global = str(competition_key) in {"global", "_global"}
        league = (
            None
            if is_global
            else reference.find_league_by_key(_reference_key(str(competition_key)))
        )
        for channel_key, route_payload in channels_payload.items():
            routes.append(
                _parse_webhook_route(
                    competition_key=str(competition_key),
                    league_id=league.league_id if league is not None else None,
                    season=league.season if league is not None else None,
                    channel_key=str(channel_key),
                    payload=route_payload,
                    env=env or os.environ,
                    reject_placeholders=reject_placeholders,
                )
            )
    return DiscordWebhooksConfig(routes)


def has_placeholder_webhook_urls(config: DiscordWebhooksConfig) -> bool:
    return any(_is_placeholder(route.webhook_url) for route in config.routes)


def _parse_channel_config(key: str, payload: Any) -> DiscordChannelConfig:
    if key not in CHANNEL_KEYS:
        raise DiscordRoutingError(f"Unknown Discord channel_key={key!r}")
    if payload is None:
        payload = {}
    if not isinstance(payload, Mapping):
        raise DiscordRoutingError(f"Invalid channel config for {key}")
    channel_id = _none_if_placeholder(payload.get("channel_id"))
    return DiscordChannelConfig(
        channel_key=key,
        channel_name=str(payload.get("channel_name") or "") or None,
        channel_id=str(channel_id) if channel_id else None,
        webhook_name=str(payload.get("webhook_name") or "") or None,
        enabled=bool(payload.get("enabled", True)),
    )


def _optional_config_season(row: Mapping[str, Any], default_season: int) -> int | None:
    if "season" in row and row.get("season") is None:
        return None
    return _optional_int(row.get("season")) or default_season


def _parse_global_channels(payload: Any) -> dict[str, DiscordChannelConfig]:
    if payload is None:
        return {}
    if not isinstance(payload, Mapping):
        raise DiscordRoutingError("Invalid global_channels mapping")
    channels = {
        str(channel_key): _parse_channel_config(str(channel_key), channel_payload)
        for channel_key, channel_payload in payload.items()
    }
    invalid = set(channels) - set(CHANNEL_KEYS)
    if invalid:
        raise DiscordRoutingError(f"Unknown Discord global channel_key={sorted(invalid)}")
    return channels


def _parse_webhook_route(
    *,
    competition_key: str,
    league_id: int | None,
    season: int | None,
    channel_key: str,
    payload: Any,
    env: Mapping[str, str],
    reject_placeholders: bool,
) -> DiscordWebhookRouteConfig:
    if channel_key not in CHANNEL_KEYS:
        raise DiscordRoutingError(f"Unknown Discord channel_key={channel_key!r}")
    if payload is None:
        payload = {}
    if not isinstance(payload, Mapping):
        raise DiscordRoutingError(f"Invalid webhook payload for {competition_key}/{channel_key}")
    webhook_url_env = payload.get("webhook_url_env")
    webhook_url = payload.get("webhook_url")
    if webhook_url_env and env.get(str(webhook_url_env)):
        webhook_url = env[str(webhook_url_env)]
    if reject_placeholders and _is_placeholder(webhook_url):
        raise DiscordRoutingError(
            f"Placeholder webhook URL for {competition_key}/{channel_key}"
        )
    webhook_url = _none_if_placeholder(webhook_url)
    return DiscordWebhookRouteConfig(
        competition_key=competition_key,
        channel_key=channel_key,
        webhook_url=str(webhook_url) if webhook_url else None,
        webhook_url_env=str(webhook_url_env) if webhook_url_env else None,
        webhook_name=str(payload.get("webhook_name") or "") or None,
        enabled=bool(payload.get("enabled", True)),
        league_id=league_id,
        season=season,
    )


def _reference_key(competition_key: str | None) -> str:
    if not competition_key:
        return ""
    return REFERENCE_KEY_ALIASES.get(competition_key, competition_key)


def _optional_int(value: Any) -> int | None:
    value = _none_if_placeholder(value)
    if value is None:
        return None
    return int(value)


def _none_if_placeholder(value: Any) -> Any | None:
    if value is None:
        return None
    text = str(value).strip()
    return None if text in PLACEHOLDER_VALUES else value


def _is_placeholder(value: Any) -> bool:
    if value is None:
        return False
    text = str(value).strip()
    return text in PLACEHOLDER_VALUES or "REPLACE" in text


def _read_yaml_object(path: str | Path) -> dict[str, Any]:
    resolved = Path(path)
    text = resolved.read_text(encoding="utf-8")
    try:
        import yaml  # type: ignore[import-untyped]
    except ModuleNotFoundError:
        payload = _load_minimal_yaml(text)
    else:
        payload = yaml.safe_load(text) or {}
    if not isinstance(payload, dict):
        raise DiscordRoutingError(f"Expected YAML object in {resolved}")
    return payload


def _load_minimal_yaml(text: str) -> dict[str, Any]:
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        pass
    else:
        return payload if isinstance(payload, dict) else {}
    lines = [_strip_comment(line) for line in text.splitlines()]
    if any(line.strip() == "competitions:" for line in lines):
        return {"competitions": _load_nested_mapping(lines, root_indent=2)}
    if any(line.strip() == "webhooks:" for line in lines):
        return {"webhooks": _load_nested_mapping(lines, root_indent=2)}
    return {}


def _load_nested_mapping(lines: list[str], *, root_indent: int) -> dict[str, Any]:
    root: dict[str, Any] = {}
    stack: list[tuple[int, dict[str, Any]]] = [(0, root)]
    for raw_line in lines:
        if not raw_line.strip() or raw_line.strip() in {"competitions:", "webhooks:"}:
            continue
        indent = len(raw_line) - len(raw_line.lstrip(" "))
        if indent < root_indent:
            continue
        line = raw_line.strip()
        key, separator, value = line.partition(":")
        if not separator:
            raise DiscordRoutingError(f"Invalid Discord YAML line: {line}")
        while stack and indent <= stack[-1][0]:
            stack.pop()
        parent = stack[-1][1] if stack else root
        key = key.strip().strip("'\"")
        value = value.strip()
        if not value:
            child: dict[str, Any] = {}
            parent[key] = child
            stack.append((indent, child))
        elif value.startswith("{") and value.endswith("}"):
            parent[key] = _parse_inline_map(value)
        else:
            parent[key] = _parse_scalar(value)
    return root


def _strip_comment(line: str) -> str:
    stripped = line.strip()
    if stripped.startswith("#"):
        return ""
    return line.rstrip()


def _parse_inline_map(value: str) -> dict[str, Any]:
    inner = value.strip()[1:-1].strip()
    if not inner:
        return {}
    parsed: dict[str, Any] = {}
    for part in inner.split(","):
        key, separator, raw_value = part.partition(":")
        if not separator:
            raise DiscordRoutingError(f"Invalid inline YAML item: {part}")
        parsed[key.strip()] = _parse_scalar(raw_value.strip())
    return parsed


def _parse_scalar(value: str) -> Any:
    text = value.strip().strip("'\"")
    if text.lower() == "true":
        return True
    if text.lower() == "false":
        return False
    if text.lower() in {"null", "none"}:
        return None
    try:
        return int(text)
    except ValueError:
        return text
