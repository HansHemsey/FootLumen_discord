"""Discord route resolution by competition, channel and message type."""

from __future__ import annotations

from dataclasses import dataclass, field

from football_predictor.discord.config import DiscordChannelsConfig, DiscordWebhooksConfig
from football_predictor.discord.exceptions import DiscordRoutingError
from football_predictor.utils.secrets import hash_secret

MESSAGE_TYPE_CHANNELS = {
    "standing": "classement",
    "standings": "classement",
    "calendar": "calendrier",
    "schedule": "calendrier",
    "daily_matches": "matchs_du_jour",
    "today_matches": "matchs_du_jour",
    "analysis": "analyses",
    "prediction": "predictions",
    "ou_prediction": "predictions",
    "result": "resultats",
    "results": "resultats",
    "weekly_prediction_score": "score_pronos_semaine",
    "discussion": "discussions",
}


@dataclass(frozen=True)
class DiscordRoute:
    competition_key: str | None
    league_id: int | None
    season: int | None
    channel_key: str
    message_type: str
    webhook_url: str | None = field(default=None, repr=False)
    channel_id: str | None = None
    channel_name: str | None = None
    webhook_name: str | None = None
    source: str = "multi-webhook"

    @property
    def webhook_hash(self) -> str | None:
        return hash_secret(self.webhook_url)

    def safe_dict(self) -> dict[str, object]:
        return {
            "competition_key": self.competition_key,
            "league_id": self.league_id,
            "season": self.season,
            "channel_key": self.channel_key,
            "message_type": self.message_type,
            "channel_id": self.channel_id,
            "channel_name": self.channel_name,
            "webhook_name": self.webhook_name,
            "source": self.source,
            "webhook_hash": self.webhook_hash,
            "webhook_configured": bool(self.webhook_url),
        }


class DiscordChannelRouter:
    def __init__(
        self,
        *,
        channels_config: DiscordChannelsConfig | None = None,
        webhooks_config: DiscordWebhooksConfig | None = None,
        legacy_webhook_url: str | None = None,
    ) -> None:
        self.channels_config = channels_config
        self.webhooks_config = webhooks_config
        self.legacy_webhook_url = legacy_webhook_url

    def resolve(
        self,
        *,
        competition_key: str | None = None,
        league_id: int | None = None,
        season: int | None = None,
        channel_key: str | None = None,
        message_type: str = "prediction",
        allow_discussions: bool = False,
        force: bool = False,
        allow_missing_webhook: bool = False,
    ) -> DiscordRoute:
        resolved_channel = channel_key or MESSAGE_TYPE_CHANNELS.get(message_type)
        if resolved_channel is None:
            raise DiscordRoutingError(f"Unknown Discord message_type={message_type!r}")
        if resolved_channel == "discussions" and not allow_discussions:
            raise DiscordRoutingError("Automated messages to discussions are disabled")

        channel_id = None
        channel_name = None
        webhook_name = None
        competition = None
        if self.channels_config is not None:
            competition = self.channels_config.find_competition(
                competition_key=competition_key,
                league_id=league_id,
                season=season,
            )
            if competition is None:
                channel = self.channels_config.find_global_channel(resolved_channel)
                if channel is None:
                    raise DiscordRoutingError("Unknown Discord competition route")
                competition_key = None
                league_id = None
                season = None
            else:
                if not competition.enabled and not force:
                    raise DiscordRoutingError(
                        f"Discord competition={competition.competition_key} is disabled"
                    )
                channel = competition.channels.get(resolved_channel)
                if channel is None:
                    raise DiscordRoutingError(
                        f"Discord channel={resolved_channel!r} is not configured for "
                        f"competition={competition.competition_key}"
                    )
                competition_key = competition.competition_key
                league_id = competition.league_id
                season = competition.season
            if not channel.enabled and not force:
                raise DiscordRoutingError(f"Discord channel={resolved_channel!r} is disabled")
            channel_id = channel.channel_id
            channel_name = channel.channel_name
            webhook_name = channel.webhook_name

        route_config = None
        if self.webhooks_config is not None:
            route_config = self.webhooks_config.find_route(
                competition_key=competition_key,
                league_id=league_id,
                season=season,
                channel_key=resolved_channel,
            )
        if route_config is not None:
            if not route_config.enabled and not force:
                raise DiscordRoutingError(
                    f"Discord webhook route is disabled for {competition_key}/{resolved_channel}"
                )
            if not route_config.webhook_url:
                if allow_missing_webhook:
                    return DiscordRoute(
                        competition_key=route_config.competition_key,
                        league_id=route_config.league_id or league_id,
                        season=route_config.season or season,
                        channel_key=resolved_channel,
                        message_type=message_type,
                        webhook_url=None,
                        channel_id=channel_id,
                        channel_name=channel_name,
                        webhook_name=route_config.webhook_name or webhook_name,
                        source="unresolved",
                    )
                raise DiscordRoutingError(
                    f"Missing Discord webhook for {competition_key}/{resolved_channel}"
                )
            return DiscordRoute(
                competition_key=route_config.competition_key,
                league_id=route_config.league_id or league_id,
                season=route_config.season or season,
                channel_key=resolved_channel,
                message_type=message_type,
                webhook_url=route_config.webhook_url,
                channel_id=channel_id,
                channel_name=channel_name,
                webhook_name=route_config.webhook_name or webhook_name,
                source="multi-webhook",
            )

        if self.legacy_webhook_url and resolved_channel == "predictions":
            return DiscordRoute(
                competition_key=competition_key,
                league_id=league_id,
                season=season,
                channel_key=resolved_channel,
                message_type=message_type,
                webhook_url=self.legacy_webhook_url,
                channel_id=channel_id,
                channel_name=channel_name,
                webhook_name=webhook_name,
                source="legacy",
            )

        if allow_missing_webhook:
            return DiscordRoute(
                competition_key=competition_key,
                league_id=league_id,
                season=season,
                channel_key=resolved_channel,
                message_type=message_type,
                webhook_url=None,
                channel_id=channel_id,
                channel_name=channel_name,
                webhook_name=webhook_name,
                source="unresolved",
            )
        raise DiscordRoutingError(
            f"Missing Discord webhook for {competition_key}/{resolved_channel}"
        )


def resolve_discord_route(
    *,
    channels_config: DiscordChannelsConfig | None,
    webhooks_config: DiscordWebhooksConfig | None,
    competition_key: str | None = None,
    league_id: int | None = None,
    season: int | None = None,
    channel_key: str | None = None,
    message_type: str = "prediction",
    legacy_webhook_url: str | None = None,
    allow_discussions: bool = False,
    force: bool = False,
    allow_missing_webhook: bool = False,
) -> DiscordRoute:
    return DiscordChannelRouter(
        channels_config=channels_config,
        webhooks_config=webhooks_config,
        legacy_webhook_url=legacy_webhook_url,
    ).resolve(
        competition_key=competition_key,
        league_id=league_id,
        season=season,
        channel_key=channel_key,
        message_type=message_type,
        allow_discussions=allow_discussions,
        force=force,
        allow_missing_webhook=allow_missing_webhook,
    )
