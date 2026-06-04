from __future__ import annotations

from pathlib import Path

import pytest

from football_predictor.discord.config import (
    DiscordWebhookRouteConfig,
    DiscordWebhooksConfig,
    load_discord_channels_config,
    load_discord_webhooks_config,
)
from football_predictor.discord.exceptions import DiscordRoutingError
from football_predictor.discord.router import resolve_discord_route
from football_predictor.reference.loaders import load_api_football_reference


def _write_webhooks(path: Path) -> Path:
    path.write_text(
        """
webhooks:
  ligue1:
    predictions:
      webhook_url: "https://example.invalid/ligue1-predictions"
      enabled: true
    resultats:
      webhook_url: "https://example.invalid/ligue1-resultats"
      enabled: true
    matchs_du_jour:
      webhook_url: "https://example.invalid/ligue1-matchs"
      enabled: true
    discussions:
      webhook_url: "https://example.invalid/ligue1-discussions"
      enabled: true
  premier_league:
    resultats:
      webhook_url: "https://example.invalid/pl-resultats"
      enabled: true
  cdm_2026:
    calendrier:
      webhook_url: "https://example.invalid/cdm-calendrier"
      enabled: true
""",
        encoding="utf-8",
    )
    return path


def _write_channels(
    path: Path,
    *,
    competition_enabled: bool = True,
    predictions_enabled: bool = True,
    discussions_enabled: bool = True,
) -> Path:
    path.write_text(
        f"""
competitions:
  ligue1:
    reference_key: ligue_1
    league_id: 61
    season: 2025
    display_name: "Ligue 1"
    enabled: {str(competition_enabled).lower()}
    channels:
      predictions:
        channel_name: "predictions"
        channel_id: "synthetic-predictions"
        webhook_name: "football-predictor-ligue1-predictions"
        enabled: {str(predictions_enabled).lower()}
      discussions:
        channel_name: "discussions"
        channel_id: "synthetic-discussions"
        webhook_name: "football-predictor-ligue1-discussions"
        enabled: {str(discussions_enabled).lower()}
""",
        encoding="utf-8",
    )
    return path


def test_router_routes_prediction_by_competition_key(
    tmp_path: Path,
    reference_path: Path,
) -> None:
    reference = load_api_football_reference(reference_path)
    channels = load_discord_channels_config("config/discord_channels.example.yaml", reference)
    webhooks = load_discord_webhooks_config(_write_webhooks(tmp_path / "webhooks.yaml"), reference)

    route = resolve_discord_route(
        channels_config=channels,
        webhooks_config=webhooks,
        competition_key="ligue1",
        message_type="prediction",
    )

    assert route.competition_key == "ligue1"
    assert route.league_id == 61
    assert route.season == 2025
    assert route.channel_key == "predictions"
    assert route.webhook_hash is not None
    assert route.webhook_url == "https://example.invalid/ligue1-predictions"


def test_router_routes_by_league_id_and_message_type(
    tmp_path: Path,
    reference_path: Path,
) -> None:
    reference = load_api_football_reference(reference_path)
    channels = load_discord_channels_config("config/discord_channels.example.yaml", reference)
    webhooks = load_discord_webhooks_config(_write_webhooks(tmp_path / "webhooks.yaml"), reference)

    route = resolve_discord_route(
        channels_config=channels,
        webhooks_config=webhooks,
        league_id=39,
        season=2025,
        message_type="result",
    )

    assert route.competition_key == "premier_league"
    assert route.channel_key == "resultats"
    assert route.webhook_url == "https://example.invalid/pl-resultats"


def test_router_routes_world_cup_calendar(tmp_path: Path, reference_path: Path) -> None:
    reference = load_api_football_reference(reference_path)
    channels = load_discord_channels_config("config/discord_channels.example.yaml", reference)
    webhooks = load_discord_webhooks_config(_write_webhooks(tmp_path / "webhooks.yaml"), reference)

    route = resolve_discord_route(
        channels_config=channels,
        webhooks_config=webhooks,
        competition_key="cdm_2026",
        message_type="schedule",
    )

    assert route.competition_key == "cdm_2026"
    assert route.channel_key == "calendrier"


def test_router_routes_world_cup_combo_messages_to_global_staff() -> None:
    webhooks = DiscordWebhooksConfig(
        routes=[
            DiscordWebhookRouteConfig(
                competition_key="global",
                channel_key="predictions_staff",
                webhook_url="https://example.invalid/staff",
            )
        ]
    )

    for message_type in (
        "worldcup_combo_public",
        "worldcup_combo_locked",
        "worldcup_combo_staff",
        "worldcup_combo_watchlist",
        "worldcup_combo_no_bet",
    ):
        route = resolve_discord_route(
            channels_config=None,
            webhooks_config=webhooks,
            competition_key="cdm_2026",
            league_id=1,
            season=2026,
            message_type=message_type,
        )
        assert route.channel_key == "predictions_staff"
        assert route.competition_key == "global"


def test_router_maps_daily_matches_to_matchs_du_jour(
    tmp_path: Path,
    reference_path: Path,
) -> None:
    reference = load_api_football_reference(reference_path)
    channels = load_discord_channels_config("config/discord_channels.example.yaml", reference)
    webhooks = load_discord_webhooks_config(_write_webhooks(tmp_path / "webhooks.yaml"), reference)

    route = resolve_discord_route(
        channels_config=channels,
        webhooks_config=webhooks,
        competition_key="ligue1",
        message_type="daily_matches",
    )

    assert route.channel_key == "matchs_du_jour"


def test_router_refuses_discussions_by_default(
    tmp_path: Path,
    reference_path: Path,
) -> None:
    reference = load_api_football_reference(reference_path)
    channels = load_discord_channels_config(
        _write_channels(tmp_path / "channels.yaml"),
        reference,
    )
    webhooks = load_discord_webhooks_config(_write_webhooks(tmp_path / "webhooks.yaml"), reference)

    with pytest.raises(DiscordRoutingError):
        resolve_discord_route(
            channels_config=channels,
            webhooks_config=webhooks,
            competition_key="ligue1",
            message_type="discussion",
        )

    route = resolve_discord_route(
        channels_config=channels,
        webhooks_config=webhooks,
        competition_key="ligue1",
        message_type="discussion",
        allow_discussions=True,
    )
    assert route.channel_key == "discussions"


def test_router_blocks_disabled_competition_or_channel(
    tmp_path: Path,
    reference_path: Path,
) -> None:
    reference = load_api_football_reference(reference_path)
    webhooks = load_discord_webhooks_config(_write_webhooks(tmp_path / "webhooks.yaml"), reference)
    disabled_comp = load_discord_channels_config(
        _write_channels(tmp_path / "disabled_comp.yaml", competition_enabled=False),
        reference,
    )
    disabled_channel = load_discord_channels_config(
        _write_channels(tmp_path / "disabled_channel.yaml", predictions_enabled=False),
        reference,
    )

    with pytest.raises(DiscordRoutingError):
        resolve_discord_route(
            channels_config=disabled_comp,
            webhooks_config=webhooks,
            competition_key="ligue1",
            message_type="prediction",
        )
    with pytest.raises(DiscordRoutingError):
        resolve_discord_route(
            channels_config=disabled_channel,
            webhooks_config=webhooks,
            competition_key="ligue1",
            message_type="prediction",
        )


def test_router_missing_webhook_and_legacy_fallback(reference_path: Path) -> None:
    reference = load_api_football_reference(reference_path)
    channels = load_discord_channels_config("config/discord_channels.example.yaml", reference)

    with pytest.raises(DiscordRoutingError):
        resolve_discord_route(
            channels_config=channels,
            webhooks_config=DiscordWebhooksConfig([]),
            competition_key="ligue1",
            message_type="result",
        )

    route = resolve_discord_route(
        channels_config=channels,
        webhooks_config=DiscordWebhooksConfig([]),
        competition_key="ligue1",
        message_type="prediction",
        legacy_webhook_url="https://example.invalid/legacy",
    )

    assert route.source == "legacy"
    assert route.webhook_url == "https://example.invalid/legacy"
