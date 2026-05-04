"""Optional Discord webhook provisioning through the Discord bot API."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx

from football_predictor.discord.config import (
    DiscordChannelsConfig,
    load_discord_channels_config,
)
from football_predictor.discord.exceptions import DiscordWebhookError
from football_predictor.reference.lookups import ApiFootballReference
from football_predictor.utils.secrets import hash_secret


@dataclass(frozen=True)
class ProvisionedWebhook:
    competition_key: str
    league_id: int | None
    season: int | None
    channel_key: str
    channel_id: str
    webhook_name: str
    webhook_url: str | None = field(default=None, repr=False)
    status: str = "dry_run"

    @property
    def webhook_hash(self) -> str | None:
        return hash_secret(self.webhook_url)


class DiscordWebhookProvisioner:
    def __init__(
        self,
        bot_token: str,
        timeout: float = 10.0,
        *,
        base_url: str = "https://discord.com/api/v10",
        client: httpx.Client | None = None,
    ) -> None:
        if not bot_token:
            raise DiscordWebhookError("DISCORD_BOT_TOKEN is required for provisioning")
        self.bot_token = bot_token
        self.timeout = timeout
        self.base_url = base_url.rstrip("/")
        self._client = client

    def list_channel_webhooks(self, channel_id: str) -> list[dict[str, Any]]:
        response = self._request("GET", f"/channels/{channel_id}/webhooks")
        try:
            data = response.json()
        except ValueError as exc:
            raise DiscordWebhookError("Discord returned invalid webhook list JSON") from exc
        if not isinstance(data, list):
            raise DiscordWebhookError("Discord returned a non-list webhook payload")
        return [item for item in data if isinstance(item, dict)]

    def create_webhook(self, channel_id: str, name: str) -> dict[str, Any]:
        response = self._request(
            "POST",
            f"/channels/{channel_id}/webhooks",
            json={"name": name},
        )
        try:
            data = response.json()
        except ValueError as exc:
            raise DiscordWebhookError("Discord returned invalid webhook JSON") from exc
        if not isinstance(data, dict):
            raise DiscordWebhookError("Discord returned a non-object webhook payload")
        return data

    def ensure_webhook(self, channel_id: str, name: str) -> dict[str, Any]:
        for webhook in self.list_channel_webhooks(channel_id):
            if webhook.get("name") == name:
                return webhook
        return self.create_webhook(channel_id, name)

    def provision_from_channels_config(
        self,
        config_path: str | Path,
        output_path: str | Path,
        reference: ApiFootballReference,
        *,
        dry_run: bool = True,
        only_competition: str | None = None,
        only_channel: str | None = None,
    ) -> list[ProvisionedWebhook]:
        channels = load_discord_channels_config(config_path, reference)
        routes = provision_webhooks(
            channels,
            provisioner=None if dry_run else self,
            dry_run=dry_run,
            only_competition=only_competition,
            only_channel=only_channel,
        )
        if not dry_run:
            write_local_webhooks_config(output_path, routes)
        return routes

    def _request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        headers = kwargs.pop("headers", {})
        headers["Authorization"] = f"Bot {self.bot_token}"
        url = f"{self.base_url}{path}"
        if self._client is not None:
            response = self._client.request(method, url, headers=headers, **kwargs)
        else:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.request(method, url, headers=headers, **kwargs)
        if response.status_code >= 400:
            raise DiscordWebhookError(
                "Discord webhook provisioning failed",
                status_code=response.status_code,
                response_text=response.text[:200],
            )
        return response


class DiscordBotClient(DiscordWebhookProvisioner):
    """Backward-compatible alias for the provisioning client."""


def provision_webhooks(
    channels_config: DiscordChannelsConfig,
    *,
    provisioner: DiscordWebhookProvisioner | None = None,
    bot_client: DiscordWebhookProvisioner | None = None,
    dry_run: bool = True,
    only_competition: str | None = None,
    only_channel: str | None = None,
) -> list[ProvisionedWebhook]:
    client = provisioner or bot_client
    results: list[ProvisionedWebhook] = []
    for competition in channels_config.competitions.values():
        if only_competition and competition.competition_key != only_competition:
            continue
        if not competition.enabled:
            continue
        for channel_key, channel in competition.channels.items():
            if only_channel and channel_key != only_channel:
                continue
            if not channel.enabled or not channel.channel_id or not channel.webhook_name:
                continue
            if dry_run:
                webhook_url = None
                status = "dry_run"
            else:
                if client is None:
                    raise DiscordWebhookError("DISCORD_BOT_TOKEN is required for provisioning")
                payload = client.ensure_webhook(channel.channel_id, channel.webhook_name)
                webhook_url = str(payload.get("url") or "") or None
                status = "reused_or_created"
            results.append(
                ProvisionedWebhook(
                    competition_key=competition.competition_key,
                    league_id=competition.league_id,
                    season=competition.season,
                    channel_key=channel_key,
                    channel_id=channel.channel_id,
                    webhook_name=channel.webhook_name,
                    webhook_url=webhook_url,
                    status=status,
                )
            )
    return results


def write_local_webhooks_config(path: str | Path, routes: list[ProvisionedWebhook]) -> None:
    grouped: dict[str, dict[str, Any]] = {}
    for route in routes:
        if not route.webhook_url:
            continue
        competition = grouped.setdefault(route.competition_key, {})
        competition[route.channel_key] = {
            "webhook_url": route.webhook_url,
            "enabled": True,
            "webhook_name": route.webhook_name,
        }
    payload = {"webhooks": grouped}
    try:
        import yaml  # type: ignore[import-untyped]
    except ModuleNotFoundError:
        text = json.dumps(payload, indent=2, sort_keys=False) + "\n"
    else:
        text = yaml.safe_dump(payload, sort_keys=False, allow_unicode=True)
    resolved = Path(path)
    resolved.parent.mkdir(parents=True, exist_ok=True)
    resolved.write_text(text, encoding="utf-8")
