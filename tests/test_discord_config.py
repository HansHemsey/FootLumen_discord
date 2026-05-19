from __future__ import annotations

from pathlib import Path

import pytest

from football_predictor.discord.config import (
    DiscordChannelsConfig,
    DiscordWebhookRouteConfig,
    DiscordWebhooksConfig,
    load_discord_channels_config,
    load_discord_webhooks_config,
)
from football_predictor.discord.exceptions import DiscordRoutingError
from football_predictor.discord.router import resolve_discord_route
from football_predictor.reference.loaders import load_api_football_reference
from football_predictor.utils.exceptions import ReferenceLookupError


def test_discord_example_configs_validate_against_reference(reference_path: Path) -> None:
    reference = load_api_football_reference(reference_path)
    channels = load_discord_channels_config("config/discord_channels.example.yaml", reference)
    webhooks = load_discord_webhooks_config("config/discord_webhooks.example.yaml", reference)

    assert set(channels.competitions) == {
        "cdm_2026",
        "ligue1",
        "premier_league",
        "liga",
        "bundesliga",
        "serie_a",
    }
    assert channels.find_competition(competition_key="ligue1").league_id == 61
    assert channels.find_competition(competition_key="ligue_1").competition_key == "ligue1"
    assert channels.find_competition(league_id=39, season=2025).competition_key == (
        "premier_league"
    )
    assert channels.find_global_channel("predictions_staff") is not None
    assert all(route.webhook_url is None for route in webhooks.routes)


def test_discord_webhook_env_is_resolved(tmp_path: Path, reference_path: Path) -> None:
    reference = load_api_football_reference(reference_path)
    config = tmp_path / "discord_webhooks.yaml"
    config.write_text(
        """
webhooks:
  ligue1:
    predictions:
      webhook_url_env: DISCORD_WEBHOOK_LIGUE1_PREDICTIONS
      enabled: true
""",
        encoding="utf-8",
    )

    webhooks = load_discord_webhooks_config(
        config,
        reference,
        env={"DISCORD_WEBHOOK_LIGUE1_PREDICTIONS": "https://example.invalid/l1"},
    )
    route = webhooks.find_route(
        competition_key="ligue1",
        league_id=None,
        season=2025,
        channel_key="predictions",
    )

    assert route is not None
    assert route.webhook_url == "https://example.invalid/l1"


def test_global_weekly_score_webhook_route_is_not_treated_as_competition(
    tmp_path: Path,
    reference_path: Path,
) -> None:
    reference = load_api_football_reference(reference_path)
    config = tmp_path / "discord_webhooks.yaml"
    config.write_text(
        """
webhooks:
  global:
    score_pronos_semaine:
      webhook_url_env: DISCORD_WEBHOOK_WEEKLY_SCORE
      enabled: true
""",
        encoding="utf-8",
    )

    webhooks = load_discord_webhooks_config(
        config,
        reference,
        env={"DISCORD_WEBHOOK_WEEKLY_SCORE": "https://example.invalid/weekly-score"},
    )
    route = webhooks.find_route(
        competition_key=None,
        league_id=None,
        season=None,
        channel_key="score_pronos_semaine",
    )

    assert route is not None
    assert route.competition_key == "global"
    assert route.league_id is None
    assert route.season is None
    assert route.webhook_url == "https://example.invalid/weekly-score"


def test_global_predictions_staff_webhook_route_is_not_treated_as_competition(
    tmp_path: Path,
    reference_path: Path,
) -> None:
    reference = load_api_football_reference(reference_path)
    config = tmp_path / "discord_webhooks.yaml"
    config.write_text(
        """
webhooks:
  global:
    predictions_staff:
      webhook_url_env: DISCORD_WEBHOOK_PREDICTIONS_STAFF
      enabled: true
""",
        encoding="utf-8",
    )

    webhooks = load_discord_webhooks_config(
        config,
        reference,
        env={"DISCORD_WEBHOOK_PREDICTIONS_STAFF": "https://example.invalid/staff"},
    )
    route = webhooks.find_route(
        competition_key=None,
        league_id=None,
        season=None,
        channel_key="predictions_staff",
    )

    assert route is not None
    assert route.competition_key == "global"
    assert route.league_id is None
    assert route.season is None
    assert route.webhook_url == "https://example.invalid/staff"


def test_discord_channel_config_season_null_matches_future_seasons(
    tmp_path: Path,
    reference_path: Path,
) -> None:
    reference = load_api_football_reference(reference_path)
    config = tmp_path / "discord_channels.yaml"
    config.write_text(
        """
competitions:
  ligue1:
    reference_key: ligue_1
    league_id: 61
    season: null
    display_name: "Ligue 1"
    enabled: true
    channels:
      classement:
        channel_id: "synthetic-channel"
        webhook_name: "synthetic-webhook"
        enabled: true
""",
        encoding="utf-8",
    )

    channels = load_discord_channels_config(config, reference)
    route = resolve_discord_route(
        channels_config=channels,
        webhooks_config=DiscordWebhooksConfig(routes=[]),
        league_id=61,
        season=2026,
        channel_key="classement",
        message_type="standings",
        allow_missing_webhook=True,
    )

    assert channels.find_competition(league_id=61, season=2026).competition_key == "ligue1"
    assert route.competition_key == "ligue1"
    assert route.season is None


def test_skipped_prediction_message_types_route_to_global_staff_channel() -> None:
    webhooks = DiscordWebhooksConfig(
        routes=[
            DiscordWebhookRouteConfig(
                competition_key="global",
                channel_key="predictions_staff",
                webhook_url="https://example.invalid/staff",
            )
        ]
    )

    prediction_route = resolve_discord_route(
        channels_config=None,
        webhooks_config=webhooks,
        message_type="prediction_skipped",
    )
    ou_route = resolve_discord_route(
        channels_config=None,
        webhooks_config=webhooks,
        message_type="ou_prediction_skipped",
    )

    assert prediction_route.channel_key == "predictions_staff"
    assert ou_route.channel_key == "predictions_staff"


def test_global_staff_route_wins_even_when_competition_is_provided(reference_path: Path) -> None:
    reference = load_api_football_reference(reference_path)
    channels = load_discord_channels_config("config/discord_channels.example.yaml", reference)
    webhooks = DiscordWebhooksConfig(
        routes=[
            DiscordWebhookRouteConfig(
                competition_key="global",
                channel_key="predictions_staff",
                webhook_url="https://example.invalid/staff",
            )
        ]
    )

    route = resolve_discord_route(
        channels_config=channels,
        webhooks_config=webhooks,
        competition_key="ligue1",
        channel_key="predictions_staff",
        message_type="prediction_skipped",
    )

    assert route.competition_key == "global"
    assert route.league_id is None
    assert route.season is None
    assert route.channel_key == "predictions_staff"


def test_global_staff_route_can_resolve_without_channel_metadata() -> None:
    webhooks = DiscordWebhooksConfig(
        routes=[
            DiscordWebhookRouteConfig(
                competition_key="global",
                channel_key="predictions_staff",
                webhook_url="https://example.invalid/staff",
            )
        ]
    )

    route = resolve_discord_route(
        channels_config=DiscordChannelsConfig(competitions={}),
        webhooks_config=webhooks,
        channel_key="predictions_staff",
        message_type="prediction_skipped",
    )

    assert route.competition_key == "global"
    assert route.channel_key == "predictions_staff"
    assert route.webhook_url == "https://example.invalid/staff"


def test_discord_config_rejects_unknown_league_id(
    tmp_path: Path,
    reference_path: Path,
) -> None:
    reference = load_api_football_reference(reference_path)
    config = tmp_path / "discord_channels.yaml"
    config.write_text(
        """
competitions:
  synthetic_unknown:
    reference_key: synthetic_unknown
    league_id: -999
    season: 2099
    display_name: "Synthetic Unknown"
    enabled: true
    channels:
      predictions:
        channel_name: "synthetic"
        channel_id: "synthetic-channel"
        webhook_name: "synthetic-webhook"
        enabled: true
""",
        encoding="utf-8",
    )

    with pytest.raises(ReferenceLookupError):
        load_discord_channels_config(config, reference)


def test_discord_webhook_config_rejects_unknown_competition_key(
    tmp_path: Path,
    reference_path: Path,
) -> None:
    reference = load_api_football_reference(reference_path)
    config = tmp_path / "discord_webhooks.yaml"
    config.write_text(
        """
webhooks:
  unknown_competition:
    predictions:
      webhook_url_env: DISCORD_WEBHOOK_UNKNOWN
      enabled: true
""",
        encoding="utf-8",
    )

    with pytest.raises(ReferenceLookupError):
        load_discord_webhooks_config(config, reference)


def test_discord_config_rejects_invalid_channel_key(
    tmp_path: Path,
    reference_path: Path,
) -> None:
    reference = load_api_football_reference(reference_path)
    config = tmp_path / "discord_channels.yaml"
    config.write_text(
        """
competitions:
  ligue1:
    reference_key: ligue_1
    league_id: 61
    season: 2025
    display_name: "Ligue 1"
    enabled: true
    channels:
      synthetic_invalid:
        channel_id: "synthetic-channel"
        webhook_name: "synthetic-webhook"
        enabled: true
""",
        encoding="utf-8",
    )

    with pytest.raises(DiscordRoutingError):
        load_discord_channels_config(config, reference)


def test_placeholder_webhook_detected_in_local_config(reference_path: Path) -> None:
    reference = load_api_football_reference(reference_path)

    with pytest.raises(DiscordRoutingError):
        load_discord_webhooks_config(
            "config/discord_webhooks.example.yaml",
            reference,
            reject_placeholders=True,
        )


def test_example_webhooks_config_contains_no_real_discord_url() -> None:
    text = Path("config/discord_webhooks.example.yaml").read_text(encoding="utf-8")

    assert "https://discord.com/api/webhooks" not in text
    assert "REPLACE_WITH_WEBHOOK_URL" in text
    assert "DISCORD_WEBHOOK_PREDICTIONS_STAFF" in text


def test_discord_local_configs_are_gitignored() -> None:
    text = Path(".gitignore").read_text(encoding="utf-8")

    assert "config/discord_webhooks.local.yaml" in text
    assert "config/discord_channels.local.yaml" in text
    assert "*.secrets.yaml" in text
