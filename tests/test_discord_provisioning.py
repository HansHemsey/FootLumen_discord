from __future__ import annotations

from pathlib import Path

import httpx
import pytest

from football_predictor.discord.config import load_discord_channels_config
from football_predictor.discord.exceptions import DiscordWebhookError
from football_predictor.discord.provisioning import (
    DiscordWebhookProvisioner,
    ProvisionedWebhook,
    provision_webhooks,
    write_local_webhooks_config,
)
from football_predictor.reference.loaders import load_api_football_reference


def _write_channels(path: Path) -> Path:
    path.write_text(
        """
competitions:
  ligue1:
    reference_key: ligue_1
    league_id: 61
    season: 2025
    display_name: "Ligue 1"
    enabled: true
    channels:
      predictions:
        channel_name: "predictions"
        channel_id: "synthetic-channel"
        webhook_name: "football-predictor-ligue1-predictions"
        enabled: true
""",
        encoding="utf-8",
    )
    return path


def test_list_channel_webhooks_mocked() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.url.path.endswith("/channels/synthetic-channel/webhooks")
        return httpx.Response(200, json=[{"name": "existing"}])

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        webhooks = DiscordWebhookProvisioner(
            "synthetic-token",
            client=client,
        ).list_channel_webhooks("synthetic-channel")

    assert webhooks == [{"name": "existing"}]


def test_create_webhook_mocked_without_logging_token() -> None:
    captured: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["authorization"] = request.headers["Authorization"]
        return httpx.Response(
            200,
            json={
                "name": "created",
                "url": "https://example.invalid/generated-webhook-secret",
            },
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        payload = DiscordWebhookProvisioner(
            "synthetic-token",
            client=client,
        ).create_webhook("synthetic-channel", "created")

    assert captured["authorization"] == "Bot synthetic-token"
    assert payload["url"] == "https://example.invalid/generated-webhook-secret"


def test_ensure_webhook_reuses_existing() -> None:
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request.method)
        return httpx.Response(
            200,
            json=[
                {
                    "name": "football-predictor-ligue1-predictions",
                    "url": "https://example.invalid/existing",
                }
            ],
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        payload = DiscordWebhookProvisioner("synthetic-token", client=client).ensure_webhook(
            "synthetic-channel",
            "football-predictor-ligue1-predictions",
        )

    assert payload["url"] == "https://example.invalid/existing"
    assert calls == ["GET"]


def test_ensure_webhook_creates_if_absent() -> None:
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request.method)
        if request.method == "GET":
            return httpx.Response(200, json=[])
        return httpx.Response(
            200,
            json={
                "name": "football-predictor-ligue1-predictions",
                "url": "https://example.invalid/created",
            },
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        payload = DiscordWebhookProvisioner("synthetic-token", client=client).ensure_webhook(
            "synthetic-channel",
            "football-predictor-ligue1-predictions",
        )

    assert payload["url"] == "https://example.invalid/created"
    assert calls == ["GET", "POST"]


def test_provision_from_channels_config_writes_local_config(
    tmp_path: Path,
    reference_path: Path,
) -> None:
    reference = load_api_football_reference(reference_path)
    channels_path = _write_channels(tmp_path / "channels.yaml")

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "GET":
            return httpx.Response(200, json=[])
        return httpx.Response(
            200,
            json={
                "name": "football-predictor-ligue1-predictions",
                "url": "https://example.invalid/generated",
            },
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        routes = DiscordWebhookProvisioner(
            "synthetic-token",
            client=client,
        ).provision_from_channels_config(
            channels_path,
            tmp_path / "discord_webhooks.local.yaml",
            reference,
            dry_run=False,
        )

    text = (tmp_path / "discord_webhooks.local.yaml").read_text(encoding="utf-8")
    assert len(routes) == 1
    assert "https://example.invalid/generated" in text


def test_provision_dry_run_does_not_require_client(
    tmp_path: Path,
    reference_path: Path,
) -> None:
    reference = load_api_football_reference(reference_path)
    channels = load_discord_channels_config(_write_channels(tmp_path / "channels.yaml"), reference)

    routes = provision_webhooks(channels, dry_run=True)

    assert len(routes) == 1
    assert routes[0].status == "dry_run"
    assert routes[0].webhook_url is None


def test_write_local_webhooks_config_and_absent_token_error(tmp_path: Path) -> None:
    with pytest.raises(DiscordWebhookError):
        DiscordWebhookProvisioner("")

    output = tmp_path / "discord_webhooks.local.yaml"
    write_local_webhooks_config(
        output,
        [
            ProvisionedWebhook(
                competition_key="ligue1",
                league_id=61,
                season=2025,
                channel_key="predictions",
                channel_id="synthetic-channel",
                webhook_name="synthetic-webhook",
                webhook_url="https://example.invalid/generated",
            )
        ],
    )
    assert output.read_text(encoding="utf-8").strip()
    assert output.stat().st_mode & 0o777 == 0o600


def test_provisioning_error_masks_secret_response_text() -> None:
    webhook = "https://discord.com/api/webhooks/123456/synthetic-secret"
    token = "synthetic-token-value"

    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            401,
            text=f"token={token} Bearer {token} {webhook}",
        )

    with (
        httpx.Client(transport=httpx.MockTransport(handler)) as client,
        pytest.raises(DiscordWebhookError) as exc_info,
    ):
        DiscordWebhookProvisioner("synthetic-token", client=client).create_webhook(
            "synthetic-channel",
            "synthetic-webhook",
        )

    rendered = str(exc_info.value)
    assert webhook not in rendered
    assert token not in rendered
    assert "<redacted>" in rendered
