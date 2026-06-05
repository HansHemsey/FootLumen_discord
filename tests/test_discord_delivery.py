from __future__ import annotations

from pathlib import Path

import httpx
import pytest
from sqlalchemy import select

from football_predictor.db import models
from football_predictor.db.init_db import create_db_and_tables
from football_predictor.db.session import create_session_factory, session_scope
from football_predictor.discord.config import (
    load_discord_channels_config,
    load_discord_webhooks_config,
)
from football_predictor.discord.exceptions import DiscordWebhookError
from football_predictor.discord.service import DiscordDeliveryService
from football_predictor.reference.loaders import load_api_football_reference


def _write_webhooks(path: Path) -> Path:
    path.write_text(
        """
webhooks:
  ligue1:
    predictions:
      webhook_url: "https://example.invalid/l1"
      enabled: true
""",
        encoding="utf-8",
    )
    return path


def test_delivery_dry_run_persists_route(reference_path: Path, tmp_path: Path) -> None:
    reference = load_api_football_reference(reference_path)
    channels = load_discord_channels_config("config/discord_channels.example.yaml", reference)
    webhooks = load_discord_webhooks_config("config/discord_webhooks.example.yaml", reference)
    engine = create_db_and_tables(f"sqlite:///{tmp_path / 'discord.db'}")
    session_factory = create_session_factory(engine)

    with session_scope(session_factory) as session:
        result = DiscordDeliveryService(
            session,
            channels_config=channels,
            webhooks_config=webhooks,
        ).send_markdown(
            "```md\nsynthetic\n```",
            competition_key="ligue1",
            message_type="prediction",
            dry_run=True,
        )

    with session_scope(session_factory) as session:
        row = session.scalar(select(models.DiscordMessage))

    assert result.status == "dry_run"
    assert row is not None
    assert row.competition_key == "ligue1"
    assert row.league_id == 61
    assert row.season == 2025
    assert row.channel_key == "predictions"
    assert row.message_type == "prediction"
    assert row.dry_run is True
    assert row.route_json["webhook_configured"] is False
    assert row.payload_json["content"] == "```md\nsynthetic\n```"


def test_delivery_sends_with_mocked_http_and_dedupes(
    reference_path: Path,
    tmp_path: Path,
) -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(204)

    reference = load_api_football_reference(reference_path)
    channels = load_discord_channels_config("config/discord_channels.example.yaml", reference)
    webhooks = load_discord_webhooks_config(
        _write_webhooks(tmp_path / "discord_webhooks.yaml"),
        reference,
    )
    engine = create_db_and_tables(f"sqlite:///{tmp_path / 'discord.db'}")
    session_factory = create_session_factory(engine)

    with (
        httpx.Client(transport=httpx.MockTransport(handler)) as client,
        session_scope(session_factory) as session,
    ):
        service = DiscordDeliveryService(
            session,
            channels_config=channels,
            webhooks_config=webhooks,
            http_client=client,
        )
        first = service.send_markdown(
            "```md\nsynthetic\n```",
            competition_key="ligue1",
            message_type="prediction",
        )
        second = service.send_markdown(
            "```md\nsynthetic\n```",
            competition_key="ligue1",
            message_type="prediction",
        )

    with session_scope(session_factory) as session:
        statuses = [row.status for row in session.execute(select(models.DiscordMessage)).scalars()]

    assert first.status == "sent"
    assert second.status == "duplicate_skipped"
    assert calls == 1
    assert statuses == ["sent", "duplicate_skipped"]


def test_delivery_wait_stores_discord_api_message_id(
    reference_path: Path,
    tmp_path: Path,
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.query.decode() == "wait=true"
        return httpx.Response(200, json={"id": "api-message-1"})

    reference = load_api_football_reference(reference_path)
    channels = load_discord_channels_config("config/discord_channels.example.yaml", reference)
    webhooks = load_discord_webhooks_config(
        _write_webhooks(tmp_path / "discord_webhooks.yaml"),
        reference,
    )
    engine = create_db_and_tables(f"sqlite:///{tmp_path / 'discord_wait.db'}")
    session_factory = create_session_factory(engine)

    with (
        httpx.Client(transport=httpx.MockTransport(handler)) as client,
        session_scope(session_factory) as session,
    ):
        result = DiscordDeliveryService(
            session,
            channels_config=channels,
            webhooks_config=webhooks,
            http_client=client,
        ).send_markdown(
            "```md\nsynthetic\n```",
            competition_key="ligue1",
            message_type="prediction",
            wait=True,
        )

    with session_scope(session_factory) as session:
        row = session.scalar(select(models.DiscordMessage))

    assert result.discord_api_message_id == "api-message-1"
    assert row is not None
    assert row.payload_json["discord_api_message_id"] == "api-message-1"


def test_delivery_print_only_does_not_send(reference_path: Path, tmp_path: Path) -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(204)

    reference = load_api_football_reference(reference_path)
    channels = load_discord_channels_config("config/discord_channels.example.yaml", reference)
    webhooks = load_discord_webhooks_config(
        _write_webhooks(tmp_path / "discord_webhooks.yaml"),
        reference,
    )
    engine = create_db_and_tables(f"sqlite:///{tmp_path / 'discord.db'}")
    session_factory = create_session_factory(engine)

    with (
        httpx.Client(transport=httpx.MockTransport(handler)) as client,
        session_scope(session_factory) as session,
    ):
        result = DiscordDeliveryService(
            session,
            channels_config=channels,
            webhooks_config=webhooks,
            http_client=client,
        ).send_markdown(
            "```md\nsynthetic\n```",
            competition_key="ligue1",
            message_type="prediction",
            print_only=True,
        )

    assert result.status == "print_only"
    assert calls == 0


def test_delivery_blocks_secret_markdown_before_webhook(
    reference_path: Path,
    tmp_path: Path,
) -> None:
    calls = 0
    webhook = "https://discord.com/api/" + "webhooks/123456789012345678/" + ("a" * 48)

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(204)

    reference = load_api_football_reference(reference_path)
    channels = load_discord_channels_config("config/discord_channels.example.yaml", reference)
    webhooks = load_discord_webhooks_config(
        _write_webhooks(tmp_path / "discord_webhooks.yaml"),
        reference,
    )
    engine = create_db_and_tables(f"sqlite:///{tmp_path / 'discord_block.db'}")
    session_factory = create_session_factory(engine)

    with (
        httpx.Client(transport=httpx.MockTransport(handler)) as client,
        session_scope(session_factory) as session,
        pytest.raises(DiscordWebhookError),
    ):
        DiscordDeliveryService(
            session,
            channels_config=channels,
            webhooks_config=webhooks,
            http_client=client,
        ).send_markdown(
            "```md\nsecret " + webhook + "\n```",
            competition_key="ligue1",
            message_type="prediction",
        )

    with session_scope(session_factory) as session:
        row = session.scalar(select(models.DiscordMessage))

    assert calls == 0
    assert row is not None
    assert row.status == "blocked_secret"
    assert webhook not in row.message_markdown
    assert webhook not in str(row.payload_json)
    assert "<redacted>" in row.message_markdown
